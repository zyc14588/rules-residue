from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import GAME_PACKAGE_ROOT, compute_lock_document, write_json


def main() -> int:
    lock_path = GAME_PACKAGE_ROOT / "package.lock.json"
    document = compute_lock_document()
    write_json(lock_path, document)
    print(f"updated {lock_path.relative_to(GAME_PACKAGE_ROOT.parent)}")
    print(f"runtime files: {len(document['files'])}")
    print(f"runtime tree sha256: {document['runtime_tree_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
