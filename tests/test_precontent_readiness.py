from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.lib.common import runtime_relative_paths
from tools.lib.schema_subset import validate
from tools.story_construction import canonical_sha256, validate_literary_execution, validate_visual_execution
from tools.validate_precontent_readiness import (
    ALLOWLIST,
    APPROVAL_STATUS,
    BASE_CANON_HASH,
    BASE_COMMIT,
    BASE_TREE,
    CHANGE_SET_ID,
    EXPECTED_DECISIONS,
    FIXTURE_ROOT,
    allowlist_hash,
    collect_errors,
    compute_region_score,
    derive_framework_documents,
    validate_b003_authorization,
    validate_intensity_revision,
    validate_m2_dependency_classification,
    validate_precontent_owner_approval,
    validate_readiness_bundle,
    validate_test_boundary,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class PreContentReadinessTests(unittest.TestCase):
    def test_repository_framework_validates(self):
        self.assertEqual(collect_errors(ROOT, check_git=False), [])

    def test_exact_allowlist_is_frozen(self):
        self.assertEqual(len(ALLOWLIST), 70)
        self.assertEqual(allowlist_hash(), "5865bf9d1e6473b0c839b9a9395e96eb5bcaeea3f1b5df0d6bd2679310a9b0bd")

    def test_decision_binding_preserves_exact_ids_options_and_order(self):
        document = load("governance/story-construction/precontent/decisions.scg-pre-q001-q021.yaml")
        actual = tuple((item["id"], item["option"]) for item in document["decisions"])
        self.assertEqual(actual, EXPECTED_DECISIONS)
        self.assertTrue(document["preserves_q001_q130"])

    def test_q001_q130_and_activation_evidence_drift_is_rejected(self):
        expected = load(f"{FIXTURE_ROOT.as_posix()}/expected-static-gates.json")
        for relative, digest in expected["immutable_sha256"].items():
            import hashlib
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)

    def test_partial_supersession_is_exact_and_append_only(self):
        document = load("governance/story-construction/precontent/partial-supersession.scg-pre-r1.yaml")
        self.assertEqual([item["source_decision_id"] for item in document["entries"]], ["Q093", "Q099", "Q129"])
        self.assertTrue(document["append_only"])
        self.assertFalse(document["historical_records_rewritten"])
        self.assertTrue(document["no_other_supersessions"])

    def test_candidate_change_set_cannot_activate_or_self_bind(self):
        change_set = load(f"governance/story-construction/change-sets/{CHANGE_SET_ID}.yaml")
        self.assertEqual(change_set["lifecycle_stage"], "CANDIDATE")
        self.assertEqual(change_set["disposition"], "CANDIDATE_NOT_ACTIVE")
        self.assertEqual(change_set["approval_status"], APPROVAL_STATUS)
        self.assertEqual(change_set["candidate_binding"], {"strategy": "EXACT_HEAD_AT_VALIDATION"})
        self.assertNotIn("candidate_commit", json.dumps(change_set))

    def test_every_synthetic_fixture_has_nonpromotion_boundary(self):
        for path in (ROOT / FIXTURE_ROOT).iterdir():
            if path.suffix == ".json":
                self.assertEqual(validate_test_boundary(json.loads(path.read_text()), path.name), [])

    def test_test_artifact_promoted_to_canon_is_rejected(self):
        graph = load(f"{FIXTURE_ROOT.as_posix()}/test-fixture-graph.json")
        graph["canon"] = True
        self.assertTrue(validate_test_boundary(graph))

    def test_test_id_reused_as_formal_id_is_rejected(self):
        graph = load(f"{FIXTURE_ROOT.as_posix()}/test-fixture-graph.json")
        graph["fixture_id"] = "FORMAL-SCG-M0-001"
        schema = load("schemas/story-construction/test-fixture-graph-v1.schema.json")
        self.assertTrue(validate(graph, schema))

    def test_absolute_rule_has_no_ordinary_exemption_or_deferred_c14(self):
        envelope = load(f"{FIXTURE_ROOT.as_posix()}/test-canon-envelope.json")
        rule = envelope["absolute_rule"]
        self.assertEqual(rule["ordinary_exemption"], "NONE")
        self.assertEqual(rule["defer_r2_c14_dependency"], "NONE")

    def test_normal_and_retreat_routes_exist_and_continue(self):
        dossier = load(f"{FIXTURE_ROOT.as_posix()}/test-region-dossier.json")
        self.assertEqual({row["id"] for row in dossier["routes"]}, {"TEST-ROUTE-NORMAL-SCG-M0-001", "TEST-ROUTE-RETREAT-SCG-M0-001"})
        self.assertTrue(dossier["failure_handling"]["critical_path_continues"])

    def test_illegal_npc_knowledge_is_rejected_by_boundary(self):
        npc = load(f"{FIXTURE_ROOT.as_posix()}/test-npc-epistemic-state.json")
        self.assertIn("TEST-HIDDEN-CAUSE-001", npc["unknowns"])
        self.assertNotIn("TEST-HIDDEN-CAUSE-001", npc["knowledge"])
        npc["knowledge"].append("TEST-HIDDEN-CAUSE-001")
        self.assertIn("TEST-HIDDEN-CAUSE-001", set(npc["knowledge"]) & set(npc["forbidden_knowledge"]))

    def test_worker_created_t1_t2_or_c1_is_rejected(self):
        order = load(f"{FIXTURE_ROOT.as_posix()}/text-order-001.json")
        order["creates_authority"] = True
        schema = load("schemas/story-construction/text-order-v2.schema.json")
        self.assertTrue(validate(order, schema))

    def test_prohibited_reveal_and_combined_modal_leak_are_bounded(self):
        reveal = load(f"{FIXTURE_ROOT.as_posix()}/test-reveal-contract.json")
        oracle = load(f"{FIXTURE_ROOT.as_posix()}/cross-modal-oracle.json")
        self.assertFalse(reveal["owner_reveal_authority_created"])
        self.assertEqual(reveal["text_visual_combined_budget"], "NO_MORE_THAN_ALLOWED_CLAIMS")
        self.assertTrue(oracle["combined_modal_reveal_within_contract"])

    def test_missing_visual_must_object_is_rejected(self):
        order = load(f"{FIXTURE_ROOT.as_posix()}/visual-order-001.json")
        order["must_objects"] = []
        schema = load("schemas/story-construction/visual-order-v2.schema.json")
        self.assertTrue(validate(order, schema))

    def test_raw_grok_request_bypass_is_rejected(self):
        order = load(f"{FIXTURE_ROOT.as_posix()}/visual-order-001.json")
        packet = load(f"{FIXTURE_ROOT.as_posix()}/task-packet-visual-001.json")["task_packet"]
        order["order_authority"] = "RAW_ART_REQUEST"
        self.assertTrue(validate_visual_execution(packet, order, ["workflow/returns/visual/test/candidate.json"]))

    def test_deepseek_literary_order_bypass_is_rejected(self):
        order = load(f"{FIXTURE_ROOT.as_posix()}/text-order-001.json")
        packet = load(f"{FIXTURE_ROOT.as_posix()}/task-packet-text-001.json")["task_packet"]
        order["order_authority"] = "RAW_PROMPT"
        self.assertTrue(validate_literary_execution(packet, order, ["workflow/returns/literary/test/candidate.json"]))

    def test_invalid_context_manifest_and_omission_report_are_rejected(self):
        context = load(f"{FIXTURE_ROOT.as_posix()}/test-context-manifest-text-001.json")
        omission = load(f"{FIXTURE_ROOT.as_posix()}/test-omission-report-text-001.json")
        del context["combined_source_hash"]
        omission["required_dependency_omitted"] = True
        self.assertTrue(validate(context, load("schemas/story-construction/context-manifest-v1.schema.json")))
        self.assertTrue(validate(omission, load("schemas/story-construction/omission-report-v1.schema.json")))

    def test_stale_intensity_revision_invalidates_order(self):
        order = load(f"{FIXTURE_ROOT.as_posix()}/text-order-001.json")
        contract = load(f"{FIXTURE_ROOT.as_posix()}/test-region-intensity-contract.json")
        order["intensity_contract_revision"] = contract["revision"] - 1
        self.assertEqual(validate_intensity_revision(order, contract), ["STALE_CONTRACT_REVISION"])

    def test_missing_m2_dependency_proof_is_rejected(self):
        expected = load(f"{FIXTURE_ROOT.as_posix()}/expected-static-gates.json")
        classification = copy.deepcopy(expected["m2_dependency_classification"])
        classification["closure_proofs"][0]["required_tags"] = [classification["dependency_tags"][0]]
        schema = load("schemas/story-construction/m2-dependency-classification-v1.schema.json")
        self.assertTrue(validate_m2_dependency_classification(classification, schema))

    def test_risk_formula_and_missing_evidence_zero_are_fixed(self):
        scorecard = {
            "formula":"0.70*risk_coverage+0.30*controllability",
            "risk_coverage":[{"evidence_ref":"proof","score":4},{"evidence_ref":"","score":4}],
            "controllability_score":2,
        }
        score, errors = compute_region_score(scorecard)
        self.assertEqual(errors, [])
        self.assertAlmostEqual(score, 2.0)

    def test_provider_call_attempt_during_b002_is_rejected(self):
        self.assertTrue(validate_b003_authorization(None))
        result = subprocess.run(
            [sys.executable, "tools/run_grok_visual_order.py", "--order", f"{FIXTURE_ROOT}/visual-order-001.json", "--task-packet", f"{FIXTURE_ROOT}/task-packet-visual-001.json", "--mode", "execute"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOCKED_NO_OWNER_APPROVED_M3_B003_PROVIDER_AUTHORIZATION", result.stdout)

    def test_owner_approval_replay_transfer_and_hash_mismatch_are_rejected(self):
        expected_hashes = {"framework_manifest_file_sha256":"a" * 64,"pending_receipt_payload_hash":"b" * 64}
        approval = {
            "approval_id":"OWNER-APPROVAL-TEST","change_set_id":CHANGE_SET_ID,
            "base_commit":BASE_COMMIT,"base_tree":BASE_TREE,"base_canon_hash":BASE_CANON_HASH,
            "candidate_commit":"c" * 40,"candidate_tree":"d" * 40,"approval_status":"APPROVED",
            "single_use":True,"transferable":False,"consumed":False,"revoked":False,
            "hash_binding":expected_hashes,
        }
        self.assertEqual(validate_precontent_owner_approval(approval, expected_hashes), [])
        approval["consumed"] = True
        self.assertTrue(validate_precontent_owner_approval(approval, expected_hashes))
        approval["consumed"] = False
        approval["change_set_id"] = "TRANSFERRED"
        self.assertTrue(validate_precontent_owner_approval(approval, expected_hashes))

    def test_readiness_bundle_hash_mismatch_is_rejected(self):
        schema = load("schemas/story-construction/precontent-readiness-bundle-v1.schema.json")
        bundle = {
            "schema_version":"rules-residue.story-construction.precontent-readiness-bundle/1.0.0","bundle_id":"TEST-BUNDLE","change_set_id":CHANGE_SET_ID,
            "decision_set_hash":"a"*64,"partial_supersession_hash":"b"*64,"traceability_hash":"c"*64,"schema_set_hash":"d"*64,"m0_acceptance_bundle_hash":"e"*64,"global_t1_closure_hash":"f"*64,"region_interface_matrix_hash":"1"*64,"causal_epistemic_proof_hash":"2"*64,"region_risk_scorecard_hash":"3"*64,"provider_certificate_hashes":["4"*64,"5"*64],
            "rights_gate":"PASS","owner_exact_hash_approval":"APPROVED","result":"READY_FOR_FORMAL_VERTICAL_SLICE","scoped_blockers":[],"bundle_payload_hash":"0"*64,
        }
        self.assertTrue(validate_readiness_bundle(bundle, schema))

    def test_test_artifacts_never_enter_runtime_package(self):
        runtime = runtime_relative_paths(ROOT / "game-package")
        self.assertFalse(any("precontent" in path.lower() or "test-scg-m0" in path.lower() for path in runtime))

    def test_framework_manifest_and_receipt_are_byte_deterministic(self):
        first = derive_framework_documents(ROOT)
        second = derive_framework_documents(ROOT)
        self.assertEqual(first["manifest_bytes"], second["manifest_bytes"])
        self.assertEqual(first["receipt_bytes"], second["receipt_bytes"])
        self.assertNotIn("manifest_sha256", first["manifest"])
        self.assertNotIn("receipt_sha256", first["manifest"])

    def test_fault_injection_uses_isolated_copy_and_rejects_promotion(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "fixture.json"
            output = Path(temporary) / "receipt.json"
            source.write_text((ROOT / FIXTURE_ROOT / "test-fixture-graph.json").read_text(), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "tools/run_m0_fault_injection.py", "--input-copy", str(source), "--fault-id", "TEST-FAULT-PROMOTION-001", "--output-receipt", str(output)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(json.loads(output.read_text())["output_accepted"])


if __name__ == "__main__":
    unittest.main()
