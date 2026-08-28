#!/usr/bin/env python3
"""Adversarial tests for the R2-INT-010 post-platform evidence transition."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "r2_int_010_post_platform_transition_validator",
    HERE / "validate_r2_int_010_post_platform_transition.py",
)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class R2Int010PostPlatformTransitionTests(unittest.TestCase):
    def load(self, path_text: str):
        return validator.load_json(validator.ROOT / path_text)

    def evidence(self):
        return self.load(validator.EVIDENCE_PATH_TEXT)

    def execution(self):
        return self.load(validator.EXECUTION_PATH_TEXT)

    def cross(self):
        return self.load(validator.CROSS_VERDICT_PATH_TEXT)

    def cross_manifest(self):
        return self.load(validator.CROSS_MANIFEST_PATH_TEXT)

    def manifest(self):
        return self.load(validator.MANIFEST_PATH_TEXT)

    def assert_rejected(self, **overrides):
        with self.assertRaises(validator.TransitionValidationError):
            validator.validate_transition(**overrides)

    def test_current_transition_candidate_validates(self):
        validator.validate_transition()

    def test_persisted_cross_verdict_is_exact_verified_source_copy(self):
        self.assertEqual(
            validator.sha256_path(validator.CROSS_VERDICT_PATH),
            validator.CROSS_VERDICT_SHA256,
        )
        validator.validate_cross_verdict(self.cross(), check_raw_path=True)

    def test_forged_new_status_pass_is_rejected(self):
        data = self.evidence()
        data["new_status"] = "PASS"
        self.assert_rejected(evidence_data=data)

    def test_previous_status_changed_from_fail_is_rejected(self):
        data = self.evidence()
        data["previous_status"] = "RESOLVED_ADAPTER"
        self.assert_rejected(evidence_data=data)
        execution = self.execution()
        execution["previous_status"] = "RESOLVED_ADAPTER"
        self.assert_rejected(execution_data=execution)

    def test_wrong_rules_commit_or_tree_is_rejected(self):
        for field in ("commit", "tree"):
            with self.subTest(field=field):
                data = self.evidence()
                data["exact_target_pair"][0][field] = "0" * 40
                self.assert_rejected(evidence_data=data)

    def test_wrong_platform_commit_or_tree_is_rejected(self):
        for field in ("commit", "tree"):
            with self.subTest(field=field):
                data = self.evidence()
                data["exact_target_pair"][1][field] = "f" * 40
                self.assert_rejected(evidence_data=data)

    def test_wrong_creator_sha_is_rejected(self):
        data = self.evidence()
        data["creator_identity"]["binary_sha256"] = "0" * 64
        self.assert_rejected(evidence_data=data)
        cross = self.cross()
        cross["identity"]["creator_binary_sha256"] = "f" * 64
        self.assert_rejected(cross_data=cross)

    def test_old_c6_adapter_identity_substitution_is_rejected(self):
        data = self.evidence()
        data["exact_target_pair"][0]["commit"] = validator.OLD_COMMITS[1]
        self.assert_rejected(evidence_data=data)

    def test_old_65_evidence_cannot_be_execution_authority(self):
        data = self.evidence()
        data["execution_authority"]["artifact"] = "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json"
        data["execution_authority"]["sha256"] = validator.HISTORICAL_HASHES[data["execution_authority"]["artifact"]]
        data["execution_authority"]["old_provisional_used_as_execution_evidence"] = True
        self.assert_rejected(evidence_data=data)

    def test_exact_pair_verdict_hash_change_is_rejected(self):
        manifest = self.cross_manifest()
        manifest["artifact"]["sha256"] = "0" * 64
        self.assert_rejected(cross_manifest_data=manifest)
        cross = self.cross()
        cross["result"] = "PASS"
        self.assert_rejected(cross_data=cross)

    def test_one_of_29_exact_pair_evidence_records_missing_is_rejected(self):
        cross = self.cross()
        cross["evidence"].pop()
        self.assert_rejected(cross_data=cross)

    def test_exact_pair_evidence_hash_altered_is_rejected(self):
        cross = self.cross()
        cross["evidence"][0]["log_sha256"] = "0" * 64
        self.assert_rejected(cross_data=cross)

    def test_duplicate_exact_pair_evidence_id_is_rejected(self):
        cross = self.cross()
        cross["evidence"][1]["evidence_id"] = cross["evidence"][0]["evidence_id"]
        self.assert_rejected(cross_data=cross)

    def test_formal_b002_promotion_is_rejected(self):
        data = self.evidence()
        data["non_claims"]["formal_B002"] = {"execution_status": "PASS", "claimed": True}
        self.assert_rejected(evidence_data=data)

    def test_formal_b009_promotion_is_rejected(self):
        data = self.evidence()
        data["non_claims"]["formal_B009"] = {"execution_status": "PASS", "claimed": True}
        self.assert_rejected(evidence_data=data)

    def test_aggregate_readiness_claim_is_rejected(self):
        data = self.evidence()
        data["non_claims"]["aggregate_status"] = "PASS"
        self.assert_rejected(evidence_data=data)

    def test_m2_b002_ready_yes_is_rejected(self):
        data = self.evidence()
        data["readiness_projection"]["M2-B002_READY"] = "YES"
        self.assert_rejected(evidence_data=data)

    def test_duplicate_raw_json_keys_are_rejected(self):
        attacks = (
            (validator.EVIDENCE_PATH_TEXT, '  "new_status": "RESOLVED_ADAPTER",', '  "new_status": "PASS",\n  "new_status": "RESOLVED_ADAPTER",'),
            (validator.EXECUTION_PATH_TEXT, '  "source_phase": "VERIFIED_EXACT_PAIR_ACCEPT_VERDICT_PROJECTION",', '  "source_phase": "FORGED",\n  "source_phase": "VERIFIED_EXACT_PAIR_ACCEPT_VERDICT_PROJECTION",'),
            (validator.CROSS_VERDICT_PATH_TEXT, '  "result": "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED",', '  "result": "FAIL",\n  "result": "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED",'),
            (validator.CROSS_MANIFEST_PATH_TEXT, f'  "task_id": "{validator.TASK_ID}",', f'  "task_id": "FORGED",\n  "task_id": "{validator.TASK_ID}",'),
            (validator.MANIFEST_PATH_TEXT, f'  "task_id": "{validator.TASK_ID}",', f'  "task_id": "FORGED",\n  "task_id": "{validator.TASK_ID}",'),
        )
        for path_text, needle, replacement in attacks:
            with self.subTest(path=path_text):
                raw = (validator.ROOT / path_text).read_text(encoding="utf-8")
                self.assertEqual(raw.count(needle), 1)
                with self.assertRaises(validator.TransitionValidationError):
                    validator.load_json_text(raw.replace(needle, replacement, 1), path_text)

    def test_nan_and_infinity_are_rejected(self):
        attacks = (
            (validator.EVIDENCE_PATH_TEXT, '  "new_status": "RESOLVED_ADAPTER",', '  "new_status": NaN,'),
            (validator.EXECUTION_PATH_TEXT, '  "source_phase": "VERIFIED_EXACT_PAIR_ACCEPT_VERDICT_PROJECTION",', '  "source_phase": Infinity,'),
            (validator.CROSS_VERDICT_PATH_TEXT, '  "result": "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED",', '  "result": -Infinity,'),
            (validator.CROSS_MANIFEST_PATH_TEXT, f'  "task_id": "{validator.TASK_ID}",', '  "task_id": NaN,'),
            (validator.MANIFEST_PATH_TEXT, f'  "task_id": "{validator.TASK_ID}",', '  "task_id": Infinity,'),
        )
        for path_text, needle, replacement in attacks:
            with self.subTest(path=path_text):
                raw = (validator.ROOT / path_text).read_text(encoding="utf-8")
                self.assertEqual(raw.count(needle), 1)
                with self.assertRaises(validator.TransitionValidationError):
                    validator.load_json_text(raw.replace(needle, replacement, 1), path_text)

    def test_missing_new_artifact_is_rejected(self):
        manifest = self.manifest()
        manifest["artifacts"] = [
            item for item in manifest["artifacts"] if item["path"] != validator.TEST_PATH_TEXT
        ]
        self.assert_rejected(manifest_data=manifest)

    def test_wrong_new_artifact_hash_is_rejected(self):
        manifest = self.manifest()
        manifest["artifacts"][0]["sha256"] = "0" * 64
        self.assert_rejected(manifest_data=manifest)

    def test_immutable_predecessor_hash_change_is_rejected(self):
        manifest = self.manifest()
        manifest["immutable_historical_artifacts"][0]["sha256"] = "0" * 64
        self.assert_rejected(manifest_data=manifest)

    def test_t_series_records_are_unique_and_old_j_records_are_not_reused(self):
        execution = self.execution()
        ids = [item["evidence_id"] for item in execution["records"]]
        self.assertEqual(ids, [f"T-R{number:03d}" for number in range(1, 15)])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(any(item.startswith("J-") for item in ids))
        attacked = copy.deepcopy(execution)
        attacked["records"][1]["evidence_id"] = attacked["records"][0]["evidence_id"]
        self.assert_rejected(execution_data=attacked)

    def test_phase_results_reference_only_persisted_exact_pair_evidence(self):
        data = self.evidence()
        accepted_ids = {item[0] for item in validator.EXPECTED_ACCEPTED_EVIDENCE}
        for phase in data["phase_results"]:
            self.assertEqual(phase["evidence_source"], "PERSISTED_EXACT_PAIR_ACCEPT_VERDICT")
            self.assertTrue(set(phase["source_verdict_evidence_ids"]).issubset(accepted_ids))
            self.assertFalse(any(item.startswith("J-") for item in phase["source_verdict_evidence_ids"]))

    def test_creator_build_command_is_sourced_from_verified_verdict(self):
        data = self.evidence()
        self.assertEqual(data["creator_build"]["source_verdict_evidence_id"], "XPAIR-R011")
        creator_record = next(item for item in self.cross()["evidence"] if item["evidence_id"] == "XPAIR-R011")
        self.assertEqual(data["creator_build"]["source_command"], creator_record["command"])

    def test_manifest_documents_non_reuse_of_hardcoded_pre_platform_schema(self):
        manifest = self.manifest()
        self.assertEqual(
            manifest["policies"]["schema_reuse"],
            "NOT_USED_HARDCODED_PRE_PLATFORM_SCHEMA_LEFT_UNCHANGED",
        )
        self.assertNotIn(
            "docs/implementation/m2/probes/remediation-evidence-v1.schema.json",
            [item["path"] for item in manifest["artifacts"]],
        )


if __name__ == "__main__":
    unittest.main()
