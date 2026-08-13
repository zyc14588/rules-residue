import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.validate_m2_plan import collect_errors


class M2PlanTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def make_fixture(self, temporary_root: Path) -> None:
        shutil.copytree(
            self.root / ".codex" / "plans" / "m2-vertical-slice",
            temporary_root / ".codex" / "plans" / "m2-vertical-slice",
        )
        for relative in [
            ".codex/state/MILESTONE_PLAN.yaml",
            ".codex/routes/m2-vertical-slice-plan-request.json",
            "docs/implementation/r2/M2_REFERENCE_WORK_PACKAGES.yaml",
            "governance/evidence/r2-authority-install/integration-conflicts.yaml",
        ]:
            source = self.root / relative
            target = temporary_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def test_frozen_m2_plan_is_machine_valid(self) -> None:
        self.assertEqual(collect_errors(), [])

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
