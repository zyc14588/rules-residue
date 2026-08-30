from __future__ import annotations

import copy
import unittest

from tools.lib.common import PROJECT_ROOT, read_json
from tools.lib.schema_subset import validate
from tools.story_construction import visual_order_hash, validate_visual_execution


def valid_visual_order() -> dict[str, object]:
    order: dict[str, object] = {
        "schema_version": "1.0.0",
        "order_id": "VISUAL-ORDER-TEST-001",
        "order_authority": "VALIDATED_VISUAL_ORDER_PACKAGE",
        "task_type": "art",
        "semantic_composition_proof": "All required objects map to approved semantic refs.",
        "canon_refs": ["R2-CANON-TEST-001"],
        "dossier_refs": ["TEST-DOSSIER-001"],
        "must_objects": ["approved-object"],
        "forbidden_objects": ["unapproved-object"],
        "spatial_relations": ["approved-object:left-of:anchor"],
        "salience": ["approved-object:primary"],
        "occlusion": ["approved-object:unoccluded"],
        "state_continuity": ["state:TEST-001"],
        "reveal_refs": ["REVEAL-TEST-001"],
        "accessibility_equivalent": "Text alternative carries the same approved reveal.",
        "rights_provenance": ["FIRST_PARTY_ORIGINAL"],
        "capability_declaration": ["VISUAL_PRODUCTION_ONLY"],
        "proposed_fact_classes": [],
        "order_hash": "",
    }
    order["order_hash"] = visual_order_hash(order)
    return order


class VisualOrderGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = read_json(
            PROJECT_ROOT / "workflow/examples/m3-visual-order-task-packet.json"
        )
        self.order = valid_visual_order()

    def test_valid_visual_order_passes(self) -> None:
        schema = read_json(
            PROJECT_ROOT / "schemas/story-construction/visual-order-v1.schema.json"
        )
        self.assertEqual(validate(self.order, schema), [])
        self.assertEqual(
            validate_visual_execution(
                self.packet,
                self.order,
                ["workflow/returns/visual/RR-TASK-1002.json"],
            ),
            [],
        )

    def test_raw_art_request_is_rejected(self) -> None:
        errors = validate_visual_execution(
            self.packet, None, ["workflow/returns/visual/test.json"]
        )
        self.assertTrue(any("raw art request rejected" in error for error in errors), errors)

        raw = copy.deepcopy(self.order)
        raw["order_authority"] = "RAW_ART_REQUEST"
        raw["order_hash"] = visual_order_hash(raw)
        errors = validate_visual_execution(
            self.packet, raw, ["workflow/returns/visual/test.json"]
        )
        self.assertTrue(any("not production authority" in error for error in errors), errors)

    def test_grok_cannot_define_authoritative_facts(self) -> None:
        for fact_class in (
            "RULE_TRUTH",
            "STORY_TRUTH",
            "PUZZLE_ANSWER",
            "MECHANICAL_VALUE",
            "MAP_TOPOLOGY",
        ):
            with self.subTest(fact_class=fact_class):
                order = copy.deepcopy(self.order)
                order["proposed_fact_classes"] = [fact_class]
                order["order_hash"] = visual_order_hash(order)
                errors = validate_visual_execution(
                    self.packet, order, ["workflow/returns/visual/test.json"]
                )
                self.assertTrue(any("cannot define authoritative facts" in error for error in errors), errors)

    def test_visual_worker_cannot_write_runtime_or_authority(self) -> None:
        for target in ("game-package/assets/illegal.png", "governance/visual-order.json"):
            with self.subTest(target=target):
                errors = validate_visual_execution(self.packet, self.order, [target])
                self.assertTrue(any("authority/schema/runtime write" in error for error in errors), errors)

    def test_cross_modal_and_accessibility_fields_are_required(self) -> None:
        for field in (
            "semantic_composition_proof",
            "state_continuity",
            "reveal_refs",
            "accessibility_equivalent",
        ):
            with self.subTest(field=field):
                order = copy.deepcopy(self.order)
                order.pop(field)
                order["order_hash"] = visual_order_hash(order)
                errors = validate_visual_execution(
                    self.packet, order, ["workflow/returns/visual/test.json"]
                )
                self.assertTrue(any(field in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
