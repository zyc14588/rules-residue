from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import zipfile

from tools.lib.common import (
    DIST_ROOT,
    GAME_PACKAGE_ROOT,
    PROJECT_ROOT,
    read_json,
    runtime_files,
    sha256_file,
)

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def build_package(
    output: Path,
    validate_first: bool = True,
    *,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> str:
    if validate_first:
        from tools.validate_project import collect_errors, validate_module_registry

        if game_package_root.resolve() == GAME_PACKAGE_ROOT.resolve():
            errors = collect_errors()
        else:
            manifest = read_json(game_package_root / "manifest.json")
            errors = validate_module_registry(manifest, game_package_root)
        if errors:
            joined = "\n".join(f"- {error}" for error in errors)
            raise RuntimeError(f"project validation failed:\n{joined}")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    sources = runtime_files(game_package_root) + [game_package_root / "package.lock.json"]
    sources = sorted(sources, key=lambda path: path.relative_to(game_package_root).as_posix())

    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for source in sources:
            relative = source.relative_to(game_package_root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.flag_bits |= 0x800
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    digest = sha256_file(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="utf-8", newline="\n"
    )
    return digest


def default_output() -> Path:
    manifest = read_json(GAME_PACKAGE_ROOT / "manifest.json")
    return DIST_ROOT / f"{manifest['id']}-{manifest['version']}.trpgpkg"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Rules Residue Game Package")
    parser.add_argument("--output", type=Path, default=default_output())
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    digest = build_package(output, validate_first=not args.skip_validation)
    print(f"built: {output}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
