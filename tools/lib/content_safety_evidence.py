"""Bounded evidence and immutable local snapshots. No semantic classification here."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import time
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = 'schemas/story-construction/content-safety-receipt-v1.schema.json'
SCHEMA_SHA256 = 'fbfeacc563c54e3e204728afebf9a0aee98b85810e4f93d3671c2aed355a5aa8'
SIGNER_KEY = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJZDkynhU9W7HUJvvVniwsft8BhUvrtT05dJgrEbsFh'
SIGNER_FINGERPRINT = 'SHA256:zR55HATrI3+mzVZW3uc8MsCxE+g5fyImXdD8X7WKkt4'
INVENTORY_DOMAIN = b'RULES-RESIDUE-SAFETY-INVENTORY-v1\0'
SCOPE_DOMAIN = b'RULES-RESIDUE-SAFETY-SCOPE-v1\0'
MAX_JSON = 1024 * 1024
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
MAX_FILES = 4096
STAGES = {'art_audio', 'region_acceptance', 'cross_region_validation', 'build', 'release_candidate'}
CODE_PATHS = ('tools/lib/content_safety_evidence.py', 'tools/content_safety_control.py',
              'tools/content_safety_consumers.py', 'tools/build_package.py')


class SafetyError(RuntimeError):
    """Admission was denied; no approved result may be inferred."""


def require(condition, message):
    if not condition:
        raise SafetyError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    def check(v):
        require(not isinstance(v, float), 'floating point is not permitted')
        if isinstance(v, dict):
            require(all(isinstance(k, str) for k in v), 'JSON object keys must be strings')
            for x in v.values(): check(x)
        elif isinstance(v, (list, tuple)):
            for x in v: check(x)
    check(value)
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SafetyError('invalid canonical JSON') from exc


def strict_json(data: bytes):
    require(isinstance(data, bytes) and len(data) <= MAX_JSON, 'JSON input exceeds 1 MiB')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    def nonfinite(_): raise SafetyError('nonfinite JSON number')
    try:
        result = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)
        canonical(result)
        return result
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise SafetyError('invalid UTF-8/JSON') from exc


def schema():
    data = (ROOT / SCHEMA_PATH).read_bytes()
    require(sha(data) == SCHEMA_SHA256, 'frozen receipt schema changed')
    return strict_json(data)


def validate_shape(value, definition=None):
    s = schema()
    if definition:
        s = {'$schema': s['$schema'], '$defs': s['$defs'], '$ref': '#/$defs/' + definition}
    errors = sorted(Draft202012Validator(s).iter_errors(value), key=lambda e: str(e.path))
    require(not errors, 'schema: ' + ('; '.join(e.message for e in errors[:3])))


def safe_path(value: str) -> str:
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_./-]{0,239}', value) is not None, 'invalid ASCII relative path')
    parts = value.split('/')
    require(len(parts) <= 16 and all(1 <= len(x) <= 64 and x not in {'.', '..'} and not x.endswith('.') for x in parts), 'path component/depth/alias rejected')
    require('\\' not in value and ':' not in value, 'non-POSIX path rejected')
    return value


def inventory(records, *, allow_empty=False):
    require(isinstance(records, list) and (allow_empty or records) and len(records) <= MAX_FILES, 'inventory count outside bound')
    seen = set(); aliases = set(); total = 0
    for record in records:
        validate_shape(record, 'inventory_member')
        p = safe_path(record['path'])
        require(p not in seen and p.lower() not in aliases, 'duplicate/aliased inventory path')
        seen.add(p); aliases.add(p.lower()); total += record['bytes']
    require(total <= MAX_TOTAL, 'inventory total exceeds 512 MiB')
    return sorted(records, key=lambda x: x['path'].encode('ascii'))


def inventory_root(records):
    return sha(INVENTORY_DOMAIN + canonical(inventory(records, allow_empty=True)))


def scope_digest(scope):
    require(isinstance(scope, dict) and scope, 'empty scope')
    return sha(SCOPE_DOMAIN + canonical(scope))


def validate_scope(stage, value):
    require(isinstance(value, dict), 'scope must be an object')
    kinds = {
        'art_audio': ('media', {'audio': {'consumer','kind','intake'}, 'image': {'consumer','kind','packet','order','asset','references','targets'}}),
        'region_acceptance': ('region', {'consumer','acceptance','region_id','candidate_revision','references','reports','owner_approvals'}),
        'cross_region_validation': ('cross-region', {'consumer','matrix','references','children'}),
        'build': ('build', {'consumer','validation'}),
        'release_candidate': ('rc', {'consumer','dab','references','archive_execution','archive','stage_executions','root_statement'}),
    }
    require(stage in kinds, 'unknown scope stage')
    consumer, keys = kinds[stage]
    require(value.get('consumer') == consumer, 'wrong consumer scope')
    if stage == 'art_audio':
        require(value.get('kind') in keys, 'unknown media scope')
        keys = keys[value['kind']]
    require(set(value) == keys, 'unknown/missing scope fields')
    for field in ('intake','packet','order','asset','acceptance','matrix','dab'):
        if field in value: safe_path(value[field])
    if 'references' in value:
        require(isinstance(value['references'],dict), 'reference index must be an object')
        for ref in value['references'].values(): validate_shape(ref,'reference')
    if stage == 'build': require(value['validation'] in {'full-project','module-registry'}, 'unknown build validation')
    if stage == 'region_acceptance':
        for field in ('region_id','candidate_revision'):
            require(isinstance(value[field],str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',value[field]), 'invalid region identity/revision')
        for field in ('reports','owner_approvals'):
            require(isinstance(value[field],dict), 'report/approval map required')
            for ref in value[field].values(): validate_shape(ref,'reference')
    if stage == 'cross_region_validation':
        require(isinstance(value['children'],dict) and len(value['children']) == 6, 'six scoped child interfaces required')
        for child in value['children'].values():
            require(isinstance(child,dict) and set(child)=={'execution_id','revision','manifest','closure'}, 'unknown child scope fields')
            validate_shape(child['manifest'],'reference')
            require(isinstance(child['closure'],dict), 'child closure map required')
            for ref in child['closure'].values(): validate_shape(ref,'reference')
    canonical(value)
    return value


def utc_seconds(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value) is not None, 'invalid UTC syntax')
    try:
        d = dt.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
        require(d.strftime('%Y-%m-%dT%H:%M:%SZ') == value, 'noncanonical Gregorian UTC')
        return int(d.timestamp())
    except ValueError as exc: raise SafetyError('invalid Gregorian UTC') from exc


def validate_receipt(data: bytes, observed_utc=None):
    r = strict_json(data); validate_shape(r)
    require(r['namespace'] == r['authority']['namespace'], 'namespace mismatch')
    require(r['source']['input_root'] == r['input_root'], 'source input root mismatch')
    require(inventory_root(r['inputs']) == r['input_root'], 'input inventory root mismatch')
    require(inventory_root(r['outputs']) == r['output_root'], 'output inventory root mismatch')
    require(r['review']['producer_task'] != r['review']['reviewer_task'] and r['review']['producer_run'] != r['review']['reviewer_run'], 'self review rejected')
    require((r['stage'] == 'build' and r['phase'] in {'INPUT', 'OUTPUT'}) or (r['stage'] != 'build' and r['phase'] == 'SINGLE'), 'wrong receipt purpose/phase')
    issued, start, end = (utc_seconds(r[x]) for x in ('issued_at', 'not_before', 'expires_at'))
    require(issued <= start < end <= issued + 3600, 'receipt validity interval outside bound')
    if observed_utc is not None:
        require(observed_utc - 2 >= start and observed_utc + 2 < end, 'receipt expired/not yet valid')
    if r['phase'] == 'INPUT': require(not r['outputs'], 'INPUT must not authorize output')
    return r


def _identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _dirfd(path):
    """Open every absolute path component without following links, including root."""
    p = Path(path).absolute()
    require('..' not in p.parts, 'root path alias rejected')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in p.parts[1:]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
        return fd
    except BaseException:
        os.close(fd); raise


def _walk(fd, prefix=''):
    before = _identity(os.fstat(fd)); found = {}
    for name in sorted(os.listdir(fd)):
        p = safe_path(prefix + name)
        s = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(s.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                require(_identity(os.fstat(child)) == _identity(s), 'directory replaced')
                found.update(_walk(child, p + '/'))
            finally: os.close(child)
        else:
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'nonregular/symlink/hardlink input')
            require(stat.S_IMODE(s.st_mode) in {0o644, 0o755}, 'input mode must be 0644/0755')
            found[p] = _identity(s)
        require(len(found) <= MAX_FILES, 'too many closure members')
    require(_identity(os.fstat(fd)) == before, 'input namespace changed')
    return found


def open_member(root_fd, path):
    parts = safe_path(path).split('/'); current = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current); current = new
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
    finally: os.close(current)


def fsync_dir(path):
    fd = _dirfd(path)
    try: os.fsync(fd)
    finally: os.close(fd)


def durable_write(path, data: bytes, *, replace=False):
    p = Path(path)
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(not p.is_symlink(), 'output link rejected')
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_TRUNC if replace else os.O_EXCL)
    fd = os.open(p, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode) and os.fstat(fd).st_nlink == 1, 'nonregular output')
        with os.fdopen(fd, 'wb', closefd=False) as f: f.write(data); f.flush(); os.fsync(fd)
    finally: os.close(fd)
    fsync_dir(p.parent)


class Snapshot:
    """A private, read-only snapshot retaining source and snapshot FDs until commit."""
    def __init__(self, source: Path, records: list, storage: Path):
        self.records = inventory(records)
        self.root = inventory_root(records)
        self.source = Path(source).absolute()
        self.fds = {}; self.source_fd = None; self.directory = None
        try:
            self.source_fd = _dirfd(self.source)
            self.source_identity = _identity(os.fstat(self.source_fd))
            self.names = _walk(self.source_fd)
            require(set(self.names) == {r['path'] for r in records}, 'missing/extra closure files')
            storage.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.directory = Path(tempfile.mkdtemp(prefix='snapshot-', dir=storage))
            for r in self.records:
                original = open_member(self.source_fd, r['path'])
                try:
                    before = os.fstat(original)
                    require(_identity(before) == self.names[r['path']], 'input replaced before copy')
                    require(before.st_size == r['bytes'] and before.st_size <= MAX_FILE, 'input length mismatch')
                    expected_mode = '100755' if stat.S_IMODE(before.st_mode) == 0o755 else '100644'
                    require(expected_mode == r['mode'], 'input mode mismatch')
                    target = self.directory / r['path']; target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    fd = os.open(target, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    self.fds[r['path']] = fd
                    h = hashlib.sha256(); count = 0
                    while chunk := os.read(original, 65536):
                        count += len(chunk); require(count <= r['bytes'], 'input grew')
                        h.update(chunk)
                        view = memoryview(chunk)
                        while view:
                            n = os.write(fd, view); require(n > 0, 'short snapshot write'); view = view[n:]
                    require(count == r['bytes'] and h.hexdigest() == r['sha256'], 'input bytes/hash mismatch')
                    require(_identity(os.fstat(original)) == self.names[r['path']], 'input changed while reading')
                    os.fsync(fd); os.fchmod(fd, 0o400)
                finally: os.close(original)
            for directory, _, _ in os.walk(self.directory, topdown=False):
                fsync_dir(directory); os.chmod(directory, 0o500)
            fsync_dir(storage)
            self.verify()
        except BaseException:
            self.close(); raise

    def bytes(self, path):
        safe_path(path); require(path in self.fds, 'reference not in closure')
        fd = self.fds[path]; s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_size <= MAX_FILE, 'snapshot damaged')
        chunks = []; offset = 0
        while chunk := os.pread(fd, min(65536, s.st_size + 1 - offset), offset):
            chunks.append(chunk); offset += len(chunk)
        data = b''.join(chunks)
        r = next(r for r in self.records if r['path'] == path)
        require(len(data) == r['bytes'] and sha(data) == r['sha256'], 'snapshot bytes changed')
        return data

    def json(self, path): return strict_json(self.bytes(path))

    def reference(self, ref, *, expected_revision=None):
        validate_shape(ref, 'reference'); data = self.bytes(ref['path'])
        require(sha(data) == ref['sha256'], 'reference hash mismatch')
        if expected_revision is not None: require(ref['revision'] == str(expected_revision), 'reference revision mismatch')
        return data

    def verify(self):
        require(self.source_fd is not None, 'snapshot is closed')
        current = _dirfd(self.source)
        try: require(_identity(os.fstat(current)) == self.source_identity, 'source root replaced')
        finally: os.close(current)
        require(_walk(self.source_fd) == self.names, 'input namespace/content metadata changed')
        for r in self.records:
            self.bytes(r['path'])
            fd = open_member(self.source_fd, r['path'])
            try:
                before = _identity(os.fstat(fd)); h = hashlib.sha256(); length = 0
                while chunk := os.read(fd, 65536):
                    length += len(chunk); require(length <= r['bytes'], 'source grew'); h.update(chunk)
                require(before == self.names[r['path']] == _identity(os.fstat(fd)), 'source changed at commit')
                require(length == r['bytes'] and h.hexdigest() == r['sha256'], 'source hash changed at commit')
            finally: os.close(fd)
        return self.root

    def close(self):
        for fd in self.fds.values(): os.close(fd)
        self.fds.clear()
        if self.source_fd is not None: os.close(self.source_fd); self.source_fd = None

    def __enter__(self): return self
    def __exit__(self, *_): self.close()


def describe_directory(root: Path):
    """Inspection only: builds a proposal inventory and grants no authority."""
    fd = _dirfd(root)
    try:
        names = _walk(fd); records = []
        for p, identity in names.items():
            f = open_member(fd, p)
            try:
                h = hashlib.sha256(); length = 0
                while b := os.read(f, 65536):
                    length += len(b); require(length <= MAX_FILE, 'member exceeds 32 MiB'); h.update(b)
                require(_identity(os.fstat(f)) == identity, 'inspection changed')
                records.append({'path':p, 'kind':'regular_file', 'mode':'100755' if stat.S_IMODE(identity[2]) == 0o755 else '100644', 'bytes':length, 'sha256':h.hexdigest()})
            finally: os.close(f)
        require(_walk(fd) == names, 'inspection namespace changed')
        return inventory(records)
    finally: os.close(fd)


def git_bytes(repository: Path, *args):
    env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_OPTIONAL_LOCKS='0')
    p = subprocess.run(['git', '-C', str(repository), *args], env=env, capture_output=True, timeout=30)
    require(p.returncode == 0, 'Git custody verification failed: ' + p.stderr.decode(errors='replace')[:300])
    return p.stdout


def verify_custody(repository: Path, locator: dict, *, trusted_locator: dict):
    validate_shape(locator, 'custody_locator'); safe_path(locator['path'])
    require(locator == trusted_locator, 'statement is not independently received at the operator root')
    require(git_bytes(repository, 'rev-parse', locator['commit']+'^{tree}').decode().strip() == locator['tree'], 'custody tree mismatch')
    tree_entry = git_bytes(repository, 'ls-tree', locator['commit'], '--', locator['path']).decode().strip()
    require(tree_entry == '100644 blob '+locator['blob']+'\t'+locator['path'], 'custody path/blob/mode mismatch')
    with tempfile.TemporaryDirectory(prefix='rr-safety-signature-') as directory:
        allowed = Path(directory)/'allowed-signers'
        allowed.write_text('rules-residue-custody '+SIGNER_KEY+'\n', encoding='ascii')
        output = git_bytes(repository, '-c', 'gpg.format=ssh', '-c', 'gpg.ssh.program=/usr/bin/ssh-keygen', '-c', 'gpg.ssh.allowedSignersFile='+str(allowed),
                           '-c', 'gpg.ssh.revocationFile=/dev/null', 'verify-commit', locator['commit'])
        # The allowed signers file contains only the fixed key. No global trust is used.
    return git_bytes(repository, 'cat-file', 'blob', locator['blob'])


def verify_authority(receipt_raw, report_raw, manifest_raw, locator, repository, trusted_locator):
    r = validate_receipt(receipt_raw)
    statement_raw = verify_custody(repository, locator, trusted_locator=trusted_locator)
    statement = strict_json(statement_raw); validate_shape(statement, 'authority_statement')
    require(statement['receipt_sha256'] == sha(receipt_raw), 'statement receipt hash mismatch')
    review = r['review']
    for field in ('producer_task','producer_run','reviewer_task','reviewer_run','report_sha256','manifest_sha256'):
        require(statement[field] == review[field], 'statement review binding mismatch: '+field)
    require(sha(report_raw) == review['report_sha256'] and sha(manifest_raw) == review['manifest_sha256'], 'report/manifest bytes mismatch')
    # Root registration, not report-shaped prose or same-key signing, establishes acceptance.
    for field in ('namespace','decision'): require(statement[field] == r[field], 'statement decision mismatch')
    for field in ('checkpoint','revocation_epoch'): require(statement[field] == r['authority'][field], 'statement checkpoint mismatch')
    require(r['decision'] == 'ALLOW', 'independent decision is not ALLOW')
    return r


def current_source(input_root, *, project_root=ROOT):
    commit = git_bytes(project_root, 'rev-parse', 'HEAD').decode().strip()
    tree = git_bytes(project_root, 'rev-parse', 'HEAD^{tree}').decode().strip()
    require(not git_bytes(project_root, 'status', '--porcelain', '--untracked-files=normal'), 'production code worktree must be clean')
    hashes = {p:sha((project_root/p).read_bytes()) for p in CODE_PATHS}
    return {'game_commit':commit, 'game_tree':tree, 'consumer_sha256':sha(canonical(hashes)),
            'schema_sha256':sha((project_root/SCHEMA_PATH).read_bytes()),
            'policy_sha256':sha((project_root/'docs/authority/r2/09_CONTENT_SAFETY_AND_ABSOLUTE_RED_LINES.md').read_bytes()),
            'input_root':input_root}
