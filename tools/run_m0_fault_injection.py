from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import PROJECT_ROOT
from tools.story_construction import canonical_json_bytes, canonical_sha256
from tools.validate_precontent_readiness import validate_test_boundary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one controlled M0 fault against an isolated local fixture copy")
    parser.add_argument("--input-copy", type=Path, required=True)
    parser.add_argument("--fault-id", choices=("TEST-FAULT-PROMOTION-001",), required=True)
    parser.add_argument("--output-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    source = args.input_copy.resolve()
    try:
        source.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        pass
    else:
        print("M0_FAULT_INJECTION: FAIL: input must be an isolated copy outside the repository")
        return 1
    document = json.loads(source.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(document)
    mutated["canon"] = True
    rejected = bool(validate_test_boundary(mutated, "fault-mutated artifact"))
    payload = {
        "receipt_id": "TEST-FAULT-RECEIPT-PROMOTION-001",
        "profile_id": "TEST-LOCAL-STATIC-VALIDATOR-PROFILE-001",
        "namespace_prefix": "TEST-", "canon": False, "release_eligible": False,
        "promotion_allowed": False, "disposition": "TEST_EVIDENCE_ONLY",
        "fault_id": args.fault_id, "isolated_copy": True, "provider_called": False,
        "fault_injected": "canon=true", "expected_gate": "TEST_NON_PROMOTION",
        "observed_rejection": rejected, "output_accepted": False,
    }
    receipt = {
        "schema_version": "rules-residue.story-construction.fault-injection-receipt/1.0.0",
        **payload,
        "receipt_payload_hash": canonical_sha256({"schema_version": "rules-residue.story-construction.fault-injection-receipt/1.0.0", **payload}),
    }
    args.output_receipt.write_bytes(canonical_json_bytes(receipt))
    if not rejected:
        print("M0_FAULT_INJECTION: FAIL: mutation was not rejected")
        return 1
    print("M0_FAULT_INJECTION: PASS")
    print("provider_request_count=0")
    print("story_m0_execution_count=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
