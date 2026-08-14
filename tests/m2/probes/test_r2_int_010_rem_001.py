#!/usr/bin/env python3
"""F001/F002 attacks for R2-INT-010-REM-001 additive Phase J evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "r2_int_010_rem_001_validator",
    HERE / "validate_r2_int_010_rem_001.py",
)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class R2Int010Rem001EvidenceTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((validator.ROOT / relative).read_text(encoding="utf-8"))

    def evidence(self):
        return self.load(validator.EVIDENCE_PATH_TEXT)

    def execution(self):
        return self.load(validator.EXECUTION_PATH_TEXT)

    def manifest(self):
        return self.load(validator.MANIFEST_PATH_TEXT)

    def schema(self):
        return self.load(validator.SCHEMA_PATH_TEXT)

    def assert_rejected(self, **overrides):
        with self.assertRaises(validator.RemediationValidationError):
            validator.validate_remediation(**overrides)

    def assert_schema_rejected(self, data):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("optional jsonschema package is unavailable")
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.schema()).validate(data)

    def test_current_evidence_validates(self):
        validator.validate_remediation()

    def test_schema_is_draft_2020_12_and_current_evidence_validates(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("optional jsonschema package is unavailable")
        schema = self.schema()
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(self.evidence())

    def test_schema_rejects_phase_extra_and_missing_fields(self):
        data = self.evidence()
        data["phase_results"][0]["unexpected"] = True
        self.assert_schema_rejected(data)
        data = self.evidence()
        del data["phase_results"][0]["source_archive_sha256"]
        self.assert_schema_rejected(data)

    def test_schema_rejects_projection_extra_and_missing_fields(self):
        data = self.evidence()
        data["projections"]["unexpected"] = True
        self.assert_schema_rejected(data)
        data = self.evidence()
        del data["projections"]["readiness"]["blocking_ids"]
        self.assert_schema_rejected(data)

    def test_f001_forged_pass_is_rejected(self):
        data = self.evidence()
        data["new_status"] = "PASS"
        self.assert_rejected(evidence_data=data)

    def test_f001_duplicate_evidence_id_command_and_negative_are_rejected(self):
        data = self.evidence()
        data["phase_results"][1]["evidence_id"] = data["phase_results"][0]["evidence_id"]
        self.assert_rejected(evidence_data=data)
        execution = self.execution()
        execution["records"][1]["command"] = execution["records"][0]["command"]
        self.assert_rejected(execution_data=execution)
        data = self.evidence()
        data["phase_results"][5]["cases"][1] = copy.deepcopy(data["phase_results"][5]["cases"][0])
        self.assert_rejected(evidence_data=data)

    def test_f001_duplicate_raw_json_keys_are_rejected_in_all_artifacts(self):
        attacks = (
            (validator.EVIDENCE_PATH_TEXT, '  "new_status": "RESOLVED_ADAPTER",', '  "new_status": "PASS",\n  "new_status": "RESOLVED_ADAPTER",'),
            (validator.EXECUTION_PATH_TEXT, '  "task_id": "R2-INT-010-REM-001",', '  "task_id": "FORGED",\n  "task_id": "R2-INT-010-REM-001",'),
            (validator.MANIFEST_PATH_TEXT, '  "task_id": "R2-INT-010-REM-001",', '  "task_id": "FORGED",\n  "task_id": "R2-INT-010-REM-001",'),
        )
        for path_text, needle, replacement in attacks:
            with self.subTest(path=path_text):
                raw = (validator.ROOT / path_text).read_text(encoding="utf-8")
                self.assertEqual(raw.count(needle), 1)
                with self.assertRaises(validator.RemediationValidationError):
                    validator.load_json_text(raw.replace(needle, replacement, 1), path_text)

    def test_f002_nonfinite_raw_json_constants_are_rejected_in_all_artifacts(self):
        attacks = (
            (validator.EVIDENCE_PATH_TEXT, '  "new_status": "RESOLVED_ADAPTER",', '  "new_status": NaN,'),
            (validator.EXECUTION_PATH_TEXT, '  "previous_status": "FAIL",', '  "previous_status": Infinity,'),
            (validator.MANIFEST_PATH_TEXT, '  "task_id": "R2-INT-010-REM-001",', '  "task_id": -Infinity,'),
        )
        for path_text, needle, replacement in attacks:
            with self.subTest(path=path_text):
                raw = (validator.ROOT / path_text).read_text(encoding="utf-8")
                self.assertEqual(raw.count(needle), 1)
                with self.assertRaises(validator.RemediationValidationError):
                    validator.load_json_text(raw.replace(needle, replacement, 1), path_text)

    def test_f001_missing_evidence_and_execution_fields_are_rejected(self):
        data = self.evidence()
        del data["creator_tool"]
        self.assert_rejected(evidence_data=data)
        execution = self.execution()
        del execution["records"][0]["source_capture_sha256"]
        self.assert_rejected(execution_data=execution)

    def test_f001_wrong_repository_commit_and_tree_are_rejected(self):
        attacks = (
            (0, "repository", "TRPG_PLATFORM"),
            (0, "commit", "0" * 40),
            (0, "tree", "f" * 40),
            (1, "repository", "rules-residue"),
            (1, "commit", "f" * 40),
            (1, "tree", "0" * 40),
        )
        for index, field, value in attacks:
            with self.subTest(index=index, field=field):
                data = self.evidence()
                data["exact_target_pair"][index][field] = value
                self.assert_rejected(evidence_data=data)

    def test_f001_missing_and_wrong_target_pair_are_rejected(self):
        data = self.evidence()
        data["exact_target_pair"].pop()
        self.assert_rejected(evidence_data=data)
        data = self.evidence()
        data["exact_target_pair"][1]["target"] = "C:Creator Tool"
        self.assert_rejected(evidence_data=data)

    def test_f001_altered_gate_and_readiness_mapping_is_rejected(self):
        data = self.evidence()
        data["projections"]["external_gates"][0]["blocking_probe_ids"] = ["R2-INT-010"]
        self.assert_rejected(evidence_data=data)
        data = self.evidence()
        data["projections"]["readiness"]["blocking_ids"] = ["R2-INT-010"]
        self.assert_rejected(evidence_data=data)

    def test_f002_stale_historical_hash_and_evidence_hash_are_rejected(self):
        manifest = self.manifest()
        manifest["immutable_historical_artifacts"][0]["sha256"] = "0" * 64
        self.assert_rejected(manifest_data=manifest)
        manifest = self.manifest()
        manifest["artifacts"][0]["sha256"] = "0" * 64
        self.assert_rejected(manifest_data=manifest)

    def test_f002_proposal_or_approval_candidate_cannot_be_execution_target(self):
        data = self.evidence()
        data["exact_target_pair"][1]["commit"] = validator.PROPOSAL_COMMIT
        self.assert_rejected(evidence_data=data)
        data = self.evidence()
        data["antecedents"]["owner_governance_approval_candidate"]["disposition"] = "EXECUTED_TARGET"
        self.assert_rejected(evidence_data=data)

    def test_f002_not_run_cannot_be_promoted_to_pass(self):
        for field in ("formal_B002", "formal_B009"):
            with self.subTest(field=field):
                data = self.evidence()
                data["non_claims"][field] = {"execution_status": "PASS", "claimed": True}
                self.assert_rejected(evidence_data=data)

    def test_f002_mismatched_creator_identity_or_output_is_rejected(self):
        data = self.evidence()
        data["creator_tool"]["binary_sha256"] = "0" * 64
        self.assert_rejected(evidence_data=data)
        execution = self.execution()
        execution["records"][4]["normalized_text"] = execution["records"][4]["normalized_text"].replace(
            validator.CREATOR_SHA256, "f" * 64
        )
        self.assert_rejected(execution_data=execution)
        data = self.evidence()
        data["phase_results"][2]["output_sha256"][1] = "f" * 64
        self.assert_rejected(evidence_data=data)

    def test_creator_edit_commands_lock_namespace_and_conflict_token(self):
        commands = [record["command"] for record in self.execution()["records"]]
        for index in (5, 6, 11):
            with self.subTest(record=index + 1):
                self.assertIn("--namespace org.trpgplatform.rules-residue.probe", commands[index])
                self.assertIn("--conflict-token sha256:" + validator.SOURCE_ARCHIVE_SHA256, commands[index])
        execution = self.execution()
        execution["records"][5]["command"] = execution["records"][5]["command"].replace(
            " --namespace org.trpgplatform.rules-residue.probe", ""
        )
        self.assert_rejected(execution_data=execution)

    def test_source_double_build_and_approval_lineage_are_exact(self):
        data = self.evidence()
        self.assertTrue(data["phase_results"][0]["source_builds_byte_and_mode_identical"])
        self.assertEqual(data["phase_results"][0]["source_tree_sha256"], "20daecd7a1b40e7d1e8dd6052e7935671bddd543ac991e2e99d8d8530210455b")
        self.assertEqual(data["antecedents"]["platform_change_proposal"]["proposal_id"], "PLATFORM-CHANGE-R2-INT-010-REM-001")
        self.assertEqual(data["antecedents"]["owner_governance_approval_candidate"]["owner_decision_id"], "OWNER-DECISION-PLATFORM-CHANGE-R2-INT-010-REM-001")
        execution = self.execution()
        execution["records"][-1]["normalized_text"] = execution["records"][-1]["normalized_text"].replace("true", "false")
        self.assert_rejected(execution_data=execution)

    def test_f002_mismatched_platform_rules_pair_is_rejected(self):
        data = self.evidence()
        data["exact_target_pair"][0]["tree"] = validator.PLATFORM_TREE
        data["exact_target_pair"][1]["tree"] = validator.RULES_TREE
        self.assert_rejected(evidence_data=data)

    def test_f002_historical_status_rewrite_is_rejected(self):
        data = self.evidence()
        data["previous_status"] = "RESOLVED_ADAPTER"
        self.assert_rejected(evidence_data=data)
        execution = self.execution()
        execution["previous_status"] = "RESOLVED_ADAPTER"
        self.assert_rejected(execution_data=execution)
        data = self.evidence()
        data["previous_evidence"][0]["previous_status"] = "PASS"
        self.assert_rejected(evidence_data=data)
        data = self.evidence()
        data["previous_evidence"][1]["sha256"] = "0" * 64
        self.assert_rejected(evidence_data=data)
        data = self.evidence()
        data["transition_reason"] = "forged transition"
        self.assert_rejected(evidence_data=data)

    def test_f002_integrity_classes_are_not_execution_results(self):
        data = self.evidence()
        data["integrity_classes"][0]["execution_status"] = "PASS"
        self.assert_rejected(evidence_data=data)
        data = self.evidence()
        data["integrity_classes"][1]["meaning"] = "EXECUTION_PASS"
        self.assert_rejected(evidence_data=data)

    def test_manifest_binds_every_non_self_new_artifact(self):
        manifest = self.manifest()
        validator.validate_manifest(manifest)
        self.assertEqual(
            [item["path"] for item in manifest["artifacts"]],
            validator.MANIFEST_ARTIFACT_PATHS,
        )
        for path_text in (
            validator.SCHEMA_PATH_TEXT,
            validator.VALIDATOR_PATH_TEXT,
            validator.TEST_PATH_TEXT,
        ):
            with self.subTest(path=path_text):
                attacked = self.manifest()
                item = next(item for item in attacked["artifacts"] if item["path"] == path_text)
                item["sha256"] = "0" * 64
                self.assert_rejected(manifest_data=attacked)
                attacked = self.manifest()
                attacked["artifacts"] = [item for item in attacked["artifacts"] if item["path"] != path_text]
                self.assert_rejected(manifest_data=attacked)

    def test_manifest_locks_exact_historical_artifact_set(self):
        manifest = self.manifest()
        self.assertEqual(
            [item["path"] for item in manifest["immutable_historical_artifacts"]],
            list(validator.HISTORICAL_HASHES),
        )
        manifest["immutable_historical_artifacts"][0]["path"] = "reports/m2/probes/forged.json"
        self.assert_rejected(manifest_data=manifest)


if __name__ == "__main__":
    unittest.main()
