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
    R4_MANIFEST_PATH,
    R4_RECEIPT_PATH,
    RECEIPT_PATH,
    derive_r4_documents,
    write_r4_documents,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic M3-B003 P0-B additive R4 manifest and receipt")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--write", action="store_true", help="write canonical tracked outputs")
    parser.add_argument("--check", action="store_true", help="require tracked outputs to match derivation")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    immutable_before = {
        path: (root / path).read_bytes()
        for path in (MANIFEST_PATH, RECEIPT_PATH, R2_MANIFEST_PATH, FINAL_RECEIPT_PATH, R3_MANIFEST_PATH, R3_RECEIPT_PATH)
    }
    derived = write_r4_documents(root) if args.write else derive_r4_documents(root)
    if any((root / path).read_bytes() != content for path, content in immutable_before.items()):
        print("PRECONTENT_FRAMEWORK_BUILD: FAIL: immutable R1/R2/R3 predecessor changed")
        return 1
    if args.check:
        if (root / R4_MANIFEST_PATH).read_bytes() != derived["manifest_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: R4 manifest drift")
            return 1
        if (root / R4_RECEIPT_PATH).read_bytes() != derived["receipt_bytes"]:
            print("PRECONTENT_FRAMEWORK_BUILD: FAIL: R4 receipt drift")
            return 1
    print("PRECONTENT_FRAMEWORK_BUILD: PASS")
    print(f"immutable_manifest={MANIFEST_PATH.as_posix()}")
    print(f"immutable_pending_receipt={RECEIPT_PATH.as_posix()}")
    print(f"immutable_r2_manifest={R2_MANIFEST_PATH.as_posix()}")
    print(f"immutable_r1_final_receipt={FINAL_RECEIPT_PATH.as_posix()}")
    print(f"immutable_r3_manifest={R3_MANIFEST_PATH.as_posix()}")
    print(f"immutable_r3_receipt={R3_RECEIPT_PATH.as_posix()}")
    print(f"manifest={R4_MANIFEST_PATH.as_posix()}")
    print(f"manifest_sha256={derived['manifest_file_sha256']}")
    print(f"framework_merkle_root={derived['framework_merkle_root']}")
    print(f"semantic_path_content_record_set_hash={derived['semantic_path_content_record_set_hash']}")
    print(f"receipt={R4_RECEIPT_PATH.as_posix()}")
    print(f"receipt_sha256={hashlib.sha256(derived['receipt_bytes']).hexdigest()}")
    print(f"receipt_payload_hash={derived['receipt_payload_hash']}")
    print("transition=75_unchanged_old+6_changed_old+7_new=88_total")
    print(f"original_schema_set_hash={derived['schemas']['original_set_hash']}")
    print(f"preserved_activation_v1_schema_set_hash={derived['schemas']['preserved_activation_v1_set_hash']}")
    print(f"r3_repair_schema_set_hash={derived['schemas']['r3_repair_set_hash']}")
    print(f"predecessor_schema_set_hash={derived['schemas']['predecessor_set_hash']}")
    print(f"r4_schema_set_hash={derived['schemas']['r4_set_hash']}")
    print(f"combined_schema_set_hash={derived['schemas']['combined_set_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
