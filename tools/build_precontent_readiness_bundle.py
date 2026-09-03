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
    R3_MANIFEST_PATH,
    R3_RECEIPT_PATH,
    RECEIPT_PATH,
    derive_repair_documents,
    write_repair_documents,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic B002 additive R3 repair manifest and receipt")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--write", action="store_true", help="write canonical tracked outputs")
    parser.add_argument("--check", action="store_true", help="require tracked outputs to match derivation")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    derived = write_repair_documents(root) if args.write else derive_repair_documents(root)
    if args.check:
        if (root / R3_MANIFEST_PATH).read_bytes() != derived["manifest_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: R3 manifest drift")
            return 1
        if (root / R3_RECEIPT_PATH).read_bytes() != derived["receipt_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: R3 receipt drift")
            return 1
    print("PRECONTENT_FRAMEWORK_BUILD: PASS")
    print(f"immutable_manifest={MANIFEST_PATH.as_posix()}")
    print(f"immutable_pending_receipt={RECEIPT_PATH.as_posix()}")
    print(f"immutable_r2_manifest={R2_MANIFEST_PATH.as_posix()}")
    print(f"immutable_r1_final_receipt={FINAL_RECEIPT_PATH.as_posix()}")
    print(f"manifest={R3_MANIFEST_PATH.as_posix()}")
    print(f"manifest_sha256={derived['manifest_file_sha256']}")
    print(f"framework_merkle_root={derived['framework_merkle_root']}")
    print(f"semantic_path_content_record_set_hash={derived['semantic_path_content_record_set_hash']}")
    print(f"receipt={R3_RECEIPT_PATH.as_posix()}")
    print(f"receipt_sha256={hashlib.sha256(derived['receipt_bytes']).hexdigest()}")
    print(f"receipt_payload_hash={derived['receipt_payload_hash']}")
    print("transition=70_unchanged_old+6_changed_old+5_new=81_total")
    print(f"original_schema_set_hash={derived['schemas']['original_set_hash']}")
    print(f"preserved_activation_v1_schema_set_hash={derived['schemas']['preserved_activation_v1_set_hash']}")
    print(f"repair_schema_set_hash={derived['schemas']['repair_set_hash']}")
    print(f"combined_schema_set_hash={derived['schemas']['combined_set_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
