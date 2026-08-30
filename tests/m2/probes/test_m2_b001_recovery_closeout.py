from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from validate_m2_b001_recovery_closeout import (
    _validate_historical_anchor_identity,
    _validate_lifecycle_anchor_structure,
    ALLOWED_CHANGED_PATHS,
    ARTIFACT_PATHS,
    BLOCKING_IDS,
    BRIDGE_TEST_PATH_TEXT,
    CANDIDATE_B_ALLOWED_CHANGED_PATHS,
    CURRENT_RECOVERY_CANDIDATE,
    EVIDENCE_PATH_TEXT,
    EVOLVABLE_HISTORICAL_ARTIFACT_PATHS,
    EXECUTION_PATH_TEXT,
    HISTORICAL_ACCEPTED_RECOVERY,
    IMMUTABLE_HASHES,
    INDEX_V1_PATH_TEXT,
    INDEX_V2_PATH_TEXT,
    LIFECYCLE_CLOSEOUT_ANCHOR,
    LIFECYCLE_CLOSEOUT_COMMIT,
    LIFECYCLE_CLOSEOUT_TREE,
    MANIFEST_PATH_TEXT,
    POST_ACCEPTED_NON_M2_DESCENDANT,
    PLAN_TEST_PATH_TEXT,
    PLAN_VALIDATOR_PATH_TEXT,
    PROBE_TEST_PATH_TEXT,
    RECOVERY_CANDIDATE_COMMIT,
    RECOVERY_CANDIDATE_TREE,
    RecoveryValidationError,
    VALIDATOR_PATH_TEXT,
    collect_changed_paths,
    read_git_blob,
    read_historical_blob,
    validate_candidate_b_changed_paths,
    validate_candidate_checkout,
    validate_changed_paths,
    validate_historical_anchor,
    validate_historical_manifest_entries,
    validate_lifecycle_preservation_state,
    validate_recovery,
)


ROOT = Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _set_path(value: Any, path: tuple[Any, ...], replacement: Any) -> None:
    target = value
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement


def _delete_path(value: Any, path: tuple[Any, ...]) -> None:
    target = value
    for component in path[:-1]:
        target = target[component]
    del target[path[-1]]


def _promote_antecedent(identity: str) -> Callable[[dict[str, Any]], None]:
    def mutate(value: dict[str, Any]) -> None:
        item = next(entry for entry in value["non_authoritative_antecedents"] if entry["identity"] == identity)
        item["may_be_used_as_execution_evidence"] = True

    return mutate


def _replace_blockers(value: dict[str, Any], blockers: list[str]) -> None:
    value["readiness"]["blocking_ids"] = blockers


class RecoveryCloseoutTests(unittest.TestCase):
    maxDiff = None

    def make_fixture(self, temporary_root: Path) -> None:
        paths = list(IMMUTABLE_HASHES) + ARTIFACT_PATHS + [MANIFEST_PATH_TEXT]
        for relative in dict.fromkeys(paths):
            target = temporary_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(read_historical_blob(ROOT, relative))

    def make_checkout(self, temporary_root: Path, commit: str) -> Path:
        root = temporary_root / "checkout"
        subprocess.run(
            ["git", "clone", "-q", "--shared", str(ROOT), str(root)],
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "-q", "--detach", commit],
            cwd=root,
            check=True,
        )
        subprocess.run(["git", "config", "user.name", "Recovery Tests"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "recovery-tests@example.invalid"],
            cwd=root,
            check=True,
        )
        return root

    def make_a2_checkout(self, temporary_root: Path) -> Path:
        return self.make_checkout(temporary_root, RECOVERY_CANDIDATE_COMMIT)

    def commit_paths(self, root: Path, paths: list[str], message: str) -> tuple[str, str]:
        subprocess.run(["git", "add", "--", *paths], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", message],
            cwd=root,
            check=True,
        )
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
        return commit, tree

    def make_lifecycle_checkout(self, temporary_root: Path) -> tuple[Path, str, str]:
        root = self.make_checkout(temporary_root, LIFECYCLE_CLOSEOUT_COMMIT)
        return root, LIFECYCLE_CLOSEOUT_COMMIT, LIFECYCLE_CLOSEOUT_TREE

    def commit_non_m2_descendant(
        self,
        root: Path,
        relative: str = "docs/story-governance-descendant.md",
    ) -> tuple[str, str]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("later non-M2 batch\n", encoding="utf-8")
        return self.commit_paths(root, [relative], "later non-M2 descendant")

    def assert_historical_mutation_rejected(self, relative: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            commit, tree = self.commit_paths(root, [relative], f"tamper {relative}")
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                    candidate=commit,
                    candidate_tree=tree,
                )

    def assert_descendant_json_mutation_rejected(
        self,
        relative: str,
        mutator: Callable[[dict[str, Any]], None],
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            self.mutate_fixture(root, relative, mutator)
            commit, tree = self.commit_paths(root, [relative], f"tamper {relative}")
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                    candidate=commit,
                    candidate_tree=tree,
                )

    def mutate_fixture(
        self,
        temporary_root: Path,
        relative: str,
        mutator: Callable[[dict[str, Any]], None],
    ) -> None:
        path = temporary_root / relative
        value = _read_json(path)
        mutator(value)
        _write_json(path, value)

    def assert_json_attack_rejected(
        self,
        relative: str,
        mutator: Callable[[dict[str, Any]], None],
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            self.mutate_fixture(root, relative, mutator)
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=CURRENT_RECOVERY_CANDIDATE,
                    check_git=False,
                )

    def test_valid_recovery_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            validate_recovery(
                root,
                mode=CURRENT_RECOVERY_CANDIDATE,
                check_git=False,
            )

    def test_reject_predecessor_evidence_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / "reports/m2/probes/probe-results.json"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=CURRENT_RECOVERY_CANDIDATE,
                    check_git=False,
                )

    def test_reject_v1_index_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / INDEX_V1_PATH_TEXT
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=CURRENT_RECOVERY_CANDIDATE,
                    check_git=False,
                )

    def test_reject_execution_missing_started_at(self) -> None:
        self.assert_json_attack_rejected(
            EXECUTION_PATH_TEXT,
            lambda value: value["records"][0].pop("started_at"),
        )

    def test_reject_execution_expected_exit_only(self) -> None:
        def mutate(value: dict[str, Any]) -> None:
            record = value["records"][0]
            record["expected_exit_code"] = record.pop("exit_code")

        self.assert_json_attack_rejected(EXECUTION_PATH_TEXT, mutate)

    def test_reject_execution_missing_output_digest(self) -> None:
        self.assert_json_attack_rejected(
            EXECUTION_PATH_TEXT,
            lambda value: value["records"][0].pop("stderr_sha256"),
        )

    def test_reject_execution_finished_before_started(self) -> None:
        def mutate(value: dict[str, Any]) -> None:
            record = value["records"][0]
            record["finished_at"] = "2000-01-01T00:00:00Z"

        self.assert_json_attack_rejected(EXECUTION_PATH_TEXT, mutate)

    def make_git_checkout(self, root: Path) -> tuple[str, str]:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Recovery Tests"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "recovery-tests@example.invalid"], cwd=root, check=True)
        marker = root / "marker.txt"
        marker.write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "marker.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
        return commit, tree

    def test_exact_candidate_checkout_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commit, tree = self.make_git_checkout(root)
            validate_candidate_checkout(root, commit, tree, source_commit=commit)

    def test_reject_candidate_validation_wrong_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commit, tree = self.make_git_checkout(root)
            wrong = "0" * 40 if commit != "0" * 40 else "1" * 40
            with self.assertRaises(RecoveryValidationError):
                validate_candidate_checkout(root, wrong, tree, source_commit=commit)

    def test_reject_candidate_validation_wrong_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commit, tree = self.make_git_checkout(root)
            wrong = "0" * 40 if tree != "0" * 40 else "1" * 40
            with self.assertRaises(RecoveryValidationError):
                validate_candidate_checkout(root, commit, wrong, source_commit=commit)

    def test_reject_dirty_candidate_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commit, tree = self.make_git_checkout(root)
            (root / "marker.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaises(RecoveryValidationError):
                validate_candidate_checkout(root, commit, tree, source_commit=commit)

    def test_reject_allowed_path_outside_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commit, _ = self.make_git_checkout(root)
            outside = root / "outside-approved-scope.txt"
            outside.write_text("attack\n", encoding="utf-8")
            changed = collect_changed_paths(root, source_ref=commit)
            with self.assertRaises(RecoveryValidationError):
                validate_changed_paths(changed, require_complete=False)

    def test_approved_path_set_is_exact(self) -> None:
        self.assertEqual(len(ALLOWED_CHANGED_PATHS), 10)
        validate_changed_paths(ALLOWED_CHANGED_PATHS)

    def test_candidate_a2_current_tree_mode_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_a2_checkout(Path(temporary))
            validate_recovery(
                root,
                mode=CURRENT_RECOVERY_CANDIDATE,
                candidate=RECOVERY_CANDIDATE_COMMIT,
                candidate_tree=RECOVERY_CANDIDATE_TREE,
            )

    def test_exact_lifecycle_anchor_mode_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, commit, tree = self.make_lifecycle_checkout(Path(temporary))
            validate_recovery(
                root,
                mode=LIFECYCLE_CLOSEOUT_ANCHOR,
                candidate=commit,
                candidate_tree=tree,
            )

    def test_later_non_m2_descendant_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            commit, tree = self.commit_non_m2_descendant(root)
            validate_recovery(
                root,
                mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                candidate=commit,
                candidate_tree=tree,
            )

    def test_story_governance_style_descendant_is_not_given_m2_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            paths = [
                "docs/governance/story-construction/example.md",
                "governance/story-construction/example.json",
                "schemas/story-construction/example.schema.json",
            ]
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n" if relative.endswith(".json") else "later batch\n", encoding="utf-8")
            commit, tree = self.commit_paths(
                root,
                paths,
                "Story Governance style descendant",
            )
            validate_recovery(
                root,
                mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                candidate=commit,
                candidate_tree=tree,
            )

    def test_dirty_non_m2_worktree_at_anchor_uses_descendant_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            marker = root / "docs/story-governance-draft.md"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("uncommitted later batch\n", encoding="utf-8")
            semantic_mode = validate_recovery(
                root,
                mode=HISTORICAL_ACCEPTED_RECOVERY,
            )
            self.assertEqual(semantic_mode, POST_ACCEPTED_NON_M2_DESCENDANT)

    def test_owner_amended_validator_and_test_descendant_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            for relative in (VALIDATOR_PATH_TEXT, PROBE_TEST_PATH_TEXT):
                target = root / relative
                shutil.copy2(ROOT / relative, target)
            commit, tree = self.commit_paths(
                root,
                [VALIDATOR_PATH_TEXT, PROBE_TEST_PATH_TEXT],
                "owner-amended historical validator compatibility",
            )
            validate_recovery(
                root,
                mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                candidate=commit,
                candidate_tree=tree,
            )

    def test_every_a2_manifest_hash_recomputes_from_git_show(self) -> None:
        manifest = _read_json(ROOT / MANIFEST_PATH_TEXT)
        for group in ("artifacts", "immutable_predecessors"):
            for item in manifest[group]:
                actual = hashlib.sha256(
                    read_historical_blob(ROOT, item["path"])
                ).hexdigest()
                self.assertEqual(actual, item["sha256"], item["path"])
        validate_historical_manifest_entries(ROOT, manifest)

    def test_changed_plan_test_does_not_corrupt_historical_manifest(self) -> None:
        self.assertNotEqual(
            (ROOT / PLAN_TEST_PATH_TEXT).read_bytes(),
            read_historical_blob(ROOT, PLAN_TEST_PATH_TEXT),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root, commit, tree = self.make_lifecycle_checkout(Path(temporary))
            validate_recovery(
                root,
                mode=HISTORICAL_ACCEPTED_RECOVERY,
                candidate=commit,
                candidate_tree=tree,
            )

    def test_reject_current_recovery_evidence_change(self) -> None:
        self.assert_historical_mutation_rejected(EVIDENCE_PATH_TEXT)

    def test_reject_current_recovery_manifest_change(self) -> None:
        self.assert_historical_mutation_rejected(MANIFEST_PATH_TEXT)

    def test_reject_current_execution_records_change(self) -> None:
        self.assert_historical_mutation_rejected(EXECUTION_PATH_TEXT)

    def test_reject_current_external_evidence_index_v2_change(self) -> None:
        self.assert_historical_mutation_rejected(INDEX_V2_PATH_TEXT)

    def test_reject_descendant_changes_m2_b001_state(self) -> None:
        self.assert_descendant_json_mutation_rejected(
            ".codex/plans/m2-vertical-slice/batches.json",
            lambda value: value["lifecycle_projection"].__setitem__(
                "M2-B001", "IMPLEMENTING"
            ),
        )

    def test_reject_descendant_starts_m2_b002(self) -> None:
        def mutate(value: dict[str, Any]) -> None:
            batch = next(item for item in value["batches"] if item["id"] == "M2-B002")
            batch["state"] = "FROZEN"
            batch["implementation_state"] = "IMPLEMENTING"

        self.assert_descendant_json_mutation_rejected(
            ".codex/plans/m2-vertical-slice/batches.json",
            mutate,
        )

    def test_reject_descendant_changes_m2_b002_ready(self) -> None:
        self.assert_descendant_json_mutation_rejected(
            ".codex/plans/m2-vertical-slice/batches.json",
            lambda value: value["lifecycle_projection"].__setitem__(
                "M2-B002_READY", "YES"
            ),
        )

    def test_reject_descendant_changes_formal_b002(self) -> None:
        self.assert_descendant_json_mutation_rejected(
            ".codex/plans/m2-vertical-slice/batches.json",
            lambda value: value["lifecycle_projection"].__setitem__(
                "formal_B002", True
            ),
        )

    def test_reject_descendant_changes_formal_b009(self) -> None:
        self.assert_descendant_json_mutation_rejected(
            ".codex/plans/m2-vertical-slice/batches.json",
            lambda value: value["lifecycle_projection"].__setitem__(
                "formal_B009", True
            ),
        )

    def test_reject_descendant_removes_blocker(self) -> None:
        self.assert_descendant_json_mutation_rejected(
            ".codex/plans/m2-vertical-slice/batches.json",
            lambda value: value["lifecycle_projection"]["blocking_ids"].pop(),
        )

    def test_reject_descendant_reorders_blockers(self) -> None:
        self.assert_descendant_json_mutation_rejected(
            ".codex/plans/m2-vertical-slice/batches.json",
            lambda value: value["lifecycle_projection"].__setitem__(
                "blocking_ids", list(reversed(BLOCKING_IDS))
            ),
        )

    def test_reject_descendant_modifies_lifecycle_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            relative = ".codex/plans/m2-vertical-slice/M2_VERTICAL_SLICE_PLAN.md"
            path = root / relative
            path.write_bytes(path.read_bytes() + b"\n")
            commit, tree = self.commit_paths(root, [relative], "tamper lifecycle evidence")
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                    candidate=commit,
                    candidate_tree=tree,
                )

    def test_reject_forged_a2_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_a2_checkout(Path(temporary))
            with self.assertRaises(RecoveryValidationError):
                _validate_historical_anchor_identity(
                    root,
                    "0" * 40,
                    RECOVERY_CANDIDATE_TREE,
                )

    def test_reject_forged_a2_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_a2_checkout(Path(temporary))
            with self.assertRaises(RecoveryValidationError):
                _validate_historical_anchor_identity(
                    root,
                    RECOVERY_CANDIDATE_COMMIT,
                    "0" * 40,
                )

    def test_reject_wrong_lifecycle_anchor_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_a2_checkout(Path(temporary))
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=LIFECYCLE_CLOSEOUT_ANCHOR,
                    candidate=RECOVERY_CANDIDATE_COMMIT,
                    candidate_tree=RECOVERY_CANDIDATE_TREE,
                )

    def test_reject_wrong_lifecycle_anchor_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, commit, _ = self.make_lifecycle_checkout(Path(temporary))
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=LIFECYCLE_CLOSEOUT_ANCHOR,
                    candidate=commit,
                    candidate_tree="0" * 40,
                )

    def test_reject_lifecycle_anchor_wrong_parent(self) -> None:
        with self.assertRaises(RecoveryValidationError):
            _validate_lifecycle_anchor_structure(
                parent="0" * 40,
                commit_count=1,
                changed_paths=CANDIDATE_B_ALLOWED_CHANGED_PATHS,
            )

    def test_reject_lifecycle_anchor_extra_path(self) -> None:
        with self.assertRaises(RecoveryValidationError):
            _validate_lifecycle_anchor_structure(
                parent=RECOVERY_CANDIDATE_COMMIT,
                commit_count=1,
                changed_paths=[
                    *CANDIDATE_B_ALLOWED_CHANGED_PATHS,
                    "outside-lifecycle.txt",
                ],
            )

    def test_reject_lifecycle_anchor_missing_path(self) -> None:
        with self.assertRaises(RecoveryValidationError):
            _validate_lifecycle_anchor_structure(
                parent=RECOVERY_CANDIDATE_COMMIT,
                commit_count=1,
                changed_paths=CANDIDATE_B_ALLOWED_CHANGED_PATHS[:-1],
            )

    def test_reject_lifecycle_anchor_more_than_one_commit(self) -> None:
        with self.assertRaises(RecoveryValidationError):
            _validate_lifecycle_anchor_structure(
                parent=RECOVERY_CANDIDATE_COMMIT,
                commit_count=2,
                changed_paths=CANDIDATE_B_ALLOWED_CHANGED_PATHS,
            )

    def test_reject_mixed_lifecycle_state_semantics(self) -> None:
        relative = ".codex/plans/m2-vertical-slice/batches.json"
        value = json.loads(
            read_git_blob(ROOT, LIFECYCLE_CLOSEOUT_COMMIT, relative).decode("utf-8")
        )
        value["lifecycle_projection"]["state"] = "FROZEN"
        mutated = (json.dumps(value) + "\n").encode("utf-8")

        def reader(path_text: str) -> bytes:
            if path_text == relative:
                return mutated
            return read_git_blob(ROOT, LIFECYCLE_CLOSEOUT_COMMIT, path_text)

        with self.assertRaises(RecoveryValidationError):
            validate_lifecycle_preservation_state(ROOT, artifact_reader=reader)

    def test_reject_candidate_that_is_not_e90_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_a2_checkout(Path(temporary))
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            tree = subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True
            ).strip()
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                    candidate=commit,
                    candidate_tree=tree,
                )

    def test_reject_missing_historical_git_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            with self.assertRaises(RecoveryValidationError):
                validate_historical_anchor(root)

    def test_reject_historical_manifest_hash_mismatch(self) -> None:
        manifest = _read_json(ROOT / MANIFEST_PATH_TEXT)
        manifest["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaises(RecoveryValidationError):
            validate_historical_manifest_entries(ROOT, manifest)

    def test_missing_git_object_never_falls_back_to_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            current = root / EVIDENCE_PATH_TEXT
            current.parent.mkdir(parents=True, exist_ok=True)
            current.write_bytes(read_historical_blob(ROOT, EVIDENCE_PATH_TEXT))
            with self.assertRaises(RecoveryValidationError):
                read_historical_blob(root, EVIDENCE_PATH_TEXT)

    def test_reject_historical_manifest_artifact_outside_candidate_b_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = self.make_lifecycle_checkout(Path(temporary))
            path = root / PLAN_VALIDATOR_PATH_TEXT
            path.write_bytes(path.read_bytes() + b"\n")
            commit, tree = self.commit_paths(
                root,
                [PLAN_VALIDATOR_PATH_TEXT],
                "tamper non-evolvable historical validator",
            )
            with self.assertRaises(RecoveryValidationError):
                validate_recovery(
                    root,
                    mode=POST_ACCEPTED_NON_M2_DESCENDANT,
                    candidate=commit,
                    candidate_tree=tree,
                )

    def test_candidate_b_allowlist_and_evolvable_paths_are_exact(self) -> None:
        self.assertEqual(len(CANDIDATE_B_ALLOWED_CHANGED_PATHS), 11)
        self.assertEqual(
            EVOLVABLE_HISTORICAL_ARTIFACT_PATHS,
            {
                VALIDATOR_PATH_TEXT,
                PROBE_TEST_PATH_TEXT,
                BRIDGE_TEST_PATH_TEXT,
                PLAN_TEST_PATH_TEXT,
            },
        )
        self.assertTrue(
            EVOLVABLE_HISTORICAL_ARTIFACT_PATHS
            <= set(CANDIDATE_B_ALLOWED_CHANGED_PATHS)
        )
        validate_candidate_b_changed_paths(CANDIDATE_B_ALLOWED_CHANGED_PATHS)


def _set_attack(path: tuple[Any, ...], replacement: Any) -> Callable[[dict[str, Any]], None]:
    return lambda value: _set_path(value, path, replacement)


def _delete_attack(path: tuple[Any, ...]) -> Callable[[dict[str, Any]], None]:
    return lambda value: _delete_path(value, path)


EVIDENCE_ATTACKS: dict[str, Callable[[dict[str, Any]], None]] = {
    "formal_b002_true": _set_attack(("non_claims", "formal_B002"), True),
    "formal_b009_true": _set_attack(("non_claims", "formal_B009"), True),
    "m2_b002_implementing": _set_attack(("readiness", "M2-B002"), "IMPLEMENTING"),
    "m2_b002_ready_yes": _set_attack(("readiness", "M2-B002_READY"), "YES"),
    "aggregate_m2_pass_true": _set_attack(("non_claims", "aggregate_M2_pass"), True),
    "aggregate_external_capability_pass_true": _set_attack(("non_claims", "aggregate_external_capability_pass"), True),
    "wrong_rules_commit": _set_attack(("accepted_post_platform_pair", "rules", "commit"), "0" * 40),
    "wrong_rules_tree": _set_attack(("accepted_post_platform_pair", "rules", "tree"), "0" * 40),
    "wrong_platform_commit": _set_attack(("accepted_post_platform_pair", "platform", "commit"), "0" * 40),
    "wrong_platform_tree": _set_attack(("accepted_post_platform_pair", "platform", "tree"), "0" * 40),
    "wrong_exact_pair_verdict_digest": _set_attack(("accepted_post_platform_pair", "verdict_sha256"), "0" * 64),
    "wrong_formal_b001_commit": _set_attack(("formal_m2_b001", "commit"), "0" * 40),
    "wrong_formal_b001_tree": _set_attack(("formal_m2_b001", "tree"), "0" * 40),
    "wrong_platform_closeout_commit": _set_attack(("platform_closeout", "commit"), "0" * 40),
    "wrong_platform_closeout_tree": _set_attack(("platform_closeout", "tree"), "0" * 40),
    "promote_c6_commit": _set_attack(("accepted_post_platform_pair", "rules", "commit"), "c6a840b10db46dc475cd9af9e6a1a13f1e68abd4"),
    "promote_65_commit": _set_attack(("accepted_post_platform_pair", "rules", "commit"), "65a0a1671720345425e0368136793754567187cc"),
    "promote_proposal": _promote_antecedent("PLATFORM_CHANGE_PROPOSAL"),
    "promote_owner_approval_antecedent": _promote_antecedent("OWNER_APPROVAL_ANTECEDENT"),
    "promote_early_phase_j": _promote_antecedent("EARLY_PHASE_J"),
    "promote_attempt_001": _promote_antecedent("ATTEMPT_001"),
    "promote_owner_route_authority": _promote_antecedent("OWNER_ROUTE_AUTHORITY"),
    "missing_blocker": lambda value: _replace_blockers(value, BLOCKING_IDS[:-1]),
    "extra_blocker": lambda value: _replace_blockers(value, [*BLOCKING_IDS, "EXTRA-BLOCKER"]),
    "renamed_blocker": lambda value: _replace_blockers(value, ["R2-INT-011", "R2-INT-012-RENAMED", "DEFER-R2-C14-001"]),
    "reordered_blockers": lambda value: _replace_blockers(value, list(reversed(BLOCKING_IDS))),
    "candidate_strategy_not_exact_head": _set_attack(("candidate_binding", "strategy"), "EMBEDDED_COMMIT"),
    "candidate_execution_status_forged_pass": _set_attack(("candidate_binding", "execution_status"), "PASS"),
    "historical_fail_rewritten": _set_attack(("historical_projection", "R2-INT-010"), "RESOLVED_ADAPTER"),
    "required_field_missing": _delete_attack(("task_id",)),
    "unknown_field": _set_attack(("unexpected" ,), True),
    "wrong_evidence_id": _set_attack(("evidence_id",), "WRONG-EVIDENCE"),
    "wrong_task_id": _set_attack(("task_id",), "WRONG-TASK"),
    "wrong_closeout_id": _set_attack(("closeout_id",), "WRONG-CLOSEOUT"),
    "wrong_attempt_number": _set_attack(("attempt_number",), 1),
    "wrong_route_id": _set_attack(("route_binding", "route_id"), "WRONG-ROUTE"),
    "wrong_route_digest": _set_attack(("route_binding", "binding_digest"), "0" * 64),
    "manifest_circular_binding": _set_attack(("evidence_links", "evidence_manifest_sha256"), "0" * 64),
}


MANIFEST_ATTACKS: dict[str, Callable[[dict[str, Any]], None]] = {
    "manifest_missing_item": lambda value: value["artifacts"].pop(),
    "manifest_duplicate_item": lambda value: value["artifacts"].append(copy.deepcopy(value["artifacts"][0])),
    "manifest_forged_digest": _set_attack(("artifacts", 0, "sha256"), "0" * 64),
    "manifest_self_binding": lambda value: value["artifacts"].append({"path": MANIFEST_PATH_TEXT, "sha256": "0" * 64}),
}


INDEX_ATTACKS: dict[str, Callable[[dict[str, Any]], None]] = {
    "ordinal_predecessor_hash_mismatch": _set_attack(("predecessor_index", "sha256"), "0" * 64),
}


def _install_generated_attack_tests() -> None:
    groups = [
        (EVIDENCE_PATH_TEXT, EVIDENCE_ATTACKS),
        (MANIFEST_PATH_TEXT, MANIFEST_ATTACKS),
        (INDEX_V2_PATH_TEXT, INDEX_ATTACKS),
    ]
    for relative, attacks in groups:
        for attack_name, mutator in attacks.items():
            def test(self: RecoveryCloseoutTests, relative: str = relative, mutator: Callable[[dict[str, Any]], None] = mutator) -> None:
                self.assert_json_attack_rejected(relative, mutator)

            test.__name__ = f"test_reject_{attack_name}"
            test.__qualname__ = f"RecoveryCloseoutTests.{test.__name__}"
            setattr(RecoveryCloseoutTests, test.__name__, test)


_install_generated_attack_tests()


if __name__ == "__main__":
    unittest.main()
