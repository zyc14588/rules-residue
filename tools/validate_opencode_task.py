from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import PROJECT_ROOT, read_json
from tools.lib.schema_subset import validate


REFUSAL_STATUS = "REFUSE / BLOCKED_NO_VALID_TASK_PACKET"
EXECUTABLE_STATUSES = {"PLANNED", "IN_PROGRESS"}
OPENCODE_AUTHORITY_FORBIDDEN_PATHS = (
    "TRPG_PLATFORM/**",
    "tools/**",
    "docs/**",
    "authoring/**",
    "governance/**",
    "workflow/**",
    ".codex/**",
    ".opencode/**",
    ".grok/**",
    ".github/**",
    "reports/**",
    "dist/**",
    "game-package/assets/**",
    "game-package/locales/**",
    "game-package/manifest.json",
    "game-package/modules/**",
    "game-package/package.lock.json",
    "game-package/rules/**",
    "game-package/schemas/**",
    "README.md",
    "AGENTS.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "NOTICE.md",
    "LICENSE*",
    "CHANGELOG.md",
    "LICENSE-PENDING.md",
)

# RR-D023 and docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md define a
# positive capability boundary.  Packet paths can narrow these scopes but can
# never create a new OpenCode scope.
OPENCODE_AUTHORITY_SCOPES = (
    ("game-package/scripts", frozenset({".lua"})),
    ("game-package/tests/fixtures", frozenset({".json", ".lua"})),
)


def _blocked(reason: str) -> str:
    return f"{REFUSAL_STATUS}: {reason}"


def _canonical_relative_path(
    raw_path: Any,
    label: str,
    allow_glob: bool,
) -> tuple[str | None, str | None]:
    if not isinstance(raw_path, str) or not raw_path:
        return None, _blocked(f"{label} must be a non-empty project-relative path")
    if "\x00" in raw_path or "\\" in raw_path:
        return None, _blocked(f"{label} must use POSIX separators: {raw_path!r}")
    if not allow_glob and any(character in raw_path for character in "*?["):
        return None, _blocked(f"{label} must name a concrete path: {raw_path!r}")
    if "[" in raw_path:
        return None, _blocked(f"{label} uses an unsupported glob expression: {raw_path!r}")

    directory_scope = allow_glob and raw_path.endswith("/")
    normalized_input = raw_path[:-1] if directory_scope else raw_path
    if not normalized_input or normalized_input.endswith("/"):
        return None, _blocked(f"{label} is not canonical: {raw_path!r}")

    relative = PurePosixPath(normalized_input)
    if (
        relative.is_absolute()
        or PureWindowsPath(normalized_input).is_absolute()
        or ".." in relative.parts
    ):
        return None, _blocked(f"{label} escapes the project root: {raw_path!r}")
    if (
        relative.as_posix() != normalized_input
        or not relative.parts
        or any(part in {"", "."} for part in relative.parts)
    ):
        return None, _blocked(f"{label} is not canonical: {raw_path!r}")
    canonical = relative.as_posix()
    if directory_scope:
        canonical += "/**"
    return canonical, None


def _authority_scope(path: str) -> tuple[str, frozenset[str]] | None:
    parts = PurePosixPath(path).parts
    for root, suffixes in OPENCODE_AUTHORITY_SCOPES:
        root_parts = PurePosixPath(root).parts
        if parts[: len(root_parts)] == root_parts:
            return root, suffixes
    return None


def _fixed_pattern_prefix(pattern: str) -> str:
    fixed_parts: list[str] = []
    for part in PurePosixPath(pattern).parts:
        if "*" in part or "?" in part:
            break
        fixed_parts.append(part)
    return PurePosixPath(*fixed_parts).as_posix()


def _resolved_within(candidate: Path, containment_root: Path) -> bool:
    try:
        resolved_candidate = candidate.resolve(strict=False)
        resolved_root = containment_root.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    return resolved_candidate.is_relative_to(resolved_root)


def _declared_path_authority_issue(
    pattern: str,
    label: str,
    project_root: Path,
) -> str | None:
    scope = _authority_scope(pattern)
    if scope is None:
        return _blocked(f"{label} is outside the OpenCode positive authority: {pattern}")

    root, allowed_suffixes = scope
    authority_root = project_root / root
    if not authority_root.is_dir() or not _resolved_within(authority_root, project_root):
        return _blocked(f"{label} does not name an existing safe authority root: {pattern}")

    fixed_prefix = _fixed_pattern_prefix(pattern)
    if not fixed_prefix or not _resolved_within(project_root / fixed_prefix, authority_root):
        return _blocked(f"{label} escapes its OpenCode authority root: {pattern}")

    final_name = PurePosixPath(pattern).name
    if not any(character in final_name for character in "*?"):
        candidate = project_root / pattern
        if not candidate.is_dir() and PurePosixPath(final_name).suffix not in allowed_suffixes:
            suffixes = ", ".join(sorted(allowed_suffixes))
            return _blocked(
                f"{label} is not an authorized script/fixture type ({suffixes}): {pattern}"
            )
    return None


def _target_authority_issue(target: str, label: str, project_root: Path) -> str | None:
    scope = _authority_scope(target)
    if scope is None:
        return _blocked(f"{label} is outside the OpenCode positive authority: {target}")

    root, allowed_suffixes = scope
    suffix = PurePosixPath(target).suffix
    if suffix not in allowed_suffixes:
        return _blocked(f"{label} is not an authorized Lua/fixture file: {target}")

    authority_root = project_root / root
    candidate = project_root.joinpath(*PurePosixPath(target).parts)
    if (
        not _resolved_within(authority_root, project_root)
        or not _resolved_within(candidate, project_root)
        or not _resolved_within(candidate, authority_root)
    ):
        return _blocked(f"{label} escapes its OpenCode authority root via path resolution: {target}")
    return None


def _matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")

    expression: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "*" and index + 1 < len(pattern) and pattern[index + 1] == "*":
            index += 2
            if index < len(pattern) and pattern[index] == "/":
                expression.append("(?:[^/]+/)*")
                index += 1
            else:
                expression.append(".*")
            continue
        if character == "*":
            expression.append("[^/]*")
        elif character == "?":
            expression.append("[^/]")
        else:
            expression.append(re.escape(character))
        index += 1
    expression.append("$")
    return re.fullmatch("".join(expression), path) is not None


def validate_opencode_task_packet(
    packet: Any | None,
    target_paths: list[str],
    schema: dict[str, Any] | None = None,
    project_root: Path = PROJECT_ROOT,
) -> list[str]:
    """Return refusal reasons unless a script packet authorizes every target."""

    if packet is None:
        return [_blocked("no Task Packet was provided")]
    if not isinstance(packet, dict):
        return [_blocked("Task Packet must be a JSON object")]

    if schema is None:
        schema = read_json(PROJECT_ROOT / "workflow" / "task-packet.schema.json")
    schema_issues = validate(packet, schema)
    if schema_issues:
        return [_blocked(f"Task Packet schema violation: {issue}") for issue in schema_issues]

    errors: list[str] = []
    if packet.get("owner") != "opencode":
        errors.append(_blocked('owner must equal "opencode"'))
    if packet.get("task_type") != "script":
        errors.append(_blocked('task_type must equal "script"'))
    if packet.get("status") not in EXECUTABLE_STATUSES:
        errors.append(_blocked("Task Packet status must be PLANNED or IN_PROGRESS"))

    allowed_paths = packet.get("allowed_paths")
    if not isinstance(allowed_paths, list) or not allowed_paths:
        errors.append(_blocked("allowed_paths must be non-empty"))
        return errors

    canonical_allowed: list[str] = []
    for index, pattern in enumerate(allowed_paths):
        canonical, issue = _canonical_relative_path(
            pattern,
            f"allowed_paths[{index}]",
            allow_glob=True,
        )
        if issue is not None:
            errors.append(issue)
        elif canonical is not None:
            authority_issue = _declared_path_authority_issue(
                canonical,
                f"allowed_paths[{index}]",
                project_root,
            )
            if authority_issue is not None:
                errors.append(authority_issue)
            else:
                candidate = project_root / canonical
                if "*" not in canonical and "?" not in canonical and candidate.is_dir():
                    canonical += "/**"
                canonical_allowed.append(canonical)

    forbidden_paths = packet.get("forbidden_paths", [])
    canonical_forbidden: list[str] = []
    for index, pattern in enumerate(forbidden_paths):
        canonical, issue = _canonical_relative_path(
            pattern,
            f"forbidden_paths[{index}]",
            allow_glob=True,
        )
        if issue is not None:
            errors.append(issue)
        elif canonical is not None:
            canonical_forbidden.append(canonical)

    if not target_paths:
        errors.append(_blocked("at least one current modification target is required"))
        return errors

    for index, raw_target in enumerate(target_paths):
        target, issue = _canonical_relative_path(
            raw_target,
            f"target[{index}]",
            allow_glob=False,
        )
        if issue is not None:
            errors.append(issue)
            continue
        assert target is not None

        if any(_matches(target, pattern) for pattern in OPENCODE_AUTHORITY_FORBIDDEN_PATHS):
            errors.append(_blocked(f"target is forbidden by RR-D023: {target}"))
            continue
        authority_issue = _target_authority_issue(
            target,
            f"target[{index}]",
            project_root,
        )
        if authority_issue is not None:
            errors.append(authority_issue)
            continue
        if any(_matches(target, pattern) for pattern in canonical_forbidden):
            errors.append(_blocked(f"target is forbidden by the Task Packet: {target}"))
            continue
        if not any(_matches(target, pattern) for pattern in canonical_allowed):
            errors.append(_blocked(f"target is outside allowed_paths: {target}"))

    return errors


def _read_packet(path: Path | None) -> tuple[Any | None, str | None]:
    if path is None:
        return None, None
    try:
        return read_json(path), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, _blocked(f"cannot read Task Packet {path}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an OpenCode script Task Packet and every intended modification target.",
    )
    parser.add_argument("--packet", type=Path, help="Codex-issued Task Packet JSON path")
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Intended project-relative modification target; repeat for every target",
    )
    args = parser.parse_args()

    packet, read_error = _read_packet(args.packet)
    errors = [read_error] if read_error is not None else validate_opencode_task_packet(packet, args.target)
    if errors:
        for error in errors:
            print(error)
        return 1

    print("OPENCODE_TASK_PACKET: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
