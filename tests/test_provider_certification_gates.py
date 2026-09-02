from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.lib.schema_subset import validate
from tools.story_construction import canonical_json_bytes, canonical_sha256
from tools.validate_precontent_readiness import (
    FIXTURE_ROOT,
    validate_b003_authorization,
    validate_external_cas_contract,
    validate_profile_preflight,
    validate_provider_certificate,
    validate_provider_run_receipt,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def make_receipt(run_id: str, **changes):
    receipt = {
        "schema_version":"rules-residue.story-construction.provider-run-receipt/1.0.0",
        "run_id":run_id,"profile_id":"TEST-DEEPSEEK-HARNESS-PRECONTENT-M0-R1","provider_id":"DEEPSEEK-HARNESS","evidence_kind":"REAL_PROVIDER_EXECUTION",
        "requested_model_alias":"deepseek-v4-pro","resolved_model":"deepseek-v4-pro@provider-revision-2026-09","provider_revision":"2026-09","actual_fingerprint":"fp-deepseek-v4-pro-202609",
        "identity_assurance":"RESOLVED_AND_FINGERPRINTED","adapter_identity":"codex-harness-adapter/test","configuration_sha256":"a"*64,
        "policy_evidence_id":"TEST-POLICY-EVIDENCE-001","policy_evidence_date":"2026-09-02","data_control_evidence":"TEST-OPT-OUT-CONTROL-001","jurisdiction_evidence":"TEST-JURISDICTION-EVIDENCE-001",
        "input_sha256":"b"*64,"order_sha256":"c"*64,"context_manifest_sha256":"d"*64,"output_sha256":canonical_sha256({"run":run_id}),
        "source_license_provenance":["first-party synthetic TEST inputs"],"rights_obligations":["Provider attribution evidence retained"],"rights_status":"RIGHTS_PENDING","release_eligible":False,
        "cost_recorded":True,"latency_recorded":True,"quality_gate_adjusted_for_cost_or_latency":False,"private_chain_of_thought_recorded":False,"secrets_recorded":False,
    }
    receipt.update(changes)
    receipt["receipt_payload_hash"] = canonical_sha256(receipt)
    return receipt


def make_certificate(receipts, **changes):
    certificate = {
        "schema_version":"rules-residue.story-construction.provider-certificate/1.0.0","certificate_id":"TEST-PROVIDER-CERT-DEEPSEEK-001","certificate_subject":"PROVIDER","provider_id":"DEEPSEEK-HARNESS","profile_id":"TEST-DEEPSEEK-HARNESS-PRECONTENT-M0-R1","profile_version":"1.0.0",
        "resolved_model":"deepseek-v4-pro@provider-revision-2026-09","provider_revision":"2026-09","actual_fingerprint":"fp-deepseek-v4-pro-202609","identity_assurance":"RESOLVED_AND_FINGERPRINTED","capability_envelope":["TEXT","THINKING_ENABLED","120000_INPUT","24000_OUTPUT"],
        "consecutive_real_run_ids":[row["run_id"] for row in receipts],"fault_injection_receipt_id":"TEST-FAULT-RECEIPT-DEEPSEEK-001","run_count":3,"distinct_run_evidence":True,"drift_preflight":"COMPATIBLE","suspension_triggers":["MODEL_DRIFT","PROFILE_DRIFT","FINGERPRINT_DRIFT","POLICY_DRIFT","DATA_CONTROL_DRIFT","CAPABILITY_DRIFT","RIGHTS_DRIFT"],"certification_result":"CERTIFIED","owner_data_boundary_approval_id":"OWNER-APPROVAL-M3-B003-TEST-001",
    }
    certificate.update(changes)
    certificate["certificate_payload_hash"] = canonical_sha256(certificate)
    return certificate


def make_preflight(**changes):
    value = {
        "schema_version":"rules-residue.story-construction.profile-compatibility-preflight/1.0.0","preflight_id":"TEST-PREFLIGHT-DEEPSEEK-001","provider_id":"DEEPSEEK-HARNESS","profile_id":"TEST-DEEPSEEK-HARNESS-PRECONTENT-M0-R1","requested_model_alias":"deepseek-v4-pro","resolved_model":"deepseek-v4-pro@provider-revision-2026-09","provider_revision":"2026-09","actual_fingerprint":"fp-deepseek-v4-pro-202609","expected_configuration_sha256":"a"*64,"actual_configuration_sha256":"a"*64,"capability_checks":[{"capability":"TEXT","expected":"SUPPORTED","actual":"SUPPORTED","match":True}],"result":"COMPATIBLE","checked_at_evidence_id":"TEST-PREFLIGHT-EVIDENCE-001",
    }
    value.update(changes)
    return value


class ProviderCertificationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_schema = load("schemas/story-construction/provider-run-receipt-v1.schema.json")
        cls.certificate_schema = load("schemas/story-construction/provider-certificate-v1.schema.json")
        cls.preflight_schema = load("schemas/story-construction/profile-compatibility-preflight-v1.schema.json")

    def test_valid_real_provider_receipt_passes(self):
        self.assertEqual(validate_provider_run_receipt(make_receipt("TEST-RUN-DEEPSEEK-001"), self.run_schema), [])

    def test_simulated_or_cached_output_cannot_be_real_evidence(self):
        receipt = make_receipt("TEST-RUN-DEEPSEEK-001", evidence_kind="SIMULATED_CACHE")
        receipt["receipt_payload_hash"] = canonical_sha256({k:v for k,v in receipt.items() if k != "receipt_payload_hash"})
        self.assertTrue(validate_provider_run_receipt(receipt, self.run_schema))

    def test_missing_provider_profile_or_resolved_identity_is_rejected(self):
        receipt = make_receipt("TEST-RUN-DEEPSEEK-001")
        del receipt["resolved_model"]
        self.assertTrue(validate_provider_run_receipt(receipt, self.run_schema))

    def test_alias_only_identity_is_rejected(self):
        receipt = make_receipt("TEST-RUN-DEEPSEEK-001", resolved_model="deepseek-v4-pro", actual_fingerprint="ALIAS_ONLY")
        receipt["receipt_payload_hash"] = canonical_sha256({k:v for k,v in receipt.items() if k != "receipt_payload_hash"})
        self.assertTrue(validate_provider_run_receipt(receipt, self.run_schema))

    def test_missing_provenance_cannot_be_release_eligible(self):
        receipt = make_receipt("TEST-RUN-DEEPSEEK-001", source_license_provenance=[], release_eligible=True)
        receipt["receipt_payload_hash"] = canonical_sha256({k:v for k,v in receipt.items() if k != "receipt_payload_hash"})
        self.assertTrue(validate_provider_run_receipt(receipt, self.run_schema))

    def test_cost_or_latency_cannot_lower_quality_gates(self):
        receipt = make_receipt("TEST-RUN-DEEPSEEK-001", quality_gate_adjusted_for_cost_or_latency=True)
        receipt["receipt_payload_hash"] = canonical_sha256({k:v for k,v in receipt.items() if k != "receipt_payload_hash"})
        self.assertTrue(validate_provider_run_receipt(receipt, self.run_schema))

    def test_three_distinct_consecutive_runs_certify_provider(self):
        receipts = [make_receipt(f"TEST-RUN-DEEPSEEK-00{index}") for index in (1,2,3)]
        certificate = make_certificate(receipts)
        self.assertEqual(validate_provider_certificate(certificate, receipts, self.certificate_schema), [])

    def test_reused_third_run_evidence_is_rejected(self):
        receipts = [make_receipt("TEST-RUN-DEEPSEEK-001"), make_receipt("TEST-RUN-DEEPSEEK-002"), make_receipt("TEST-RUN-DEEPSEEK-002")]
        certificate = make_certificate(receipts)
        self.assertTrue(validate_provider_certificate(certificate, receipts, self.certificate_schema))

    def test_run_model_profile_and_fingerprint_drift_is_rejected(self):
        receipts = [make_receipt(f"TEST-RUN-DEEPSEEK-00{index}") for index in (1,2,3)]
        receipts[2] = make_receipt("TEST-RUN-DEEPSEEK-003", actual_fingerprint="fp-drift")
        certificate = make_certificate(receipts)
        self.assertTrue(validate_provider_certificate(certificate, receipts, self.certificate_schema))

    def test_certificate_subject_is_provider(self):
        receipts = [make_receipt(f"TEST-RUN-DEEPSEEK-00{index}") for index in (1,2,3)]
        certificate = make_certificate(receipts, certificate_subject="MODEL")
        certificate["certificate_payload_hash"] = canonical_sha256({k:v for k,v in certificate.items() if k != "certificate_payload_hash"})
        self.assertTrue(validate_provider_certificate(certificate, receipts, self.certificate_schema))

    def test_incompatible_preflight_cannot_claim_compatible(self):
        preflight = make_preflight(actual_configuration_sha256="b"*64)
        self.assertTrue(validate_profile_preflight(preflight, self.preflight_schema))

    def test_preflight_result_enum_is_exact(self):
        for result in ("COMPATIBLE","INCOMPATIBLE","REVALIDATION_REQUIRED"):
            value = make_preflight(result=result)
            if result != "COMPATIBLE":
                value["capability_checks"][0]["match"] = False
            self.assertFalse(validate(value, self.preflight_schema))
        self.assertTrue(validate(make_preflight(result="PASS"), self.preflight_schema))

    def test_certification_suspends_on_noncompatible_drift(self):
        receipts = [make_receipt(f"TEST-RUN-DEEPSEEK-00{index}") for index in (1,2,3)]
        certificate = make_certificate(receipts, drift_preflight="REVALIDATION_REQUIRED")
        certificate["certificate_payload_hash"] = canonical_sha256({k:v for k,v in certificate.items() if k != "certificate_payload_hash"})
        self.assertTrue(validate_provider_certificate(certificate, receipts, self.certificate_schema))

    def test_fault_injection_output_cannot_be_accepted_as_valid(self):
        schema = load("schemas/story-construction/fault-injection-receipt-v1.schema.json")
        receipt = {
            "schema_version":"rules-residue.story-construction.fault-injection-receipt/1.0.0","receipt_id":"TEST-FAULT-RECEIPT-INVALID-001","profile_id":"TEST-PROFILE-001","namespace_prefix":"TEST-","canon":False,"release_eligible":False,"promotion_allowed":False,"disposition":"TEST_EVIDENCE_ONLY","fault_id":"TEST-FAULT-INVALID-001","isolated_copy":True,"provider_called":False,"fault_injected":"bad identity","expected_gate":"PROVIDER_IDENTITY","observed_rejection":True,"output_accepted":False,"receipt_payload_hash":"a"*64,
        }
        self.assertFalse(validate(receipt, schema))
        receipt["output_accepted"] = True
        self.assertTrue(validate(receipt, schema))

    def test_valid_b003_authorization_envelope_passes(self):
        envelope = {"authorization_kind":"OWNER_APPROVED_M3_B003_PROVIDER_EXECUTION","milestone":"M3","batch_id":"M3-B003","status":"APPROVED","synthetic_test_only":True,"owner_approval_id":"OWNER-B003","candidate_commit":"a"*40,"candidate_tree":"b"*40,"data_boundary_hash":"c"*64}
        self.assertEqual(validate_b003_authorization(envelope), [])
        envelope["batch_id"] = "M3-B002"
        self.assertTrue(validate_b003_authorization(envelope))

    def test_external_cas_contract_passes_with_0700_append_only_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cas"
            root.mkdir(mode=0o700)
            policy = {"manifest":"CONTENT_ADDRESSED_APPEND_ONLY","raw_private_chain_of_thought":"FORBIDDEN","secrets":"FORBIDDEN","redacted_raw_protocol_retention":"THROUGH_M3_B004_ACCEPT_PLUS_90_DAYS","post_retention_action":"OWNER_DECISION_REQUIRED","normalized_test_evidence":"PERMANENT_HISTORICAL"}
            (root / "retention-policy.json").write_bytes(canonical_json_bytes(policy))
            (root / "manifest.jsonl").write_text(json.dumps({"sha256":"a"*64,"kind":"NORMALIZED_TEST_EVIDENCE"})+"\n", encoding="utf-8")
            self.assertEqual(validate_external_cas_contract(root), [])

    def test_external_cas_wrong_permissions_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cas"
            root.mkdir(mode=0o755)
            (root / "retention-policy.json").write_text("{}\n", encoding="utf-8")
            (root / "manifest.jsonl").write_text("", encoding="utf-8")
            self.assertTrue(validate_external_cas_contract(root))

    def test_external_cas_private_chain_of_thought_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cas"
            root.mkdir(mode=0o700)
            policy = {"manifest":"CONTENT_ADDRESSED_APPEND_ONLY","raw_private_chain_of_thought":"FORBIDDEN","secrets":"FORBIDDEN","redacted_raw_protocol_retention":"THROUGH_M3_B004_ACCEPT_PLUS_90_DAYS","post_retention_action":"OWNER_DECISION_REQUIRED","normalized_test_evidence":"PERMANENT_HISTORICAL"}
            (root / "retention-policy.json").write_bytes(canonical_json_bytes(policy))
            (root / "manifest.jsonl").write_text(json.dumps({"sha256":"a"*64,"private_chain_of_thought":False})+"\n", encoding="utf-8")
            self.assertTrue(validate_external_cas_contract(root))

    def test_harness_receipt_export_normalizes_local_evidence_without_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "receipt.json"
            output = Path(temporary) / "normalized.json"
            source.write_bytes(canonical_json_bytes(make_receipt("TEST-RUN-DEEPSEEK-001")))
            result = subprocess.run([sys.executable,"tools/export_harness_run_receipt.py","--input-json",str(source),"--output-json",str(output)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertTrue(output.is_file())

    def test_grok_wrapper_validation_and_dry_run_make_zero_requests(self):
        for mode in ("validate","dry-run"):
            result = subprocess.run([sys.executable,"tools/run_grok_visual_order.py","--order",f"{FIXTURE_ROOT}/visual-order-001.json","--task-packet",f"{FIXTURE_ROOT}/task-packet-visual-001.json","--mode",mode],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn("provider_request_count=0",result.stdout)


if __name__ == "__main__":
    unittest.main()
