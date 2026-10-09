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


def _quarantine_encode(
    output: Path,
    validate_first: bool = True,
    *,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> str:
    """Encode structural test/quarantine bytes only; never grants admission."""
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


def build_package(output: Path, validate_first: bool = True, *,
                  game_package_root: Path = GAME_PACKAGE_ROOT,
                  execution_id: str | None = None, store=None) -> str:
    """Production boundary. Skip-validation and alternate roots grant no bypass."""
    from tools.content_safety_control import ControlStore
    from tools.content_safety_consumers import admit
    from tools.lib.content_safety_evidence import SafetyError, require, sha, durable_write
    require(execution_id is not None, 'production build requires a control-issued operation and INPUT/OUTPUT evidence')
    control = store or ControlStore.production()
    control.assert_production()
    operation = control.operation(execution_id)
    expected = 'full-project' if game_package_root.resolve() == GAME_PACKAGE_ROOT.resolve() else 'module-registry'
    require(operation['binding']['scope'] == {'consumer':'build','validation':expected}, 'build validation scope mismatch')
    result = admit('build',game_package_root,execution_id,store=control)
    # Exporting even a historical result is new consumption: require current
    # authorization, unlike the read-only historical replay API.
    control.replay(execution_id,current=True)
    expected_sha = result['manifest']['details']['archive_sha256']
    artifact = control.directory/'work'/execution_id/'archive.trpgpkg'
    require(artifact.is_file() and not artifact.is_symlink() and artifact.stat().st_nlink == 1, 'committed archive missing/nonregular')
    data = artifact.read_bytes(); require(sha(data) == expected_sha, 'committed archive bytes changed')
    if output.exists():
        require(not output.is_symlink() and output.read_bytes() == data, 'output exists with different bytes')
    else: durable_write(output,data)
    digest_path = output.with_suffix(output.suffix+'.sha256')
    digest_bytes = f'{expected_sha}  {output.name}\n'.encode()
    if digest_path.exists(): require(not digest_path.is_symlink() and digest_path.read_bytes()==digest_bytes, 'digest output conflict')
    else: durable_write(digest_path,digest_bytes)
    return expected_sha


def default_output() -> Path:
    manifest = read_json(GAME_PACKAGE_ROOT / "manifest.json")
    return DIST_ROOT / f"{manifest['id']}-{manifest['version']}.trpgpkg"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Rules Residue Game Package")
    parser.add_argument("--output", type=Path, default=default_output())
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--execution", help="control-issued build operation UUID")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    try:
        digest = build_package(output, validate_first=not args.skip_validation, execution_id=args.execution)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"CONTENT_SAFETY_BUILD: DENY: {exc}")
        return 1
    print(f"built: {output}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
