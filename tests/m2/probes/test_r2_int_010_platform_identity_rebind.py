#!/usr/bin/env python3
"""Adversarial tests for the fresh M1-B011 Platform identity rebind."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "r2_int_010_platform_identity_rebind_validator",
    HERE / "validate_r2_int_010_platform_identity_rebind.py",
)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class R2Int010PlatformIdentityRebindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.archive_observation = validator.validate_platform_archive()

    def load(self, path_text: str):
        return validator.load_json(validator.ROOT / path_text)

    def platform(self):
        return self.load(validator.PLATFORM_PATH_TEXT)

    def rebind(self):
        return self.load(validator.REBIND_PATH_TEXT)

    def execution(self):
        return self.load(validator.EXECUTION_PATH_TEXT)

    def index(self):
        return self.load(validator.INDEX_V3_PATH_TEXT)

    def manifest(self):
        return self.load(validator.MANIFEST_PATH_TEXT)

    def schema(self):
        return self.load(validator.SCHEMA_PATH_TEXT)

    def assert_rejected(self, **overrides):
        overrides.setdefault("archive_observation", self.archive_observation)
        with self.assertRaises(validator.RebindValidationError):
            validator.validate_candidate(check_git=False, **overrides)

    def append_archive_member(
        self,
        archive: Path,
        name: str,
        payload: bytes,
        *,
        mode: int = stat.S_IFREG | 0o644,
    ) -> None:
        info = zipfile.ZipInfo(name)
        info.create_system = 3
        info.external_attr = mode << 16
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "a") as target:
                target.writestr(info, payload)

    def rewrite_archive(self, target: Path, replacements: dict[str, bytes]) -> None:
        with zipfile.ZipFile(validator.PLATFORM_ARCHIVE_PATH, "r") as source:
            with zipfile.ZipFile(target, "w", allowZip64=True) as output:
                for old_info in source.infolist():
                    info = zipfile.ZipInfo(old_info.filename, old_info.date_time)
                    info.create_system = old_info.create_system
                    info.external_attr = old_info.external_attr
                    info.compress_type = zipfile.ZIP_STORED
                    info.flag_bits = old_info.flag_bits
                    data = replacements.get(old_info.filename, source.read(old_info.filename))
                    output.writestr(info, data)

    def validate_mutated_archive(self, path: Path) -> None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(validator.RebindValidationError):
            validator.validate_platform_archive(path, expected_archive_sha256=digest)

    def test_01_current_rebind_evidence_validates(self):
        validator.validate_candidate(
            check_git=False,
            archive_observation=self.archive_observation,
        )

    def test_02_current_git_scope_validates(self):
        validator.validate_git_objects_and_scope()

    def test_03_current_persistent_archive_validates(self):
        observed = validator.validate_platform_archive()
        self.assertEqual(observed["artifact_count"], 60)
        self.assertEqual(observed["manifest_root_sha256"], validator.FRESH_EVIDENCE_ROOT)

    def test_04_wrong_new_platform_commit_is_rejected(self):
        data = self.rebind()
        data["new_platform_identity"]["commit"] = "0" * 40
        self.assert_rejected(rebind_data=data)

    def test_05_wrong_new_platform_tree_is_rejected(self):
        data = self.rebind()
        data["new_platform_identity"]["tree"] = "f" * 40
        self.assert_rejected(rebind_data=data)

    def test_06_product_and_verifying_identities_swapped_are_rejected(self):
        data = self.platform()
        product = copy.deepcopy(data["current_platform_identity"]["product"])
        governance = copy.deepcopy(data["current_platform_identity"]["verifying_governance"])
        data["current_platform_identity"]["product"]["commit"] = governance["commit"]
        data["current_platform_identity"]["product"]["tree"] = governance["tree"]
        data["current_platform_identity"]["verifying_governance"]["commit"] = product["commit"]
        data["current_platform_identity"]["verifying_governance"]["tree"] = product["tree"]
        self.assert_rejected(platform_data=data)

    def test_07_wrong_accept_route_binding_is_rejected(self):
        data = self.platform()
        data["current_platform_identity"]["accept_route_binding_digest"] = "0" * 64
        self.assert_rejected(platform_data=data)

    def test_08_wrong_fresh_root_is_rejected(self):
        data = self.rebind()
        data["evidence_roots"]["current_evidence_root"] = "f" * 64
        self.assert_rejected(rebind_data=data)

    def test_09_old_root_substituted_as_current_is_rejected(self):
        data = self.rebind()
        data["evidence_roots"]["current_evidence_root"] = validator.HISTORICAL_EVIDENCE_ROOT
        self.assert_rejected(rebind_data=data)

    def test_10_fresh_root_substituted_as_historical_is_rejected(self):
        data = self.rebind()
        data["evidence_roots"]["historical_prior_evidence_root"] = validator.FRESH_EVIDENCE_ROOT
        self.assert_rejected(rebind_data=data)

    def test_11_historical_root_claimed_reverified_is_rejected(self):
        data = self.rebind()
        data["evidence_roots"]["historical_reported_root_reverified"] = True
        self.assert_rejected(rebind_data=data)

    def test_12_historical_platform_record_claimed_reverified_is_rejected(self):
        data = self.platform()
        data["historical_acceptance"]["reported_root_reverified"] = True
        self.assert_rejected(platform_data=data)

    def test_13_wrong_fresh_archive_sha_is_rejected(self):
        data = self.platform()
        data["fresh_reissuance"]["archive_sha256"] = "0" * 64
        self.assert_rejected(platform_data=data)

    def test_14_wrong_fresh_reissuance_task_is_rejected(self):
        data = self.platform()
        data["fresh_reissuance"]["task_id"] = "M1-B011-PLATFORM-INDEPENDENT-ACCEPT-001"
        self.assert_rejected(platform_data=data)

    def test_15_wrong_fresh_reissuance_result_is_rejected(self):
        data = self.platform()
        data["fresh_reissuance"]["result"] = validator.HISTORICAL_ACCEPT_RESULT
        self.assert_rejected(platform_data=data)

    def test_16_wrong_fresh_creator_is_rejected(self):
        data = self.rebind()
        data["creator_identities"]["current_creator_sha"] = "0" * 64
        self.assert_rejected(rebind_data=data)

    def test_17_old_creator_substituted_as_current_is_rejected(self):
        data = self.rebind()
        data["creator_identities"]["current_creator_sha"] = validator.HISTORICAL_CREATOR_SHA256
        self.assert_rejected(rebind_data=data)

    def test_18_wrong_historical_creator_is_rejected(self):
        data = self.platform()
        data["creator_identity"]["historical_creator_sha"] = "f" * 64
        self.assert_rejected(platform_data=data)

    def test_19_binary_reproducibility_match_is_rejected(self):
        data = self.rebind()
        data["creator_identities"]["binary_reproducibility"] = "MATCH"
        self.assert_rejected(rebind_data=data)

    def test_20_non_exact_source_identity_is_rejected(self):
        data = self.platform()
        data["creator_identity"]["source_identity_exact"] = False
        self.assert_rejected(platform_data=data)

    def test_21_fresh_behavioral_acceptance_fail_is_rejected(self):
        data = self.rebind()
        data["creator_identities"]["fresh_behavioral_acceptance"] = "FAIL"
        self.assert_rejected(rebind_data=data)

    def test_22_wrong_deterministic_product_is_rejected(self):
        data = self.platform()
        data["deterministic_product"]["run_2_sha256"] = "0" * 64
        self.assert_rejected(platform_data=data)

    def test_23_wrong_rules_adapter_identity_is_rejected(self):
        data = self.rebind()
        data["rules_adapter"]["commit"] = "0" * 40
        self.assert_rejected(rebind_data=data)

    def test_24_governance_head_cannot_replace_adapter_identity(self):
        data = self.rebind()
        data["rules_adapter"]["commit"] = validator.SOURCE_COMMIT
        data["rules_adapter"]["tree"] = validator.SOURCE_TREE
        self.assert_rejected(rebind_data=data)

    def test_25_historical_exact_pair_mutation_is_rejected(self):
        observed = dict(validator.HISTORICAL_HASHES)
        path = "reports/m2/probes/remediations/r2-int-010-post-platform-transition/cross-accept-verdict.json"
        observed[path] = "0" * 64
        self.assert_rejected(historical_hashes=observed)

    def test_26_historical_platform_antecedent_mutation_is_rejected(self):
        observed = dict(validator.HISTORICAL_HASHES)
        path = "reports/m2/probes/external/r2-int-010-platform-acceptance/platform-acceptance.json"
        observed[path] = "0" * 64
        self.assert_rejected(historical_hashes=observed)

    def test_27_fresh_exact_pair_overclaim_is_rejected(self):
        data = self.rebind()
        data["fresh_exact_pair_acceptance"] = "PASS"
        self.assert_rejected(rebind_data=data)

    def test_28_cross_repository_overclaim_is_rejected(self):
        data = self.platform()
        data["cross_repository_acceptance"] = "PASS"
        self.assert_rejected(platform_data=data)

    def test_29_formal_b002_promotion_is_rejected(self):
        data = self.rebind()
        data["formal_B002"] = True
        self.assert_rejected(rebind_data=data)

    def test_30_formal_b009_promotion_is_rejected(self):
        data = self.rebind()
        data["formal_B009"] = True
        self.assert_rejected(rebind_data=data)

    def test_31_m2_b002_ready_yes_is_rejected(self):
        data = self.rebind()
        data["M2_B002_READY"] = "YES"
        self.assert_rejected(rebind_data=data)

    def test_32_m1_b011_completion_authorized_is_rejected(self):
        data = self.rebind()
        data["m1_b011_completion"] = "AUTHORIZED"
        self.assert_rejected(rebind_data=data)

    def test_33_effective_status_pass_overclaim_is_rejected(self):
        data = self.rebind()
        data["effective_status_after"] = "PASS"
        self.assert_rejected(rebind_data=data)

    def test_34_v3_predecessor_hash_mutation_is_rejected(self):
        data = self.index()
        data["predecessor_index"]["sha256"] = "0" * 64
        self.assert_rejected(index_data=data)

    def test_35_v3_chain_deletion_is_rejected(self):
        data = self.index()
        data["evidence_chain"].pop(0)
        self.assert_rejected(index_data=data)

    def test_36_v3_rebind_disposition_pass_is_rejected(self):
        data = self.index()
        data["evidence_chain"][-1]["disposition"] = "PASS"
        self.assert_rejected(index_data=data)

    def test_37_v3_old_root_as_current_is_rejected(self):
        data = self.index()
        data["evidence_chain"][-1]["fresh_platform_evidence_root_sha256"] = validator.HISTORICAL_EVIDENCE_ROOT
        self.assert_rejected(index_data=data)

    def test_38_v3_old_creator_as_current_is_rejected(self):
        data = self.index()
        data["evidence_chain"][-1]["fresh_creator_sha256"] = validator.HISTORICAL_CREATOR_SHA256
        self.assert_rejected(index_data=data)

    def test_39_v3_effective_projection_pass_is_rejected(self):
        data = self.index()
        data["projections"]["effective_R2_INT_010"] = "PASS"
        self.assert_rejected(index_data=data)

    def test_40_schema_top_level_relaxation_is_rejected(self):
        data = self.schema()
        data["additionalProperties"] = True
        self.assert_rejected(schema_data=data)

    def test_41_schema_nested_relaxation_is_rejected(self):
        data = self.schema()
        data["$defs"]["evidenceRoots"]["additionalProperties"] = True
        self.assert_rejected(schema_data=data)

    def test_42_schema_sha_format_relaxation_is_rejected(self):
        data = self.schema()
        data["$defs"]["sha256"]["pattern"] = ".*"
        self.assert_rejected(schema_data=data)

    def test_43_schema_not_run_enum_relaxation_is_rejected(self):
        data = self.schema()
        data["properties"]["fresh_exact_pair_acceptance"]["enum"].append("PASS")
        self.assert_rejected(schema_data=data)

    def test_44_manifest_missing_artifact_is_rejected(self):
        data = self.manifest()
        data["artifacts"].pop()
        self.assert_rejected(manifest_data=data)

    def test_45_manifest_wrong_artifact_hash_is_rejected(self):
        data = self.manifest()
        data["artifacts"][0]["sha256"] = "0" * 64
        self.assert_rejected(manifest_data=data)

    def test_46_manifest_self_hash_cycle_is_rejected(self):
        data = self.manifest()
        data["artifacts"][0]["path"] = validator.MANIFEST_PATH_TEXT
        self.assert_rejected(manifest_data=data)

    def test_47_manifest_old_root_as_external_authority_is_rejected(self):
        data = self.manifest()
        data["external_authority"]["manifest_root_sha256"] = validator.HISTORICAL_EVIDENCE_ROOT
        self.assert_rejected(manifest_data=data)

    def test_48_execution_missing_required_command_is_rejected(self):
        data = self.execution()
        data["records"].pop()
        self.assert_rejected(execution_data=data)

    def test_49_execution_cross_repository_overclaim_is_rejected(self):
        data = self.execution()
        data["non_executions"]["cross_repository_acceptance"] = "PASS"
        self.assert_rejected(execution_data=data)

    def test_50_execution_route_drift_is_rejected(self):
        data = self.execution()
        data["route_binding"]["binding_digest"] = "0" * 64
        self.assert_rejected(execution_data=data)

    def test_51_unknown_field_is_rejected(self):
        data = self.rebind()
        data["unexpected"] = True
        self.assert_rejected(rebind_data=data)

    def test_52_duplicate_json_key_is_rejected(self):
        raw = (validator.ROOT / validator.REBIND_PATH_TEXT).read_text(encoding="utf-8")
        needle = '  "effective_status_after": "RESOLVED_ADAPTER",'
        self.assertEqual(raw.count(needle), 1)
        with self.assertRaises(validator.RebindValidationError):
            validator.load_json_text(raw.replace(needle, needle + "\n" + needle, 1), validator.REBIND_PATH_TEXT)

    def test_53_nonfinite_json_constant_is_rejected(self):
        raw = (validator.ROOT / validator.REBIND_PATH_TEXT).read_text(encoding="utf-8")
        needle = '  "effective_status_after": "RESOLVED_ADAPTER",'
        with self.assertRaises(validator.RebindValidationError):
            validator.load_json_text(raw.replace(needle, '  "effective_status_after": NaN,', 1), validator.REBIND_PATH_TEXT)

    def test_54_archive_byte_tamper_is_rejected_by_exact_sha(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "tampered.zip"
            shutil.copyfile(validator.PLATFORM_ARCHIVE_PATH, target)
            with target.open("ab") as handle:
                handle.write(b"tamper")
            with self.assertRaises(validator.RebindValidationError):
                validator.validate_platform_archive(target)

    def test_55_archive_unregistered_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "unregistered.zip"
            shutil.copyfile(validator.PLATFORM_ARCHIVE_PATH, target)
            self.append_archive_member(target, "payload/unregistered.txt", b"attack")
            self.validate_mutated_archive(target)

    def test_56_archive_symlink_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "symlink.zip"
            shutil.copyfile(validator.PLATFORM_ARCHIVE_PATH, target)
            self.append_archive_member(
                target,
                "payload/symlink",
                b"identity.json",
                mode=stat.S_IFLNK | 0o777,
            )
            self.validate_mutated_archive(target)

    def test_57_archive_parent_escape_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "escape.zip"
            shutil.copyfile(validator.PLATFORM_ARCHIVE_PATH, target)
            self.append_archive_member(target, "../escape", b"attack")
            self.validate_mutated_archive(target)

    def test_58_archive_duplicate_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "duplicate.zip"
            shutil.copyfile(validator.PLATFORM_ARCHIVE_PATH, target)
            self.append_archive_member(target, "ROOT_SHA256", b"0" * 64)
            self.validate_mutated_archive(target)

    def test_59_archive_reported_root_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "root-tamper.zip"
            self.rewrite_archive(target, {"ROOT_SHA256": b"0" * 64})
            self.validate_mutated_archive(target)

    def test_60_archive_manifested_artifact_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact-tamper.zip"
            with zipfile.ZipFile(validator.PLATFORM_ARCHIVE_PATH, "r") as source:
                original = source.read("payload/identity.json")
            self.rewrite_archive(target, {"payload/identity.json": original + b"\n"})
            self.validate_mutated_archive(target)

    def test_61_archive_manifest_hash_forgery_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "manifest-forgery.zip"
            with zipfile.ZipFile(validator.PLATFORM_ARCHIVE_PATH, "r") as source:
                manifest = json.loads(source.read("payload-manifest.json"))
            manifest["artifacts"][0]["sha256"] = "0" * 64
            manifest_raw = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
            root_raw = hashlib.sha256(manifest_raw).hexdigest().encode("ascii") + b"\n"
            self.rewrite_archive(
                target,
                {
                    "payload-manifest.json": manifest_raw,
                    "ROOT_SHA256": root_raw,
                },
            )
            self.validate_mutated_archive(target)


if __name__ == "__main__":
    unittest.main(verbosity=2)
