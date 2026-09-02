from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import PROJECT_ROOT
from tools.story_construction import canonical_json_bytes
from tools.validate_precontent_readiness import validate_provider_run_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize an already captured local Harness run receipt; never launches Harness")
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)
    receipt = json.loads(args.input_json.read_text(encoding="utf-8"))
    schema = json.loads((PROJECT_ROOT / "schemas/story-construction/provider-run-receipt-v1.schema.json").read_text(encoding="utf-8"))
    errors = validate_provider_run_receipt(receipt, schema)
    if errors:
        print("HARNESS_RUN_RECEIPT_EXPORT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    output = canonical_json_bytes(receipt)
    if args.output_json is None:
        sys.stdout.buffer.write(output)
    else:
        args.output_json.write_bytes(output)
        print(f"HARNESS_RUN_RECEIPT_EXPORT: PASS output={args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
