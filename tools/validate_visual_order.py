from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import PROJECT_ROOT, read_json
from tools.lib.schema_subset import validate
from tools.story_construction import validate_visual_execution
from tools.validate_precontent_readiness import validate_test_boundary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Grok Task Packet and Visual Order Package")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--order", type=Path, required=True)
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)
    try:
        packet_document = read_json(args.packet)
        order = read_json(args.order)
        packet_schema = read_json(args.project_root / "workflow/task-packet.schema.json")
        is_precontent = isinstance(order, dict) and order.get("schema_version") == "2.0.0"
        order_schema_name = "visual-order-v2.schema.json" if is_precontent else "visual-order-v1.schema.json"
        order_schema = read_json(args.project_root / "schemas/story-construction" / order_schema_name)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"VISUAL_ORDER_GATE: FAIL: {exc}")
        return 1
    if isinstance(packet_document, dict) and "task_packet" in packet_document:
        packet = packet_document.get("task_packet")
        errors = validate_test_boundary(packet_document, "Task Packet envelope")
        if packet_document.get("execution_authorized_in_m3_b002") is not False:
            errors.append("Task Packet envelope must preserve M3-B002 execution=false")
    else:
        packet = packet_document
        errors = []
    errors.extend(f"Task Packet schema: {issue}" for issue in validate(packet, packet_schema))
    errors.extend(f"Visual Order schema: {issue}" for issue in validate(order, order_schema))
    errors.extend(validate_visual_execution(packet, order, args.target))
    if is_precontent:
        errors.extend(validate_test_boundary(order, "Pre-Content Visual Order"))
        if order.get("provider_execution_authorized") is not False:
            errors.append("M3-B002 Visual Order cannot authorize Provider execution")
        if order.get("raw_request") is not False:
            errors.append("raw Grok request bypass rejected")
    if errors:
        print("VISUAL_ORDER_GATE: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VISUAL_ORDER_GATE: PASS")
    if is_precontent:
        print("provider_request_count=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
