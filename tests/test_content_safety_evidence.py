"""TEST_ONLY authority fixtures exercise mechanics, never production decisions."""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
import multiprocessing
import os
import shutil
import sqlite3
import struct
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from tools.lib import content_safety_evidence as e
from tools.content_safety_control import ControlStore
from tools.content_safety_consumers import exercise_test_only,admit


class Clock:
    def __init__(self):self.utc=2000000000;self.monotonic_ns=1000;self.boot='TEST-BOOT'
    def __call__(self):return {'utc':self.utc,'monotonic_ns':self.monotonic_ns,'boot':self.boot}


class ObservationClock(Clock):
    """Explicit TEST_ONLY clock schedule, never a production clock override."""
    def __init__(self):
        super().__init__();self.pending=[];self.trace=[]
    def arm(self, observations):
        self.pending=list(observations);self.trace=[]
    def __call__(self):
        if self.pending:self.utc,self.monotonic_ns,self.boot=self.pending.pop(0)
        value=super().__call__();self.trace.append(dict(value));return value


def remove_owned(path):
    if not Path(path).exists():return
    for root,dirs,files in os.walk(path):
        os.chmod(root,0o700)
        for f in files:
            p=Path(root)/f
            if not p.is_symlink():os.chmod(p,0o600)
    shutil.rmtree(path)


def stamp(seconds):return dt.datetime.fromtimestamp(seconds,dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def pcm(frames=4,channels=1,rate=48000):
    n=frames*channels*2
    return struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',36+n,b'WAVE',b'fmt ',16,1,channels,rate,rate*channels*2,channels*2,16,b'data',n)+bytes(n)


def receipt(binding,clock,*,phase=None,outputs=None):
    result={k:copy.deepcopy(binding[k]) for k in ('namespace','execution_id','task_id','occurrence_id','stage','scope_digest','source','authority','inputs','input_root')}
    outputs=outputs or []
    result.update(schema_version='1.0.0',kind='CONTENT_SAFETY_RECEIPT',receipt_id=str(uuid.uuid4()),
        phase=phase or ('INPUT' if binding['stage']=='build' else 'SINGLE'),outputs=outputs,output_root=e.inventory_root(outputs),decision='ALLOW',
        review={'producer_task':'TEST-PRODUCER','producer_run':str(uuid.uuid4()),'reviewer_task':'TEST-REVIEWER',
                'reviewer_run':str(uuid.uuid4()),'report_sha256':'1'*64,'manifest_sha256':'2'*64},
        issued_at=stamp(clock.utc-10),not_before=stamp(clock.utc-5),expires_at=stamp(clock.utc+300))
    return result


class Fixture:
    def __init__(self,directory):
        self.root=Path(directory);self.inputs=self.root/'inputs';self.inputs.mkdir(mode=0o700)
        self.clock=Clock()
        self.source={'game_commit':'1'*40,'game_tree':'2'*40,'consumer_sha256':'3'*64,'schema_sha256':e.SCHEMA_SHA256,'policy_sha256':'4'*64}
        self.store=ControlStore.create_test_only(self.root/'store',self.source,clock=self.clock)
        self.counter=0
    def put(self,path,value):
        data=value if isinstance(value,bytes) else e.canonical(value)
        p=self.inputs/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(0o644)
        return {'path':path,'sha256':e.sha(data),'revision':'1'}
    def audio(self,absent=False):
        wav=self.put('silence.wav',pcm());source=self.put('source.json',{'revision':'1','origin':'finite TEST_ONLY generated silence'})
        rights=self.put('rights.json',{'revision':'1','notice':'TEST_ONLY mechanical fixture'})
        access=self.put('accessibility.json',{'revision':'1','text':'Four silent PCM frames; no speech.'})
        transcripts=[] if absent else [self.put('transcript.json',{'revision':'1','text':'Four silent PCM frames; no speech.'})]
        self.put('intake.json',{'schema_version':'1.0.0','media_kind':'audio','asset_id':'TEST-SILENCE-1','task_id':'TEST-TASK-1',
            'use':'bounded mechanical test','wav':wav,'encoding':'PCM_S16LE','channels':1,'sample_rate':48000,'frames':4,
            'source':source,'author':'TEST_ONLY generator','rights':[rights],'accessibility':access,
            'transcript_status':'EXPLICITLY_ABSENT' if absent else 'PRESENT','transcripts':transcripts,'attachments':[]})
        return {'consumer':'media','kind':'audio','intake':'intake.json'}
    def issue(self,stage,scope,*,occurrence_id=None):
        self.counter+=1
        return self.store.issue('TEST-TASK-'+str(self.counter),stage,scope,e.describe_directory(self.inputs),occurrence_id=occurrence_id)
    def authorize(self,binding,*,phase=None,outputs=None,subjects=None):
        r=receipt(binding,self.clock,phase=phase,outputs=outputs)
        self.store.test_only_ingest(e.canonical(r),subjects);return r


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=Path(tempfile.mkdtemp(prefix='b018-evidence-'));self.addCleanup(remove_owned,self.temp)
        self.f=Fixture(self.temp)
    def test_exact_frozen_schema(self):
        self.assertEqual(e.sha((e.ROOT/e.SCHEMA_PATH).read_bytes()),e.SCHEMA_SHA256)
        e.Draft202012Validator.check_schema(e.schema())
    def test_strict_json_boundaries(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1.1}',b'\xff',b'"'+b'x'*e.MAX_JSON+b'"'):
            with self.subTest(raw=raw[:30]),self.assertRaises(e.SafetyError):e.strict_json(raw)
    def test_canonical_inventory_domain_uses_nul(self):
        self.assertEqual(e.inventory_root([]),hashlib.sha256(b'RULES-RESIDUE-SAFETY-INVENTORY-v1\0[]').hexdigest())
        self.assertNotEqual(e.inventory_root([]),hashlib.sha256(b'RULES-RESIDUE-SAFETY-INVENTORY-v1\\0[]').hexdigest())
    def test_path_alias_limits(self):
        for p in ('../x','a/../x','a//x','/a','a\\b','C:/x','.hidden','a/'+('x'*65),'/'.join(['a']*17),'é.json'):
            with self.subTest(path=p),self.assertRaises(e.SafetyError):e.safe_path(p)
    def test_schema_unknown_nested_and_namespace_reject_before_write(self):
        b=self.f.issue('art_audio',self.f.audio());r=receipt(b,self.f.clock)
        c=self.f.store._connect();before='\n'.join(c.iterdump());c.close()
        for mutate in (lambda x:x.update(unknown=True),lambda x:x['authority'].update(unknown=True),
                       lambda x:x['authority'].update(namespace='OTHER'),lambda x:x['source'].update(input_root='0'*64),
                       lambda x:x['review'].update(reviewer_task=x['review']['producer_task'])):
            bad=copy.deepcopy(r);mutate(bad)
            with self.assertRaises(e.SafetyError):self.f.store.test_only_ingest(e.canonical(bad))
        c=self.f.store._connect();self.assertEqual(before,'\n'.join(c.iterdump()));c.close()
    def test_timestamp_and_conservative_window(self):
        b=self.f.issue('art_audio',self.f.audio());r=receipt(b,self.f.clock)
        for value in ('2026-02-30T00:00:00Z','2026-10-09T23:59:60Z','2026-10-09T00:00:00+00:00','2026-10-09T00:00:00.1Z'):
            bad=copy.deepcopy(r);bad['issued_at']=value
            with self.assertRaises(e.SafetyError):e.validate_receipt(e.canonical(bad),self.f.clock.utc)
        r['expires_at']=stamp(self.f.clock.utc+2)
        with self.assertRaises(e.SafetyError):e.validate_receipt(e.canonical(r),self.f.clock.utc)
    def test_snapshot_reads_bound_raw_and_detects_replacement(self):
        self.f.audio();records=e.describe_directory(self.f.inputs)
        with e.Snapshot(self.f.inputs,records,self.temp/'quarantine') as snap:
            self.assertEqual(snap.bytes('silence.wav'),pcm());self.assertEqual(snap.verify(),e.inventory_root(records))
            p=self.f.inputs/'silence.wav';p.unlink();p.write_bytes(pcm());p.chmod(0o644)
            with self.assertRaises(e.SafetyError):snap.verify()
    def test_extra_missing_symlink_hardlink_and_parent_link(self):
        self.f.audio();records=e.describe_directory(self.f.inputs)
        p=self.f.inputs/'silence.wav';raw=p.read_bytes()
        for kind in ('extra','missing','symlink','hardlink'):
            with self.subTest(kind=kind):
                if kind=='extra':(self.f.inputs/'extra').write_bytes(b'x')
                else:
                    p.unlink()
                    if kind=='symlink':p.symlink_to(self.f.inputs/'source.json')
                    if kind=='hardlink':os.link(self.f.inputs/'source.json',p)
                with self.assertRaises((e.SafetyError,OSError)):e.Snapshot(self.f.inputs,records,self.temp/'quarantine')
                if kind=='extra':(self.f.inputs/'extra').unlink()
                else:
                    if p.exists() or p.is_symlink():p.unlink()
                    p.write_bytes(raw);p.chmod(0o644)
        link=self.temp/'alias';link.symlink_to(self.f.inputs,target_is_directory=True)
        with self.assertRaises(OSError):e.Snapshot(link,records,self.temp/'quarantine')
    def test_two_receipts_one_phase_and_same_occurrence_conflict(self):
        scope=self.f.audio();inputs=e.describe_directory(self.f.inputs)
        b=self.f.store.issue('TEST-UNIQUE','art_audio',scope,inputs);r=self.f.authorize(b)
        seq=self.f.store.control['receipt_sequence'];epoch=self.f.store.control['authority']['revocation_epoch']
        self.f.store.test_only_ingest(e.canonical(r));self.assertEqual(self.f.store.control['receipt_sequence'],seq)
        self.assertEqual(self.f.store.control['authority']['revocation_epoch'],epoch)
        r['receipt_id']=str(uuid.uuid4())
        with self.assertRaises(e.SafetyError):self.f.store.test_only_ingest(e.canonical(r))
        with self.assertRaises(e.SafetyError):self.f.store.issue('TEST-UNIQUE','art_audio',scope,inputs,occurrence_id=b['occurrence_id'])
    def test_wrong_phase_and_operation_rejected(self):
        b=self.f.issue('art_audio',self.f.audio());r=receipt(b,self.f.clock);r['phase']='OUTPUT'
        with self.assertRaises(e.SafetyError):self.f.store.test_only_ingest(e.canonical(r))
        r=receipt(b,self.f.clock);r['execution_id']=str(uuid.uuid4())
        with self.assertRaises(e.SafetyError):self.f.store.test_only_ingest(e.canonical(r))
    def test_production_rejects_test_store_before_effect(self):
        b=self.f.issue('art_audio',self.f.audio());self.f.authorize(b)
        with self.assertRaisesRegex(e.SafetyError,'TEST_ONLY'):admit('art_audio',self.f.inputs,b['execution_id'],store=self.f.store)
        self.assertEqual(self.f.store.operation(b['execution_id'])['state'],'ISSUED')
    def test_real_sqlite_constraints_and_pragmas(self):
        c=self.f.store._connect()
        try:
            self.assertEqual(c.execute('PRAGMA journal_mode').fetchone()[0],'wal')
            self.assertEqual(c.execute('PRAGMA synchronous').fetchone()[0],2)
            self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()[0],1)
            self.assertEqual(c.execute('PRAGMA busy_timeout').fetchone()[0],5000)
            with self.assertRaises(sqlite3.IntegrityError):c.execute("INSERT INTO phases VALUES('TEST-B018','missing','SINGLE','x',x'00',x'00')")
        finally:c.close()
    def test_independent_process_prepare_has_one_cas_winner(self):
        b=self.f.issue('art_audio',self.f.audio());self.f.authorize(b);queue=multiprocessing.get_context("fork").Queue()
        def worker():
            try:
                store=ControlStore(self.f.store.directory,_test_clock=self.f.clock)
                with e.Snapshot(self.f.inputs,b['inputs'],store.directory/'snapshots') as snap:store.prepare(b['execution_id'],snap)
                queue.put('WIN')
            except e.SafetyError:queue.put('DENY')
        jobs=[multiprocessing.get_context("fork").Process(target=worker) for _ in range(2)]
        for p in jobs:p.start()
        for p in jobs:p.join(15);self.assertEqual(p.exitcode,0)
        self.assertEqual(sorted(queue.get(timeout=2) for _ in jobs),['DENY','WIN'])
        self.assertEqual(self.f.store.operation(b['execution_id'])['version'],1)
    def test_crash_restart_all_boundaries_and_exact_replay(self):
        scope=self.f.audio()
        for point in ('before_prepare','after_prepare','after_output_fsync','before_commit','after_commit_before_response'):
            with self.subTest(point=point):
                b=self.f.issue('art_audio',scope);self.f.authorize(b)
                def worker():
                    store=ControlStore(self.f.store.directory,_test_clock=self.f.clock)
                    exercise_test_only('art_audio',self.f.inputs,b['execution_id'],store,crash=lambda p:os._exit(73) if p==point else None)
                p=multiprocessing.get_context("fork").Process(target=worker);p.start();p.join(15);self.assertEqual(p.exitcode,73)
                row=self.f.store.operation(b['execution_id']);expected='ISSUED' if point=='before_prepare' else 'COMMITTED' if point=='after_commit_before_response' else 'PREPARED'
                self.assertEqual(row['state'],expected)
                if expected!='COMMITTED':
                    with self.assertRaises(e.SafetyError):self.f.store.replay(b['execution_id'])
                result=exercise_test_only('art_audio',self.f.inputs,b['execution_id'],self.f.store)
                again=exercise_test_only('art_audio',Path('/input-not-reopened'),b['execution_id'],self.f.store)
                self.assertEqual(result['pointer'],again['pointer']);self.assertEqual(result['manifest'],again['manifest']);self.assertTrue(again['replay'])
                self.assertFalse(again['production_authority'])
    def test_recovery_revocation_source_schema_clock_aborts(self):
        # Separate owned stores prevent a revoked fixture from polluting cases.
        for kind in ('epoch','source','schema','rollback','boot'):
            with self.subTest(kind=kind):
                root=self.temp/kind;root.mkdir();f=Fixture(root);b=f.issue('art_audio',f.audio());f.authorize(b)
                with e.Snapshot(f.inputs,b['inputs'],root/'snapshots') as snap:f.store.prepare(b['execution_id'],snap)
                if kind=='epoch':f.store.test_only_reconfigure()
                elif kind in ('source','schema'):
                    src=dict(f.store.control['source']);src['schema_sha256' if kind=='schema' else 'consumer_sha256']='9'*64;f.store.test_only_reconfigure(source=src)
                elif kind=='rollback':f.clock.utc-=10
                else:f.clock.boot='OTHER-BOOT'
                with self.assertRaises(e.SafetyError):exercise_test_only('art_audio',f.inputs,b['execution_id'],f.store)
                self.assertEqual(f.store.operation(b['execution_id'])['state'],'ABORTED')
    def test_historical_replay_survives_revocation_but_downstream_does_not(self):
        b=self.f.issue('art_audio',self.f.audio());self.f.authorize(b)
        first=exercise_test_only('art_audio',self.f.inputs,b['execution_id'],self.f.store)
        self.f.store.test_only_reconfigure()
        self.assertEqual(self.f.store.replay(b['execution_id'])['pointer'],first['pointer'])
        with self.assertRaises(e.SafetyError):self.f.store.replay(b['execution_id'],current=True)
    def test_restored_database_cannot_restore_guard_epoch_or_clock(self):
        c=self.f.store._connect();backup=self.temp/'backup.sqlite';target=sqlite3.connect(backup);c.backup(target);target.close();c.close()
        self.f.store.test_only_reconfigure()
        c=self.f.store._connect();older=sqlite3.connect(backup);older.backup(c);older.close();c.close()
        with self.assertRaisesRegex(e.SafetyError,'restored/conflicting'):ControlStore(self.f.store.directory,_test_clock=self.f.clock)
    def test_unknown_scope_rejects_without_operation_or_control_write(self):
        scope=self.f.audio();scope['unknown_authority']='ALLOW'
        conn=self.f.store._connect();before='\n'.join(conn.iterdump());conn.close()
        with self.assertRaises(e.SafetyError):self.f.issue('art_audio',scope)
        conn=self.f.store._connect();self.assertEqual(before,'\n'.join(conn.iterdump()));conn.close()
    def test_abort_invalidates_older_database_even_with_invalid_clock(self):
        b=self.f.issue('art_audio',self.f.audio());self.f.authorize(b)
        conn=self.f.store._connect();backup=self.temp/'before-abort.sqlite';target=sqlite3.connect(backup);conn.backup(target);target.close();conn.close()
        self.f.clock.utc-=10;self.f.store.abort(b['execution_id'],'clock rollback')
        self.assertEqual(self.f.store.operation(b['execution_id'])['state'],'ABORTED')
        conn=self.f.store._connect();older=sqlite3.connect(backup);older.backup(conn);older.close();conn.close()
        self.f.clock.utc+=10
        with self.assertRaisesRegex(e.SafetyError,'restored/conflicting'):ControlStore(self.f.store.directory,_test_clock=self.f.clock)

    def test_actual_signed_git_custody_is_not_semantic_authority(self):
        head=e.git_bytes(e.ROOT,'rev-parse','HEAD').decode().strip();tree=e.git_bytes(e.ROOT,'rev-parse','HEAD^{tree}').decode().strip()
        path='schemas/r2/exemption-protocol-v1.schema.json';blob=e.git_bytes(e.ROOT,'rev-parse',head+':'+path).decode().strip()
        locator={'commit':head,'tree':tree,'path':path,'blob':blob}
        self.assertEqual(e.verify_custody(e.ROOT,locator,trusted_locator=locator),e.git_bytes(e.ROOT,'cat-file','blob',blob))
        changed=dict(locator,commit='0'*40)
        with self.assertRaisesRegex(e.SafetyError,'independently received'):e.verify_custody(e.ROOT,changed,trusted_locator=locator)
        # A real valid custody signature on old bytes is not a safety statement.
        b=self.f.issue('art_audio',self.f.audio());r=receipt(b,self.f.clock)
        with self.assertRaises(e.SafetyError):e.verify_authority(e.canonical(r),b'{}',b'{}',locator,e.ROOT,locator)

    def clock_fixture(self, name):
        root=self.temp/name;root.mkdir();f=Fixture(root);f.clock=ObservationClock()
        f.store=ControlStore(f.store.directory,_test_clock=f.clock)
        binding=f.issue('art_audio',f.audio());f.authorize(binding)
        return f,binding

    def assert_clock_state(self, f, utc, monotonic_ns):
        c=f.store._connect()
        try:control=e.strict_json(c.execute('SELECT document FROM control WHERE id=1').fetchone()[0])
        finally:c.close()
        self.assertEqual(control['max_seen_utc'],utc)
        self.assertEqual(control['last_monotonic_ns'],monotonic_ns)
        self.assertEqual(control['boot'],'TEST-BOOT')
        self.assertEqual(e.strict_json((f.store.directory/'guard.json').read_bytes()),ControlStore._guard(control))
        return control

    def run_observed_phase(self, f, binding, phase, observations):
        if phase=='prepare':
            f.clock.arm(observations)
            with e.Snapshot(f.inputs,binding['inputs'],f.store.directory/'snapshots') as snap:
                f.store.prepare(binding['execution_id'],snap)
        else:
            def before_commit(point):
                if point=='before_commit':f.clock.arm(observations)
            exercise_test_only('art_audio',f.inputs,binding['execution_id'],f.store,crash=before_commit)

    def test_prepare_latest_clock_observation_survives_restart(self):
        f,b=self.clock_fixture('prepare-high');initial=f.clock.utc
        self.run_observed_phase(f,b,'prepare',[(initial,2000,'TEST-BOOT'),(initial,3000,'TEST-BOOT'),(initial+30,30000001000,'TEST-BOOT')])
        self.assertFalse(f.clock.pending);self.assert_clock_state(f,initial+30,30000001000)
        reopened=ControlStore(f.store.directory,_test_clock=f.clock)
        self.assertEqual(reopened.operation(b['execution_id'])['state'],'PREPARED')
        f.clock.utc=initial+1;f.clock.monotonic_ns+=1000000000
        with self.assertRaisesRegex(e.SafetyError,'clock rollback'):ControlStore(f.store.directory,_test_clock=f.clock)
        with self.assertRaisesRegex(e.SafetyError,'clock rollback'):exercise_test_only('art_audio',f.inputs,b['execution_id'],f.store)
        self.assertEqual(f.store.operation(b['execution_id'])['state'],'ABORTED')
        self.assert_clock_state(f,initial+30,30000001000)

    def test_commit_latest_clock_observation_survives_restart(self):
        f,b=self.clock_fixture('commit-high');initial=f.clock.utc
        self.run_observed_phase(f,b,'commit',[(initial,2000,'TEST-BOOT'),(initial,3000,'TEST-BOOT'),(initial+30,30000001000,'TEST-BOOT')])
        self.assertFalse(f.clock.pending);self.assert_clock_state(f,initial+30,30000001000)
        reopened=ControlStore(f.store.directory,_test_clock=f.clock)
        first=reopened.replay(b['execution_id'],current=True)
        self.assertEqual(reopened.operation(b['execution_id'])['version'],2)
        f.clock.utc=initial+1;f.clock.monotonic_ns+=1000000000
        with self.assertRaisesRegex(e.SafetyError,'clock rollback'):ControlStore(f.store.directory,_test_clock=f.clock)
        with self.assertRaisesRegex(e.SafetyError,'clock rollback'):reopened.replay(b['execution_id'],current=True)
        self.assertEqual(reopened.replay(b['execution_id'])['pointer'],first['pointer'])
        self.assert_clock_state(f,initial+30,30000001000)

    def assert_within_transaction_rollback(self, phase):
        for kind in ('utc','monotonic','boot'):
            with self.subTest(phase=phase,kind=kind):
                f,b=self.clock_fixture(phase+'-'+kind);initial=f.clock.utc
                before=f.store.control.copy()
                last=(initial+1,31000001000,'TEST-BOOT') if kind=='utc' else (initial+30,1000001000,'TEST-BOOT') if kind=='monotonic' else (initial+30,31000001000,'OTHER-BOOT')
                observations=[(initial,2000,'TEST-BOOT'),(initial+30,30000001000,'TEST-BOOT'),last]
                with self.assertRaises(e.SafetyError):self.run_observed_phase(f,b,phase,observations)
                self.assertFalse(f.clock.pending)
                # Even a rejected callback cannot discard a previously trusted
                # observation. Only clock/generation changes may survive its
                # savepoint rollback; no business authority or receipt is added.
                control=self.assert_clock_state(f,initial+30,30000001000)
                for key in ('authority','source','receipt_sequence','checkpoint_expires','revoked_receipts'):
                    self.assertEqual(control[key],before[key])
                row=f.store.operation(b['execution_id'])
                self.assertEqual(row['state'],'ISSUED' if phase=='prepare' else 'ABORTED')
                self.assertIsNone(row['result'])
                with self.assertRaises(e.SafetyError):f.store.replay(b['execution_id'])
                with self.assertRaises(e.SafetyError):ControlStore(f.store.directory,_test_clock=f.clock)
                f.clock.utc=initial+30;f.clock.monotonic_ns=32000001000;f.clock.boot='TEST-BOOT'
                reopened=ControlStore(f.store.directory,_test_clock=f.clock)
                self.assertEqual(reopened.control['max_seen_utc'],initial+30)
                self.assertEqual(reopened.operation(b['execution_id'])['state'],row['state'])

    def test_prepare_rejects_rollback_between_trusted_observations(self):
        self.assert_within_transaction_rollback('prepare')

    def test_commit_rejects_rollback_between_trusted_observations(self):
        self.assert_within_transaction_rollback('commit')

    def test_tolerated_utc_rollback_never_lowers_high_water_in_either_phase(self):
        for phase in ('prepare','commit'):
            with self.subTest(phase=phase):
                f,b=self.clock_fixture('tolerance-'+phase);initial=f.clock.utc
                self.run_observed_phase(f,b,phase,[(initial,2000,'TEST-BOOT'),(initial+30,30000001000,'TEST-BOOT'),(initial+29,31000001000,'TEST-BOOT')])
                self.assertFalse(f.clock.pending);self.assert_clock_state(f,initial+30,31000001000)
                f.clock.utc=initial+28;f.clock.monotonic_ns+=1000000000
                ControlStore(f.store.directory,_test_clock=f.clock)
                f.clock.utc=initial+27
                with self.assertRaisesRegex(e.SafetyError,'clock rollback'):ControlStore(f.store.directory,_test_clock=f.clock)

    def test_database_restore_cannot_discard_later_transaction_clock(self):
        f,b=self.clock_fixture('restore-high');initial=f.clock.utc
        c=f.store._connect();backup=self.temp/'old-clock.sqlite3';target=sqlite3.connect(backup)
        try:c.backup(target)
        finally:target.close();c.close()
        self.run_observed_phase(f,b,'prepare',[(initial,2000,'TEST-BOOT'),(initial,3000,'TEST-BOOT'),(initial+30,30000001000,'TEST-BOOT')])
        self.assert_clock_state(f,initial+30,30000001000)
        c=f.store._connect();older=sqlite3.connect(backup)
        try:older.backup(c)
        finally:older.close();c.close()
        f.clock.utc=initial+1;f.clock.monotonic_ns+=1000000000
        with self.assertRaisesRegex(e.SafetyError,'restored/conflicting'):ControlStore(f.store.directory,_test_clock=f.clock)

    def test_opening_checkpoint_failure_retains_valid_observation(self):
        f,b=self.clock_fixture('opening-checkpoint');before=copy.deepcopy(f.store.control)
        f.clock.utc=before['checkpoint_expires']+1;f.clock.monotonic_ns+=3601000000000
        observed=f.clock.utc;monotonic=f.clock.monotonic_ns
        with e.Snapshot(f.inputs,b['inputs'],f.store.directory/'snapshots') as snap:
            with self.assertRaisesRegex(e.SafetyError,'authority checkpoint stale'):
                f.store.prepare(b['execution_id'],snap)
        control=self.assert_clock_state(f,observed,monotonic)
        for key in ('authority','source','receipt_sequence','checkpoint_expires','revoked_receipts'):
            self.assertEqual(control[key],before[key])
        self.assertEqual(f.store.operation(b['execution_id'])['state'],'ISSUED')
        self.assertEqual(f.store.operation(b['execution_id'])['version'],0)
        f.clock.utc=before['max_seen_utc']+1;f.clock.monotonic_ns+=1000000000
        with self.assertRaisesRegex(e.SafetyError,'clock rollback'):
            ControlStore(f.store.directory,_test_clock=f.clock)
        with self.assertRaisesRegex(e.SafetyError,'clock rollback'):
            exercise_test_only('art_audio',f.inputs,b['execution_id'],f.store)
        self.assertEqual(f.store.operation(b['execution_id'])['state'],'ABORTED')
        self.assertIsNone(f.store.operation(b['execution_id'])['result'])
        self.assert_clock_state(f,observed,monotonic)

    def test_opening_source_and_configuration_rejections_keep_clock(self):
        # Explicit TEST_ONLY fault injection into production checks. No signed
        # receipt or production admission is created by these synthetic controls.
        from unittest.mock import patch
        from tools import content_safety_control as module
        for kind,message in (('configuration','operator configuration changed'),
                             ('authority','operator authority/source changed'),
                             ('source','current source/code/schema/policy changed')):
            with self.subTest(kind=kind):
                f,b=self.clock_fixture('opening-'+kind);control=copy.deepcopy(f.store.control)
                control['mode']='PRODUCTION'
                c=f.store._connect()
                try:c.execute('UPDATE control SET document=? WHERE id=1',(e.canonical(control),))
                finally:c.close()
                config={'authority':copy.deepcopy(control['authority']),'source':copy.deepcopy(control['source'])}
                with patch.object(module,'PRODUCTION_ROOT',f.store.directory), \
                     patch.object(module,'system_clock',f.clock), \
                     patch.object(module,'_protected_json',return_value=config) as configuration, \
                     patch.object(module,'current_source',return_value=dict(control['source'],input_root='0'*64)) as source:
                    store=ControlStore.production();f.store=store
                    f.clock.utc+=30;f.clock.monotonic_ns+=30000000000
                    if kind=='configuration':configuration.return_value=dict(config,changed=True)
                    elif kind=='authority':
                        changed=copy.deepcopy(config);changed['authority']['revocation_epoch']+=1
                        store.configuration=changed;configuration.return_value=changed
                    else:source.return_value=dict(control['source'],consumer_sha256='9'*64,input_root='0'*64)
                    with e.Snapshot(f.inputs,b['inputs'],store.directory/'snapshots') as snap:
                        with self.assertRaisesRegex(e.SafetyError,message):store.prepare(b['execution_id'],snap)
                    after=self.assert_clock_state(f,f.clock.utc,f.clock.monotonic_ns)
                    for key in ('authority','source','receipt_sequence','checkpoint_expires','revoked_receipts'):
                        self.assertEqual(after[key],control[key])
                    self.assertEqual(store.operation(b['execution_id'])['state'],'ISSUED')
                    self.assertEqual(store.operation(b['execution_id'])['version'],0)
                    configuration.return_value=config;store.configuration=config
                    source.return_value=dict(control['source'],input_root='0'*64)
                    f.clock.utc-=29;f.clock.monotonic_ns+=1000000000
                    with self.assertRaisesRegex(e.SafetyError,'clock rollback'):ControlStore.production()

    def test_untrusted_opening_clock_or_control_does_not_write(self):
        for kind in ('utc','monotonic','boot','unestablished','guard','malformed-guard','malformed-control'):
            with self.subTest(kind=kind):
                f,b=self.clock_fixture('untrusted-'+kind)
                if kind=='utc':f.clock.utc-=3
                elif kind=='monotonic':f.clock.monotonic_ns-=1
                elif kind=='boot':f.clock.boot='UNTRUSTED-BOOT'
                elif kind in ('unestablished','malformed-control'):
                    c=f.store._connect()
                    try:
                        control=copy.deepcopy(f.store.control);control['clock_established']=False
                        raw=b'{' if kind=='malformed-control' else e.canonical(control)
                        c.execute('UPDATE control SET document=? WHERE id=1',(raw,))
                    finally:c.close()
                else:
                    guard=ControlStore._guard(f.store.control);guard['generation']+=1
                    (f.store.directory/'guard.json').write_bytes(b'{' if kind=='malformed-guard' else e.canonical(guard))
                c=f.store._connect()
                try:before='\n'.join(c.iterdump())
                finally:c.close()
                guard=(f.store.directory/'guard.json').read_bytes()
                with e.Snapshot(f.inputs,b['inputs'],f.store.directory/'snapshots') as snap:
                    with self.assertRaises(e.SafetyError):f.store.prepare(b['execution_id'],snap)
                c=f.store._connect()
                try:self.assertEqual('\n'.join(c.iterdump()),before)
                finally:c.close()
                self.assertEqual((f.store.directory/'guard.json').read_bytes(),guard)
                self.assertEqual(f.store._write_clocks,{})

    def assert_publication_failure(self, boundary):
        from unittest.mock import patch
        from tools import content_safety_control as module
        f,b=self.clock_fixture('publication-'+boundary);initial=f.clock.utc
        original=copy.deepcopy(f.store.control);calls=[]
        write=module.durable_write;replace=module.os.replace;sync=module.fsync_dir
        def fail_write(path,data):
            if Path(path).name.startswith('guard-') and not calls:
                calls.append('before_guard');raise OSError('injected before guard publication')
            return write(path,data)
        def fail_replace(src,dst):
            result=replace(src,dst)
            if Path(dst).name=='guard.json' and not calls:
                calls.append('after_guard');raise OSError('injected after guard publication')
            return result
        def fail_sync(path):
            sync(path);calls.append('sync')
            if len(calls)==2:raise OSError('injected after database commit')
        target=module.os if boundary=='after_guard' else module
        name='replace' if boundary=='after_guard' else 'durable_write' if boundary=='before_guard' else 'fsync_dir'
        replacement=fail_replace if boundary=='after_guard' else fail_write if boundary=='before_guard' else fail_sync
        with e.Snapshot(f.inputs,b['inputs'],f.store.directory/'snapshots') as snap:
            f.clock.arm([(initial,2000,'TEST-BOOT'),(initial,3000,'TEST-BOOT'),(initial+30,30000001000,'TEST-BOOT')])
            with patch.object(target,name,side_effect=replacement),self.assertRaisesRegex(OSError,'injected'):
                f.store.prepare(b['execution_id'],snap)
        self.assertTrue(calls);self.assertFalse(f.clock.pending);self.assertEqual(f.store._write_clocks,{})
        row=f.store.operation(b['execution_id']);self.assertIsNone(row['result'])
        if boundary=='after_guard':
            self.assertEqual(row['state'],'ISSUED');self.assertEqual(row['version'],0)
            guard=e.strict_json((f.store.directory/'guard.json').read_bytes())
            self.assertEqual(guard['max_seen_utc'],initial+30)
            c=f.store._connect()
            try:self.assertEqual(f.store._read_control(c),original)
            finally:c.close()
            with self.assertRaisesRegex(e.SafetyError,'restored/conflicting'):
                ControlStore(f.store.directory,_test_clock=f.clock)
        else:
            control=self.assert_clock_state(f,initial+30,30000001000)
            for key in ('authority','source','receipt_sequence','checkpoint_expires','revoked_receipts'):
                self.assertEqual(control[key],original[key])
            reopened=ControlStore(f.store.directory,_test_clock=f.clock)
            self.assertEqual(row['state'],'ISSUED' if boundary=='before_guard' else 'PREPARED')
            self.assertEqual(row['version'],0 if boundary=='before_guard' else 1)
            if boundary=='after_commit':
                result=exercise_test_only('art_audio',f.inputs,b['execution_id'],reopened)
                replay=exercise_test_only('art_audio',Path('/input-not-reopened'),b['execution_id'],reopened)
                self.assertEqual(result['pointer'],replay['pointer'])
                self.assertEqual(reopened.operation(b['execution_id'])['version'],2)
            f.clock.utc=initial+1;f.clock.monotonic_ns+=1000000000
            with self.assertRaisesRegex(e.SafetyError,'clock rollback'):
                ControlStore(f.store.directory,_test_clock=f.clock)

    def test_failure_before_guard_rolls_back_effects_but_keeps_clock(self):
        self.assert_publication_failure('before_guard')

    def test_failure_after_guard_retains_conflict_and_denies_recovery(self):
        self.assert_publication_failure('after_guard')

    def test_failure_after_database_commit_preserves_recoverable_state(self):
        self.assert_publication_failure('after_commit')

    def test_savepoint_failure_occurs_before_any_clock_observation(self):
        from unittest.mock import patch
        f,b=self.clock_fixture('savepoint-failure');c=f.store._connect()
        before='\n'.join(c.iterdump());guard=(f.store.directory/'guard.json').read_bytes()
        class Connection:
            def execute(self,sql,*args):
                if sql.startswith('SAVEPOINT'):raise sqlite3.OperationalError('injected savepoint failure')
                return c.execute(sql,*args)
            def __getattr__(self,key):return getattr(c,key)
        with e.Snapshot(f.inputs,b['inputs'],f.store.directory/'snapshots') as snap:
            f.clock.arm([(f.clock.utc+30,30000001000,'TEST-BOOT')])
            with patch.object(f.store,'_connect',return_value=Connection()), \
                 self.assertRaisesRegex(sqlite3.OperationalError,'injected savepoint failure'):
                f.store.prepare(b['execution_id'],snap)
        self.assertEqual(f.clock.trace,[]);self.assertEqual(f.store._write_clocks,{})
        c=f.store._connect()
        try:self.assertEqual('\n'.join(c.iterdump()),before)
        finally:c.close()
        self.assertEqual((f.store.directory/'guard.json').read_bytes(),guard)

if __name__=='__main__':unittest.main()
