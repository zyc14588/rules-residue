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
    ACTIVATION_ALLOWLIST,
    ACTIVATION_PROOF_TAG,
    ALLOWLIST,
    APPROVAL_STATUS,
    BASE_CANON_HASH,
    BASE_COMMIT,
    BASE_TREE,
    CANDIDATE_APPROVAL_STATUS,
    CHANGED_OLD_PATHS,
    CHANGE_SET_ID,
    EXPECTED_DECISIONS,
    FIXTURE_ROOT,
    NEW_SEMANTIC_PATHS,
    R1_MANIFEST_FILE_SHA256,
    R1_MERKLE_ROOT,
    activation_allowlist_hash,
    activation_path_records,
    activation_path_set_hash,
    allowlist_hash,
    authoritative_precontent_activation_status,
    collect_errors,
    compute_region_score,
    derive_activation_documents,
    derive_framework_documents,
    expected_approval_consumption,
    validate_b003_authorization,
    validate_activation_closeout_envelope,
    validate_activation_owner_approval,
    validate_final_receipt_binding,
    validate_framework_manifest_transition,
    validate_implementation_approval_consumption,
    validate_intensity_revision,
    validate_m2_dependency_classification,
    validate_precontent_lifecycle_state,
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
        self.assertEqual(len(ACTIVATION_ALLOWLIST), 18)
        self.assertEqual(len(set(ACTIVATION_ALLOWLIST)), 18)
        self.assertEqual(set(CHANGED_OLD_PATHS) | set(NEW_SEMANTIC_PATHS), set(ACTIVATION_ALLOWLIST) - {
            "governance/story-construction/precontent/manifests/framework-manifest.r2.json",
            "governance/story-construction/approvals/OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-CANDIDATE-74FECBE6-R1.consumption.json",
            "governance/story-construction/receipts/scg-precontent-readiness-r1.final.json",
        })
        self.assertEqual(len(activation_allowlist_hash()), 64)

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

    def test_fixed_implementation_candidate_object_validates(self):
        self.assertEqual(
            collect_errors(ROOT, check_git=False, phase="implementation-candidate-object"),
            [],
        )

    def test_tracked_change_set_is_active_but_not_authoritatively_effective(self):
        change_set = load(f"governance/story-construction/change-sets/{CHANGE_SET_ID}.yaml")
        self.assertEqual(change_set["lifecycle_stage"], "APPROVED")
        self.assertEqual(change_set["disposition"], "ACTIVE")
        self.assertEqual(change_set["release"], "NOT_RELEASED")
        self.assertEqual(change_set["approval_status"], APPROVAL_STATUS)
        self.assertTrue(change_set["active_wip"])
        self.assertFalse(change_set["activation_state"]["authoritative_activation_effective"])
        self.assertEqual(validate_precontent_lifecycle_state(change_set), [])

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
        import hashlib
        self.assertEqual(hashlib.sha256(first["manifest_bytes"]).hexdigest(), R1_MANIFEST_FILE_SHA256)
        self.assertEqual(first["framework_merkle_root"], R1_MERKLE_ROOT)
        active_first = derive_activation_documents(ROOT)
        active_second = derive_activation_documents(ROOT)
        self.assertEqual(active_first["manifest_bytes"], active_second["manifest_bytes"])
        self.assertEqual(active_first["receipt_bytes"], active_second["receipt_bytes"])

    def test_exact_r2_merkle_transition_and_schema_counts(self):
        derived = derive_activation_documents(ROOT)
        transition = derived["transition"]
        self.assertEqual(
            tuple(transition[key] for key in (
                "old_record_count", "unchanged_old_count", "changed_old_count",
                "new_record_count", "total_record_count",
            )),
            (68, 61, 7, 8, 76),
        )
        self.assertEqual([item["path"] for item in transition["changed_old_records"]], sorted(CHANGED_OLD_PATHS))
        self.assertEqual([item["path"] for item in transition["new_records"]], sorted(NEW_SEMANTIC_PATHS))
        self.assertEqual(derived["schemas"]["original_count"], 20)
        self.assertEqual(derived["schemas"]["activation_count"], 5)
        self.assertEqual(derived["schemas"]["combined_count"], 25)
        self.assertEqual(validate_framework_manifest_transition(derived["manifest"], derive_framework_documents(ROOT)["manifest"]), [])

    def test_implementation_approval_consumption_and_accept_evidence_are_exact(self):
        record = load("governance/story-construction/approvals/OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-CANDIDATE-74FECBE6-R1.consumption.json")
        self.assertEqual(record, expected_approval_consumption())
        self.assertEqual(validate_implementation_approval_consumption(record), [])
        for field, bad in (("consumption_count", 2), ("transferable", True), ("consumption_result", "FAIL")):
            attack = copy.deepcopy(record)
            attack[field] = bad
            self.assertTrue(validate_implementation_approval_consumption(attack), field)
        missing = copy.deepcopy(record)
        del missing["accept_route_digest"]
        self.assertTrue(validate_implementation_approval_consumption(missing))

    def test_manifest_and_receipt_cycles_are_rejected(self):
        derived = derive_activation_documents(ROOT)
        manifest = copy.deepcopy(derived["manifest"])
        manifest["records"].append({
            "path":"governance/story-construction/precontent/manifests/framework-manifest.r2.json",
            "sha256":"0" * 64,
        })
        self.assertTrue(validate_framework_manifest_transition(manifest, derive_framework_documents(ROOT)["manifest"]))
        wrong_count = copy.deepcopy(derived["manifest"])
        wrong_count["transition"]["total_record_count"] = 75
        self.assertTrue(validate_framework_manifest_transition(wrong_count, derive_framework_documents(ROOT)["manifest"]))
        receipt = copy.deepcopy(derived["receipt"])
        receipt["payload"]["final_inner_receipt_file_sha256"] = "0" * 64
        receipt["payload_hash"] = canonical_sha256(receipt["payload"])
        self.assertTrue(validate_final_receipt_binding(receipt))

    def test_invalid_mixed_lifecycle_and_early_wip_release_are_rejected(self):
        fixture = load("tests/fixtures/story-construction/precontent-lifecycle-state-v1.json")
        for attack in fixture["invalid_mixed_states"]:
            self.assertTrue(validate_precontent_lifecycle_state(attack))
        self.assertEqual(collect_errors(ROOT, check_git=False, phase="invalid-mixed-state"), [])

    def test_provider_m0_canon_runtime_and_m2_drift_are_rejected(self):
        change_set = load(f"governance/story-construction/change-sets/{CHANGE_SET_ID}.yaml")
        schema = load("schemas/story-construction/precontent-change-set-v2.schema.json")
        for mutation in (
            ("provider_request_counts", {"deepseek":0,"grok":0,"opencode":0,"story_m0":1}),
            ("proposed_canon_hash", "0" * 64),
            ("m2_preservation", {}),
        ):
            attack = copy.deepcopy(change_set)
            attack[mutation[0]] = mutation[1]
            self.assertTrue(validate(attack, schema), mutation[0])
        receipt = copy.deepcopy(derive_activation_documents(ROOT)["receipt"])
        receipt["payload"]["fixed_preservation"]["runtime_package_sha256"] = "0" * 64
        receipt["payload_hash"] = canonical_sha256(receipt["payload"])
        self.assertTrue(validate(receipt, load("schemas/story-construction/precontent-final-receipt-v2.schema.json")))

    def test_activation_owner_approval_replay_and_transfer_are_rejected(self):
        records = activation_path_records(ROOT)
        approval = {
            "approval_id":"OWNER-APPROVAL-FUTURE-ACTIVATION",
            "approval_model":"MODEL_B_FULL_FRAMEWORK_HASH_REAPPROVAL",
            "approval_status":"APPROVED",
            "single_use":True,"transferable":False,"consumed":False,"revoked":False,
            "activation_candidate_parent":"74fecbe6984f150f83c364e5d5a5850132cfc147",
            "activation_path_allowlist_sha256":activation_allowlist_hash(),
            "activation_path_hashes":records,
            "activation_path_set_hash":activation_path_set_hash(ROOT),
        }
        self.assertEqual(validate_activation_owner_approval(approval, {}), [])
        approval["consumed"] = True
        self.assertTrue(validate_activation_owner_approval(approval, {}))
        approval["consumed"] = False
        approval["transferable"] = True
        self.assertTrue(validate_activation_owner_approval(approval, {}))

    def test_wrong_tag_lineage_and_remote_proofs_are_rejected(self):
        payload = {
            "binding_strategy": "DETACHED_ANNOTATED_TAG_EXACT_COMMIT_TREE",
            "tag_name": ACTIVATION_PROOF_TAG,
            "tag_target_commit": "a" * 40,
            "activation_candidate_commit": "a" * 40,
            "tag_target_tree": "b" * 40,
            "activation_candidate_tree": "b" * 40,
            "accepted_candidate_commit": "a" * 40,
            "accepted_candidate_tree": "b" * 40,
            "activation_candidate_parent": "74fecbe6984f150f83c364e5d5a5850132cfc147",
            "candidate_to_activation_commit_count": 1,
            "base_to_activation_commit_count": 2,
            "authoritative_remote_before_activation": BASE_COMMIT,
            "activation_accept_task_id": "SCG-PRECONTENT-M3-B002-ACTIVATION-CLOSEOUT-ACCEPT-001",
            "activation_accept_result": "PASS_FIXED_M3_B002_ACTIVATION_CANDIDATE_ACCEPTED",
            "activation_accept_route": "SCG-PRECONTENT-M3-B002-ACTIVATION-CLOSEOUT-ACCEPT",
            "integration_mode": "FAST_FORWARD_ONLY",
            "producer_id": "BUILDER",
            "verifier_id": "INDEPENDENT-VERIFIER",
            "verifier_worktree_state": "CLEAN",
        }
        envelope = {"payload":payload,"payload_hash":canonical_sha256(payload)}
        self.assertEqual(validate_activation_closeout_envelope(envelope, {}), [])
        for field, bad in (
            ("tag_name", "wrong-tag"),
            ("candidate_to_activation_commit_count", 2),
            ("authoritative_remote_before_activation", "0" * 40),
        ):
            attack = copy.deepcopy(envelope)
            attack["payload"][field] = bad
            attack["payload_hash"] = canonical_sha256(attack["payload"])
            self.assertTrue(validate_activation_closeout_envelope(attack, {}), field)
        effective, proof_errors = authoritative_precontent_activation_status(
            tracked_active=True,
            activation_approval=None,
            expected_activation_approval={},
            envelope=None,
            expected_envelope={},
            integration=None,
        )
        self.assertFalse(effective)
        self.assertTrue(proof_errors)

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
