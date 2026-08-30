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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Grok Task Packet and Visual Order Package")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--order", type=Path, required=True)
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)
    try:
        packet = read_json(args.packet)
        order = read_json(args.order)
        packet_schema = read_json(args.project_root / "workflow/task-packet.schema.json")
        order_schema = read_json(args.project_root / "schemas/story-construction/visual-order-v1.schema.json")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"VISUAL_ORDER_GATE: FAIL: {exc}")
        return 1
    errors = [f"Task Packet schema: {issue}" for issue in validate(packet, packet_schema)]
    errors.extend(f"Visual Order schema: {issue}" for issue in validate(order, order_schema))
    errors.extend(validate_visual_execution(packet, order, args.target))
    if errors:
        print("VISUAL_ORDER_GATE: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VISUAL_ORDER_GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
