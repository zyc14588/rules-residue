#!/usr/bin/env python3
"""F001/F002 attacks for M2-B001-EXT-001 additive external evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "m2_b001_external_supplement_validator",
    HERE / "validate_m2_b001_external_supplement.py",
)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class M2B001ExternalSupplementTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((validator.ROOT / relative).read_text(encoding="utf-8"))

    def supplement(self):
        return self.load(validator.SUPPLEMENT_PATH_TEXT)

    def commands(self):
        return self.load(validator.COMMAND_PATH_TEXT)

    def assert_rejected(self, **overrides):
        with self.assertRaises(validator.ProbeValidationError):
            validator.validate_supplement(**overrides)

    def test_current_supplement_validates(self):
        validator.validate_supplement()

    def test_schema_validates_current_supplement(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("optional jsonschema package is unavailable")
        schema = self.load(validator.SCHEMA_PATH_TEXT)
        jsonschema.Draft202012Validator(schema).validate(self.supplement())

    def test_f001_forged_pass_is_rejected(self):
        data = self.supplement()
        transition = next(item for item in data["probe_result_transitions"] if item["probe_id"] == "R2-INT-012")
        transition["new"]["execution_status"] = "PASS"
        transition["new"]["target_results"][1]["execution_status"] = "PASS"
        data["int_012_determination"]["execution_status"] = "PASS"
        data["int_012_determination"]["all_required_dimensions_pass"] = True
        data["int_012_determination"]["pass_claimed"] = True
        self.assert_rejected(data=data)

    def test_f001_duplicate_command_evidence_is_rejected(self):
        commands = self.commands()
        commands["commands"].append(copy.deepcopy(commands["commands"][-1]))
        self.assert_rejected(command_data=commands)

    def test_f001_missing_provenance_and_incomplete_fields_are_rejected(self):
        data = self.supplement()
        del data["external_binding"]["repository"]
        self.assert_rejected(data=data)
        commands = self.commands()
        del commands["commands"][0]["observed_output"]
        self.assert_rejected(command_data=commands)

    def test_f001_wrong_repository_commit_and_tree_are_rejected(self):
        for field, value in (
            ("repository", "/tmp/forged-platform"),
            ("commit", "0" * 40),
            ("tree", "f" * 40),
        ):
            with self.subTest(field=field):
                commands = self.commands()
                commands["external_system"][field] = value
                self.assert_rejected(command_data=commands)

    def test_f001_wrong_captured_source_worktree_is_rejected(self):
        commands = self.commands()
        commands["commands"][0]["workdir"] = "/tmp/forged-rules-residue-worktree"
        self.assert_rejected(command_data=commands)

    def test_f001_missing_and_wrong_target_pairs_are_rejected(self):
        data = self.supplement()
        transition = next(item for item in data["probe_result_transitions"] if item["probe_id"] == "R2-INT-012")
        transition["new"]["target_results"].pop()
        self.assert_rejected(data=data)
        data = self.supplement()
        transition = next(item for item in data["probe_result_transitions"] if item["probe_id"] == "R2-INT-012")
        transition["new"]["target_results"][1]["target"] = "C:Creator Tool"
        self.assert_rejected(data=data)

    def test_f001_altered_gate_mapping_is_rejected(self):
        data = self.supplement()
        data["external_gate_transitions"][0]["target"] = "C:Creator Tool"
        data["current_external_gates"][0]["target"] = "C:Creator Tool"
        self.assert_rejected(data=data)

    def test_f002_stale_historical_and_raw_command_evidence_are_rejected(self):
        data = self.supplement()
        data["accepted_b001_binding"]["historical_result_sha256"] = "0" * 64
        self.assert_rejected(data=data)
        commands = self.commands()
        commands["commands"][0]["output_sha256"] = "0" * 64
        self.assert_rejected(command_data=commands)
        commands = self.commands()
        commands["captured_at"] = "2026-08-13T08:54:29Z"
        self.assert_rejected(command_data=commands)

    def test_f002_previous_probe_and_gate_evidence_cannot_be_rewritten(self):
        data = self.supplement()
        data["probe_result_transitions"][0]["previous"]["execution_status"] = "PASS"
        self.assert_rejected(data=data)
        data = self.supplement()
        data["external_gate_transitions"][0]["previous"]["blocks"] = []
        self.assert_rejected(data=data)

    def test_f002_int_010_has_one_supported_remediation_class_and_blocks_b002(self):
        data = self.supplement()
        remediation = data["int_010_remediation"]
        self.assertEqual(remediation["execution_status"], "FAIL")
        self.assertEqual(remediation["remediation_class"], "MULTI_REPO_CHANGE_REQUIRED")
        self.assertTrue(remediation["blocks_b002"])
        remediation["remediation_class"] = ["PLATFORM_CHANGE_REQUIRED", "RULES_PACKAGE_ADAPTER"]
        self.assert_rejected(data=data)

    def test_f002_int_012_requires_all_nine_platform_dimensions(self):
        data = self.supplement()
        determination = data["int_012_determination"]
        self.assertEqual(len(determination["required_dimension_results"]), 9)
        self.assertEqual(determination["execution_status"], "BLOCKED_EXTERNAL")
        determination["required_dimension_results"][0]["execution_status"] = "PASS"
        self.assert_rejected(data=data)

    def test_latest_index_applies_append_and_update_layers_without_reopening_b001(self):
        index = self.load(validator.INDEX_PATH_TEXT)
        validator.validate_index(index)
        self.assertEqual(index["latest_external_evidence"]["evidence_id"], validator.SUPPLEMENT_ID)
        self.assertFalse(index["formal_batch_reopened"])
        self.assertFalse(index["b002_started"])

    def test_manifest_is_complete_and_historical_artifacts_are_immutable(self):
        manifest = self.load(validator.MANIFEST_PATH_TEXT)
        validator.validate_manifest(manifest)
        self.assertEqual(
            {item["path"] for item in manifest["immutable_historical_artifacts"]},
            set(validator.HISTORICAL_HASHES),
        )
        manifest["immutable_historical_artifacts"][0]["sha256"] = "0" * 64
        self.assert_rejected(manifest_data=manifest)

    def test_supplement_candidate_scope_is_default_deny(self):
        self.assertTrue(validator.is_allowed_supplement_path(validator.SUPPLEMENT_PATH_TEXT))
        self.assertTrue(validator.is_allowed_supplement_path(validator.ROUTE_REQUEST_PATH_TEXT))
        self.assertFalse(validator.is_allowed_supplement_path("game-package/lua/main.lua"))
        self.assertFalse(validator.is_allowed_supplement_path(".codex/state/MILESTONE_PLAN.yaml"))

    def test_exact_validator_is_invocation_root_independent(self):
        candidate_paths = validator.SUPPLEMENT_ARTIFACT_PATHS | {validator.MANIFEST_PATH_TEXT}
        with tempfile.TemporaryDirectory(prefix="m2-b001-independent-root-") as temporary:
            independent_root = Path(temporary) / "differently-named-accept-root"
            subprocess.run(
                ["git", "clone", "--quiet", "--shared", "--no-checkout", str(validator.ROOT), str(independent_root)],
                check=True,
            )
            subprocess.run(
                ["git", "checkout", "--quiet", "--detach", validator.ACCEPTED_B001_COMMIT],
                cwd=independent_root,
                check=True,
            )
            for path_text in sorted(candidate_paths):
                destination = independent_root / path_text
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(validator.ROOT / path_text, destination)

            environment = os.environ.copy()
            environment.update({
                "GIT_AUTHOR_NAME": "M2 B001 Regression",
                "GIT_AUTHOR_EMAIL": "m2-b001-regression@example.invalid",
                "GIT_COMMITTER_NAME": "M2 B001 Regression",
                "GIT_COMMITTER_EMAIL": "m2-b001-regression@example.invalid",
            })
            subprocess.run(["git", "add", "--all"], cwd=independent_root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "M2-B001 external evidence supplement candidate"],
                cwd=independent_root,
                env=environment,
                check=True,
            )
            candidate_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=independent_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            candidate_tree = subprocess.run(
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=independent_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            self.assertNotEqual(str(independent_root), validator.CAPTURE_SOURCE_WORKTREE)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(independent_root / validator.VALIDATOR_PATH_TEXT),
                    "--supplement",
                    "--candidate",
                    candidate_commit,
                    "--candidate-tree",
                    candidate_tree,
                ],
                cwd=independent_root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["validation_status"], "PASS")
            self.assertEqual(result["route_binding_digest"], validator.SUPPLEMENT_ROUTE_DIGEST)


if __name__ == "__main__":
    unittest.main()
