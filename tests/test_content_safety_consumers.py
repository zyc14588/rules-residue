"""Distinct bounded consumer fixtures. Synthetic receipts remain TEST_ONLY."""
from __future__ import annotations
import binascii
import copy
import io
import json
import os
import shutil
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
from unittest.mock import patch

from tools.lib import content_safety_evidence as e
from tools import content_safety_consumers as c
from tests.test_content_safety_evidence import Fixture,receipt,remove_owned,pcm
from tools.lib.common import GAME_PACKAGE_ROOT


def png(width=1,height=1,colour=2):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',binascii.crc32(kind+data)&0xffffffff)
    channels=3 if colour==2 else 4
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,colour,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(width*channels))*height))+chunk(b'IEND',b'')


def region_fixture(f,region_id='TEST-REGION-1',revision='1'):
    refs={};subjects=[]
    dossier=f.put('dossier.json',{'approvals':{x:'APPROVED' for x in ('T1','T2','T3_ENVELOPE','C1_REVEAL_FAMILY')},
        'design_complete_gate':{x:True for x in ('rules_exceptions_frozen','timeline_verified','npc_epistemic_verified','routes_closed','failure_covered','retreat_covered','remediation_covered','tpk_covered','reachability_verified','style_frozen','visual_anchors_frozen','no_blocker')}})
    refs['dossier']=dossier
    reports={}
    for i in range(7):
        layer='V'+str(i);ref=f.put(layer+'.json',{'layer':layer,'result':'PASS','candidate_revision':revision,'scope':'TEST_ONLY benign structure'})
        reports[layer]=ref;refs[layer]=ref;subjects.append({'kind':'validation_report','layer':layer,'region_id':region_id,'revision':revision,'sha256':ref['sha256']})
    approvals={}
    for kind in ('T1','T2','C1'):
        ref=f.put(kind+'.json',{'kind':kind,'decision':'APPROVED','scope':'TEST_ONLY mechanics, no actual Owner/world approval'})
        approvals[kind]=ref;refs[kind]=ref;subjects.append({'kind':'owner_approval','authority':kind,'region_id':region_id,'revision':revision,'sha256':ref['sha256']})
    dab=f.put('dab.json',{'schema_version':'1.0.0','dab_id':'TEST-DAB-1','tier':'FORENSIC','subject_ref':'dossier',
        'decision_refs':[],'approval_refs':list(approvals),'generation_refs':[],'validation_refs':list(reports),
        'repair_refs':[],'waiver_refs':[],'release_refs':[],'private_chain_of_thought_recorded':False})
    refs['dab']=dab
    f.put('region.json',{'schema_version':'1.0.0','acceptance_id':'TEST-ACCEPT-1','dossier_ref':'dossier','dab_ref':'dab',
        'validation_layers':{x:'PASS' for x in reports},'defects':[],'result':'PASS','owner_approvals':list(approvals),'candidate_hashes':[revision]})
    scope={'consumer':'region','acceptance':'region.json','region_id':region_id,'candidate_revision':revision,'references':refs,'reports':reports,'owner_approvals':approvals}
    return scope,subjects


def image_fixture(f):
    from tools.story_construction import visual_order_hash
    # Construct a minimal v1 visual request within the unchanged native schema.
    source=e.strict_json((e.ROOT/'schemas/story-construction/visual-order-v1.schema.json').read_bytes())
    order={}
    for key,spec in source['properties'].items():
        if 'const' in spec:order[key]=spec['const']
        elif spec.get('type')=='array':order[key]=['TEST-REF'] if spec.get('minItems',0)>0 else []
        elif spec.get('type')=='boolean':order[key]=False
        elif spec.get('type')=='string':order[key]='TEST-REF'
    order.update(schema_version='1.0.0',order_id='VISUAL-ORDER-TEST-1',order_authority='VALIDATED_VISUAL_ORDER_PACKAGE',proposed_fact_classes=[])
    order['order_hash']=visual_order_hash(order)
    ref=f.put('reference.json',{'revision':'1','text':'TEST_ONLY benign visual technical reference'})
    f.put('order.json',order);f.put('asset.png',png())
    packet={'schema_version':'rules-residue.task-packet/1.1','task_id':'RR-TASK-9000','status':'PLANNED','owner':'grok','task_type':'art','objective':'TEST_ONLY pixel',
        'authority':['TEST-REF'],'inputs':['TEST-REF'],'allowed_paths':['workflow/returns/visual/TEST.png'],'forbidden_paths':['game-package/'],
        'open_decisions':[],'acceptance':['TEST-REF'],'expected_outputs':['TEST-REF']}
    f.put('packet.json',packet)
    return {'consumer':'media','kind':'image','packet':'packet.json','order':'order.json','asset':'asset.png','references':{'TEST-REF':ref},'targets':['workflow/returns/visual/TEST.png']}


class ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp=Path(tempfile.mkdtemp(prefix='b018-consumers-'));self.addCleanup(remove_owned,self.temp);self.f=Fixture(self.temp)
    def run_case(self,stage,scope,subjects=None):
        b=self.f.issue(stage,scope);self.f.authorize(b,subjects=subjects)
        return c.exercise_test_only(stage,self.f.inputs,b['execution_id'],self.f.store),b
    def test_audio_real_decoder_and_bound_transcript(self):
        result,b=self.run_case('art_audio',self.f.audio())
        self.assertEqual(result['manifest']['details']['decode']['frames'],4)
        self.assertFalse(result['manifest']['production_authority'])
        (self.f.inputs/'transcript.json').write_bytes(b'{}')
        # Committed historical response replays; a new occurrence cannot reuse bytes.
        with self.assertRaises(e.SafetyError):
            b2=self.f.store.issue('TEST-CHANGED','art_audio',b['scope'],b['inputs']);self.f.authorize(b2)
            c.exercise_test_only('art_audio',self.f.inputs,b2['execution_id'],self.f.store)
    def test_absent_transcript_requires_explicit_review(self):
        scope=self.f.audio(absent=True);b=self.f.issue('art_audio',scope);self.f.authorize(b)
        with self.assertRaisesRegex(e.SafetyError,'reviewed authority'):c.exercise_test_only('art_audio',self.f.inputs,b['execution_id'],self.f.store)
        b2=self.f.issue('art_audio',scope);self.f.authorize(b2,subjects=[{'kind':'audio_transcript_absence','asset_id':'TEST-SILENCE-1','input_root':b2['input_root']}])
        self.assertEqual(c.exercise_test_only('art_audio',self.f.inputs,b2['execution_id'],self.f.store)['manifest']['details']['kind'],'audio')
    def test_pcm_exact_format_and_boundary_sizes(self):
        for rate in (44100,48000):
            for channels in (1,2):
                data=pcm(rate*60,channels,rate)
                result=c.inspect_pcm(data,{'channels':channels,'sample_rate':rate,'frames':rate*60})
                self.assertEqual(result['frames'],rate*60)
        valid=pcm();decl={'channels':1,'sample_rate':48000,'frames':4}
        bads=[valid+b'\0',valid[:12]+b'JUNK'+valid[16:],valid[:20]+b'\x03\x00'+valid[22:],pcm(0),pcm(48000*60+1)]
        for bad in bads:
            with self.subTest(size=len(bad)),self.assertRaises(e.SafetyError):c.inspect_pcm(bad,decl)
    def test_png_crc_chunks_dimensions_and_decode_bound(self):
        self.assertEqual(c.inspect_png(png())['width'],1)
        for bad in (b'GIF89a'+b'0'*40,png()+b'junk',png()[:-1]+b'0',png(4097,1)):
            with self.subTest(size=len(bad)),self.assertRaises(e.SafetyError):c.inspect_png(bad)
        with patch.object(c.time,'monotonic',side_effect=[0,3]):
            with self.assertRaisesRegex(e.SafetyError,'budget'):c.inspect_png(png())
    def test_image_runs_unchanged_native_visual_helper(self):
        scope=image_fixture(self.f)
        result,b=self.run_case('art_audio',scope)
        self.assertEqual(result['manifest']['details']['decode']['format'],'PNG')
        self.assertEqual(result['manifest']['details']['kind'],'image')
    def test_region_requires_actual_layer_review_not_pass_strings(self):
        scope,subjects=region_fixture(self.f);b=self.f.issue('region_acceptance',scope);self.f.authorize(b)
        with self.assertRaisesRegex(e.SafetyError,'reviewed authority'):c.exercise_test_only('region_acceptance',self.f.inputs,b['execution_id'],self.f.store)
        result,b=self.run_case('region_acceptance',scope,subjects)
        self.assertEqual(result['manifest']['details']['region_id'],'TEST-REGION-1')
    def test_region_missing_owner_layer_and_revision_are_distinct_rejections(self):
        scope,subjects=region_fixture(self.f)
        for kind in ('owner','layer','revision'):
            bad=copy.deepcopy(scope)
            if kind=='owner':bad['owner_approvals'].pop('T1')
            if kind=='layer':bad['reports'].pop('V6')
            if kind=='revision':bad['candidate_revision']='2'
            b=self.f.issue('region_acceptance',bad);self.f.authorize(b,subjects=subjects)
            with self.assertRaises(e.SafetyError):c.exercise_test_only('region_acceptance',self.f.inputs,b['execution_id'],self.f.store)
    def _cross(self):
        # Six real child transactions, sharing the same controlled namespace/store.
        children={};rows=[];combined=self.temp/'combined';combined.mkdir();refs={}
        for i in range(6):
            child_root=self.temp/('child'+str(i));child_root.mkdir();f=Fixture(child_root);f.store=self.f.store
            rid='TEST-REGION-'+str(i);scope,subjects=region_fixture(f,rid)
            b=f.issue('region_acceptance',scope);f.authorize(b,subjects=subjects)
            admission=c.exercise_test_only('region_acceptance',f.inputs,b['execution_id'],f.store)
            manifest=f.store.directory/admission['pointer']['path']
            target=combined/('child'+str(i));target.mkdir()
            manifest_raw=manifest.read_bytes();(target/'admission.json').write_bytes(manifest_raw)
            closure={}
            for record in b['inputs']:
                data=(f.inputs/record['path']).read_bytes();(target/record['path']).write_bytes(data)
                closure[record['path']]={'path':'child'+str(i)+'/'+record['path'],'sha256':e.sha(data),'revision':'1'}
            children[rid]={'execution_id':b['execution_id'],'revision':'1','manifest':{'path':'child'+str(i)+'/admission.json','sha256':e.sha(manifest_raw),'revision':'1'},'closure':closure}
            rows.append({'region_id':rid,'imports':['symbol-'+str((i+1)%6)],'exports':['symbol-'+str(i)],'revision':1,'status':'FROZEN'})
        matrix={'schema_version':'rules-residue.story-construction.region-interface-matrix/1.0.0','matrix_id':'TEST-MATRIX-1','minimum_region_count':6,'regions':rows,'all_interfaces_frozen':True,'formal_vertical_slice_allowed':False}
        (combined/'matrix.json').write_bytes(e.canonical(matrix))
        for p in combined.rglob('*'):
            if p.is_file():p.chmod(0o644)
        self.f.inputs=combined
        return {'consumer':'cross-region','matrix':'matrix.json','references':refs,'children':children}
    def test_cross_region_consumes_six_actual_current_child_admissions(self):
        scope=self._cross();result,b=self.run_case('cross_region_validation',scope)
        self.assertEqual(len(result['manifest']['details']['adjacency']),6)
    def test_cross_region_rejects_ambiguous_edges_and_child_revision(self):
        scope=self._cross();matrix=e.strict_json((self.f.inputs/'matrix.json').read_bytes())
        matrix['regions'][1]['exports']=['symbol-0'];(self.f.inputs/'matrix.json').write_bytes(e.canonical(matrix))
        b=self.f.issue('cross_region_validation',scope);self.f.authorize(b)
        with self.assertRaisesRegex(e.SafetyError,'missing/ambiguous'):c.exercise_test_only('cross_region_validation',self.f.inputs,b['execution_id'],self.f.store)
    def _build(self):
        shutil.rmtree(self.f.inputs);shutil.copytree(GAME_PACKAGE_ROOT,self.f.inputs)
        for p in self.f.inputs.rglob('*'):
            if p.is_file():p.chmod(0o755 if p.stat().st_mode & 0o111 else 0o644)
        scope={'consumer':'build','validation':'module-registry'};b=self.f.issue('build',scope);self.f.authorize(b,phase='INPUT')
        with self.assertRaises(c.AwaitingOutputReview):c.exercise_test_only('build',self.f.inputs,b['execution_id'],self.f.store)
        row=self.f.store.operation(b['execution_id']);self.assertEqual(row['state'],'PREPARED')
        work=self.f.store.directory/'work'/b['execution_id'];computed=e.strict_json((work/'computed.json').read_bytes())
        self.f.authorize(b,phase='OUTPUT',outputs=computed['outputs'])
        return b,work
    def test_build_same_operation_input_output_and_zero_encode_replay(self):
        b,work=self._build()
        with patch('tools.build_package._quarantine_encode',side_effect=AssertionError('must reuse durable quarantined output')):
            result=c.exercise_test_only('build',self.f.inputs,b['execution_id'],self.f.store)
            again=c.exercise_test_only('build',Path('/no-input-read'),b['execution_id'],self.f.store)
        self.assertEqual(result['pointer'],again['pointer']);self.assertTrue(again['replay'])
        self.assertEqual(result['manifest']['details']['archive_sha256'],'29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314')
        self.assertEqual(len(result['manifest']['details']['members']),37)
        self.assertEqual(self.f.store.control['receipt_sequence'],2);self.assertEqual(self.f.store.control['authority']['revocation_epoch'],0)
    def test_build_output_phase_cannot_precede_input_prepare(self):
        shutil.rmtree(self.f.inputs);shutil.copytree(GAME_PACKAGE_ROOT,self.f.inputs)
        for p in self.f.inputs.rglob('*'):
            if p.is_file():p.chmod(0o755 if p.stat().st_mode & 0o111 else 0o644)
        b=self.f.issue('build',{'consumer':'build','validation':'module-registry'})
        with self.assertRaisesRegex(e.SafetyError,'prepared INPUT'):self.f.authorize(b,phase='OUTPUT')
    def test_build_modified_quarantine_and_output_receipt_are_rejected(self):
        b,work=self._build();(work/'archive.trpgpkg').chmod(0o600);(work/'archive.trpgpkg').write_bytes(b'changed')
        with self.assertRaises(e.SafetyError):c.exercise_test_only('build',self.f.inputs,b['execution_id'],self.f.store)
        self.assertEqual(self.f.store.operation(b['execution_id'])['state'],'ABORTED')
    def test_build_full_snapshot_runs_original_current_validator(self):
        shutil.rmtree(self.f.inputs);shutil.copytree(GAME_PACKAGE_ROOT,self.f.inputs)
        for p in self.f.inputs.rglob('*'):
            if p.is_file():p.chmod(0o755 if p.stat().st_mode & 0o111 else 0o644)
        source=dict(self.f.source)
        source['game_commit']=e.git_bytes(e.ROOT,'rev-parse','HEAD').decode().strip()
        source['game_tree']=e.git_bytes(e.ROOT,'rev-parse','HEAD^{tree}').decode().strip()
        from tools.content_safety_control import ControlStore
        self.f.store=ControlStore.create_test_only(self.temp/'full-validation-store',source,clock=self.f.clock)
        b=self.f.issue('build',{'consumer':'build','validation':'full-project'});self.f.authorize(b,phase='INPUT')
        with self.assertRaises(c.AwaitingOutputReview):c.exercise_test_only('build',self.f.inputs,b['execution_id'],self.f.store)
        work=self.f.store.directory/'work'/b['execution_id']
        self.assertEqual(e.sha((work/'archive.trpgpkg').read_bytes()),'29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314')

    def test_rc_success_consumes_actual_media_region_cross_build_chain(self):
        cross_scope=self._cross();cross,cross_binding=self.run_case('cross_region_validation',cross_scope)
        region_id=next(iter(cross_scope['children'].values()))['execution_id']
        region=self.f.store.replay(region_id,current=True)
        media_root=self.temp/'rc-media';media_root.mkdir();mf=Fixture(media_root);mf.store=self.f.store
        mb=mf.issue('art_audio',mf.audio());mf.authorize(mb)
        media=c.exercise_test_only('art_audio',mf.inputs,mb['execution_id'],mf.store)
        self.f.inputs=self.temp/'rc-build';self.f.inputs.mkdir()
        build_binding,work=self._build()
        build_result=c.exercise_test_only('build',self.f.inputs,build_binding['execution_id'],self.f.store)
        self.f.inputs=self.temp/'rc-input';self.f.inputs.mkdir()
        refs={};subjects=[]
        archive_ref=self.f.put('archive.trpgpkg',(work/'archive.trpgpkg').read_bytes());refs['archive']=archive_ref
        stage_results=[media,region,cross,build_result]
        executions=[]
        for index,result in enumerate(stage_results):
            execution=result['manifest']['execution_id'];executions.append(execution)
            refs['stage-'+str(index)]=self.f.put('stage-'+str(index)+'.json',e.canonical(result['manifest']))
            subjects.append({'kind':'stage_admission','execution_id':execution,'manifest_sha256':result['pointer']['sha256']})
        conn=self.f.store._connect()
        try: raw=conn.execute("SELECT receipt FROM phases WHERE execution_id=? AND phase='OUTPUT'",(build_binding['execution_id'],)).fetchone()[0]
        finally:conn.close()
        r=e.strict_json(raw)
        statement={'schema_version':'1.0.0','kind':'CONTENT_SAFETY_ACCEPTANCE_STATEMENT','namespace':r['namespace'],
            'receipt_sha256':e.sha(raw),'decision':r['decision'],'checkpoint':r['authority']['checkpoint'],'revocation_epoch':r['authority']['revocation_epoch'],
            **r['review']}
        statement_ref=self.f.put('root-statement.json',statement);refs['root-statement']=statement_ref
        subjects.append({'kind':'root_statement','sha256':statement_ref['sha256']})
        self.f.put('dab.json',{'schema_version':'1.0.0','dab_id':'TEST-RC-FORENSIC','tier':'FORENSIC','subject_ref':'archive','decision_refs':['root-statement'],
            'approval_refs':[],'generation_refs':[],'validation_refs':['stage-'+str(i) for i in range(4)],'repair_refs':[],'waiver_refs':[],'release_refs':[],
            'private_chain_of_thought_recorded':False})
        scope={'consumer':'rc','dab':'dab.json','references':refs,'archive_execution':build_binding['execution_id'],'archive':archive_ref,
            'stage_executions':executions,'root_statement':statement_ref}
        result,b=self.run_case('release_candidate',scope,subjects)
        self.assertEqual(result['manifest']['details']['release'],'BLOCKED_BY_DESIGN')
        self.assertFalse(result['manifest']['production_authority'])

    def test_output_changed_between_fsync_and_commit_is_rejected(self):
        b,work=self._build()
        def mutate(point):
            if point=='before_commit':
                p=work/'archive.trpgpkg';p.chmod(0o600);p.write_bytes(b'changed after OUTPUT validation')
        with self.assertRaises(e.SafetyError):c.exercise_test_only('build',self.f.inputs,b['execution_id'],self.f.store,crash=mutate)
        self.assertEqual(self.f.store.operation(b['execution_id'])['state'],'ABORTED')

    def test_archive_duplicate_traversal_symlink_and_bomb_reject(self):
        for name,mode in (('../escape',0o100644),('link',0o120777),('dup',0o100644)):
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as archive:
                item=zipfile.ZipInfo(name);item.external_attr=mode<<16;archive.writestr(item,b'x')
                if name=='dup':archive.writestr(item,b'x')
            with self.assertRaises(e.SafetyError):c.inspect_archive(out.getvalue())
    def test_rc_is_distinct_and_requires_forensic_current_chain(self):
        self.f.put('dab.json',{'schema_version':'1.0.0','dab_id':'TEST-DAB','tier':'MINIMAL','subject_ref':'subject','decision_refs':[],
            'approval_refs':[],'generation_refs':[],'validation_refs':[],'repair_refs':[],'waiver_refs':[],'release_refs':[],'private_chain_of_thought_recorded':False})
        ref=self.f.put('subject.json',{'text':'TEST_ONLY'})
        scope={'consumer':'rc','dab':'dab.json','references':{'subject':ref},'archive_execution':'00000000-0000-4000-8000-000000000001','archive':ref,'stage_executions':[],'root_statement':ref}
        b=self.f.issue('release_candidate',scope);self.f.authorize(b)
        with self.assertRaisesRegex(e.SafetyError,'FORENSIC'):c.exercise_test_only('release_candidate',self.f.inputs,b['execution_id'],self.f.store)
        self.assertEqual(self.f.store.operation(b['execution_id'])['state'],'ABORTED')

if __name__=='__main__':unittest.main()
