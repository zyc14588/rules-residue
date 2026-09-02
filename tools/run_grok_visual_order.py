from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import PROJECT_ROOT
from tools.lib.schema_subset import validate
from tools.story_construction import validate_visual_execution
from tools.validate_precontent_readiness import validate_b003_authorization


def _read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or dry-run one synthetic Grok Visual Order")
    parser.add_argument("--order", type=Path, required=True)
    parser.add_argument("--task-packet", type=Path, required=True)
    parser.add_argument("--mode", choices=("validate", "dry-run", "execute"), default="validate")
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args(argv)
    order = _read(args.order)
    envelope = _read(args.task_packet)
    packet = envelope.get("task_packet") if isinstance(envelope, dict) else None
    schema = _read(PROJECT_ROOT / "schemas/story-construction/visual-order-v2.schema.json")
    errors = list(validate(order, schema))
    errors.extend(validate_visual_execution(packet, order, [f"workflow/returns/visual/{order.get('order_id', 'INVALID')}/candidate.json"]))
    if not isinstance(envelope, dict) or envelope.get("execution_authorized_in_m3_b002") is not False:
        errors.append("task envelope does not preserve M3-B002 execution=false")
    if args.mode == "execute":
        if args.authorization is None:
            errors.append("BLOCKED_NO_OWNER_APPROVED_M3_B003_PROVIDER_AUTHORIZATION")
        else:
            errors.extend(validate_b003_authorization(_read(args.authorization)))
            errors.append("BLOCKED_PROVIDER_ADAPTER_NOT_BOUND_BY_M3_B003")
    if errors:
        print("GROK_VISUAL_ORDER: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("GROK_VISUAL_ORDER: PASS")
    print(f"mode={args.mode}")
    print("provider_request_count=0")
    print("network_execution=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
