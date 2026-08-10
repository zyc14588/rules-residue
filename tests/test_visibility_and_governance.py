import csv
import unittest

from tools.lib.common import PROJECT_ROOT, find_duplicates, read_json


class VisibilityAndGovernanceTests(unittest.TestCase):
    def test_gm_authority_is_locked(self) -> None:
        state = read_json(PROJECT_ROOT / "game-package/tests/fixtures/sample_state.json")
        self.assertTrue(state["authority"]["locked"])
        self.assertIn(state["authority"]["gm_mode"], {"human", "ai"})

    def test_world_truth_fixture_contains_separate_visibility_domains(self) -> None:
        state = read_json(PROJECT_ROOT / "game-package/tests/fixtures/sample_state.json")
        labels = {fact["visibility"] for fact in state["world_truth"]["facts"]}
        self.assertIn("gm_only", labels)
        self.assertIn("public", labels)
        self.assertTrue(any(label.startswith("participant:") for label in labels))

    def test_decision_ids_are_unique(self) -> None:
        data = read_json(PROJECT_ROOT / "governance/decisions.json")
        ids = [item["id"] for item in data["decisions"]]
        self.assertEqual(find_duplicates(ids), [])

    def test_every_p0_requirement_is_traced(self) -> None:
        scope = read_json(PROJECT_ROOT / "governance/scope.json")
        requirements = {item["id"] for item in scope["p0"]}
        with (PROJECT_ROOT / "governance/traceability.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            traced = {row["Requirement"] for row in csv.DictReader(handle)}
        self.assertEqual(requirements - traced, set())


if __name__ == "__main__":
    unittest.main()
