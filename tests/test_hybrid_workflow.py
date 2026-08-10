import unittest
from tools.lib.common import PROJECT_ROOT, read_json
from tools.lib.schema_subset import validate


class HybridWorkflowTests(unittest.TestCase):
    def test_task_packet_examples_validate(self) -> None:
        schema = read_json(PROJECT_ROOT / "workflow/task-packet.schema.json")
        examples = sorted((PROJECT_ROOT / "workflow/examples").glob("*.json"))
        self.assertGreaterEqual(len(examples), 3)
        for path in examples:
            self.assertEqual(validate(read_json(path), schema), [], path.name)

    def test_role_routing_is_explicit(self) -> None:
        packets = [read_json(path) for path in sorted((PROJECT_ROOT / "workflow/examples").glob("*.json"))]
        by_owner = {packet["owner"]: packet["task_type"] for packet in packets}
        self.assertEqual(by_owner["opencode"], "script")
        self.assertEqual(by_owner["grok"], "art")
        self.assertEqual(by_owner["codex"], "acceptance")

    def test_core_genre_decisions_are_accepted(self) -> None:
        data = read_json(PROJECT_ROOT / "governance/decisions.json")
        status = {item["id"]: item["status"] for item in data["decisions"]}
        for decision_id in ["RR-D019", "RR-D020", "RR-D021", "RR-D022", "RR-D023"]:
            self.assertEqual(status.get(decision_id), "ACCEPTED")


if __name__ == "__main__":
    unittest.main()
