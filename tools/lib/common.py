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

NON_RUNTIME_MODULE_MARKER = ".non-runtime-module"


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


def is_non_runtime_module_path(
    path: Path,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> bool:
    modules_root = game_package_root / "modules"
    try:
        path.relative_to(modules_root)
    except ValueError:
        return False

    current = path.parent
    while current != modules_root:
        if (current / NON_RUNTIME_MODULE_MARKER).is_file():
            return True
        if current == game_package_root or current.parent == current:
            break
        current = current.parent
    return False


def _has_runtime_path_shape(path: Path, game_package_root: Path) -> bool:
    try:
        relative = path.relative_to(game_package_root)
    except ValueError:
        return False
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
    if is_non_runtime_module_path(path, game_package_root):
        return False
    return True


def is_runtime_file(path: Path, game_package_root: Path = GAME_PACKAGE_ROOT) -> bool:
    if not _has_runtime_path_shape(path, game_package_root):
        return False
    try:
        resolved_root = game_package_root.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    if not resolved_path.is_relative_to(resolved_root):
        return False
    if not _has_runtime_path_shape(resolved_path, resolved_root):
        return False
    return path.is_file()


def runtime_files(game_package_root: Path = GAME_PACKAGE_ROOT) -> list[Path]:
    files = [
        path
        for path in game_package_root.rglob("*")
        if is_runtime_file(path, game_package_root)
    ]
    return sorted(files, key=lambda path: path.relative_to(game_package_root).as_posix())


def runtime_relative_paths(game_package_root: Path = GAME_PACKAGE_ROOT) -> list[str]:
    return [
        path.relative_to(game_package_root).as_posix()
        for path in runtime_files(game_package_root)
    ]


def compute_lock_document(game_package_root: Path = GAME_PACKAGE_ROOT) -> dict[str, Any]:
    manifest = read_json(game_package_root / "manifest.json")
    entries: list[dict[str, Any]] = []
    for path in runtime_files(game_package_root):
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(game_package_root).as_posix(),
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
