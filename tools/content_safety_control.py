"""Local control writer and durable operation store; never a semantic reviewer."""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import json
import os
import sqlite3
import stat
import sys
import time
import uuid
from pathlib import Path

if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.lib.content_safety_evidence import (
    SafetyError, require, sha, canonical, strict_json, validate_receipt, validate_shape,
    inventory_root, scope_digest, durable_write, fsync_dir, verify_authority, verify_custody, current_source,
    STAGES, safe_path, MAX_JSON, validate_scope, open_member, _dirfd, _identity,
)

# Deployment control, not a request argument/environment variable. The operator
# provisions this directory and a root-owned configuration outside any checkout.
PRODUCTION_ROOT = Path('/var/lib/rules-residue/content-safety')

DDL = '''
CREATE TABLE control(id INTEGER PRIMARY KEY CHECK(id=1), document BLOB NOT NULL);
CREATE TABLE operations(
 namespace TEXT NOT NULL, execution_id TEXT NOT NULL, task_id TEXT NOT NULL,
 occurrence_id TEXT NOT NULL, stage TEXT NOT NULL, scope_digest TEXT NOT NULL,
 binding BLOB NOT NULL, state TEXT NOT NULL CHECK(state IN ('ISSUED','PREPARED','COMMITTED','ABORTED')),
 version INTEGER NOT NULL, result BLOB, PRIMARY KEY(namespace,execution_id),
 UNIQUE(namespace,task_id,occurrence_id,stage,scope_digest));
CREATE TABLE phases(namespace TEXT NOT NULL, execution_id TEXT NOT NULL, phase TEXT NOT NULL,
 receipt_id TEXT NOT NULL UNIQUE, receipt BLOB NOT NULL, evidence BLOB NOT NULL,
 PRIMARY KEY(namespace,execution_id,phase),
 FOREIGN KEY(namespace,execution_id) REFERENCES operations(namespace,execution_id));
'''


def system_clock():
    return {'utc':int(time.time()), 'monotonic_ns':time.monotonic_ns(),
            'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def _uuid(value):
    try: u = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc: raise SafetyError('invalid UUIDv4') from exc
    require(str(u) == value and u.version == 4, 'invalid canonical UUIDv4')
    return value


def _protected_json(path):
    p = Path(path); s = p.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_nlink == 1 and s.st_mode & 0o022 == 0,
            'production trust configuration must be operator installed and protected')
    require(s.st_size <= MAX_JSON, 'oversized operator configuration')
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(os.fstat(fd).st_ino == s.st_ino, 'operator configuration replaced')
        data = os.read(fd, MAX_JSON + 1)
        require(os.fstat(fd).st_mtime_ns == s.st_mtime_ns, 'operator configuration changed')
        return strict_json(data)
    finally: os.close(fd)


class ControlStore:
    """Production is opened only from protected deployment configuration.

    TEST_ONLY instances run the same transactions but cannot issue production
    admission. Test authority is deliberately not representable as a signed root.
    """
    def __init__(self, directory, *, _configuration=None, _test_clock=None, _reconcile=False):
        self.directory = Path(directory)
        self.configuration = _configuration
        self._test_clock = _test_clock
        self._write_clocks = {}
        require(self.directory.is_dir() and not self.directory.is_symlink(), 'control store unavailable')
        self.db_path = self.directory/'control.sqlite3'
        s = self.db_path.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and not s.st_mode & 0o077, 'unsafe control database')
        require(self.directory.stat().st_mode & 0o077 == 0, 'control directory must be private')
        c = self._connect()
        try:
            self.control = strict_json(c.execute('SELECT document FROM control WHERE id=1').fetchone()[0])
            if self.control['mode'] == 'PRODUCTION':
                require(_configuration is not None and self.directory == PRODUCTION_ROOT, 'caller cannot choose production trust root')
                require(_test_clock is None, 'caller clock cannot authorize production')
            else: require(self.control['mode'] == 'TEST_ONLY' and _configuration is None, 'invalid control mode')
            self._check(c, reconcile=_reconcile)
        finally: c.close()

    @classmethod
    def production(cls):
        return cls(PRODUCTION_ROOT, _configuration=_protected_json(PRODUCTION_ROOT/'operator.json'))

    @classmethod
    def create_test_only(cls, directory, source, *, clock=None, namespace='TEST-B018'):
        """Mechanical fixtures only. Never enables production API/CLI admission."""
        require(namespace.startswith('TEST-'), 'test namespace must be explicit')
        now = (clock or system_clock)()
        control = {'mode':'TEST_ONLY','namespace':namespace,
            'authority':{'namespace':namespace,'checkpoint':sha(b'TEST_ONLY checkpoint'), 'revocation_epoch':0,
                         'policy_revision':'TEST-POLICY-1','consumer_revision':'TEST-CODE-1','schema_revision':'1.0.0'},
            'source':dict(source), 'receipt_sequence':0, 'generation':0,
            'max_seen_utc':now['utc'], 'last_monotonic_ns':now['monotonic_ns'], 'boot':now['boot'],
            'clock_established':True, 'checkpoint_expires':now['utc']+3600, 'revoked_receipts':[]}
        control['source'].pop('input_root', None)
        cls._initialize(Path(directory), control)
        return cls(directory, _test_clock=clock)

    @staticmethod
    def _initialize(directory, control):
        """Offline operator provisioning primitive, never called by consumer CLI.

        A PRODUCTION database still requires the protected fixed-path operator.json
        with matching authority/source and independently received locator pins.
        """
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        c = sqlite3.connect(directory/'control.sqlite3')
        try:
            os.chmod(directory/'control.sqlite3', 0o600)
            c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL')
            c.executescript(DDL); c.execute('INSERT INTO control VALUES(1,?)',(canonical(control),)); c.commit()
        finally: c.close()
        durable_write(directory/'guard.json', canonical(ControlStore._guard(control)))
        (directory/'locks').mkdir(mode=0o700); (directory/'objects').mkdir(mode=0o700)
        fsync_dir(directory)

    @staticmethod
    def _guard(c):
        return {k:c[k] for k in ('generation','max_seen_utc','last_monotonic_ns','boot')} | {
            'checkpoint':c['authority']['checkpoint'], 'revocation_epoch':c['authority']['revocation_epoch']}

    def _connect(self):
        c = sqlite3.connect('file:'+str(self.db_path)+'?mode=rw', uri=True, timeout=5, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL')
        c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=5000')
        require(c.execute('PRAGMA synchronous').fetchone()[0] == 2, 'durability unavailable')
        return c

    def _read_control(self, c):
        return strict_json(c.execute('SELECT document FROM control WHERE id=1').fetchone()[0])

    def _now(self):
        require(not(self.configuration is not None and self._test_clock is not None), 'production clock override')
        return (self._test_clock or system_clock)()

    def _check(self, c, binding=None, *, reconcile=False):
        control = self._read_control(c)
        guard = strict_json((self.directory/'guard.json').read_bytes())
        require(guard == self._guard(control), 'restored/conflicting control checkpoint; operator recovery required')
        now = self._now()
        require(control['clock_established'] is True and now['boot'] == control['boot'], 'clock context unavailable/reset')
        observed = self._write_clocks.get(c)
        high = observed or control
        require(now['boot'] == high['boot'] and
                now['monotonic_ns'] >= max(control['last_monotonic_ns'], high['last_monotonic_ns']) and
                now['utc']+2 >= max(control['max_seen_utc'], high['max_seen_utc']), 'clock rollback')
        if observed is not None:
            # Keep every trusted observation, including callback freshness reads.
            # A later reading within the UTC tolerance must not lower the mark.
            observed.update(max_seen_utc=max(control['max_seen_utc'], high['max_seen_utc'], now['utc']),
                            last_monotonic_ns=now['monotonic_ns'], boot=now['boot'])
        require(now['utc']+2 < control['checkpoint_expires'], 'authority checkpoint stale')
        if control['mode'] == 'PRODUCTION' and not reconcile:
            configuration = _protected_json(PRODUCTION_ROOT/'operator.json')
            require(configuration == self.configuration, 'operator configuration changed; reopen required')
            require(configuration['authority'] == control['authority'] and configuration['source'] == control['source'], 'operator authority/source changed')
            actual = current_source('0'*64); actual.pop('input_root')
            require(actual == control['source'], 'current source/code/schema/policy changed')
        if binding:
            require(binding['authority'] == control['authority'], 'operation authority/revocation mismatch')
            require({k:v for k,v in binding['source'].items() if k!='input_root'} == control['source'], 'operation source mismatch')
        return control, now

    def assert_production(self):
        require(self.control['mode'] == 'PRODUCTION' and self.configuration is not None, 'TEST_ONLY store has no production authority')

    def _write(self, callback, *, reconcile=False):
        c = self._connect()
        observed = self._write_clocks[c] = {}
        try:
            for attempt in range(4):
                try: c.execute('BEGIN IMMEDIATE'); break
                except sqlite3.OperationalError as exc:
                    if 'locked' not in str(exc).lower() or attempt == 3: raise SafetyError('control store busy/unavailable') from exc
                    time.sleep((.05,.1,.2)[attempt])
            try:
                # Capture rollback state and establish the effects boundary
                # before any check can record a trusted clock observation.
                original = self._read_control(c)
                c.execute('SAVEPOINT operation_effects')
                try:
                    control, now = self._check(c,reconcile=reconcile)
                    result = callback(c, control, now)
                    control.update(observed)
                    self._publish_control(c, control)
                    return result
                except BaseException:
                    if c.in_transaction:
                        # Covers opening checks, callbacks and pre-commit
                        # publication failures. Preserve only validated time,
                        # never rejected business changes, under the same lock.
                        c.execute('ROLLBACK TO operation_effects')
                        c.execute('RELEASE operation_effects')
                        guard = strict_json((self.directory/'guard.json').read_bytes()) if observed else None
                        if observed and guard == self._guard(original) and any(
                                original[key] != value for key, value in observed.items()):
                            original.update(observed)
                            self._publish_control(c, original)
                        # An already published guard must never be rolled back:
                        # an uncommitted DB/guard mismatch denies on recovery.
                    # A completed SQLite commit is not undone after a later
                    # fsync/response failure; recovery uses its durable state.
                    raise
            except BaseException:
                c.rollback(); raise
        finally:
            self._write_clocks.pop(c, None)
            c.close()

    def _publish_control(self, c, control):
        control['generation'] += 1
        c.execute('UPDATE control SET document=? WHERE id=1',(canonical(control),))
        # Guard precedes DB commit. Any crash between the two is a denied
        # conflict, never permission to roll back time/epoch or re-admit.
        temporary = self.directory/('guard-'+str(uuid.uuid4())+'.tmp')
        durable_write(temporary, canonical(self._guard(control)))
        os.replace(temporary, self.directory/'guard.json'); fsync_dir(self.directory)
        c.commit(); fsync_dir(self.directory)
        self.control = control

    @classmethod
    def reconcile_operator_configuration(cls):
        """Exclusive trusted writer: only consume the fixed protected configuration.

        No request supplies a clock, checkpoint, reviewer, source or trust root.
        Changed authority/source/revocation must advance epoch exactly once.
        """
        config = _protected_json(PRODUCTION_ROOT/'operator.json')
        store = cls(PRODUCTION_ROOT,_configuration=config,_reconcile=True)
        store.assert_production()
        validate_shape(config['authority'],'authority')
        validate_shape(config['source'] | {'input_root':'0'*64},'source')
        actual = current_source('0'*64); actual.pop('input_root')
        require(actual == config['source'],'operator source is not current code')
        def apply(c,control,now):
            require(config['authority']['namespace']==control['namespace'],'operator namespace cannot change')
            changed = config['authority'] != control['authority'] or config['source'] != control['source'] or config['revoked_receipts'] != control['revoked_receipts']
            epoch = control['authority']['revocation_epoch']
            require(config['authority']['revocation_epoch'] == epoch + (1 if changed else 0),'authority changes require next revocation epoch')
            require(type(config['checkpoint_expires']) is int and now['utc']+2 < config['checkpoint_expires'],'stale operator checkpoint')
            control['authority'] = config['authority']; control['source'] = config['source']
            control['revoked_receipts'] = config['revoked_receipts'];control['checkpoint_expires'] = config['checkpoint_expires']
            return {'revocation_epoch':control['authority']['revocation_epoch'],'checkpoint':control['authority']['checkpoint']}
        return store._write(apply,reconcile=True)

    def issue(self, task_id, stage, scope, inputs, *, occurrence_id=None):
        """Trusted control operation, distinct from receipt ingestion."""
        require(isinstance(task_id,str) and len(task_id)<=128 and task_id, 'invalid task id')
        require(stage in STAGES, 'unknown stage')
        validate_scope(stage,scope)
        digest = scope_digest(scope); root = inventory_root(inputs)
        require(inputs, 'operation needs bounded input')
        execution = str(uuid.uuid4()); occurrence = _uuid(occurrence_id) if occurrence_id else str(uuid.uuid4())
        def apply(c, control, now):
            binding = {'namespace':control['namespace'],'execution_id':execution,'task_id':task_id,'occurrence_id':occurrence,
                       'stage':stage,'scope_digest':digest,'scope':scope,'inputs':inputs,'input_root':root,
                       'source':control['source'] | {'input_root':root},'authority':control['authority']}
            try:
                c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,\'ISSUED\',0,NULL)',
                    (control['namespace'],execution,task_id,occurrence,stage,digest,canonical(binding)))
            except sqlite3.IntegrityError as exc: raise SafetyError('operation occurrence already issued') from exc
            return binding
        return self._write(apply)

    def operation(self, execution):
        _uuid(execution); c=self._connect()
        try:
            row=c.execute('SELECT * FROM operations WHERE namespace=? AND execution_id=?',(self.control['namespace'],execution)).fetchone()
            require(row is not None, 'operation not issued by control')
            return dict(row) | {'binding':strict_json(row['binding'])}
        finally:c.close()

    def _authority(self, raw, evidence, control, now):
        receipt=validate_receipt(raw, now['utc'])
        require(receipt['decision']=='ALLOW', 'receipt is not ALLOW')
        require(receipt['receipt_id'] not in control['revoked_receipts'], 'receipt revoked')
        require(receipt['authority']==control['authority'], 'receipt checkpoint/epoch/revisions changed')
        if control['mode']=='PRODUCTION':
            require(set(evidence)=={'report','manifest','locator'}, 'invalid custody evidence')
            key=sha(raw); pins=self.configuration['accepted_statements']
            require(key in pins, 'receipt lacks independent root reception')
            verify_authority(raw, bytes.fromhex(evidence['report']), bytes.fromhex(evidence['manifest']),
                             evidence['locator'], Path(self.configuration['custody_repository']), pins[key])
        else:
            require(set(evidence)=={'test_only','reviewed_subjects'} and evidence['test_only'] is True and isinstance(evidence['reviewed_subjects'],list), 'synthetic store cannot import production authority')
        return receipt

    def ingest(self, raw: bytes, evidence: dict):
        # Structural failures happen before any database transaction/write.
        r=validate_receipt(raw)
        def apply(c, control, now):
            self._authority(raw,evidence,control,now)
            row=c.execute('SELECT * FROM operations WHERE namespace=? AND execution_id=?',(r['namespace'],r['execution_id'])).fetchone()
            require(row is not None and row['state'] in {'ISSUED','PREPARED'}, 'no mutable issued operation')
            b=strict_json(row['binding']); self._check(c,b)
            for field in ('namespace','execution_id','task_id','occurrence_id','stage','scope_digest','source','authority','inputs','input_root'):
                require(r[field]==b[field], 'receipt operation binding mismatch: '+field)
            if r['phase']=='OUTPUT':
                require(row['state']=='PREPARED' and c.execute('SELECT 1 FROM phases WHERE namespace=? AND execution_id=? AND phase=\'INPUT\'',(r['namespace'],r['execution_id'])).fetchone(), 'OUTPUT requires prepared INPUT in same operation')
            old=c.execute('SELECT receipt,evidence FROM phases WHERE namespace=? AND execution_id=? AND phase=?',(r['namespace'],r['execution_id'],r['phase'])).fetchone()
            if old:
                require(old['receipt']==raw and old['evidence']==canonical(evidence), 'conflicting receipt for operation phase')
                return {'replay':True,'receipt_sequence':control['receipt_sequence']}
            try:c.execute('INSERT INTO phases VALUES(?,?,?,?,?,?)',(r['namespace'],r['execution_id'],r['phase'],r['receipt_id'],raw,canonical(evidence)))
            except sqlite3.IntegrityError as exc:raise SafetyError('receipt already bound elsewhere') from exc
            control['receipt_sequence']+=1
            return {'replay':False,'receipt_sequence':control['receipt_sequence']}
        return self._write(apply)

    def test_only_ingest(self, raw, reviewed_subjects=None):
        require(self.control['mode']=='TEST_ONLY','synthetic authorization forbidden in production')
        return self.ingest(raw,{'test_only':True,'reviewed_subjects':reviewed_subjects or []})

    def _phases(self,c,b,control,now,required):
        result={}
        for row in c.execute('SELECT * FROM phases WHERE namespace=? AND execution_id=?',(b['namespace'],b['execution_id'])):
            r=self._authority(row['receipt'],strict_json(row['evidence']),control,now)
            for field in ('namespace','execution_id','task_id','occurrence_id','stage','scope_digest','source','authority','inputs','input_root'):
                require(r[field]==b[field], 'stored phase binding changed')
            result[row['phase']]=r
        require(set(required)<=set(result),'missing independently received phase receipt')
        require(set(result)<=({'INPUT','OUTPUT'} if b['stage']=='build' else {'SINGLE'}),'unexpected phase')
        return result

    def prepare(self, execution, snapshot, *, recovery=False):
        def apply(c,control,now):
            row=c.execute('SELECT * FROM operations WHERE namespace=? AND execution_id=?',(control['namespace'],execution)).fetchone()
            require(row is not None,'unknown operation'); b=strict_json(row['binding']); self._check(c,b)
            require(snapshot.verify()==b['input_root'],'actual input root mismatch')
            phases=self._phases(c,b,control,now,['INPUT' if b['stage']=='build' else 'SINGLE'])
            _,fresh_now=self._check(c,b)
            for phase in phases.values():validate_receipt(canonical(phase),fresh_now['utc'])
            if recovery:
                require(row['state']=='PREPARED','only PREPARED can recover'); return b
            require(row['state']=='ISSUED','operation already prepared/terminal')
            update=c.execute('UPDATE operations SET state=\'PREPARED\',version=version+1 WHERE namespace=? AND execution_id=? AND state=\'ISSUED\' AND version=? AND binding=?',
                            (control['namespace'],execution,row['version'],row['binding']))
            require(update.rowcount==1,'PREPARE CAS conflict')
            return b
        return self._write(apply)

    def _verify_output_files(self, execution, records):
        root=self.directory/'work'/execution
        fd=_dirfd(root)
        try:
            require(set(os.listdir(fd))=={r['path'] for r in records}|{'computed.json'},'output namespace changed')
            for record in records:
                member=open_member(fd,record['path'])
                try:
                    before=os.fstat(member)
                    require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==record['bytes'],'nonregular/changed output')
                    h=__import__('hashlib').sha256();length=0
                    while chunk:=os.read(member,65536):
                        length+=len(chunk);require(length<=record['bytes'],'output grew');h.update(chunk)
                    require(length==record['bytes'] and h.hexdigest()==record['sha256'] and _identity(before)==_identity(os.fstat(member)),'output hash/identity changed')
                    os.fsync(member)
                finally:os.close(member)
            os.fsync(fd)
        finally:os.close(fd)

    def commit(self,execution,snapshot,outputs,manifest_bytes):
        output_root=inventory_root(outputs)
        result_name=sha(manifest_bytes); result_path=self.directory/'objects'/result_name
        if result_path.exists(): require(result_path.read_bytes()==manifest_bytes,'object collision')
        else:durable_write(result_path,manifest_bytes)
        pointer={'path':'objects/'+result_name,'sha256':sha(manifest_bytes),'bytes':len(manifest_bytes),'output_root':output_root}
        def apply(c,control,now):
            row=c.execute('SELECT * FROM operations WHERE namespace=? AND execution_id=?',(control['namespace'],execution)).fetchone()
            require(row is not None and row['state']=='PREPARED','COMMIT requires PREPARED')
            b=strict_json(row['binding']);self._check(c,b)
            require(snapshot.verify()==b['input_root'],'input changed before commit')
            phases=self._phases(c,b,control,now,['INPUT','OUTPUT'] if b['stage']=='build' else ['SINGLE'])
            approval=phases['OUTPUT' if b['stage']=='build' else 'SINGLE']
            require(approval['outputs']==outputs and approval['output_root']==output_root,'unreviewed output bytes')
            require(result_path.read_bytes()==manifest_bytes,'manifest changed before commit')
            self._verify_output_files(execution,outputs)
            _,fresh_now=self._check(c,b)
            for phase in phases.values():validate_receipt(canonical(phase),fresh_now['utc'])
            updated=c.execute('UPDATE operations SET state=\'COMMITTED\',version=version+1,result=? WHERE namespace=? AND execution_id=? AND state=\'PREPARED\' AND version=? AND binding=?',
                (canonical(pointer),control['namespace'],execution,row['version'],row['binding']))
            require(updated.rowcount==1,'COMMIT CAS conflict')
            return pointer
        return self._write(apply)

    def replay(self,execution,*,current=False):
        row=self.operation(execution);require(row['state']=='COMMITTED','uncommitted objects cannot be consumed')
        if current:
            c=self._connect()
            try:
                control,now=self._check(c,row['binding'])
                self._phases(c,row['binding'],control,now,['INPUT','OUTPUT'] if row['stage']=='build' else ['SINGLE'])
            finally:c.close()
        pointer=strict_json(row['result']);p=self.directory/safe_path(pointer['path'])
        require(not p.is_symlink() and p.is_file() and p.stat().st_nlink==1,'committed manifest is not regular')
        data=p.read_bytes();require(len(data)==pointer['bytes'] and sha(data)==pointer['sha256'],'committed bytes damaged')
        return {'manifest':strict_json(data),'pointer':pointer,'replay':True,'production_authority':self.control['mode']=='PRODUCTION'}

    def current_statement_hashes(self, execution):
        row=self.operation(execution);require(row['state']=='COMMITTED','root evidence requires committed stage')
        connection=self._connect()
        try:
            control,now=self._check(connection,row['binding'])
            self._phases(connection,row['binding'],control,now,['INPUT','OUTPUT'] if row['stage']=='build' else ['SINGLE'])
            hashes=set()
            for phase in connection.execute('SELECT receipt,evidence FROM phases WHERE namespace=? AND execution_id=?',(row['namespace'],execution)):
                raw=phase['receipt'];r=validate_receipt(raw);evidence=strict_json(phase['evidence'])
                if control['mode']=='PRODUCTION':
                    statement=verify_custody(Path(self.configuration['custody_repository']),evidence['locator'],trusted_locator=self.configuration['accepted_statements'][sha(raw)])
                else:
                    # Explicit synthetic equivalent, never usable by production.
                    statement=canonical({'schema_version':'1.0.0','kind':'CONTENT_SAFETY_ACCEPTANCE_STATEMENT',
                        'namespace':r['namespace'],'receipt_sha256':sha(raw),'decision':r['decision'],
                        'checkpoint':r['authority']['checkpoint'],'revocation_epoch':r['authority']['revocation_epoch'],**r['review']})
                hashes.add(sha(statement))
            return hashes
        finally:connection.close()

    def abort(self,execution,reason):
        # Quarantine an operation even when clock/checkpoint is unavailable. This
        # denies authority only and cannot create/revive a committed admission.
        c=self._connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            update=c.execute('UPDATE operations SET state=\'ABORTED\',version=version+1 WHERE namespace=? AND execution_id=? AND state IN (\'ISSUED\',\'PREPARED\')',(self.control['namespace'],execution))
            control=self._read_control(c)
            guard=strict_json((self.directory/'guard.json').read_bytes())
            if update.rowcount and guard==self._guard(control):
                # Denial needs no valid clock, but must still invalidate an older
                # database snapshot so an ABORTED operation can never revive.
                control['generation']+=1
                c.execute('UPDATE control SET document=? WHERE id=1',(canonical(control),))
                temporary=self.directory/('guard-'+str(uuid.uuid4())+'.tmp')
                durable_write(temporary,canonical(self._guard(control)))
                os.replace(temporary,self.directory/'guard.json');fsync_dir(self.directory)
            # Existing control conflicts remain conflicts; never overwrite a
            # newer independent guard with stale database data.
            c.commit()
        finally:c.close()

    def test_only_reconfigure(self, *, authority=None, source=None, clock_established=None):
        require(self.control['mode']=='TEST_ONLY','test mutation cannot change production control')
        def apply(c,control,now):
            old_epoch=control['authority']['revocation_epoch']
            if authority is not None:control['authority']=authority
            if source is not None:control['source']=source
            control['authority']['revocation_epoch']=old_epoch+1
            if clock_established is not None:control['clock_established']=clock_established
        return self._write(apply)

    @contextlib.contextmanager
    def exclusive_operation(self,execution):
        _uuid(execution);p=self.directory/'locks'/execution
        fd=os.open(p,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as exc:raise SafetyError('operation already executing') from exc
            yield
        finally:os.close(fd)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Fixed-root local content safety control; no semantic classifier')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status');sub.add_parser('reconcile')
    issue=sub.add_parser('issue');issue.add_argument('--request',type=Path,required=True)
    ingest=sub.add_parser('ingest');ingest.add_argument('--receipt',type=Path,required=True);ingest.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='reconcile':
            print(json.dumps(ControlStore.reconcile_operator_configuration(),sort_keys=True));return 0
        store=ControlStore.production();store.assert_production()
        if args.command=='status':result={'mode':'PRODUCTION','namespace':store.control['namespace'],'authority':store.control['authority']}
        elif args.command=='issue':
            q=strict_json(args.request.read_bytes());require(set(q)=={'task_id','stage','scope','inputs'},'closed operation issue request')
            result=store.issue(**q)
        else:result=store.ingest(args.receipt.read_bytes(),strict_json(args.evidence.read_bytes()))
        print(json.dumps(result,sort_keys=True));return 0
    except (SafetyError,OSError,ValueError,sqlite3.Error) as exc:
        print('CONTENT_SAFETY_CONTROL: DENY: '+str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
