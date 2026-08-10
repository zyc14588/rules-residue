from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GAME_PACKAGE_ROOT = PROJECT_ROOT / "game-package"
DIST_ROOT = PROJECT_ROOT / "dist"
REPORT_ROOT = PROJECT_ROOT / "reports" / "generated"

RUNTIME_TOP_LEVEL = {
    "manifest.json",
    "rules",
    "schemas",
    "scripts",
    "modules",
    "locales",
    "assets",
}

RUNTIME_EXCLUDED_NAMES = {
    ".gitkeep",
    "README.md",
    "package.lock.json",
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_runtime_file(path: Path) -> bool:
    relative = path.relative_to(GAME_PACKAGE_ROOT)
    if not relative.parts:
        return False
    if relative.parts[0] not in RUNTIME_TOP_LEVEL:
        return False
    if "tests" in relative.parts:
        return False
    if path.name in RUNTIME_EXCLUDED_NAMES:
        return False
    if any(part.startswith(".") for part in relative.parts):
        return False
    return path.is_file()


def runtime_files() -> list[Path]:
    files = [path for path in GAME_PACKAGE_ROOT.rglob("*") if is_runtime_file(path)]
    return sorted(files, key=lambda path: path.relative_to(GAME_PACKAGE_ROOT).as_posix())


def runtime_relative_paths() -> list[str]:
    return [path.relative_to(GAME_PACKAGE_ROOT).as_posix() for path in runtime_files()]


def compute_lock_document() -> dict[str, Any]:
    manifest = read_json(GAME_PACKAGE_ROOT / "manifest.json")
    entries: list[dict[str, Any]] = []
    for path in runtime_files():
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(GAME_PACKAGE_ROOT).as_posix(),
                "size": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    tree_input = "".join(
        f"{entry['path']}\0{entry['size']}\0{entry['sha256']}\n" for entry in entries
    ).encode("utf-8")
    return {
        "schema_version": "rules-residue.package-lock/1.0",
        "package_id": manifest["id"],
        "package_version": manifest["version"],
        "algorithm": "sha256",
        "runtime_tree_sha256": sha256_bytes(tree_input),
        "files": entries,
    }


def find_duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)
