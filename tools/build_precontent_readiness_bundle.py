from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import PROJECT_ROOT
from tools.validate_precontent_readiness import (
    FINAL_RECEIPT_PATH,
    MANIFEST_PATH,
    R2_MANIFEST_PATH,
    RECEIPT_PATH,
    derive_activation_documents,
    write_activation_documents,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic B002 R2 activation manifest and final inner receipt")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--write", action="store_true", help="write canonical tracked outputs")
    parser.add_argument("--check", action="store_true", help="require tracked outputs to match derivation")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    derived = write_activation_documents(root) if args.write else derive_activation_documents(root)
    if args.check:
        if (root / R2_MANIFEST_PATH).read_bytes() != derived["manifest_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: R2 manifest drift")
            return 1
        if (root / FINAL_RECEIPT_PATH).read_bytes() != derived["receipt_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: final receipt drift")
            return 1
    print("PRECONTENT_FRAMEWORK_BUILD: PASS")
    print(f"immutable_manifest={MANIFEST_PATH.as_posix()}")
    print(f"immutable_pending_receipt={RECEIPT_PATH.as_posix()}")
    print(f"manifest={R2_MANIFEST_PATH.as_posix()}")
    print(f"manifest_sha256={derived['manifest_file_sha256']}")
    print(f"framework_merkle_root={derived['framework_merkle_root']}")
    print(f"receipt={FINAL_RECEIPT_PATH.as_posix()}")
    print(f"receipt_sha256={hashlib.sha256(derived['receipt_bytes']).hexdigest()}")
    print(f"receipt_payload_hash={derived['receipt_payload_hash']}")
    print("transition=61_unchanged_old+7_changed_old+8_new=76_total")
    print(f"activation_schema_set_hash={derived['schemas']['activation_set_hash']}")
    print(f"combined_schema_set_hash={derived['schemas']['combined_set_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
