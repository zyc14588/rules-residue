from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import validate_r2_install as r2_install
from tools.lib.common import PROJECT_ROOT, read_json, write_json
from tools.lib.schema_subset import validate
from tools.story_construction import (
    ACTIVATION_BINDING_STRATEGY,
    APPROVAL_CONSUMPTION_PATH,
    BASE_CANON_HASH,
    CANONICAL_MANIFEST_PATH,
    CHANGE_SET_PATH,
    FINAL_RECEIPT_PATH,
    IMPLEMENTATION_CANDIDATE_COMMIT,
    IMPLEMENTATION_CANDIDATE_TREE,
    IMPLEMENTATION_OWNER_APPROVAL_ID,
    PACKAGE_SHA256,
    PREVIOUS_GOVERNANCE_MERKLE_ROOT,
    RECEIPT_PATH,
    SOURCE_INTAKE_PATH,
    SUPERSESSION_PATH,
    TRACEABILITY_PATH,
    DECISIONS_PATH,
    authoritative_activation_status,
    canonical_sha256,
    derive_installation,
    validate_activation_closeout_envelope,
    validate_activation_owner_approval,
    validate_acceptance_independence,
    validate_canon_hash_invariants,
    validate_candidate_approval,
    validate_canonical_manifest_binding,
    validate_dab,
    validate_final_receipt_binding,
    validate_implementation_approval_consumption,
    validate_lifecycle_state,
    validate_m3_route_request,
    validate_merkle_transition,
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
    ACTIVATION_CANDIDATE_COMMIT,
    ACTIVATION_CANDIDATE_PARENT,
    ACTIVATION_CANDIDATE_TREE,
    CONTENT_SAFETY_SCHEMA_NAME,
    PUBLIC_CONTENT_SAFETY_ARTIFACTS,
    SCHEMA_FILES,
    SCHEMA_ROOT,
    _check_public_content_safety_attachment,
    _check_schemas,
    _check_activation_git_scope,
    _check_authority_and_supersession,
    _check_decisions_and_traceability,
    _check_m2_preservation,
    _check_package_and_roots,
    _check_source_intake,
    collect_errors,
    validate_activation_candidate_structure,
    validate_activation_changed_paths,
)


class StoryConstructionGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.change_set = read_json(PROJECT_ROOT / CHANGE_SET_PATH)
        cls.current_manifest = read_json(PROJECT_ROOT / CANONICAL_MANIFEST_PATH)
        cls.final_receipt = read_json(PROJECT_ROOT / FINAL_RECEIPT_PATH)
        cls.consumption = read_json(PROJECT_ROOT / APPROVAL_CONSUMPTION_PATH)
        cls.previous_manifest = json.loads(
            subprocess.check_output(
                [
                    "git",
                    "show",
                    f"{IMPLEMENTATION_CANDIDATE_COMMIT}:{CANONICAL_MANIFEST_PATH.as_posix()}",
                ],
                cwd=PROJECT_ROOT,
                text=True,
            )
        )

    def _make_activation_checkout(self, temporary_root: Path) -> Path:
        root = temporary_root / "checkout"
        subprocess.run(
            ["git", "clone", "-q", "--shared", str(PROJECT_ROOT), str(root)],
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "-q", "--detach", ACTIVATION_CANDIDATE_COMMIT],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Story Governance Tests"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "story-governance@example.invalid"],
            cwd=root,
            check=True,
        )
        return root

    def _commit_activation_descendant(
        self,
        root: Path,
        relative: str,
        content: str,
    ) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "--", relative], cwd=root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-q",
                "-m",
                f"descendant {relative}",
            ],
            cwd=root,
            check=True,
        )

    def _activation_approval(self) -> tuple[dict[str, object], dict[str, object]]:
        expected: dict[str, object] = {
            "approval_id": "OWNER-APPROVAL-R2-SC-GOV-ACTIVATION-TEST-001",
            "change_set_id": "CS-R2-SC-GOV-INSTALL-001",
            "base_commit": "e90a717d3863e4fb0e5e1a0fcc01661f24d2157d",
            "base_tree": "7a1ce74ad0b82c7c288b94c47c966028e916137d",
            "base_canon_hash": BASE_CANON_HASH,
            "implementation_candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
            "implementation_candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
            "implementation_owner_approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
            "implementation_accept_task_id": "R2-SC-GOV-INSTALL-001-ACCEPT-001",
            "implementation_accept_result": "PASS_FIXED_CANDIDATE_ACCEPTED",
            "implementation_accept_route_digest": "706cd9195ef483ddc47a76774780059d46b24b813e948ab28b532a613e9f1cd6",
            "activation_closeout_task_id": "R2-SC-GOV-INSTALL-ACTIVATION-CLOSEOUT-IMPLEMENT-001",
            "activation_candidate_commit": "c" * 40,
            "activation_candidate_tree": "d" * 40,
            "activation_candidate_parent": IMPLEMENTATION_CANDIDATE_COMMIT,
            "proposed_canon_hash": BASE_CANON_HASH,
            "canonical_decisions_hash": "01fdebbd338a8abdbc0226d0290b1bc2b02366cb615a22182f0df0a5f75fa7b2",
            "canonical_manifest_hash": hashlib.sha256(
                (PROJECT_ROOT / CANONICAL_MANIFEST_PATH).read_bytes()
            ).hexdigest(),
            "previous_governance_merkle_root": PREVIOUS_GOVERNANCE_MERKLE_ROOT,
            "new_activation_merkle_root": self.change_set["merkle_root"],
            "changed_merkle_leaves": [
                "SCG-AUTHORITY-OVERLAY",
                "SCG-CANON-REGISTRY",
                "SCG-SUPERSESSION",
            ],
            "final_inner_receipt_path": FINAL_RECEIPT_PATH.as_posix(),
            "final_inner_receipt_file_sha256": hashlib.sha256(
                (PROJECT_ROOT / FINAL_RECEIPT_PATH).read_bytes()
            ).hexdigest(),
            "final_inner_receipt_payload_hash": self.final_receipt["payload_hash"],
            "source_package_id": "RR-SC-GOV-V2-Q001-Q130",
            "source_zip_sha256": "158e6e82e50ae4a411b780e718f16353dd668b6f94320c685a95d20d766d0e36",
            "source_manifest_file_sha256": "721ef281e1a25cbd85d4979264498e207582e1d8f43e01845ca7b8e9bbd1bc88",
            "source_integrity_defect": "CIRCULAR_MANIFEST_METADATA_BINDING",
            "package_sha256": PACKAGE_SHA256,
        }
        approval = {
            "schema_version": "1.0.0",
            **expected,
            "approval_model": "FULL_ACTIVATION_HASH_SET_REAPPROVAL_REQUIRED",
            "approval_status": "APPROVED",
            "single_use": True,
            "transferable": False,
            "consumed": False,
            "revoked": False,
            "owner_id": "owner-test",
            "approved_at": "2026-08-31T00:00:00Z",
        }
        return approval, expected

    def _activation_envelope(
        self, approval: dict[str, object]
    ) -> tuple[dict[str, object], dict[str, object]]:
        payload: dict[str, object] = {
            "envelope_id": "RR-SC-GOV-ACTIVATION-ENVELOPE-TEST-001",
            "change_set_id": "CS-R2-SC-GOV-INSTALL-001",
            "binding_strategy": ACTIVATION_BINDING_STRATEGY,
            "activation_candidate_commit": "c" * 40,
            "activation_candidate_tree": "d" * 40,
            "activation_candidate_parent": IMPLEMENTATION_CANDIDATE_COMMIT,
            "tag_name": "story-governance-activation-test",
            "tag_target_commit": "c" * 40,
            "tag_target_tree": "d" * 40,
            "final_inner_receipt_path": FINAL_RECEIPT_PATH.as_posix(),
            "final_inner_receipt_file_sha256": hashlib.sha256(
                (PROJECT_ROOT / FINAL_RECEIPT_PATH).read_bytes()
            ).hexdigest(),
            "final_inner_receipt_payload_hash": self.final_receipt["payload_hash"],
            "activation_owner_approval_id": approval["approval_id"],
            "activation_owner_approval_sha256": canonical_sha256(approval),
            "activation_accept_task_id": "R2-SC-GOV-INSTALL-ACTIVATION-CLOSEOUT-ACCEPT-001",
            "activation_accept_result": "PASS_FIXED_ACTIVATION_CANDIDATE_ACCEPTED",
            "activation_accept_route_digest": "a" * 64,
            "accepted_candidate_commit": "c" * 40,
            "accepted_candidate_tree": "d" * 40,
            "producer_id": "builder-test",
            "verifier_id": "verifier-test",
            "verifier_worktree_state": "CLEAN",
            "lineage_commit_count": 1,
            "integration_mode": "FAST_FORWARD_ONLY",
        }
        envelope = {
            "schema_version": "1.0.0",
            "envelope_kind": "DETACHED_ACCEPTED_ACTIVATION_ENVELOPE",
            "payload": payload,
            "payload_hash": canonical_sha256(payload),
        }
        return envelope, copy.deepcopy(payload)

    def _authority_mutation_errors(self, mutate) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (
                Path("governance/story-construction/authority-overlay.yaml"),
                Path("governance/story-construction/canon-registry.yaml"),
                SUPERSESSION_PATH,
            )
            values = []
            for relative in paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                value = read_json(PROJECT_ROOT / relative)
                values.append(value)
                write_json(target, value)
            mutate(*values)
            for relative, value in zip(paths, values):
                write_json(root / relative, value)
            errors: list[str] = []
            _check_authority_and_supersession(root, errors)
            return errors

    def test_repository_candidate_validates(self) -> None:
        self.assertEqual(collect_errors(PROJECT_ROOT), [])

    def test_exact_fixed_activation_candidate_passes_git_scope(self) -> None:
        errors: list[str] = []
        _check_activation_git_scope(PROJECT_ROOT, errors)
        self.assertEqual(errors, [])

    def test_one_unrelated_activation_descendant_passes_lineage_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._make_activation_checkout(Path(temporary))
            self._commit_activation_descendant(
                root,
                "docs/unrelated-post-activation.md",
                "unrelated descendant\n",
            )
            errors: list[str] = []
            _check_activation_git_scope(root, errors)
            self.assertEqual(errors, [])

    def test_multiple_unrelated_activation_descendants_pass_lineage_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._make_activation_checkout(Path(temporary))
            self._commit_activation_descendant(
                root,
                "docs/unrelated-post-activation-1.md",
                "first descendant\n",
            )
            self._commit_activation_descendant(
                root,
                "tests/unrelated_post_activation_2.txt",
                "second descendant\n",
            )
            errors: list[str] = []
            _check_activation_git_scope(root, errors)
            self.assertEqual(errors, [])

    def test_activation_descendant_does_not_make_authority_effective(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._make_activation_checkout(Path(temporary))
            self._commit_activation_descendant(
                root,
                "docs/unrelated-post-activation.md",
                "unrelated descendant\n",
            )
            scope_errors: list[str] = []
            _check_activation_git_scope(root, scope_errors)
            self.assertEqual(scope_errors, [])
            _, expected_approval = self._activation_approval()
            approval, _ = self._activation_approval()
            _, expected_envelope = self._activation_envelope(approval)
            effective, proof_errors = authoritative_activation_status(
                tracked_target_state_active=True,
                activation_approval=None,
                expected_activation_approval=expected_approval,
                envelope=None,
                expected_envelope=expected_envelope,
                integration=None,
            )
            self.assertFalse(effective)
            self.assertTrue(proof_errors)

    def test_fixed_activation_wrong_parent_fails(self) -> None:
        errors = validate_activation_candidate_structure(
            tree=ACTIVATION_CANDIDATE_TREE,
            parent="0" * 40,
            commit_count=1,
            changed_paths=set(),
        )
        self.assertTrue(any("parent identity mismatch" in error for error in errors))

    def test_fixed_activation_wrong_tree_fails(self) -> None:
        errors = validate_activation_candidate_structure(
            tree="0" * 40,
            parent=ACTIVATION_CANDIDATE_PARENT,
            commit_count=1,
            changed_paths=set(),
        )
        self.assertTrue(any("tree identity mismatch" in error for error in errors))

    def test_fixed_activation_wrong_commit_count_fails(self) -> None:
        errors = validate_activation_candidate_structure(
            tree=ACTIVATION_CANDIDATE_TREE,
            parent=ACTIVATION_CANDIDATE_PARENT,
            commit_count=2,
            changed_paths=set(),
        )
        self.assertTrue(any("not exactly one commit" in error for error in errors))

    def test_fixed_activation_unapproved_changed_path_fails(self) -> None:
        errors = validate_activation_candidate_structure(
            tree=ACTIVATION_CANDIDATE_TREE,
            parent=ACTIVATION_CANDIDATE_PARENT,
            commit_count=1,
            changed_paths={"outside-activation-scope.txt"},
        )
        self.assertTrue(any("exceed approved scope" in error for error in errors))

    def test_non_descendant_activation_head_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._make_activation_checkout(Path(temporary))
            subprocess.run(
                ["git", "checkout", "-q", "--detach", ACTIVATION_CANDIDATE_PARENT],
                cwd=root,
                check=True,
            )
            errors: list[str] = []
            _check_activation_git_scope(root, errors)
            self.assertTrue(
                any("not the fixed activation candidate or its descendant" in error for error in errors),
                errors,
            )

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

    def test_candidate_and_active_schema_versions_validate(self) -> None:
        fixture = read_json(
            PROJECT_ROOT / "tests/fixtures/story-construction/lifecycle-state-v1.json"
        )
        candidate = fixture["candidate_change_set"]
        candidate_schema = read_json(
            PROJECT_ROOT / "schemas/story-construction/change-set-v1.schema.json"
        )
        active_schema = read_json(
            PROJECT_ROOT / "schemas/story-construction/change-set-v2.schema.json"
        )
        active_fixture = read_json(
            PROJECT_ROOT / fixture["active_change_set_fixture_path"]
        )
        self.assertEqual(validate(candidate, candidate_schema), [])
        self.assertEqual(validate_lifecycle_state(candidate), [])
        self.assertEqual(validate(active_fixture, active_schema), [])
        self.assertEqual(validate_lifecycle_state(active_fixture), [])

    def test_mixed_candidate_active_and_released_states_are_rejected(self) -> None:
        fixture = read_json(
            PROJECT_ROOT / "tests/fixtures/story-construction/lifecycle-state-v1.json"
        )
        active_schema = read_json(
            PROJECT_ROOT / "schemas/story-construction/change-set-v2.schema.json"
        )
        labels = (
            "approved-with-candidate-disposition",
            "candidate-with-active-disposition",
            "released-impersonates-active",
        )
        for label, state in zip(labels, fixture["invalid_mixed_states"]):
            with self.subTest(label=label):
                self.assertTrue(validate_lifecycle_state(state))
                self.assertTrue(validate(state, active_schema))

    def test_active_state_rejects_pending_only_receipt(self) -> None:
        self.assertEqual(validate_lifecycle_state(self.change_set), [])
        pending = read_json(PROJECT_ROOT / RECEIPT_PATH)
        errors = validate_final_receipt_binding(
            pending,
            expected_new_merkle_root=self.change_set["merkle_root"],
            expected_consumption_sha256=self.change_set[
                "approval_consumption_record_sha256"
            ],
        )
        self.assertTrue(errors)

    def test_implementation_approval_consumption_record_validates(self) -> None:
        schema = read_json(
            PROJECT_ROOT
            / "schemas/story-construction/owner-approval-consumption-v1.schema.json"
        )
        self.assertEqual(validate(self.consumption, schema), [])
        self.assertEqual(
            validate_implementation_approval_consumption(self.consumption), []
        )

    def test_implementation_approval_hash_replay_revocation_and_transfer_are_rejected(
        self,
    ) -> None:
        mutations = {
            "transport-hash": ("owner_approval_transport_sha256", "0" * 64),
            "replay": ("consumption_count", 2),
            "revoked": ("revoked", True),
            "transferable": ("transferable", True),
            "not-consumed": ("consumed", False),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label):
                record = copy.deepcopy(self.consumption)
                record[field] = value
                self.assertTrue(validate_implementation_approval_consumption(record))

    def test_wrong_implementation_accept_binding_is_rejected(self) -> None:
        mutations = {
            "task": ("consumption_event", "WRONG-ACCEPT-TASK"),
            "result": ("consumption_result", "FAIL"),
            "candidate-commit": ("accepted_candidate_commit", "0" * 40),
            "candidate-tree": ("accepted_candidate_tree", "0" * 40),
            "route": ("accept_route_digest", "0" * 64),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label):
                record = copy.deepcopy(self.consumption)
                record[field] = value
                self.assertTrue(validate_implementation_approval_consumption(record))

    def test_activation_owner_approval_schema_and_binding_validate(self) -> None:
        approval, expected = self._activation_approval()
        schema = read_json(
            PROJECT_ROOT
            / "schemas/story-construction/activation-owner-approval-v1.schema.json"
        )
        self.assertEqual(validate(approval, schema), [])
        self.assertEqual(validate_activation_owner_approval(approval, expected), [])
        pending = copy.deepcopy(approval)
        pending["approval_status"] = "PENDING_OWNER_ACTIVATION_HASH_APPROVAL"
        pending["owner_id"] = None
        pending["approved_at"] = None
        self.assertEqual(validate(pending, schema), [])
        self.assertTrue(validate_activation_owner_approval(pending, expected))

    def test_implementation_approval_id_cannot_be_activation_approval(self) -> None:
        approval, expected = self._activation_approval()
        approval["approval_id"] = IMPLEMENTATION_OWNER_APPROVAL_ID
        expected["approval_id"] = IMPLEMENTATION_OWNER_APPROVAL_ID
        errors = validate_activation_owner_approval(approval, expected)
        self.assertTrue(any("cannot serve" in error for error in errors), errors)

    def test_activation_owner_approval_wrong_hash_set_is_rejected(self) -> None:
        mutations = {
            "candidate-commit": ("activation_candidate_commit", "0" * 40),
            "candidate-tree": ("activation_candidate_tree", "0" * 40),
            "merkle": ("new_activation_merkle_root", "0" * 64),
            "receipt": ("final_inner_receipt_payload_hash", "0" * 64),
            "package": ("package_sha256", "0" * 64),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label):
                approval, expected = self._activation_approval()
                approval[field] = value
                self.assertTrue(validate_activation_owner_approval(approval, expected))

    def test_final_inner_receipt_schema_and_binding_validate(self) -> None:
        schema = read_json(
            PROJECT_ROOT
            / "schemas/story-construction/installation-receipt-v2.schema.json"
        )
        self.assertEqual(validate(self.final_receipt, schema), [])
        self.assertEqual(
            validate_final_receipt_binding(
                self.final_receipt,
                expected_new_merkle_root=self.change_set["merkle_root"],
                expected_consumption_sha256=self.change_set[
                    "approval_consumption_record_sha256"
                ],
            ),
            [],
        )

    def test_final_inner_receipt_self_and_external_bindings_are_rejected(self) -> None:
        mutations = {
            "self-reference": ("payload_hash", "0" * 64),
            "activation-candidate": ("activation_candidate_commit", "0" * 40),
            "second-accept": (
                "activation_accept_result",
                "PASS_FIXED_ACTIVATION_CANDIDATE_ACCEPTED",
            ),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label):
                receipt = copy.deepcopy(self.final_receipt)
                receipt["payload"][field] = value
                receipt["payload_hash"] = canonical_sha256(receipt["payload"])
                errors = validate_final_receipt_binding(
                    receipt,
                    expected_new_merkle_root=self.change_set["merkle_root"],
                    expected_consumption_sha256=self.change_set[
                        "approval_consumption_record_sha256"
                    ],
                )
                self.assertTrue(
                    any("forbidden self/external binding" in error for error in errors),
                    errors,
                )

    def test_activation_closeout_envelope_schema_and_binding_validate(self) -> None:
        approval, _ = self._activation_approval()
        envelope, expected = self._activation_envelope(approval)
        schema = read_json(
            PROJECT_ROOT
            / "schemas/story-construction/activation-closeout-envelope-v1.schema.json"
        )
        self.assertEqual(validate(envelope, schema), [])
        self.assertEqual(validate_activation_closeout_envelope(envelope, expected), [])

    def test_activation_envelope_wrong_tag_receipt_approval_and_accept_are_rejected(
        self,
    ) -> None:
        mutations = {
            "tag-target": ("tag_target_commit", "0" * 40),
            "receipt-hash": ("final_inner_receipt_file_sha256", "0" * 64),
            "approval-hash": ("activation_owner_approval_sha256", "0" * 64),
            "accept-result": ("activation_accept_result", "FAIL"),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label):
                approval, _ = self._activation_approval()
                envelope, expected = self._activation_envelope(approval)
                envelope["payload"][field] = value
                envelope["payload_hash"] = canonical_sha256(envelope["payload"])
                self.assertTrue(
                    validate_activation_closeout_envelope(envelope, expected)
                )

    def test_activation_envelope_rejects_self_accept_dirty_verifier_and_bad_lineage(
        self,
    ) -> None:
        mutations = {
            "builder-self-accept": ("verifier_id", "builder-test"),
            "dirty-verifier": ("verifier_worktree_state", "DIRTY"),
            "wrong-parent": ("activation_candidate_parent", "0" * 40),
            "multi-commit": ("lineage_commit_count", 2),
            "non-ff": ("integration_mode", "REBASE"),
        }
        for label, (field, value) in mutations.items():
            with self.subTest(label=label):
                approval, _ = self._activation_approval()
                envelope, expected = self._activation_envelope(approval)
                envelope["payload"][field] = value
                envelope["payload_hash"] = canonical_sha256(envelope["payload"])
                self.assertTrue(
                    validate_activation_closeout_envelope(envelope, expected)
                )

    def test_authoritative_activation_requires_every_external_proof(self) -> None:
        approval, expected_approval = self._activation_approval()
        envelope, expected_envelope = self._activation_envelope(approval)
        integration = {
            "integrated": True,
            "mode": "FAST_FORWARD_ONLY",
            "commit": expected_envelope["activation_candidate_commit"],
            "tree": expected_envelope["activation_candidate_tree"],
        }
        effective, errors = authoritative_activation_status(
            tracked_target_state_active=True,
            activation_approval=approval,
            expected_activation_approval=expected_approval,
            envelope=envelope,
            expected_envelope=expected_envelope,
            integration=integration,
        )
        self.assertTrue(effective, errors)
        effective, errors = authoritative_activation_status(
            tracked_target_state_active=True,
            activation_approval=None,
            expected_activation_approval=expected_approval,
            envelope=None,
            expected_envelope=expected_envelope,
            integration=None,
        )
        self.assertFalse(effective)
        self.assertGreaterEqual(len(errors), 3)

    def test_exact_three_leaf_merkle_transition_validates(self) -> None:
        self.assertEqual(
            validate_merkle_transition(
                self.previous_manifest,
                self.current_manifest,
                self.change_set["merkle_transition"],
            ),
            [],
        )

    def test_approval_receipt_or_accept_cannot_enter_merkle(self) -> None:
        for record_id in (
            "IMPLEMENTATION_APPROVAL_CONSUMPTION",
            "FINAL_INNER_RECEIPT",
            "ACTIVATION_ACCEPT",
        ):
            with self.subTest(record_id=record_id):
                current = copy.deepcopy(self.current_manifest)
                current["records"].append(
                    {
                        "record_id": record_id,
                        "record_type": record_id,
                        "source_path": f"governance/story-construction/{record_id.lower()}.json",
                        "canonical_sha256": "0" * 64,
                    }
                )
                errors = validate_merkle_transition(
                    self.previous_manifest,
                    current,
                    self.change_set["merkle_transition"],
                )
                self.assertTrue(any("entered governance Merkle" in e for e in errors), errors)

    def test_fourth_semantic_merkle_leaf_change_is_rejected(self) -> None:
        current = copy.deepcopy(self.current_manifest)
        next(
            item for item in current["records"] if item["record_id"] == "Q130"
        )["canonical_sha256"] = "0" * 64
        errors = validate_merkle_transition(
            self.previous_manifest,
            current,
            self.change_set["merkle_transition"],
        )
        self.assertTrue(any("semantic leaf transition" in e for e in errors), errors)

    def test_merkle_leaf_count_drift_is_rejected(self) -> None:
        current = copy.deepcopy(self.current_manifest)
        current["records"].pop()
        errors = validate_merkle_transition(
            self.previous_manifest,
            current,
            self.change_set["merkle_transition"],
        )
        self.assertTrue(any("exactly 135" in e for e in errors), errors)

    def test_q_source_intake_and_traceability_leaf_drift_are_rejected(self) -> None:
        for record_id in ("Q001", "SCG-SOURCE-INTAKE", "SCG-TRACEABILITY"):
            with self.subTest(record_id=record_id):
                current = copy.deepcopy(self.current_manifest)
                next(
                    item
                    for item in current["records"]
                    if item["record_id"] == record_id
                )["canonical_sha256"] = "0" * 64
                errors = validate_merkle_transition(
                    self.previous_manifest,
                    current,
                    self.change_set["merkle_transition"],
                )
                self.assertTrue(any("semantic leaf transition" in e for e in errors), errors)

    def test_active_overlay_cannot_remain_pending(self) -> None:
        errors = self._authority_mutation_errors(
            lambda overlay, _registry, _supersession: overlay.__setitem__(
                "story_construction_governance_status",
                "CANDIDATE_PENDING_OWNER_HASH_APPROVAL",
            )
        )
        self.assertTrue(any("still represents pending" in e for e in errors), errors)

    def test_active_registry_cannot_remain_candidate(self) -> None:
        errors = self._authority_mutation_errors(
            lambda _overlay, registry, _supersession: registry.__setitem__(
                "framework_status", "CANDIDATE"
            )
        )
        self.assertTrue(any("candidate framework" in e for e in errors), errors)

    def test_supersession_effective_binding_cannot_be_null_or_wrong(self) -> None:
        for field, value in (
            ("effective_candidate_commit", None),
            ("effective_candidate_tree", "0" * 40),
            ("effective_state", "CANDIDATE"),
        ):
            with self.subTest(field=field):
                errors = self._authority_mutation_errors(
                    lambda _overlay, _registry, supersession, f=field, v=value: supersession.__setitem__(
                        f, v
                    )
                )
                self.assertTrue(any("active binding drift" in e for e in errors), errors)

    def test_q_owner_answer_and_frozen_status_drift_are_rejected(self) -> None:
        for label, mutate in (
            (
                "owner-answer",
                lambda decisions: decisions["decisions"][0]["owner_answer"].__setitem__(
                    "statement", "DRIFT"
                ),
            ),
            (
                "frozen-status",
                lambda decisions: decisions["decisions"][0].__setitem__(
                    "decision_status", "DRAFT"
                ),
            ),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                decisions = read_json(PROJECT_ROOT / DECISIONS_PATH)
                trace = read_json(PROJECT_ROOT / TRACEABILITY_PATH)
                mutate(decisions)
                (root / DECISIONS_PATH).parent.mkdir(parents=True)
                write_json(root / DECISIONS_PATH, decisions)
                write_json(root / TRACEABILITY_PATH, trace)
                errors: list[str] = []
                _check_decisions_and_traceability(root, errors)
                self.assertTrue(errors)

    def test_canonical_decisions_and_canon_hash_drift_are_rejected(self) -> None:
        for label, kwargs in (
            (
                "canonical-decisions",
                {
                    "base_canon_hash": BASE_CANON_HASH,
                    "proposed_canon_hash": BASE_CANON_HASH,
                    "canonical_decisions_hash": "0" * 64,
                },
            ),
            (
                "base-canon",
                {
                    "base_canon_hash": "0" * 64,
                    "proposed_canon_hash": BASE_CANON_HASH,
                    "canonical_decisions_hash": "01fdebbd338a8abdbc0226d0290b1bc2b02366cb615a22182f0df0a5f75fa7b2",
                },
            ),
            (
                "proposed-canon",
                {
                    "base_canon_hash": BASE_CANON_HASH,
                    "proposed_canon_hash": "0" * 64,
                    "canonical_decisions_hash": "01fdebbd338a8abdbc0226d0290b1bc2b02366cb615a22182f0df0a5f75fa7b2",
                },
            ),
        ):
            with self.subTest(label=label):
                self.assertTrue(validate_canon_hash_invariants(**kwargs))

    def test_r2_authoring_runtime_and_platform_scope_drift_are_rejected(self) -> None:
        for path in (
            "governance/r2/decisions.r2.yaml",
            "authoring/world/truth.json",
            "game-package/scripts/story.lua",
            "TRPG_PLATFORM/src/story.rs",
        ):
            with self.subTest(path=path):
                errors = validate_activation_changed_paths({path})
                self.assertTrue(errors)

    def test_old_story_execution_authority_cannot_be_restored(self) -> None:
        def restore(_overlay, _registry, supersession) -> None:
            entry = next(
                item
                for item in supersession["entries"]
                if item["predecessor_path"] == ".codex/STORY_UPDATE_PROMPT.md"
            )
            entry["removed_scope"].remove("ORACLE_AUTHORITY")

        errors = self._authority_mutation_errors(restore)
        self.assertTrue(any("old Story Update" in e for e in errors), errors)

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


class PublicContentSafetyAttachmentTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="scg-public-attachment-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.r2_artifacts = {
            **r2_install.UNREGISTERED_INTERFACE_ARTIFACTS,
            **r2_install.INTERFACE_COMPATIBILITY_ARTIFACTS,
            **r2_install.PUBLIC_BASELINE_CONTROL_ARTIFACTS,
        }
        paths = (
            set(PUBLIC_CONTENT_SAFETY_ARTIFACTS)
            | set(self.r2_artifacts)
            | set(r2_install.R2_AUTHORITY_SCHEMA_PATHS)
            | {(SCHEMA_ROOT / name).as_posix() for name in SCHEMA_FILES}
        )
        for relative in sorted(paths):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT_ROOT / relative, target)

    def _schema_errors(self) -> list[str]:
        errors: list[str] = []
        schemas = _check_schemas(self.root, errors)
        self.assertEqual(set(schemas), SCHEMA_FILES)
        self.assertNotIn(CONTENT_SAFETY_SCHEMA_NAME, schemas)
        return errors

    def _assert_attachment_rejected(self) -> list[str]:
        errors: list[str] = []
        self.assertIsNone(_check_public_content_safety_attachment(self.root, errors))
        self.assertTrue(errors)
        return errors

    def test_exact_public_attachment_preserves_49_scg_and_10_r2_schemas(self) -> None:
        self.assertEqual(len(SCHEMA_FILES), 49)
        self.assertEqual(len(r2_install.R2_AUTHORITY_SCHEMA_PATHS), 10)
        self.assertEqual(len(PUBLIC_CONTENT_SAFETY_ARTIFACTS), 13)
        errors: list[str] = []
        self.assertEqual(
            _check_public_content_safety_attachment(self.root, errors),
            self.root / SCHEMA_ROOT / CONTENT_SAFETY_SCHEMA_NAME,
        )
        self.assertEqual(errors, [])
        self.assertEqual(self._schema_errors(), [])
        r2_install._check_schemas_and_json(self.root, errors)
        self.assertEqual(errors, [])

    def test_absent_attachment_preserves_legacy_schema_checks(self) -> None:
        for relative in PUBLIC_CONTENT_SAFETY_ARTIFACTS:
            (self.root / relative).unlink()
        errors: list[str] = []
        self.assertIsNone(_check_public_content_safety_attachment(self.root, errors))
        self.assertEqual(errors, [])
        self.assertEqual(self._schema_errors(), [])

    def test_receipt_alone_is_not_an_attachment(self) -> None:
        for relative in PUBLIC_CONTENT_SAFETY_ARTIFACTS:
            if Path(relative).name != CONTENT_SAFETY_SCHEMA_NAME:
                (self.root / relative).unlink()
        self._assert_attachment_rejected()
        self.assertTrue(any("schema set mismatch" in error for error in self._schema_errors()))

    def test_every_missing_public_artifact_is_rejected(self) -> None:
        for relative in PUBLIC_CONTENT_SAFETY_ARTIFACTS:
            with self.subTest(relative=relative):
                path = self.root / relative
                data = path.read_bytes()
                path.unlink()
                errors = self._assert_attachment_rejected()
                self.assertTrue(any(relative in error for error in errors), errors)
                self.assertTrue(self._schema_errors())
                path.write_bytes(data)

    def test_every_public_artifact_byte_drift_is_rejected(self) -> None:
        for relative in PUBLIC_CONTENT_SAFETY_ARTIFACTS:
            with self.subTest(relative=relative):
                path = self.root / relative
                data = path.read_bytes()
                path.write_bytes(data + b"\n")
                errors = self._assert_attachment_rejected()
                self.assertTrue(any("byte drift" in error and relative in error for error in errors), errors)
                path.write_bytes(data)

    def test_every_r2_interface_evidence_and_control_drift_is_rejected(self) -> None:
        for relative in self.r2_artifacts:
            with self.subTest(relative=relative):
                path = self.root / relative
                data = path.read_bytes()
                path.write_bytes(data + b"\n")
                errors = self._assert_attachment_rejected()
                self.assertTrue(any(relative in error for error in errors), errors)
                self.assertTrue(any("schema set mismatch" in error for error in self._schema_errors()))
                path.write_bytes(data)

    def test_missing_r2_attachment_cannot_classify_receipt(self) -> None:
        for relative in r2_install.UNREGISTERED_INTERFACE_ARTIFACTS:
            (self.root / relative).unlink()
        errors = self._assert_attachment_rejected()
        self.assertTrue(any("R2 compatibility attachment unavailable" in error for error in errors), errors)
        self.assertTrue(any("schema set mismatch" in error for error in self._schema_errors()))

    def test_executable_modes_are_rejected_for_public_and_r2_artifacts(self) -> None:
        for relative in set(PUBLIC_CONTENT_SAFETY_ARTIFACTS) | set(self.r2_artifacts):
            with self.subTest(relative=relative):
                path = self.root / relative
                path.chmod(0o755)
                errors = self._assert_attachment_rejected()
                self.assertTrue(any("Git mode 100644" in error and relative in error for error in errors), errors)
                path.chmod(0o644)

    def test_nonregular_artifact_is_rejected(self) -> None:
        path = self.root / "tools/content_safety_control.py"
        path.unlink()
        path.mkdir()
        self._assert_attachment_rejected()

    def test_leaf_symlinks_are_rejected(self) -> None:
        for relative in (f"{SCHEMA_ROOT}/{CONTENT_SAFETY_SCHEMA_NAME}",
                         "tools/content_safety_control.py",
                         next(iter(r2_install.INTERFACE_COMPATIBILITY_ARTIFACTS))):
            with self.subTest(relative=relative):
                path = self.root / relative
                saved = path.with_suffix(path.suffix + ".saved")
                path.rename(saved)
                path.symlink_to(saved)
                errors = self._assert_attachment_rejected()
                self.assertTrue(any("symlink" in error and relative in error for error in errors), errors)
                path.unlink()
                saved.rename(path)

    def test_parent_symlink_is_rejected_even_with_identical_bytes(self) -> None:
        path = self.root / "tools"
        saved = self.root / "saved-tools"
        path.rename(saved)
        path.symlink_to(saved, target_is_directory=True)
        errors = self._assert_attachment_rejected()
        self.assertTrue(any("symlink artifact path" in error for error in errors), errors)

    def test_unknown_schema_attachment_still_fails_exact_set(self) -> None:
        for name in ("content-safety-receipt-v2.schema.json", "unknown.schema.json"):
            with self.subTest(name=name):
                path = self.root / SCHEMA_ROOT / name
                shutil.copy2(self.root / SCHEMA_ROOT / CONTENT_SAFETY_SCHEMA_NAME, path)
                errors = self._schema_errors()
                self.assertTrue(any("schema set mismatch" in error and name in error for error in errors), errors)
                path.unlink()

    def test_missing_original_schema_and_frozen_byte_drift_still_fail(self) -> None:
        path = self.root / SCHEMA_ROOT / "activation-owner-approval-v1.schema.json"
        path.unlink()
        errors: list[str] = []
        schemas = _check_schemas(self.root, errors)
        self.assertEqual(len(schemas), 48)
        self.assertTrue(any("schema set mismatch" in error and path.name in error for error in errors), errors)
        shutil.copy2(PROJECT_ROOT / SCHEMA_ROOT / path.name, path)
        frozen = self.root / SCHEMA_ROOT / "change-set-v1.schema.json"
        frozen.write_bytes(frozen.read_bytes() + b"\n")
        self.assertTrue(any("frozen v1 schema bytes changed" in error for error in self._schema_errors()))

    def test_original_metadata_checks_still_fail(self) -> None:
        path = self.root / SCHEMA_ROOT / "activation-owner-approval-v1.schema.json"
        schema = read_json(path)
        schema["$schema"] = "https://invalid.example/schema"
        schema["additionalProperties"] = True
        schema["properties"]["schema_version"]["const"] = "invalid"
        write_json(path, schema)
        errors = self._schema_errors()
        for marker in ("must declare draft 2020-12", "root unknown fields must be rejected", "explicit SemVer"):
            self.assertTrue(any(marker in error and path.name in error for error in errors), errors)

    def test_invalid_receipt_metadata_is_checked_after_hash_rejection(self) -> None:
        path = self.root / SCHEMA_ROOT / CONTENT_SAFETY_SCHEMA_NAME
        original = read_json(path)
        mutations = {
            "draft": ("$schema", "https://invalid.example/schema", "must declare draft"),
            "identity": ("$id", "", "exact receipt schema $id"),
            "unknown-fields": ("additionalProperties", True, "root unknown fields"),
            "draft-metadata": ("required", "invalid", "invalid Draft 2020-12 schema"),
            "missing-local-ref": ("$ref", "#/$defs/missing", "unresolved local $ref"),
            "external-ref": ("$ref", "https://invalid.example/schema", "must resolve locally"),
        }
        for label, (field, value, marker) in mutations.items():
            with self.subTest(label=label):
                schema = copy.deepcopy(original)
                schema[field] = value
                write_json(path, schema)
                errors = self._schema_errors()
                self.assertTrue(any("artifact byte drift" in error for error in errors), errors)
                self.assertTrue(any("SCG_SCHEMA_ATTACHMENT_META" in error and marker in error for error in errors), errors)
        schema = copy.deepcopy(original)
        schema["properties"]["schema_version"]["const"] = "2.0.0"
        write_json(path, schema)
        self.assertTrue(any("explicit receipt schema_version" in error for error in self._schema_errors()))
        schema = copy.deepcopy(original)
        schema["$id"] = read_json(self.root / SCHEMA_ROOT / "change-set-v1.schema.json")["$id"]
        write_json(path, schema)
        self.assertTrue(any("duplicate $id" in error for error in self._schema_errors()))

    def test_invalid_receipt_json_is_rejected(self) -> None:
        path = self.root / SCHEMA_ROOT / CONTENT_SAFETY_SCHEMA_NAME
        for data in (b"{", b"[]", b"\xff"):
            with self.subTest(data=data):
                path.write_bytes(data)
                errors = self._schema_errors()
                self.assertTrue(any("SCG_SCHEMA_ATTACHMENT_META" in error for error in errors), errors)

    def test_missing_full_metadata_dependency_fails_closed(self) -> None:
        with patch.object(r2_install, "Draft202012Validator", None):
            errors = self._schema_errors()
        self.assertTrue(any("full Draft 2020-12 metadata validator unavailable" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
