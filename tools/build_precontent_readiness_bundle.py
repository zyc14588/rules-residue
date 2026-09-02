from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import PROJECT_ROOT
from tools.validate_precontent_readiness import (
    MANIFEST_PATH,
    RECEIPT_PATH,
    derive_framework_documents,
    write_framework_documents,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic B002 framework manifest and pending receipt")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--write", action="store_true", help="write canonical tracked outputs")
    parser.add_argument("--check", action="store_true", help="require tracked outputs to match derivation")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    derived = write_framework_documents(root) if args.write else derive_framework_documents(root)
    if args.check:
        if (root / MANIFEST_PATH).read_bytes() != derived["manifest_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: manifest drift")
            return 1
        if (root / RECEIPT_PATH).read_bytes() != derived["receipt_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: receipt drift")
            return 1
    print("PRECONTENT_FRAMEWORK_BUILD: PASS")
    print(f"manifest={MANIFEST_PATH.as_posix()}")
    print(f"manifest_sha256={hashlib.sha256(derived['manifest_bytes']).hexdigest()}")
    print(f"framework_merkle_root={derived['framework_merkle_root']}")
    print(f"receipt={RECEIPT_PATH.as_posix()}")
    print(f"receipt_sha256={hashlib.sha256(derived['receipt_bytes']).hexdigest()}")
    print(f"receipt_payload_hash={derived['receipt']['payload_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
