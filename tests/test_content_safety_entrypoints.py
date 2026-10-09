"""Exercise actual default production entrypoints without ambient test authority."""
import ast
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from tools import build_package as builder
from tools.content_safety_control import ControlStore
from tools.lib.content_safety_evidence import ROOT,SafetyError
from tests.test_content_safety_evidence import Fixture,remove_owned


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.directory=Path(tempfile.mkdtemp(prefix='b018-entrypoints-'));self.addCleanup(remove_owned,self.directory)
    def command(self,*args):
        return subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True,text=True,timeout=30)
    def test_all_five_real_cli_consumers_fail_closed_without_control(self):
        for consumer in ('media','region','cross-region','build','rc'):
            with self.subTest(consumer=consumer):
                result=self.command('tools/content_safety_consumers.py',consumer,'--input-root',str(self.directory),'--execution',str(uuid.uuid4()))
                self.assertEqual(result.returncode,1,result.stdout+result.stderr)
                self.assertIn('DENY',result.stdout)
    def test_cli_cannot_bootstrap_or_choose_test_trust_clock(self):
        for args in (('bootstrap',),('status','--test-only'),('status','--trust-root',str(self.directory)),('status','--now','2026-10-09T00:00:00Z')):
            with self.subTest(args=args):
                result=self.command('tools/content_safety_control.py',*args)
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)
    def test_default_and_skip_builder_api_never_output_without_evidence(self):
        for validate in (True,False):
            for root in (builder.GAME_PACKAGE_ROOT,self.directory/'alternative'):
                output=self.directory/(str(validate)+root.name+'.trpgpkg')
                with self.assertRaisesRegex(SafetyError,'control-issued'):builder.build_package(output,validate_first=validate,game_package_root=root)
                self.assertFalse(output.exists());self.assertFalse(output.with_suffix(output.suffix+'.sha256').exists())
    def test_actual_builder_cli_default_and_skip_cannot_bypass(self):
        for skip in ([],['--skip-validation']):
            output=self.directory/('skip.trpgpkg' if skip else 'default.trpgpkg')
            result=self.command('tools/build_package.py','--output',str(output),*skip)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr);self.assertIn('DENY',result.stdout);self.assertFalse(output.exists())
    def test_builder_with_test_store_and_issued_operation_is_still_denied(self):
        f=Fixture(self.directory);b=f.issue('art_audio',f.audio());f.authorize(b)
        output=self.directory/'not-admitted.trpgpkg'
        with self.assertRaisesRegex(SafetyError,'TEST_ONLY'):builder.build_package(output,validate_first=False,execution_id=b['execution_id'],store=f.store)
        self.assertFalse(output.exists())
    def test_raw_encoder_deterministic37_is_explicit_quarantine_only(self):
        output=self.directory/'raw.trpgpkg';digest=builder._quarantine_encode(output,validate_first=True)
        self.assertEqual(digest,'29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314')
        import zipfile
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(len(archive.namelist()),37)
            self.assertEqual(json.loads(archive.read('manifest.json'))['schema_version'],'trpg.game-package.manifest/0.1-draft')
        self.assertFalse((self.directory/'control.sqlite3').exists())
    def test_raw_encoder_preserves_full_and_module_validation_calls(self):
        output=self.directory/'blocked.trpgpkg'
        with patch('tools.validate_project.collect_errors',return_value=['TEST injected full validation error']) as gate:
            with self.assertRaisesRegex(RuntimeError,'full validation error'):builder._quarantine_encode(output,validate_first=True)
            gate.assert_called_once();self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
