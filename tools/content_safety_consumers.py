"""Five local admissions of independently reviewed, bounded bytes.

Format/graph validation is deliberately separate from semantic authorization.
No classifier, provider call, asset installation or release publication occurs.
"""
from __future__ import annotations
import argparse
import binascii
import io
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
import zlib
from pathlib import Path

if __package__ in {None, ''}:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jsonschema import Draft202012Validator
from tools.lib.content_safety_evidence import (
    ROOT, SafetyError, Snapshot, require, sha, canonical, strict_json, safe_path,
    validate_shape, inventory_root, durable_write, fsync_dir, git_bytes, validate_scope,
)
from tools.content_safety_control import ControlStore


class AwaitingOutputReview(SafetyError):
    """INPUT accepted; output remains quarantined pending independent OUTPUT."""


def _closed(value, keys, label):
    require(isinstance(value,dict) and set(value)==set(keys),label+' has missing/unknown fields')


def registered_shape(value,name):
    s=strict_json((ROOT/'schemas/story-construction'/name).read_bytes())
    errors=list(Draft202012Validator(s).iter_errors(value))
    require(not errors,'registered '+name+': '+('; '.join(e.message for e in errors[:3])))


class Closure:
    def __init__(self,snapshot,references=None):
        self.snapshot=snapshot;self.references=references or {};self.used=set();self.active=set()
        require(isinstance(self.references,dict),'reference index must be an object')
        for ref in self.references.values():validate_shape(ref,'reference')

    def read(self,path,*,json_document=False):
        safe_path(path);self.used.add(path)
        data=self.snapshot.bytes(path)
        if not json_document:return data
        value=strict_json(data)
        if path not in self.active:
            self.active.add(path);self.scan(value)
        return value

    def ref(self,value,revision=None,*,follow=True):
        if isinstance(value,str):
            require(value in self.references,'unknown reference: '+value)
            value=self.references[value]
        validate_shape(value,'reference')
        data=self.snapshot.reference(value,expected_revision=revision);self.used.add(value['path'])
        if follow and value['path'].endswith('.json') and value['path'] not in self.active:
            self.active.add(value['path']);self.scan(strict_json(data))
        return data

    def scan(self,value):
        if isinstance(value,dict):
            if set(value)=={'path','sha256','revision'}:self.ref(value);return
            for key,item in value.items():
                if key.endswith('_ref') and isinstance(item,str):self.ref(item)
                elif key.endswith('_refs') and isinstance(item,list):
                    for ref in item:self.ref(ref)
                else:self.scan(item)
        elif isinstance(value,list):
            for item in value:self.scan(item)

    def complete(self):
        require(self.used=={r['path'] for r in self.snapshot.records},'unresolved/extra input closure members')


def inspect_pcm(data, intake):
    started=time.monotonic()
    require(44<=len(data)<=11520044,'PCM WAV size outside bound')
    riff,size,wave,fmt,fmt_size,encoding,ch,rate,byterate,align,bits,chunk,n=struct.unpack('<4sI4s4sIHHIIHH4sI',data[:44])
    require((riff,wave,fmt,fmt_size,encoding,bits,chunk)==(b'RIFF',b'WAVE',b'fmt ',16,1,16,b'data'),'unsupported WAV encoding/chunks')
    require(ch in (1,2) and rate in (44100,48000),'unsupported PCM channel/rate')
    require(align==ch*2 and byterate==rate*align and n%align==0,'PCM alignment mismatch')
    frames=n//align
    require(1<=frames<=rate*60 and size==len(data)-8 and n==len(data)-44,'PCM duration/trailing bytes/length mismatch')
    require((ch,rate,frames)==(intake['channels'],intake['sample_rate'],intake['frames']),'intake PCM declaration mismatch')
    # Finite PCM interpretation consumes at most one 64 KiB block at a time.
    samples=0
    for offset in range(44,len(data),65536):
        block=memoryview(data)[offset:offset+65536]
        samples+=len(block)//2
        require(time.monotonic()-started<=2,'PCM decode budget exceeded')
    return {'encoding':'PCM_S16LE','channels':ch,'sample_rate':rate,'frames':frames,'samples':samples}


def inspect_png(data):
    started=time.monotonic()
    require(len(data)<=16*1024*1024 and data[:8]==b'\x89PNG\r\n\x1a\n','unsupported image/PNG size')
    offset=8;state='IHDR';decoder=None;width=height=channels=None;row_size=0;pending=b'';rows=0;total=0
    while offset<len(data):
        require(offset+12<=len(data),'truncated PNG chunk')
        length,kind=struct.unpack('>I4s',data[offset:offset+8]);offset+=8
        require(length<=16*1024*1024 and offset+length+4<=len(data),'PNG chunk length')
        payload=data[offset:offset+length];crc=struct.unpack('>I',data[offset+length:offset+length+4])[0];offset+=length+4
        require(binascii.crc32(payload,binascii.crc32(kind))&0xffffffff==crc,'PNG CRC mismatch')
        require(time.monotonic()-started<=2,'PNG decode budget exceeded')
        if kind==b'IHDR':
            require(state=='IHDR' and length==13,'PNG IHDR order/size')
            width,height,depth,colour,compression,filter_method,interlace=struct.unpack('>IIBBBBB',payload)
            require(1<=width<=4096 and 1<=height<=4096 and width*height<=16777216,'PNG dimensions')
            require(depth==8 and colour in (2,6) and (compression,filter_method,interlace)==(0,0,0),'unsupported PNG semantics')
            channels=3 if colour==2 else 4;row_size=1+width*channels;decoder=zlib.decompressobj();state='IDAT'
        elif kind==b'IDAT':
            require(state in {'IDAT','DATA'} and decoder is not None,'PNG IDAT order');state='DATA'
            compressed=payload
            while compressed:
                chunk=decoder.decompress(compressed,65536);compressed=decoder.unconsumed_tail
                total+=len(chunk);require(total<=row_size*height,'PNG expanded data overflow')
                pending+=chunk
                while len(pending)>=row_size:
                    require(pending[0]<=4,'unsupported PNG row filter')
                    pending=pending[row_size:];rows+=1
                require(time.monotonic()-started<=2,'PNG decode budget exceeded')
                require(not decoder.unused_data,'trailing/composed PNG zlib stream')
        elif kind==b'IEND':
            require(state=='DATA' and length==0 and offset==len(data),'PNG IEND/trailing bytes')
            require(decoder.eof and not decoder.unused_data and not pending and rows==height and total==row_size*height,'PNG truncated image')
            state='DONE'
        else:raise SafetyError('unsupported PNG chunk semantics: '+repr(kind))
    require(state=='DONE','missing PNG IEND')
    return {'format':'PNG','width':width,'height':height,'channels':channels}


def _reviewed_subject(store,binding,subject):
    """A root-accepted report must explicitly cover the fact being consumed."""
    c=store._connect()
    try:
        control,now=store._check(c,binding)
        phase='INPUT' if binding['stage']=='build' else 'SINGLE'
        store._phases(c,binding,control,now,[phase])
        row=c.execute('SELECT evidence FROM phases WHERE namespace=? AND execution_id=? AND phase=?',(binding['namespace'],binding['execution_id'],phase)).fetchone()
        evidence=strict_json(row['evidence'])
        if control['mode']=='TEST_ONLY':
            subjects=evidence.get('reviewed_subjects',[])
        else:
            report=strict_json(bytes.fromhex(evidence['report']))
            subjects=report.get('accepted_subjects',[])
        require(subject in subjects,'no current independently reviewed authority for subject')
    finally:c.close()


def media(snapshot,scope,store,binding):
    require(scope.get('consumer')=='media','wrong media scope')
    closure=Closure(snapshot,scope.get('references'))
    if scope.get('kind')=='audio':
        _closed(scope,('consumer','kind','intake'),'audio scope')
        intake=closure.read(scope['intake'],json_document=True);validate_shape(intake,'audio_intake')
        require((intake['transcript_status']=='PRESENT' and 1<=len(intake['transcripts'])<=16) or
                (intake['transcript_status']=='EXPLICITLY_ABSENT' and not intake['transcripts']),'transcript absence/presence mismatch')
        if intake['transcript_status']=='EXPLICITLY_ABSENT':
            _reviewed_subject(store,binding,{'kind':'audio_transcript_absence','asset_id':intake['asset_id'],'input_root':snapshot.root})
        result=inspect_pcm(closure.ref(intake['wav']),intake)
        # The recursive reader bound source, author metadata, rights, accessibility,
        # transcripts and attachments; no assertion about arbitrary speech follows.
        closure.complete();return {'consumer':'media','kind':'audio','asset_id':intake['asset_id'],'decode':result}
    _closed(scope,('consumer','kind','packet','order','asset','references','targets'),'image scope')
    require(scope['kind']=='image','unknown media kind')
    packet=closure.read(scope['packet'],json_document=True);order=closure.read(scope['order'],json_document=True)
    from tools.lib.schema_subset import validate
    from tools.story_construction import validate_visual_execution
    from tools.validate_precontent_readiness import validate_test_boundary
    packet_document=packet
    errors=[]
    if isinstance(packet,dict) and 'task_packet' in packet:
        errors.extend(validate_test_boundary(packet,'Task Packet envelope'));packet=packet['task_packet']
        require(packet_document.get('execution_authorized_in_m3_b002') is False,'precontent cannot grant execution')
    packet_schema=strict_json((ROOT/'workflow/task-packet.schema.json').read_bytes())
    errors.extend(str(e) for e in validate(packet,packet_schema))
    name='visual-order-v2.schema.json' if order.get('schema_version')=='2.0.0' else 'visual-order-v1.schema.json'
    registered_shape(order,name)
    errors.extend(validate_visual_execution(packet,order,scope['targets']))
    if name=='visual-order-v2.schema.json':
        errors.extend(validate_test_boundary(order,'Pre-Content Visual Order'))
        require(order['provider_execution_authorized'] is False and order['raw_request'] is False,'precontent provider authority rejected')
    require(not errors,'native Visual Order/Task Packet gate: '+'; '.join(errors))
    for name in ('rights_provenance','accessibility_equivalent','semantic_composition_proof'):
        values=order[name] if isinstance(order[name],list) else [order[name]]
        for v in values:closure.ref(v)
    for v in packet['inputs']:closure.ref(v)
    result=inspect_png(closure.read(scope['asset']));closure.complete()
    return {'consumer':'media','kind':'image','decode':result,'order_id':order['order_id']}


def region(snapshot,scope,store,binding):
    _closed(scope,('consumer','acceptance','region_id','candidate_revision','references','reports','owner_approvals'),'region scope')
    require(scope['consumer']=='region','wrong region scope')
    closure=Closure(snapshot,scope['references']);bundle=closure.read(scope['acceptance'],json_document=True)
    registered_shape(bundle,'region-acceptance-v1.schema.json')
    from tools.story_construction import validate_region_acceptance,validate_region_design_complete,validate_dab
    errors=validate_region_acceptance(bundle);require(not errors and bundle['result']=='PASS','native Region Acceptance gate: '+'; '.join(errors))
    dossier=strict_json(closure.ref(bundle['dossier_ref'],scope['candidate_revision']))
    require(not validate_region_design_complete(dossier),'region design incomplete')
    dab=strict_json(closure.ref(bundle['dab_ref']));registered_shape(dab,'dab-v1.schema.json')
    require(not validate_dab(dab,'T1'),'region forensic DAB required')
    require(set(scope['reports'])=={'V'+str(i) for i in range(7)},'requires every V0..V6 report')
    for layer,ref in scope['reports'].items():
        report=strict_json(closure.ref(ref,scope['candidate_revision']))
        require(report.get('layer')==layer and report.get('result')=='PASS' and report.get('candidate_revision')==scope['candidate_revision'],'layer report revision/result mismatch')
        _reviewed_subject(store,binding,{'kind':'validation_report','layer':layer,'region_id':scope['region_id'],
            'revision':scope['candidate_revision'],'sha256':ref['sha256']})
    require(set(scope['owner_approvals'])=={'T1','T2','C1'},'separate T1/T2/C1 Owner approvals required')
    for kind,ref in scope['owner_approvals'].items():
        approval=strict_json(closure.ref(ref,scope['candidate_revision']))
        require(approval.get('decision')=='APPROVED' and approval.get('kind')==kind,'Owner approval mismatch')
        _reviewed_subject(store,binding,{'kind':'owner_approval','authority':kind,'region_id':scope['region_id'],
            'revision':scope['candidate_revision'],'sha256':ref['sha256']})
    require(scope['candidate_revision'] in bundle['candidate_hashes'],'candidate revision not in acceptance')
    require(set(scope['owner_approvals'])<=set(bundle['owner_approvals']),'acceptance missing Owner approval classes')
    closure.complete();return {'consumer':'region','region_id':scope['region_id'],'candidate_revision':scope['candidate_revision']}


def cross_region(snapshot,scope,store,binding):
    _closed(scope,('consumer','matrix','references','children'),'cross-region scope')
    require(scope['consumer']=='cross-region','wrong cross-region scope')
    closure=Closure(snapshot,scope['references']);matrix=closure.read(scope['matrix'],json_document=True)
    registered_shape(matrix,'region-interface-matrix-v1.schema.json')
    rows=matrix['regions'];ids=[r['region_id'] for r in rows]
    require(len(rows)==6 and len(set(ids))==6 and set(ids)==set(scope['children']),'exactly six unique current children required')
    require(matrix['all_interfaces_frozen'] and all(r['status']=='FROZEN' for r in rows),'interfaces not frozen')
    exports={};edges=[]
    for row in rows:
        child=scope['children'][row['region_id']]
        _closed(child,('execution_id','revision','manifest','closure'),'child interface binding')
        require(str(row['revision'])==child['revision'],'child interface revision mismatch')
        admission=store.replay(child['execution_id'],current=True)
        data=closure.ref(child['manifest'],child['revision'])
        require(sha(data)==admission['pointer']['sha256'],'child admission byte mismatch')
        result=admission['manifest']
        require(result['stage']=='region_acceptance' and result['details']['region_id']==row['region_id'] and result['details']['candidate_revision']==child['revision'],'wrong/stale child admission')
        require(set(child['closure'])=={r['path'] for r in result['inputs']},'missing child raw closure')
        for record in result['inputs']:
            ref=child['closure'][record['path']];raw=closure.ref(ref,child['revision'],follow=False)
            require(sha(raw)==record['sha256'] and len(raw)==record['bytes'],'child payload differs from admitted bytes')
        for symbol in row['exports']:exports.setdefault(symbol,[]).append(row)
    for row in rows:
        for symbol in row['imports']:
            candidates=exports.get(symbol,[]);require(len(candidates)==1,'import missing/ambiguous export')
            other=candidates[0];edges.append([row['region_id'],other['region_id'],symbol,row['revision'],other['revision']])
    closure.complete()
    return {'consumer':'cross-region','matrix_id':matrix['matrix_id'],'adjacency':sorted(edges),'children':ids}


def inspect_archive(data):
    require(len(data)<=128*1024*1024,'compressed archive exceeds 128 MiB')
    seen=set();aliases=set();members=[];total=0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            require(len(z.infolist())<=4096,'archive member count')
            for item in z.infolist():
                name=safe_path(item.filename);mode=(item.external_attr>>16)&0xffff
                require(name not in seen and name.lower() not in aliases and not item.is_dir() and stat.S_ISREG(mode),'archive duplicate/alias/nonregular member')
                require(stat.S_IMODE(mode) in {0o644,0o755},'archive mode unsupported');seen.add(name);aliases.add(name.lower())
                require(item.file_size<=32*1024*1024 and item.file_size<=max(item.compress_size,1)*256,'archive expansion bound')
                total+=item.file_size;require(total<=512*1024*1024,'archive total expansion bound')
                require(not item.flag_bits&1,'encrypted archive unsupported')
                h=__import__('hashlib').sha256();length=0
                with z.open(item) as f:
                    while b:=f.read(65536):length+=len(b);require(length<=item.file_size,'archive expanded size mismatch');h.update(b)
                require(length==item.file_size,'truncated archive member')
                members.append({'path':name,'kind':'regular_file','mode':format(mode,'06o'),'bytes':length,'sha256':h.hexdigest()})
            require('package.lock.json' in seen,'archive lacks lock')
            lock=strict_json(z.read('package.lock.json'))
            expected={x['path']:(x['size'],x['sha256']) for x in lock['files']}
            actual={x['path']:(x['bytes'],x['sha256']) for x in members if x['path']!='package.lock.json'}
            require(expected==actual and len(expected)==len(lock['files']),'archive lock/member mismatch')
    except (zipfile.BadZipFile,KeyError,ValueError,zlib.error) as exc:raise SafetyError('invalid package archive') from exc
    return members


def _snapshot_materialize(snapshot,destination):
    destination.mkdir(mode=0o700,parents=True,exist_ok=False)
    for record in snapshot.records:
        p=destination/record['path'];durable_write(p,snapshot.bytes(record['path']));os.chmod(p,int(record['mode'],8)&0o777)
    fsync_dir(destination)


def build(snapshot,scope,store,binding):
    _closed(scope,('consumer','validation'),'build scope')
    require(scope['consumer']=='build' and scope['validation'] in {'full-project','module-registry'},'unknown build validation scope')
    from tools.build_package import _quarantine_encode
    with tempfile.TemporaryDirectory(prefix='safety-build-',dir=store.directory) as temp:
        root=Path(temp);package=root/'game-package';_snapshot_materialize(snapshot,package)
        if scope['validation']=='full-project':
            # Existing full/default-root checks run on an isolated fixed-source
            # repository with input package bytes replaced only from snapshot FDs.
            repo=root/'repository'
            git_bytes(ROOT,'clone','--quiet','--no-hardlinks','--no-checkout',str(ROOT),str(repo))
            git_bytes(repo,'checkout','--quiet','--detach',binding['source']['game_commit'])
            shutil.rmtree(repo/'game-package');shutil.move(str(package),repo/'game-package');package=repo/'game-package'
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',GIT_NO_REPLACE_OBJECTS='1')
            p=subprocess.run([sys.executable,'tools/validate_project.py'],cwd=repo,env=env,capture_output=True,timeout=60)
            require(p.returncode==0,'original full project validation rejected snapshot: '+p.stdout.decode(errors='replace')[-1000:])
        output=root/'archive.trpgpkg'
        _quarantine_encode(output,validate_first=True,game_package_root=package)
        data=output.read_bytes();members=inspect_archive(data)
    return {'consumer':'build','members':members,'archive_sha256':sha(data),'draft_only':True}, {'archive.trpgpkg':data,'members.json':canonical(members)}


def rc(snapshot,scope,store,binding):
    _closed(scope,('consumer','dab','references','archive_execution','archive','stage_executions','root_statement'),'RC scope')
    require(scope['consumer']=='rc','wrong RC scope')
    closure=Closure(snapshot,scope['references']);dab=closure.read(scope['dab'],json_document=True)
    registered_shape(dab,'dab-v1.schema.json')
    from tools.story_construction import validate_dab
    require(not validate_dab(dab,'RC'),'RC requires entire FORENSIC DAB')
    archive=store.replay(scope['archive_execution'],current=True)
    require(archive['manifest']['stage']=='build','RC archive is not an admitted build')
    archive_data=closure.ref(scope['archive']);inspect_archive(archive_data)
    require(sha(archive_data)==archive['manifest']['details']['archive_sha256'],'RC archive changed')
    stages=set();current_root_statements=set()
    for execution in scope['stage_executions']:
        admission=store.replay(execution,current=True);stages.add(admission['manifest']['stage'])
        current_root_statements.update(store.current_statement_hashes(execution))
        _reviewed_subject(store,binding,{'kind':'stage_admission','execution_id':execution,'manifest_sha256':admission['pointer']['sha256']})
    require({'art_audio','region_acceptance','cross_region_validation','build'}<=stages,'RC missing current stage admissions')
    raw=closure.ref(scope['root_statement']);statement=strict_json(raw);validate_shape(statement,'authority_statement')
    require(statement['checkpoint']==binding['authority']['checkpoint'],'RC root statement checkpoint mismatch')
    require(sha(raw) in current_root_statements,'RC root statement is not actual received stage custody')
    _reviewed_subject(store,binding,{'kind':'root_statement','sha256':sha(raw)})
    closure.complete();return {'consumer':'rc','archive_sha256':sha(archive_data),'release':'BLOCKED_BY_DESIGN'}


_HANDLERS={'art_audio':media,'region_acceptance':region,'cross_region_validation':cross_region,'build':build,'release_candidate':rc}


def _output_records(outputs):
    return [{'path':name,'kind':'regular_file','mode':'100644','bytes':len(data),'sha256':sha(data)} for name,data in sorted(outputs.items())]


def _execute(stage,root,execution,store,*,test_only=False,crash=None):
    if test_only:require(store.control['mode']=='TEST_ONLY','test path requires TEST_ONLY store')
    else:store.assert_production()
    row=store.operation(execution);require(row['stage']==stage,'operation stage mismatch')
    if row['state']=='COMMITTED':return store.replay(execution)
    require(row['state'] in {'ISSUED','PREPARED'},'aborted operation cannot revive')
    b=row['binding'];validate_scope(stage,b['scope'])
    if stage=='build' and Path(root).resolve()==(ROOT/'game-package').resolve():
        require(b['scope']['validation']=='full-project','default root requires full original validation')
    with store.exclusive_operation(execution):
        # A competing worker may have committed while this process was opening.
        row=store.operation(execution)
        if row['state']=='COMMITTED':return store.replay(execution)
        try:
            with Snapshot(Path(root),b['inputs'],store.directory/'snapshots') as snapshot:
                if crash:crash('before_prepare')
                store.prepare(execution,snapshot,recovery=row['state']=='PREPARED')
                if crash:crash('after_prepare')
                work=store.directory/'work'/execution;work.mkdir(mode=0o700,parents=True,exist_ok=True)
                cached=work/'computed.json'
                if cached.exists() and stage=='build':
                    computed=strict_json(cached.read_bytes());require(computed['input_root']==snapshot.root,'cached computation belongs to other input')
                    details=computed['details'];outputs={}
                    for item in computed['outputs']:
                        p=work/safe_path(item['path']);require(not p.is_symlink(),'quarantine output link')
                        raw=p.read_bytes();require(sha(raw)==item['sha256'] and len(raw)==item['bytes'],'quarantine output changed');outputs[item['path']]=raw
                    actual_members=inspect_archive(outputs.get('archive.trpgpkg',b''))
                    require(set(outputs)=={'archive.trpgpkg','members.json'} and outputs['members.json']==canonical(actual_members),'cached archive/member binding mismatch')
                    details={'consumer':'build','members':actual_members,'archive_sha256':sha(outputs['archive.trpgpkg']),'draft_only':True}
                else:
                    result=_HANDLERS[stage](snapshot,b['scope'],store,b)
                    if stage=='build':details,outputs=result
                    else:details,outputs=result,{}
                    for name,data in outputs.items():durable_write(work/safe_path(name),data)
                    computed={'input_root':snapshot.root,'details':details,'outputs':_output_records(outputs)}
                    if cached.exists(): require(cached.read_bytes()==canonical(computed),'recovery computation changed')
                    else: durable_write(cached,canonical(computed))
                records=_output_records(outputs)
                for entry in work.iterdir():
                    require(entry.is_file() and not entry.is_symlink() and entry.stat().st_nlink==1,'nonregular quarantine output')
                    entry.chmod(0o400)
                fsync_dir(work);work.chmod(0o500);fsync_dir(work.parent)
                if crash:crash('after_output_fsync')
                if stage=='build':
                    c=store._connect()
                    try:
                        row=c.execute('SELECT 1 FROM phases WHERE namespace=? AND execution_id=? AND phase=\'OUTPUT\'',(b['namespace'],execution)).fetchone()
                    finally:c.close()
                    if not row:raise AwaitingOutputReview('OUTPUT review required; quarantined bytes at '+str(work))
                manifest={'schema_version':'1.0.0','kind':'LOCAL_CONTENT_SAFETY_ADMISSION','namespace':b['namespace'],
                    'execution_id':execution,'stage':stage,'scope_digest':b['scope_digest'],'input_root':snapshot.root,
                    'inputs':snapshot.records,'outputs':records,'details':details,
                    'production_authority':not test_only,'release':'BLOCKED_BY_DESIGN'}
                if crash:crash('before_commit')
                store.commit(execution,snapshot,records,canonical(manifest))
                if crash:crash('after_commit_before_response')
                result=store.replay(execution);result['replay']=False;return result
        except AwaitingOutputReview:raise
        except (SafetyError,OSError,ValueError) as exc:
            store.abort(execution,str(exc));raise


def admit(stage,root,execution,*,store=None):
    """Production API; every consumer and build caller uses this same boundary."""
    require(stage in _HANDLERS,'unknown consumer stage')
    return _execute(stage,root,execution,store or ControlStore.production())


def exercise_test_only(stage,root,execution,store,*,crash=None):
    """Explicit mechanics exercise, no production capability or consumption token."""
    return _execute(stage,root,execution,store,test_only=True,crash=crash)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Consume current independently accepted safety evidence')
    parser.add_argument('consumer',choices=('media','region','cross-region','build','rc'))
    parser.add_argument('--input-root',type=Path,required=True);parser.add_argument('--execution',required=True)
    args=parser.parse_args(argv)
    stage={'media':'art_audio','region':'region_acceptance','cross-region':'cross_region_validation','build':'build','rc':'release_candidate'}[args.consumer]
    try:
        result=admit(stage,args.input_root,args.execution);print(json.dumps(result,sort_keys=True));return 0
    except (SafetyError,OSError,ValueError) as exc:
        print('CONTENT_SAFETY_ADMISSION: DENY: '+str(exc));return 1

if __name__=='__main__':raise SystemExit(main())
