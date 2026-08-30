import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.validate_m2_plan import (
    ACCEPTED_WITH_BLOCKERS,
    FROZEN_RECOVERY_PENDING,
    INVALID_MIXED_STATE,
    collect_errors,
    collect_validation,
)


class M2PlanTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]
    recovery_candidate = "f5964d4c0b02e5969747a628dae64a02f87b8417"

    def historical_bytes(self, relative: str) -> bytes:
        return subprocess.check_output(
            ["git", "show", f"{self.recovery_candidate}:{relative}"],
            cwd=self.root,
        )

    def copy_fixture_path(self, temporary_root: Path, relative: str, historical: bool) -> None:
        target = temporary_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if historical:
            target.write_bytes(self.historical_bytes(relative))
        else:
            shutil.copy2(self.root / relative, target)

    def make_fixture(self, temporary_root: Path, *, historical: bool = False) -> None:
        plan_root = ".codex/plans/m2-vertical-slice"
        if historical:
            plan_paths = subprocess.check_output(
                [
                    "git",
                    "ls-tree",
                    "-r",
                    "--name-only",
                    self.recovery_candidate,
                    "--",
                    plan_root,
                ],
                cwd=self.root,
                text=True,
            ).splitlines()
            for relative in plan_paths:
                self.copy_fixture_path(temporary_root, relative, historical=True)
        else:
            shutil.copytree(
                self.root / plan_root,
                temporary_root / plan_root,
            )
        for relative in [
            ".codex/state/MILESTONE_PLAN.yaml",
            ".codex/routes/m2-vertical-slice-plan-request.json",
            "docs/implementation/r2/M2_REFERENCE_WORK_PACKAGES.yaml",
            "governance/evidence/r2-authority-install/integration-conflicts.yaml",
            "reports/m2/probes/closeouts/m2-b001-recovery-closeout-001/evidence.json",
        ]:
            self.copy_fixture_path(temporary_root, relative, historical)

    def test_frozen_m2_plan_is_machine_valid(self) -> None:
        self.assertEqual(collect_errors(), [])

    def test_frozen_plan_with_recovery_evidence_is_pending_lifecycle_closeout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root, historical=True)
            errors, state = collect_validation(root)
            self.assertEqual(errors, [])
            self.assertEqual(state, FROZEN_RECOVERY_PENDING)

    def test_current_lifecycle_candidate_is_accepted_with_downstream_blockers(self) -> None:
        errors, state = collect_validation()
        self.assertEqual(errors, [])
        self.assertEqual(state, ACCEPTED_WITH_BLOCKERS)

    def test_accepted_lifecycle_with_downstream_blockers_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            errors, state = collect_validation(root)
            self.assertEqual(errors, [])
            self.assertEqual(state, ACCEPTED_WITH_BLOCKERS)

    def test_mixed_lifecycle_state_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root, historical=True)
            path = root / ".codex/state/MILESTONE_PLAN.yaml"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["state"] = "ACCEPTED"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            errors, state = collect_validation(root)
            self.assertEqual(state, INVALID_MIXED_STATE)
            self.assertTrue(any(INVALID_MIXED_STATE in error for error in errors))

    def test_accepted_lifecycle_cannot_drop_downstream_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            recovery_path = root / "reports/m2/probes/closeouts/m2-b001-recovery-closeout-001/evidence.json"
            recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
            recovery["readiness"]["blocking_ids"].pop()
            recovery_path.write_text(json.dumps(recovery, ensure_ascii=False), encoding="utf-8")
            errors, state = collect_validation(root)
            self.assertEqual(state, ACCEPTED_WITH_BLOCKERS)
            self.assertTrue(any("downstream blockers" in error for error in errors))

    def test_forward_dependency_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / ".codex/plans/m2-vertical-slice/batches.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["dependency_graph"]["M2-B002"] = ["M2-B003"]
            data["batches"][1]["dependencies"] = ["M2-B003"]
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            errors = collect_errors(root)
            self.assertTrue(any("forward, or cyclic dependency" in error for error in errors))

    def test_external_not_run_cannot_be_changed_to_pass_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / ".codex/plans/m2-vertical-slice/controls.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["external_gates"][0]["status"] = "PASS"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            errors = collect_errors(root)
            self.assertTrue(any("external gates must remain NOT_RUN" in error for error in errors))

    def test_probe_execution_status_contract_requires_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / ".codex/plans/m2-vertical-slice/capability-probes.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["rules"]["allowed_probe_execution_statuses"].remove("NOT_RUN")
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            errors = collect_errors(root)
            self.assertTrue(any("probe execution statuses" in error for error in errors))

    def test_batch_result_contract_preserves_five_states(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / ".codex/plans/m2-vertical-slice/capability-probes.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["rules"]["allowed_batch_results"].remove("BLOCKED_DESIGN_CONFLICT")
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            errors = collect_errors(root)
            self.assertTrue(any("five-state contract" in error for error in errors))

    def test_probe_result_contract_requires_all_evidence_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / ".codex/plans/m2-vertical-slice/capability-probes.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["rules"]["probe_result_required_fields"].remove("root_cause")
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            errors = collect_errors(root)
            self.assertTrue(any("required evidence field" in error for error in errors))

    def test_routed_projection_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_fixture(root)
            path = root / ".codex/plans/m2-vertical-slice/ROUTED_INPUT_PROJECTIONS.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("risk: HIGH", "risk: LOW", 1), encoding="utf-8")
            errors = collect_errors(root)
            self.assertTrue(any("not byte-identical" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
