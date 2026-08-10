import unittest

from tools.lib.common import GAME_PACKAGE_ROOT, read_json
from tools.lib.reference_rules import classify, expected_effect_types


class RulesVectorTests(unittest.TestCase):
    def test_check_boundaries(self) -> None:
        difficulty = 9
        self.assertEqual(classify(12, difficulty), "strong_success")
        self.assertEqual(classify(9, difficulty), "success")
        self.assertEqual(classify(7, difficulty), "success_with_cost")
        self.assertEqual(classify(6, difficulty), "failure_with_consequence")

    def test_all_expected_vectors_match_reference(self) -> None:
        for module in ["tutorial", "golden"]:
            path = GAME_PACKAGE_ROOT / "modules" / module / "expected-path.json"
            data = read_json(path)
            for vector in data["vectors"]:
                outcome, effects = expected_effect_types(
                    vector["action"], vector["rule_input"], vector["resolution_input"]
                )
                self.assertEqual(outcome, vector["expected"]["outcome"], vector["id"])
                self.assertEqual(effects, vector["expected"]["effect_types"], vector["id"])


    def test_bounded_player_control_vector_exists(self) -> None:
        data = read_json(GAME_PACKAGE_ROOT / "modules" / "golden" / "expected-path.json")
        vector = next(item for item in data["vectors"] if item["id"] == "golden.control.player-substitution")
        self.assertTrue(vector["rule_input"]["substitute_next_action"])
        self.assertEqual(vector["rule_input"]["max_substituted_actions"], 1)
        self.assertEqual(vector["expected"]["effect_types"], ["append_event", "set_status"])

    def test_golden_covers_all_outcomes(self) -> None:
        data = read_json(GAME_PACKAGE_ROOT / "modules" / "golden" / "expected-path.json")
        outcomes = {
            vector["expected"]["outcome"]
            for vector in data["vectors"]
            if vector["resolution_input"]["kind"] == "roll"
        }
        self.assertEqual(
            outcomes,
            {"strong_success", "success", "success_with_cost", "failure_with_consequence"},
        )


if __name__ == "__main__":
    unittest.main()
