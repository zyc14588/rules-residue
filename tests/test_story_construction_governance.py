from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.lib.common import PROJECT_ROOT, read_json, write_json
from tools.story_construction import (
    CANONICAL_MANIFEST_PATH,
    RECEIPT_PATH,
    SOURCE_INTAKE_PATH,
    SUPERSESSION_PATH,
    TRACEABILITY_PATH,
    DECISIONS_PATH,
    derive_installation,
    validate_acceptance_independence,
    validate_candidate_approval,
    validate_canonical_manifest_binding,
    validate_dab,
    validate_m3_route_request,
    validate_pending_receipt_binding,
    validate_region_acceptance,
    validate_region_design_complete,
    validate_runtime_projection,
)
from tools.validate_r2_install import (
    DEFAULT_PACKAGE_ROOT,
    NORMALIZED_INSTALL_CANONICAL,
    _check_installed_bytes,
)
from tools.validate_story_construction_governance import (
    _check_authority_and_supersession,
    _check_decisions_and_traceability,
    _check_m2_preservation,
    _check_package_and_roots,
    _check_source_intake,
    collect_errors,
)


class StoryConstructionGovernanceTests(unittest.TestCase):
    def test_repository_candidate_validates(self) -> None:
        self.assertEqual(collect_errors(PROJECT_ROOT), [])

    def test_q001_q130_missing_duplicate_and_reordered_identity_are_rejected(self) -> None:
        decisions = read_json(PROJECT_ROOT / DECISIONS_PATH)
        trace = read_json(PROJECT_ROOT / TRACEABILITY_PATH)
        mutations = {
            "missing": lambda d, t: (d["decisions"].pop(), t["entries"].pop()),
            "duplicate": lambda d, t: (
                d["decisions"].__setitem__(1, copy.deepcopy(d["decisions"][0])),
                t["entries"].__setitem__(1, copy.deepcopy(t["entries"][0])),
            ),
            "reordered": lambda d, t: (
                d["decisions"].reverse(),
                t["entries"].reverse(),
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bad_decisions = copy.deepcopy(decisions)
                bad_trace = copy.deepcopy(trace)
                mutate(bad_decisions, bad_trace)
                (root / DECISIONS_PATH).parent.mkdir(parents=True)
                write_json(root / DECISIONS_PATH, bad_decisions)
                write_json(root / TRACEABILITY_PATH, bad_trace)
                errors: list[str] = []
                _check_decisions_and_traceability(root, errors)
                self.assertTrue(any("identity/count/order drift" in error or "duplicate identity" in error for error in errors), errors)

    def test_source_circular_manifest_defect_is_detected_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            intake = read_json(PROJECT_ROOT / SOURCE_INTAKE_PATH)
            intake["source_package"]["metadata_declared_manifest_sha256"] = intake[
                "source_package"
            ]["source_manifest_file_sha256"]
            (root / SOURCE_INTAKE_PATH).parent.mkdir(parents=True)
            write_json(root / SOURCE_INTAKE_PATH, intake)
            errors: list[str] = []
            _check_source_intake(root, errors)
            self.assertTrue(any("incorrectly repaired" in error for error in errors), errors)

    def test_supersession_manifest_incomplete_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                Path("governance/story-construction/authority-overlay.yaml"),
                Path("governance/story-construction/canon-registry.yaml"),
                SUPERSESSION_PATH,
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(PROJECT_ROOT / relative, target)
            supersession = read_json(root / SUPERSESSION_PATH)
            supersession["entries"].pop()
            write_json(root / SUPERSESSION_PATH, supersession)
            errors: list[str] = []
            _check_authority_and_supersession(root, errors)
            self.assertTrue(any("predecessor set incomplete" in error for error in errors), errors)

    def test_old_predecessor_and_wrong_m3_route_identity_are_rejected(self) -> None:
        request = read_json(
            PROJECT_ROOT / ".codex/routes/m3-story-construction-plan-request.json"
        )
        wrong = copy.deepcopy(request)
        wrong["route_id"] = "OLD-STORY-ROUTE"
        wrong["documents"].append(
            {
                "path": ".codex/STORY_UPDATE_PROMPT.md",
                "sections": ["WHOLE_FILE"],
            }
        )
        errors = validate_m3_route_request(
            wrong, "M3-STORY-CONSTRUCTION-PLAN", "PLAN"
        )
        self.assertTrue(any("wrong M3 route route_id" in error for error in errors), errors)
        self.assertTrue(any("old predecessor selected" in error for error in errors), errors)

    def test_candidate_approval_hash_mismatch_is_rejected(self) -> None:
        derived = derive_installation(PROJECT_ROOT)
        expected = {
            "change_set_id": "CS-R2-SC-GOV-INSTALL-001",
            "base_commit": "e90a717d3863e4fb0e5e1a0fcc01661f24d2157d",
            "base_tree": "7a1ce74ad0b82c7c288b94c47c966028e916137d",
            "base_canon_hash": derived["base_canon_hash"],
            "candidate_commit": "c" * 40,
            "candidate_tree": "d" * 40,
            "proposed_canon_hash": derived["proposed_canon_hash"],
            "merkle_root": derived["merkle_root"],
            "receipt_payload_hash": derived["receipt_payload_hash"],
        }
        approval = {
            **expected,
            "approval_status": "APPROVED",
            "single_use": True,
            "transferable": False,
            "consumed": False,
            "revoked": False,
        }
        self.assertEqual(validate_candidate_approval(approval, expected), [])
        approval["candidate_tree"] = "e" * 40
        self.assertTrue(
            any(
                "candidate_tree mismatch" in error
                for error in validate_candidate_approval(approval, expected)
            )
        )

    def test_missing_t1_t2_and_c1_approvals_are_rejected(self) -> None:
        dossier = {
            "approvals": {
                "T1": "APPROVED",
                "T2": "APPROVED",
                "T3_ENVELOPE": "APPROVED",
                "C1_REVEAL_FAMILY": "APPROVED",
            },
            "design_complete_gate": {
                key: True
                for key in (
                    "rules_exceptions_frozen",
                    "timeline_verified",
                    "npc_epistemic_verified",
                    "routes_closed",
                    "failure_covered",
                    "retreat_covered",
                    "remediation_covered",
                    "tpk_covered",
                    "reachability_verified",
                    "style_frozen",
                    "visual_anchors_frozen",
                    "no_blocker",
                )
            },
        }
        self.assertEqual(validate_region_design_complete(dossier), [])
        for approval in ("T1", "T2", "C1_REVEAL_FAMILY"):
            with self.subTest(approval=approval):
                invalid = copy.deepcopy(dossier)
                invalid["approvals"][approval] = "PENDING"
                errors = validate_region_design_complete(invalid)
                self.assertTrue(any(approval in error for error in errors), errors)

    def test_worker_self_review_cannot_form_final_pass(self) -> None:
        errors = validate_acceptance_independence(
            {
                "producer_id": "worker-1",
                "verifier_id": "worker-1",
                "worker_self_review": "PASS",
                "result": "PASS",
            }
        )
        self.assertTrue(any("self-review" in error for error in errors), errors)

    def test_governance_order_and_approval_artifacts_are_excluded_from_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            leak = root / "game-package/assets/story-construction-candidate-approval.json"
            leak.parent.mkdir(parents=True)
            leak.write_text("{}\n", encoding="utf-8")
            errors: list[str] = []
            _check_package_and_roots(root, errors)
            self.assertTrue(any("enter runtime package" in error for error in errors), errors)

    def test_unapproved_literary_candidate_runtime_projection_is_rejected(self) -> None:
        errors = validate_runtime_projection(
            {"content_class": "LITERARY_CANDIDATE", "owner_hash_approval": "PENDING"}
        )
        self.assertTrue(any("cannot enter runtime" in error for error in errors), errors)

    def test_canonical_manifest_self_or_receipt_binding_is_rejected(self) -> None:
        manifest = read_json(PROJECT_ROOT / CANONICAL_MANIFEST_PATH)
        self.assertEqual(validate_canonical_manifest_binding(manifest), [])
        for field, value in (
            ("manifest_sha256", "0" * 64),
            ("receipt_ref", "installation-receipt.pending.json"),
        ):
            with self.subTest(field=field):
                invalid = copy.deepcopy(manifest)
                invalid[field] = value
                self.assertTrue(validate_canonical_manifest_binding(invalid))

    def test_receipt_self_reference_is_rejected(self) -> None:
        receipt = read_json(PROJECT_ROOT / RECEIPT_PATH)
        self.assertEqual(validate_pending_receipt_binding(receipt), [])
        receipt["payload"]["payload_hash"] = receipt["payload_hash"]
        errors = validate_pending_receipt_binding(receipt)
        self.assertTrue(any("self-references" in error for error in errors), errors)

    def test_parallel_canon_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "game-package").mkdir()
            (root / "canon").mkdir()
            errors: list[str] = []
            _check_package_and_roots(root, errors)
            self.assertTrue(any("parallel Canon" in error for error in errors), errors)

    def test_m2_preservation_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".codex/state/MILESTONE_PLAN.yaml"
            target.parent.mkdir(parents=True)
            plan = read_json(PROJECT_ROOT / ".codex/state/MILESTONE_PLAN.yaml")
            plan["active_plan"]["lifecycle_projection"]["M2-B002"]["ready"] = "YES"
            write_json(target, plan)
            errors: list[str] = []
            _check_m2_preservation(root, errors)
            self.assertTrue(any("M2-B002" in error for error in errors), errors)

    def test_frozen_r2_prompt_drift_is_rejected_by_installed_byte_gate(self) -> None:
        target_path = ".codex/prompts/r2/R2-AUTHORITY-INSTALL/IMPLEMENT.md"
        source_path, _, _ = NORMALIZED_INSTALL_CANONICAL[target_path]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / target_path
            target.parent.mkdir(parents=True)
            target.write_bytes((PROJECT_ROOT / target_path).read_bytes() + b"\nDRIFT\n")
            errors: list[str] = []
            _check_installed_bytes(
                root,
                DEFAULT_PACKAGE_ROOT,
                [(source_path, "INSTALL_CANONICAL", target_path)],
                errors,
            )
            self.assertTrue(any("normalized byte mismatch" in error for error in errors), errors)

    def test_v0_v6_and_major_defect_gate_region_acceptance(self) -> None:
        bundle = {
            "validation_layers": {f"V{index}": "PASS" for index in range(7)},
            "defects": [],
            "result": "PASS",
        }
        self.assertEqual(validate_region_acceptance(bundle), [])
        bundle["defects"] = [
            {"defect_id": "D-1", "severity": "MAJOR", "status": "OPEN"}
        ]
        errors = validate_region_acceptance(bundle)
        self.assertTrue(any("MAJOR" in error for error in errors), errors)

    def test_forensic_dab_is_required_and_private_cot_is_forbidden(self) -> None:
        bundle = {"tier": "STANDARD", "private_chain_of_thought_recorded": True}
        errors = validate_dab(bundle, "C1")
        self.assertTrue(any("FORENSIC" in error for error in errors), errors)
        self.assertTrue(any("chain-of-thought" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
