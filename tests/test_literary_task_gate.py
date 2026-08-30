from __future__ import annotations

import copy
import unittest

from tools.lib.common import PROJECT_ROOT, read_json
from tools.lib.schema_subset import validate
from tools.story_construction import (
    literary_input_hash,
    literary_order_hash,
    validate_literary_execution,
    validate_task_packet_pairing,
)


def valid_literary_order() -> dict[str, object]:
    order: dict[str, object] = {
        "schema_version": "1.0.0",
        "order_id": "TEXT-ORDER-TEST-001",
        "order_authority": "VALIDATED_TEXT_ORDER_PACKAGE",
        "owner_token": "deepseek_harness",
        "task_type": "literary",
        "dossier_ref": "TEST-DOSSIER-001",
        "canon_refs": ["R2-CANON-TEST-001"],
        "reveal_refs": ["REVEAL-TEST-001"],
        "input_components": {
            "canon_slice_hash": "1" * 64,
            "dossier_hash": "2" * 64,
            "reveal_contract_hash": "3" * 64,
            "style_contract_hash": "4" * 64,
            "source_matrix_hash": "5" * 64,
        },
        "input_hash": "",
        "workflow_stages": [
            "COORDINATOR",
            "SEMANTIC_IMPLEMENTER",
            "LITERARY_WRITER",
            "INDEPENDENT_CHECKER",
            "DEFECT_ROUTER",
            "TARGETED_REPAIR",
        ],
        "max_targeted_repairs": 2,
        "forbidden_capabilities": [
            "CREATE_T1",
            "CREATE_T2",
            "CREATE_C1",
            "MODIFY_AUTHORITY",
            "WRITE_PERSISTENT_STATE",
            "MODIFY_RUNTIME",
            "MODIFY_LUA",
            "MODIFY_GAME_PACKAGE",
        ],
        "return_contract": {
            "semantic_draft": True,
            "literary_draft": True,
            "semantic_mapping": True,
            "source_matrix": True,
            "self_check": True,
            "issues": True,
            "version_usage": True,
            "return_hashes": True,
            "blocked_status": "BLOCKED_NEEDS_CANON",
        },
        "order_hash": "",
    }
    order["input_hash"] = literary_input_hash(order)
    order["order_hash"] = literary_order_hash(order)
    return order


class LiteraryTaskGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = read_json(
            PROJECT_ROOT / "workflow/examples/m3-literary-task-packet.json"
        )
        self.order = valid_literary_order()

    def test_valid_deepseek_literary_order_passes(self) -> None:
        schema = read_json(
            PROJECT_ROOT / "schemas/story-construction/text-order-v1.schema.json"
        )
        self.assertEqual(validate(self.order, schema), [])
        self.assertEqual(
            validate_literary_execution(
                self.packet,
                self.order,
                ["workflow/returns/literary/RR-TASK-1001.json"],
            ),
            [],
        )

    def test_opencode_literary_pairing_is_rejected(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["owner"] = "opencode"
        self.assertTrue(validate_task_packet_pairing(packet))

    def test_opencode_literary_authoring_target_is_rejected(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["owner"] = "opencode"
        errors = validate_literary_execution(
            packet, self.order, ["authoring/story/generated.md"]
        )
        self.assertTrue(any("cannot execute task_type=literary" in error for error in errors), errors)
        self.assertTrue(any("authority/schema/runtime write" in error for error in errors), errors)

    def test_deepseek_without_order_is_rejected(self) -> None:
        errors = validate_literary_execution(
            self.packet, None, ["workflow/returns/literary/test.json"]
        )
        self.assertTrue(any("valid Literary Order Package" in error for error in errors), errors)

    def test_wrong_input_hash_is_rejected(self) -> None:
        order = copy.deepcopy(self.order)
        order["input_hash"] = "0" * 64
        order["order_hash"] = literary_order_hash(order)
        errors = validate_literary_execution(
            self.packet, order, ["workflow/returns/literary/test.json"]
        )
        self.assertTrue(any("input hash mismatch" in error for error in errors), errors)

    def test_authority_schema_and_runtime_writes_are_rejected(self) -> None:
        for target in (
            "governance/story-construction/illegal.json",
            "schemas/story-construction/illegal.json",
            "game-package/content/illegal.json",
        ):
            with self.subTest(target=target):
                errors = validate_literary_execution(self.packet, self.order, [target])
                self.assertTrue(
                    any("authority/schema/runtime write" in error for error in errors),
                    errors,
                )

    def test_worker_self_review_cannot_form_final_pass(self) -> None:
        return_bundle = {
            "semantic_draft": {},
            "literary_draft": "candidate",
            "semantic_mapping": {},
            "source_matrix": [],
            "self_check": "PASS",
            "issues": [],
            "version_usage": [],
            "return_hashes": {},
            "final_acceptance": "PASS",
        }
        errors = validate_literary_execution(
            self.packet,
            self.order,
            ["workflow/returns/literary/test.json"],
            return_bundle,
        )
        self.assertTrue(any("self-review" in error for error in errors), errors)

    def test_missing_canon_uses_blocked_contract(self) -> None:
        self.assertEqual(
            validate_literary_execution(
                self.packet,
                self.order,
                ["workflow/returns/literary/test.json"],
                {"status": "BLOCKED_NEEDS_CANON", "missing_canon": ["T2-TEST"]},
            ),
            [],
        )
        errors = validate_literary_execution(
            self.packet,
            self.order,
            ["workflow/returns/literary/test.json"],
            {"status": "BLOCKED_NEEDS_CANON", "missing_canon": []},
        )
        self.assertTrue(any("identify missing canon" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
