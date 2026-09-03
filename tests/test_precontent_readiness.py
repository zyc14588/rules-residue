from __future__ import annotations

import copy
import hashlib
import json
import shutil
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
from tools.story_construction import canonical_json_bytes, canonical_sha256, validate_literary_execution, validate_visual_execution
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
    REPAIR_ACCEPT_RESULT,
    REPAIR_ACCEPT_ROUTE,
    REPAIR_ACCEPT_TASK_ID,
    REPAIR_ACCEPT_VERIFIER,
    REPAIR_ALLOWLIST,
    REPAIR_PATH_ALLOWLIST_SHA256,
    REPAIR_PROOF_TAG_REF,
    R2_MANIFEST_FILE_SHA256,
    R2_MANIFEST_PATH,
    R3_CHANGED_OLD_PATHS,
    R3_NEW_SEMANTIC_PATHS,
    R1_MANIFEST_FILE_SHA256,
    R1_MERKLE_ROOT,
    activation_allowlist_hash,
    activation_path_records,
    activation_path_set_hash,
    allowlist_hash,
    authoritative_precontent_activation_status,
    collect_errors,
    compute_region_score,
    derive_repair_documents,
    derive_framework_documents,
    expected_repair_approval_fields,
    expected_approval_consumption,
    load_external_proof_json,
    repair_allowlist_hash,
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
    validate_repair_closeout_envelope,
    validate_repair_manifest_transition,
    validate_repair_owner_approval,
    validate_repair_receipt_binding,
    validate_readiness_bundle,
    validate_test_boundary,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout.rstrip("\n")


def build_repair_envelope(expected: dict, approval: dict, raw_sha256: str, canonical_digest: str) -> dict:
    lineage = expected["lineage"]
    transition = expected["r3_transition"]
    schemas = expected["schema_sets"]
    contracts = expected["contracts"]
    proof = expected["proof_contract"]
    payload = {
        "envelope_id": f"SCG-PRECONTENT-M3-B002-AUTHORITATIVE-EFFECT-REPAIR-{lineage['repair_commit'][:8].upper()}",
        "defect_id": expected["defect_id"],
        "change_set_id": expected["change_set_id"],
        "binding_strategy": "DETACHED_ANNOTATED_TAG_EXACT_COMMIT_TREE_REMOTE_REFS",
        "repair_candidate": {
            "commit": lineage["repair_commit"],
            "tree": lineage["repair_tree"],
            "parent": lineage["repair_parent"],
            "defective_to_repair_count": 1,
            "implementation_to_repair_count": 2,
            "base_to_repair_count": 3,
        },
        "repair_path_set_hash": expected["repair_path_set_hash"],
        "framework_manifest_r3": {
            "file_sha256": expected["framework_manifests"]["r3"]["file_sha256"],
            "merkle_root": expected["framework_manifests"]["r3"]["merkle_root"],
            "record_count": 81,
            "semantic_path_content_record_set_hash": transition["r3_leaf_set_hash"],
        },
        "schema_sets": {
            "original_schema_set_hash": schemas["original_schema_set_hash"],
            "preserved_activation_v1_schema_set_hash": schemas["preserved_activation_v1_schema_set_hash"],
            "repair_schema_set_hash": schemas["repair_schema_set_hash"],
            "combined_schema_set_hash": schemas["combined_schema_set_hash"],
        },
        "final_receipt_v3": {
            "path": contracts["final_receipt_v3_path"],
            "file_sha256": contracts["final_receipt_v3_file_sha256"],
            "payload_hash": contracts["final_receipt_v3_payload_hash"],
        },
        "activation_owner_approval": {
            "approval_id": approval["approval_id"],
            "raw_sha256": raw_sha256,
            "canonical_sha256": canonical_digest,
            "approval_issued_consumed": False,
            "single_use": True,
            "transferable": False,
            "revoked": False,
        },
        "approval_consumption": {
            "consumption_count": 1,
            "consumed_by_accept_task": REPAIR_ACCEPT_TASK_ID,
            "events": [{
                "approval_id": approval["approval_id"],
                "approval_raw_sha256": raw_sha256,
                "approval_canonical_sha256": canonical_digest,
                "accept_task_id": REPAIR_ACCEPT_TASK_ID,
                "accept_result": REPAIR_ACCEPT_RESULT,
                "accept_verifier": REPAIR_ACCEPT_VERIFIER,
                "accept_route": REPAIR_ACCEPT_ROUTE,
                "accept_route_digest": proof["repair_accept_route_digest"],
            }],
        },
        "repair_accept": {
            "task_id": REPAIR_ACCEPT_TASK_ID,
            "result": REPAIR_ACCEPT_RESULT,
            "verifier": REPAIR_ACCEPT_VERIFIER,
            "route": REPAIR_ACCEPT_ROUTE,
            "route_digest": proof["repair_accept_route_digest"],
        },
        "proof_tag": {
            "ref": proof["proof_tag_ref"],
            "target_commit": lineage["repair_commit"],
            "target_tree": lineage["repair_tree"],
        },
        "integration": {
            "mode": "FAST_FORWARD_ONLY",
            "authoritative_ref": proof["authoritative_ref"],
            "remote_name": proof["remote_name"],
            "expected_remote_url": proof["expected_remote_url"],
            "remote_authoritative_ref": proof["remote_authoritative_ref"],
            "remote_proof_tag_ref": proof["remote_proof_tag_ref"],
            "authoritative_remote_before_repair": BASE_COMMIT,
            "authoritative_remote_after_repair": lineage["repair_commit"],
        },
        "fixed_preservation": {
            "canon_hash": BASE_CANON_HASH,
            "runtime_package_sha256": expected["fixed_preservation"]["runtime_package_sha256"],
            "provider_request_counts": {"deepseek": 0, "grok": 0, "opencode": 0, "story_m0": 0},
        },
        "producer_id": "TEST-INDEPENDENT-ACCEPT-PRODUCER",
        "verifier_id": REPAIR_ACCEPT_VERIFIER,
        "verifier_worktree_state": "CLEAN",
    }
    return {
        "schema_version": "rules-residue.story-construction.precontent-activation-closeout-envelope/2.0.0",
        "envelope_kind": "DETACHED_ACCEPTED_AUTHORITATIVE_EFFECT_REPAIR_ENVELOPE",
        "payload": payload,
        "payload_hash": canonical_sha256(payload),
    }


def create_authoritative_fixture(temporary: Path) -> dict:
    repository = temporary / "candidate"
    remote = temporary / "remote.git"
    proof_root = temporary / "proofs"
    subprocess.run(
        ["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(repository)],
        check=True,
        capture_output=True,
        text=True,
    )
    run_git(repository, "config", "user.name", "PreContent Test")
    run_git(repository, "config", "user.email", "precontent-test@invalid.example")
    run_git(repository, "switch", "-C", "design/r1-story-architecture", "d80aae8d1dfede85d91ff0367f4c6a18d62bb2a7")
    for relative in REPAIR_ALLOWLIST:
        source = ROOT / relative
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    run_git(repository, "add", "--", *REPAIR_ALLOWLIST)
    run_git(repository, "commit", "-m", "test: synthetic authoritative-effect repair candidate")
    repair_commit = run_git(repository, "rev-parse", "HEAD")
    repair_tree = run_git(repository, "rev-parse", "HEAD^{tree}")
    subprocess.run(
        ["git", "init", "--bare", "--quiet", str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )
    run_git(repository, "remote", "set-url", "origin", str(remote))
    run_git(
        repository,
        "push",
        "origin",
        f"{BASE_COMMIT}:refs/heads/design/r1-story-architecture",
    )
    expected = expected_repair_approval_fields(
        repository,
        repair_commit=repair_commit,
        repair_tree=repair_tree,
        repair_parent="d80aae8d1dfede85d91ff0367f4c6a18d62bb2a7",
        proof_tag_ref=REPAIR_PROOF_TAG_REF,
        authoritative_ref="refs/heads/design/r1-story-architecture",
        remote_name="origin",
        expected_remote_url=str(remote),
        remote_authoritative_ref="refs/heads/design/r1-story-architecture",
        remote_proof_tag_ref=REPAIR_PROOF_TAG_REF,
    )
    approval = {
        "schema_version": "rules-residue.story-construction.precontent-activation-owner-approval/2.0.0",
        "approval_id": f"OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-AUTHORITATIVE-EFFECT-REPAIR-CANDIDATE-{repair_commit[:8].upper()}-R1",
        **expected,
        "approval_status": "APPROVED",
        "single_use": True,
        "transferable": False,
        "consumed": False,
        "revoked": False,
        "owner_id": "OWNER",
        "approved_at": "2030-01-01T00:00:00Z",
    }
    proof_root.mkdir()
    approval_path = (proof_root / "owner-approval.json").resolve()
    approval_bytes = canonical_json_bytes(approval)
    approval_path.write_bytes(approval_bytes)
    approval_sha256 = hashlib.sha256(approval_bytes).hexdigest()
    envelope = build_repair_envelope(expected, approval, approval_sha256, approval_sha256)
    envelope_path = (proof_root / "closeout-envelope.json").resolve()
    envelope_path.write_bytes(canonical_json_bytes(envelope))
    tag_name = REPAIR_PROOF_TAG_REF.removeprefix("refs/tags/")
    run_git(repository, "tag", "--annotate", "--cleanup=verbatim", "--file", str(envelope_path), tag_name, repair_commit)
    run_git(
        repository,
        "push",
        "--atomic",
        "origin",
        "refs/heads/design/r1-story-architecture",
        REPAIR_PROOF_TAG_REF,
    )
    base_cli = [
        sys.executable,
        "tools/validate_precontent_readiness.py",
        "--project-root", str(repository),
        "--phase", "authoritative-effect",
    ]
    proof_cli = [
        "--activation-owner-approval", str(approval_path),
        "--activation-closeout-envelope", str(envelope_path),
        "--expected-repair-commit", repair_commit,
        "--expected-repair-tree", repair_tree,
        "--expected-repair-parent", "d80aae8d1dfede85d91ff0367f4c6a18d62bb2a7",
        "--proof-tag-ref", REPAIR_PROOF_TAG_REF,
        "--authoritative-ref", "refs/heads/design/r1-story-architecture",
        "--remote-name", "origin",
        "--expected-remote-url", str(remote),
        "--remote-authoritative-ref", "refs/heads/design/r1-story-architecture",
        "--remote-proof-tag-ref", REPAIR_PROOF_TAG_REF,
    ]
    return {
        "repository": repository,
        "remote": remote,
        "approval": approval,
        "approval_bytes": approval_bytes,
        "approval_path": approval_path,
        "envelope": envelope,
        "envelope_path": envelope_path,
        "expected": expected,
        "repair_commit": repair_commit,
        "repair_tree": repair_tree,
        "base_cli": base_cli,
        "proof_cli": proof_cli,
    }


def run_authoritative_cli(fixture: dict, proof_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        fixture["base_cli"] + (fixture["proof_cli"] if proof_args is None else proof_args),
        cwd=fixture["repository"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


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
        self.assertEqual(len(REPAIR_ALLOWLIST), 13)
        self.assertEqual(len(set(REPAIR_ALLOWLIST)), 13)
        self.assertEqual(repair_allowlist_hash(), REPAIR_PATH_ALLOWLIST_SHA256)
        self.assertEqual(
            set(R3_CHANGED_OLD_PATHS) | set(R3_NEW_SEMANTIC_PATHS),
            set(REPAIR_ALLOWLIST) - {
                "governance/story-construction/precontent/manifests/framework-manifest.r3.json",
                "governance/story-construction/receipts/scg-precontent-readiness-r3.final.json",
            },
        )

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
        self.assertEqual(hashlib.sha256(first["manifest_bytes"]).hexdigest(), R1_MANIFEST_FILE_SHA256)
        self.assertEqual(first["framework_merkle_root"], R1_MERKLE_ROOT)
        self.assertEqual(hashlib.sha256((ROOT / R2_MANIFEST_PATH).read_bytes()).hexdigest(), R2_MANIFEST_FILE_SHA256)
        repair_first = derive_repair_documents(ROOT)
        repair_second = derive_repair_documents(ROOT)
        self.assertEqual(repair_first["manifest_bytes"], repair_second["manifest_bytes"])
        self.assertEqual(repair_first["receipt_bytes"], repair_second["receipt_bytes"])
        receipt_bytes = repair_first["receipt_bytes"]
        for forbidden in (
            b'"repair_commit"', b'"repair_tree"', b'"repair_owner_approval_id"',
            REPAIR_ACCEPT_TASK_ID.encode(), REPAIR_ACCEPT_RESULT.encode(),
            REPAIR_PROOF_TAG_REF.encode(), b'"authoritative_remote_after_repair"',
            b'"tag_object_id"', b'"envelope_file_sha256"',
        ):
            self.assertNotIn(forbidden, receipt_bytes)

    def test_exact_r3_merkle_transition_and_schema_counts(self):
        derived = derive_repair_documents(ROOT)
        transition = derived["transition"]
        self.assertEqual(
            tuple(transition[key] for key in (
                "old_record_count", "unchanged_old_count", "changed_old_count",
                "new_record_count", "total_record_count",
            )),
            (76, 70, 6, 5, 81),
        )
        self.assertEqual([item["path"] for item in transition["changed_old_records"]], sorted(R3_CHANGED_OLD_PATHS))
        self.assertEqual([item["path"] for item in transition["new_records"]], sorted(R3_NEW_SEMANTIC_PATHS))
        self.assertEqual(derived["schemas"]["original_count"], 20)
        self.assertEqual(derived["schemas"]["preserved_activation_v1_count"], 5)
        self.assertEqual(derived["schemas"]["repair_count"], 3)
        self.assertEqual(derived["schemas"]["combined_count"], 28)
        self.assertEqual(validate_repair_manifest_transition(derived["manifest"], load(R2_MANIFEST_PATH.as_posix())), [])

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
        derived = derive_repair_documents(ROOT)
        manifest = copy.deepcopy(derived["manifest"])
        manifest["records"].append({
            "path":"governance/story-construction/precontent/manifests/framework-manifest.r3.json",
            "sha256":"0" * 64,
        })
        self.assertTrue(validate_repair_manifest_transition(manifest, load(R2_MANIFEST_PATH.as_posix())))
        wrong_count = copy.deepcopy(derived["manifest"])
        wrong_count["transition"]["total_record_count"] = 80
        self.assertTrue(validate_repair_manifest_transition(wrong_count, load(R2_MANIFEST_PATH.as_posix())))
        receipt = copy.deepcopy(derived["receipt"])
        receipt["payload"]["framework_manifests"]["r3"]["file_sha256"] = "0" * 64
        receipt["payload_hash"] = canonical_sha256(receipt["payload"])
        self.assertTrue(validate_repair_receipt_binding(receipt, derived["receipt"]))

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
        derived = derive_repair_documents(ROOT)
        receipt = copy.deepcopy(derived["receipt"])
        receipt["payload"]["fixed_preservation"]["runtime_package_sha256"] = "0" * 64
        receipt["payload_hash"] = canonical_sha256(receipt["payload"])
        self.assertTrue(validate_repair_receipt_binding(receipt, derived["receipt"]))

    def test_authoritative_effect_real_cli_accepts_complete_external_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = create_authoritative_fixture(Path(temporary))
            result = run_authoritative_cli(fixture)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PRECONTENT_READINESS: PASS", result.stdout)
            self.assertIn("AUTHORITATIVE_M3_B002_EFFECTIVE=true", result.stdout)
            self.assertIn("effective_active_wip=false", result.stdout)
            self.assertIn("global_active_WIP=0", result.stdout)
            self.assertEqual(run_git(fixture["repository"], "cat-file", "-t", REPAIR_PROOF_TAG_REF), "tag")
            self.assertEqual(
                run_git(fixture["repository"], "rev-parse", f"{REPAIR_PROOF_TAG_REF}^{{commit}}"),
                fixture["repair_commit"],
            )

    def test_authoritative_effect_proof_matrix_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = create_authoritative_fixture(Path(temporary))
            approval_schema = json.loads(
                (fixture["repository"] / "schemas/story-construction/precontent-activation-owner-approval-v2.schema.json").read_text()
            )
            envelope_schema = json.loads(
                (fixture["repository"] / "schemas/story-construction/precontent-activation-closeout-envelope-v2.schema.json").read_text()
            )
            approval_sha256 = hashlib.sha256(fixture["approval_bytes"]).hexdigest()
            self.assertEqual(
                validate_repair_owner_approval(fixture["approval"], fixture["expected"], approval_schema),
                [],
            )
            self.assertEqual(
                validate_repair_closeout_envelope(
                    fixture["envelope"],
                    approval=fixture["approval"],
                    approval_raw_sha256=approval_sha256,
                    approval_canonical_sha256=approval_sha256,
                    expected_approval=fixture["expected"],
                    schema=envelope_schema,
                ),
                [],
            )

            approval_attacks = []
            for path, value in (
                (("consumed",), True),
                (("approval_id",), "OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-ACTIVATION-CANDIDATE-D80AAE8D-R1"),
                (("repair_path_set_hash",), "0" * 64),
                (("lineage", "repair_parent"), "0" * 40),
                (("proof_contract", "remote_authoritative_ref"), "refs/heads/wrong"),
            ):
                attack = copy.deepcopy(fixture["approval"])
                target = attack
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                approval_attacks.append((".".join(path), attack))
            for label, attack in approval_attacks:
                self.assertTrue(
                    validate_repair_owner_approval(attack, fixture["expected"], approval_schema),
                    label,
                )

            envelope_attacks = []
            bad_payload_hash = copy.deepcopy(fixture["envelope"])
            bad_payload_hash["payload_hash"] = "0" * 64
            envelope_attacks.append(("payload_hash", bad_payload_hash))
            for path, value in (
                (("approval_consumption", "consumption_count"), 2),
                (("repair_accept", "result"), "FAIL"),
                (("activation_owner_approval", "raw_sha256"), "0" * 64),
                (("producer_id",), REPAIR_ACCEPT_VERIFIER),
            ):
                attack = copy.deepcopy(fixture["envelope"])
                target = attack["payload"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                attack["payload_hash"] = canonical_sha256(attack["payload"])
                envelope_attacks.append((".".join(path), attack))
            self_reference = copy.deepcopy(fixture["envelope"])
            self_reference["payload"]["envelope_file_sha256"] = "0" * 64
            self_reference["payload_hash"] = canonical_sha256(self_reference["payload"])
            envelope_attacks.append(("self_reference", self_reference))
            for label, attack in envelope_attacks:
                self.assertTrue(
                    validate_repair_closeout_envelope(
                        attack,
                        approval=fixture["approval"],
                        approval_raw_sha256=approval_sha256,
                        approval_canonical_sha256=approval_sha256,
                        expected_approval=fixture["expected"],
                        schema=envelope_schema,
                    ),
                    label,
                )

            malformed = fixture["approval_path"].parent / "malformed.json"
            malformed.write_bytes(b'{"duplicate":1,"duplicate":2}\n')
            with self.assertRaises(ValueError):
                load_external_proof_json(malformed.resolve(), "duplicate proof")
            malformed.write_bytes(b'{"nonfinite":NaN}\n')
            with self.assertRaises(ValueError):
                load_external_proof_json(malformed.resolve(), "non-finite proof")
            proof_symlink = fixture["approval_path"].parent / "approval-link.json"
            proof_symlink.symlink_to(fixture["approval_path"])
            with self.assertRaises(ValueError):
                load_external_proof_json(proof_symlink.absolute(), "symlink proof")
            with self.assertRaises(ValueError):
                load_external_proof_json(Path("relative-proof.json"), "relative proof")

            def assert_cli_fail(result: subprocess.CompletedProcess[str], label: str) -> None:
                self.assertNotEqual(result.returncode, 0, label + "\n" + result.stdout + result.stderr)
                self.assertIn("PRECONTENT_READINESS: FAIL", result.stdout, label)
                self.assertIn("AUTHORITATIVE_M3_B002_EFFECTIVE=false", result.stdout, label)
                self.assertIn("effective_active_wip=true", result.stdout, label)
                self.assertIn("global_active_WIP=1", result.stdout, label)

            assert_cli_fail(run_authoritative_cli(fixture, []), "missing proof")
            assert_cli_fail(run_authoritative_cli(fixture, fixture["proof_cli"][:2]), "partial proof")
            wrong_tree_args = list(fixture["proof_cli"])
            wrong_tree_args[wrong_tree_args.index("--expected-repair-tree") + 1] = "0" * 40
            assert_cli_fail(run_authoritative_cli(fixture, wrong_tree_args), "wrong tree")
            unsafe_remote_args = list(fixture["proof_cli"])
            unsafe_remote_args[unsafe_remote_args.index("--expected-remote-url") + 1] = "ext::arbitrary-command"
            assert_cli_fail(run_authoritative_cli(fixture, unsafe_remote_args), "unsafe remote transport")

            fixture["approval_path"].write_text(json.dumps(fixture["approval"], indent=2), encoding="utf-8")
            assert_cli_fail(run_authoritative_cli(fixture), "non-canonical approval transport")
            fixture["approval_path"].write_bytes(fixture["approval_bytes"])

            consumed = copy.deepcopy(fixture["approval"])
            consumed["consumed"] = True
            fixture["approval_path"].write_bytes(canonical_json_bytes(consumed))
            assert_cli_fail(run_authoritative_cli(fixture), "replayed approval")
            fixture["approval_path"].write_bytes(fixture["approval_bytes"])

            bad_envelope = copy.deepcopy(fixture["envelope"])
            bad_envelope["payload"]["approval_consumption"]["consumption_count"] = 2
            bad_envelope["payload_hash"] = canonical_sha256(bad_envelope["payload"])
            fixture["envelope_path"].write_bytes(canonical_json_bytes(bad_envelope))
            assert_cli_fail(run_authoritative_cli(fixture), "invalid consumption")
            fixture["envelope_path"].write_bytes(canonical_json_bytes(fixture["envelope"]))

            dirty_path = fixture["repository"] / "UNTRACKED-AUTHORITATIVE-EFFECT-ATTACK"
            dirty_path.write_text("dirty", encoding="utf-8")
            assert_cli_fail(run_authoritative_cli(fixture), "dirty verifier worktree")
            dirty_path.unlink()

            subprocess.run(
                ["git", "--git-dir", str(fixture["remote"]), "update-ref", "refs/heads/design/r1-story-architecture", BASE_COMMIT],
                check=True,
                capture_output=True,
                text=True,
            )
            assert_cli_fail(run_authoritative_cli(fixture), "remote authoritative ref mismatch")
            subprocess.run(
                ["git", "--git-dir", str(fixture["remote"]), "update-ref", "refs/heads/design/r1-story-architecture", fixture["repair_commit"]],
                check=True,
                capture_output=True,
                text=True,
            )

            tag_name = REPAIR_PROOF_TAG_REF.removeprefix("refs/tags/")
            local_tag_object = run_git(fixture["repository"], "rev-parse", REPAIR_PROOF_TAG_REF)
            subprocess.run(
                ["git", "--git-dir", str(fixture["remote"]), "update-ref", REPAIR_PROOF_TAG_REF, fixture["repair_commit"]],
                check=True,
                capture_output=True,
                text=True,
            )
            assert_cli_fail(run_authoritative_cli(fixture), "remote annotated tag/peel mismatch")
            subprocess.run(
                ["git", "--git-dir", str(fixture["remote"]), "update-ref", REPAIR_PROOF_TAG_REF, local_tag_object],
                check=True,
                capture_output=True,
                text=True,
            )

            wrong_tag_message = fixture["approval_path"].parent / "wrong-tag-message.txt"
            wrong_tag_message.write_text("not the canonical closeout envelope\n", encoding="utf-8")
            run_git(fixture["repository"], "tag", "--delete", tag_name)
            run_git(
                fixture["repository"], "tag", "--annotate", "--cleanup=verbatim",
                "--file", str(wrong_tag_message), tag_name, fixture["repair_commit"],
            )
            assert_cli_fail(run_authoritative_cli(fixture), "wrong annotated tag message")

            run_git(fixture["repository"], "tag", "--delete", tag_name)
            run_git(fixture["repository"], "tag", tag_name, fixture["repair_commit"])
            assert_cli_fail(run_authoritative_cli(fixture), "lightweight proof tag")

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
