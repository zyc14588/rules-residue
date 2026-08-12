from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"
SOFT_LIMIT = 0.55
HARD_LIMIT = 0.70
MODES = {"PLAN", "IMPLEMENT", "ACCEPT", "REPAIR"}
CONTEXT_STATUSES = {"OK", "SOFT_REDUCED", "HARD_BLOCKED"}

ROUTE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
MILESTONE_PATTERN = re.compile(r"^M[0-9]+$")
BATCH_PATTERN = re.compile(r"^M[0-9]+-B[0-9]{3,}$")
SECTION_ID_PATTERN = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")
HEX_40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SECTION_MARKER_PATTERN = re.compile(
    r"^<!-- SECTION-ID: ([A-Z0-9]+(?:-[A-Z0-9]+)+) -->[ \t]*(?:\r?\n|$)",
    re.MULTILINE,
)
GLOB_CHARACTERS = frozenset("*?[]{}")

REQUEST_KEYS = {
    "schema_version",
    "route_id",
    "mode",
    "milestone",
    "batch_id",
    "capacity_bytes",
    "documents",
    "forbidden_bulk_reads",
}
REQUEST_DOCUMENT_KEYS = {
    "path",
    "required_sections",
    "optional_sections",
    "reason",
}
MAP_KEYS = {
    "schema_version",
    "route_id",
    "mode",
    "milestone",
    "batch_id",
    "source_commit",
    "source_tree",
    "generated_at",
    "context_budget",
    "documents",
    "forbidden_bulk_reads",
    "binding_digest",
}
CONTEXT_KEYS = {
    "capacity_bytes",
    "planned_bytes",
    "ratio",
    "soft_limit",
    "hard_limit",
    "status",
}
MAP_DOCUMENT_KEYS = {"path", "sha256", "sections", "reason"}


class RouteError(Exception):
    """A deterministic route rejection with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _reject(code: str, message: str) -> None:
    raise RouteError(code, message)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        _reject(
            "INVALID_STRUCTURE",
            f"{label} keys differ; missing={missing}, extra={extra}",
        )


def _check_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _reject("INVALID_STRUCTURE", f"{label} must be a non-empty string")
    return value


def _check_string_list(
    value: Any,
    label: str,
    *,
    allow_empty: bool,
    pattern: re.Pattern[str] | None = None,
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "an array" if allow_empty else "a non-empty array"
        _reject("INVALID_STRUCTURE", f"{label} must be {qualifier}")
    items: list[str] = []
    for index, item in enumerate(value):
        item = _check_nonempty_string(item, f"{label}[{index}]")
        if pattern is not None and pattern.fullmatch(item) is None:
            _reject("INVALID_STRUCTURE", f"{label}[{index}] has invalid format: {item!r}")
        items.append(item)
    if len(items) != len(set(items)):
        _reject("DUPLICATE_SECTION" if pattern is SECTION_ID_PATTERN else "INVALID_STRUCTURE", f"{label} contains duplicates")
    return items


def _validate_identity(route_id: Any, mode: Any, milestone: Any, batch_id: Any) -> None:
    if (
        not isinstance(route_id, str)
        or len(route_id) > 128
        or ROUTE_ID_PATTERN.fullmatch(route_id) is None
    ):
        _reject("INVALID_STRUCTURE", f"invalid route_id: {route_id!r}")
    if not isinstance(mode, str) or mode not in MODES:
        _reject("INVALID_STRUCTURE", f"invalid mode: {mode!r}")
    if not isinstance(milestone, str) or MILESTONE_PATTERN.fullmatch(milestone) is None:
        _reject("INVALID_STRUCTURE", f"invalid milestone: {milestone!r}")
    if not isinstance(batch_id, str) or BATCH_PATTERN.fullmatch(batch_id) is None:
        _reject("INVALID_STRUCTURE", f"invalid batch_id: {batch_id!r}")
    if not batch_id.startswith(f"{milestone}-"):
        _reject("INVALID_STRUCTURE", "batch_id must belong to milestone")


def validate_request(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        _reject("INVALID_STRUCTURE", "route request must be an object")
    _check_exact_keys(request, REQUEST_KEYS, "route request")
    if request["schema_version"] != SCHEMA_VERSION:
        _reject("INVALID_STRUCTURE", "route request schema_version must be 1.0")
    _validate_identity(
        request["route_id"],
        request["mode"],
        request["milestone"],
        request["batch_id"],
    )
    if not _is_int(request["capacity_bytes"]) or request["capacity_bytes"] < 1:
        _reject("INVALID_STRUCTURE", "capacity_bytes must be a positive integer")
    documents = request["documents"]
    if not isinstance(documents, list) or not documents:
        _reject("INVALID_STRUCTURE", "documents must be a non-empty array")
    seen_paths: set[str] = set()
    seen_requested_sections: set[str] = set()
    requested_count = 0
    for index, document in enumerate(documents):
        label = f"documents[{index}]"
        if not isinstance(document, dict):
            _reject("INVALID_STRUCTURE", f"{label} must be an object")
        _check_exact_keys(document, REQUEST_DOCUMENT_KEYS, label)
        path = _check_nonempty_string(document["path"], f"{label}.path")
        if path in seen_paths:
            _reject("DUPLICATE_DOCUMENT", f"duplicate document path: {path}")
        seen_paths.add(path)
        required = _check_string_list(
            document["required_sections"],
            f"{label}.required_sections",
            allow_empty=True,
            pattern=SECTION_ID_PATTERN,
        )
        optional = _check_string_list(
            document["optional_sections"],
            f"{label}.optional_sections",
            allow_empty=True,
            pattern=SECTION_ID_PATTERN,
        )
        if set(required) & set(optional):
            _reject("DUPLICATE_SECTION", f"{label} requests a section as both required and optional")
        for section_id in required + optional:
            if section_id in seen_requested_sections:
                _reject("DUPLICATE_SECTION", f"requested Section ID is duplicated: {section_id}")
            seen_requested_sections.add(section_id)
        requested_count += len(required) + len(optional)
        _check_nonempty_string(document["reason"], f"{label}.reason")
    if requested_count == 0:
        _reject("INVALID_STRUCTURE", "route request must select at least one Section ID")
    _check_string_list(
        request["forbidden_bulk_reads"],
        "forbidden_bulk_reads",
        allow_empty=True,
    )
    return request


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _reject("INVALID_JSON", f"cannot read {label} {path}: {exc}")


def _git_value(repo_root: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", revision],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        _reject("GIT_BINDING_ERROR", f"git rev-parse {revision} failed: {detail}")
    value = result.stdout.strip()
    if HEX_40_PATTERN.fullmatch(value) is None:
        _reject("GIT_BINDING_ERROR", f"git rev-parse {revision} returned an invalid object ID")
    return value


def current_git_binding(repo_root: Path) -> tuple[str, str]:
    root = repo_root.resolve()
    if not root.is_dir():
        _reject("GIT_BINDING_ERROR", f"repository root is not a directory: {repo_root}")
    return _git_value(root, "HEAD"), _git_value(root, "HEAD^{tree}")


def _normalise_allowed_roots(allow_roots: Iterable[Path | str]) -> tuple[Path, ...]:
    normalised: list[Path] = []
    for raw_root in allow_roots:
        raw_text = str(raw_root)
        path = Path(raw_text)
        if not path.is_absolute():
            _reject("INVALID_ALLOW_ROOT", f"allow-root must be absolute: {raw_text}")
        if ".." in PurePosixPath(raw_text).parts or any(char in raw_text for char in GLOB_CHARACTERS):
            _reject("INVALID_ALLOW_ROOT", f"allow-root is not a literal canonical path: {raw_text}")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            _reject("INVALID_ALLOW_ROOT", f"cannot resolve allow-root {raw_text}: {exc}")
        if not resolved.is_dir():
            _reject("INVALID_ALLOW_ROOT", f"allow-root is not a directory: {raw_text}")
        if resolved not in normalised:
            normalised.append(resolved)
    return tuple(normalised)


def resolve_document_path(
    raw_path: str,
    repo_root: Path,
    allow_roots: Sequence[Path],
) -> tuple[str, Path]:
    if not isinstance(raw_path, str) or not raw_path:
        _reject("INVALID_DOCUMENT_PATH", "document path must be a non-empty string")
    if "\\" in raw_path or any(character in raw_path for character in GLOB_CHARACTERS):
        _reject("BULK_PATH_REJECTED", f"document path must be one literal file: {raw_path}")
    pure_path = PurePosixPath(raw_path)
    if ".." in pure_path.parts or any(part in {"", "."} for part in pure_path.parts):
        _reject("PATH_ESCAPE_REJECTED", f"document path is not canonical: {raw_path}")
    if pure_path.as_posix() != raw_path:
        _reject("INVALID_DOCUMENT_PATH", f"document path must use canonical POSIX syntax: {raw_path}")

    root = repo_root.resolve()
    if pure_path.is_absolute():
        candidate = Path(raw_path)
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            _reject("MISSING_DOCUMENT", f"cannot resolve external document {raw_path}: {exc}")
        approved = next((item for item in allow_roots if resolved.is_relative_to(item)), None)
        if approved is None:
            _reject("UNAPPROVED_EXTERNAL_PATH", f"external document is outside approved roots: {raw_path}")
        stored_path = raw_path
    else:
        candidate = root.joinpath(*pure_path.parts)
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            _reject("MISSING_DOCUMENT", f"cannot resolve repository document {raw_path}: {exc}")
        if not resolved.is_relative_to(root):
            _reject("PATH_ESCAPE_REJECTED", f"repository document escapes through a symlink: {raw_path}")
        stored_path = raw_path
    if not resolved.is_file():
        _reject("DIRECTORY_PATH_REJECTED", f"document path is not a regular file: {raw_path}")
    return stored_path, resolved


def _extract_sections(data: bytes, path_label: str) -> tuple[dict[str, bytes], list[str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _reject("INVALID_DOCUMENT_ENCODING", f"document is not UTF-8: {path_label}: {exc}")
    matches = list(SECTION_MARKER_PATTERN.finditer(text))
    sections: dict[str, bytes] = {}
    order: list[str] = []
    for index, match in enumerate(matches):
        section_id = match.group(1)
        if section_id in sections:
            _reject("DUPLICATE_SECTION", f"duplicate Section ID {section_id} in {path_label}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[section_id] = text[match.start() : end].encode("utf-8")
        order.append(section_id)
    return sections, order


def _read_routed_documents(
    documents: list[dict[str, Any]],
    repo_root: Path,
    allow_roots: Sequence[Path],
) -> list[dict[str, Any]]:
    routed: list[dict[str, Any]] = []
    globally_seen: dict[str, str] = {}
    for document in documents:
        stored_path, resolved_path = resolve_document_path(document["path"], repo_root, allow_roots)
        try:
            data = resolved_path.read_bytes()
        except OSError as exc:
            _reject("MISSING_DOCUMENT", f"cannot read document {stored_path}: {exc}")
        sections, marker_order = _extract_sections(data, stored_path)
        for section_id in marker_order:
            previous = globally_seen.get(section_id)
            if previous is not None:
                _reject(
                    "DUPLICATE_SECTION",
                    f"Section ID {section_id} occurs in both {previous} and {stored_path}",
                )
            globally_seen[section_id] = stored_path
        requested = document.get("required_sections", []) + document.get("optional_sections", [])
        if "sections" in document:
            requested = document["sections"]
        for section_id in requested:
            if section_id not in sections:
                _reject("MISSING_SECTION", f"Section ID {section_id} is missing from {stored_path}")
        routed.append(
            {
                "path": stored_path,
                "resolved_path": resolved_path,
                "data": data,
                "sha256": hashlib.sha256(data).hexdigest(),
                "section_bytes": sections,
                "reason": document["reason"],
            }
        )
    return routed


def _planned_bytes(routed: list[dict[str, Any]], selections: list[list[str]]) -> int:
    return sum(
        len(routed[document_index]["section_bytes"][section_id])
        for document_index, section_ids in enumerate(selections)
        for section_id in section_ids
    )


def binding_payload(reading_map: dict[str, Any]) -> dict[str, Any]:
    """Return every map field except the timestamp and digest itself.

    Canonical serialization is UTF-8 JSON with sorted keys, no insignificant whitespace,
    and non-ASCII characters preserved. generated_at is deliberately non-binding.
    """

    return {
        key: value
        for key, value in reading_map.items()
        if key not in {"generated_at", "binding_digest"}
    }


def calculate_binding_digest(reading_map: dict[str, Any]) -> str:
    canonical = json.dumps(
        binding_payload(reading_map),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def generate_reading_map(
    request: dict[str, Any],
    *,
    repo_root: Path = PROJECT_ROOT,
    allow_roots: Iterable[Path | str] = (),
) -> dict[str, Any]:
    validate_request(request)
    root = repo_root.resolve()
    approved_roots = _normalise_allowed_roots(allow_roots)
    source_commit, source_tree = current_git_binding(root)
    routed = _read_routed_documents(request["documents"], root, approved_roots)

    selections = [
        document["required_sections"] + document["optional_sections"]
        for document in request["documents"]
    ]
    optional_order = [
        (document_index, section_id)
        for document_index, document in enumerate(request["documents"])
        for section_id in document["optional_sections"]
    ]
    capacity = request["capacity_bytes"]
    planned = _planned_bytes(routed, selections)
    initial_ratio = planned / capacity
    if initial_ratio > HARD_LIMIT:
        _reject(
            "BLOCK_AND_REPLAN",
            f"initial context ratio {initial_ratio:.6f} exceeds hard limit {HARD_LIMIT:.2f}",
        )

    status = "OK"
    if initial_ratio > SOFT_LIMIT:
        for document_index, section_id in reversed(optional_order):
            selections[document_index].remove(section_id)
            planned = _planned_bytes(routed, selections)
            if planned / capacity <= SOFT_LIMIT:
                break
        ratio = planned / capacity
        if ratio > SOFT_LIMIT:
            _reject(
                "SOFT_LIMIT_REPLAN",
                f"required context ratio {ratio:.6f} remains above soft limit {SOFT_LIMIT:.2f}",
            )
        status = "SOFT_REDUCED"
    else:
        ratio = initial_ratio

    output_documents = [
        {
            "path": routed[index]["path"],
            "sha256": routed[index]["sha256"],
            "sections": section_ids,
            "reason": routed[index]["reason"],
        }
        for index, section_ids in enumerate(selections)
        if section_ids
    ]
    if not output_documents:
        _reject("SOFT_LIMIT_REPLAN", "soft reduction removed every routed document")

    reading_map: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "route_id": request["route_id"],
        "mode": request["mode"],
        "milestone": request["milestone"],
        "batch_id": request["batch_id"],
        "source_commit": source_commit,
        "source_tree": source_tree,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "context_budget": {
            "capacity_bytes": capacity,
            "planned_bytes": planned,
            "ratio": ratio,
            "soft_limit": SOFT_LIMIT,
            "hard_limit": HARD_LIMIT,
            "status": status,
        },
        "documents": output_documents,
        "forbidden_bulk_reads": request["forbidden_bulk_reads"],
        "binding_digest": "",
    }
    reading_map["binding_digest"] = calculate_binding_digest(reading_map)
    validate_reading_map_structure(reading_map)
    return reading_map


def validate_reading_map_structure(reading_map: Any) -> dict[str, Any]:
    if not isinstance(reading_map, dict):
        _reject("INVALID_STRUCTURE", "Reading Map must be an object")
    _check_exact_keys(reading_map, MAP_KEYS, "Reading Map")
    if reading_map["schema_version"] != SCHEMA_VERSION:
        _reject("INVALID_STRUCTURE", "Reading Map schema_version must be 1.0")
    _validate_identity(
        reading_map["route_id"],
        reading_map["mode"],
        reading_map["milestone"],
        reading_map["batch_id"],
    )
    for field in ("source_commit", "source_tree"):
        value = reading_map[field]
        if not isinstance(value, str) or HEX_40_PATTERN.fullmatch(value) is None:
            _reject("INVALID_STRUCTURE", f"{field} must be a 40-character lowercase hex ID")
    generated_at = reading_map["generated_at"]
    if not isinstance(generated_at, str):
        _reject("INVALID_STRUCTURE", "generated_at must be a date-time string")
    try:
        parsed_timestamp = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        _reject("INVALID_STRUCTURE", "generated_at must be an RFC 3339 date-time")
    if parsed_timestamp.tzinfo is None:
        _reject("INVALID_STRUCTURE", "generated_at must include a timezone")

    context = reading_map["context_budget"]
    if not isinstance(context, dict):
        _reject("INVALID_STRUCTURE", "context_budget must be an object")
    _check_exact_keys(context, CONTEXT_KEYS, "context_budget")
    if not _is_int(context["capacity_bytes"]) or context["capacity_bytes"] < 1:
        _reject("INVALID_STRUCTURE", "context_budget.capacity_bytes must be positive")
    if not _is_int(context["planned_bytes"]) or context["planned_bytes"] < 0:
        _reject("INVALID_STRUCTURE", "context_budget.planned_bytes must be non-negative")
    if not _is_number(context["ratio"]) or context["ratio"] < 0:
        _reject("INVALID_STRUCTURE", "context_budget.ratio must be non-negative")
    if context["soft_limit"] != SOFT_LIMIT or context["hard_limit"] != HARD_LIMIT:
        _reject("INVALID_STRUCTURE", "context limits must be exactly 0.55 and 0.70")
    if not isinstance(context["status"], str) or context["status"] not in CONTEXT_STATUSES:
        _reject("INVALID_STRUCTURE", f"invalid context status: {context['status']!r}")

    documents = reading_map["documents"]
    if not isinstance(documents, list) or not documents:
        _reject("INVALID_STRUCTURE", "Reading Map documents must be a non-empty array")
    paths: list[str] = []
    for index, document in enumerate(documents):
        label = f"documents[{index}]"
        if not isinstance(document, dict):
            _reject("INVALID_STRUCTURE", f"{label} must be an object")
        _check_exact_keys(document, MAP_DOCUMENT_KEYS, label)
        paths.append(_check_nonempty_string(document["path"], f"{label}.path"))
        digest = document["sha256"]
        if not isinstance(digest, str) or HEX_64_PATTERN.fullmatch(digest) is None:
            _reject("INVALID_STRUCTURE", f"{label}.sha256 must be lowercase SHA-256")
        _check_string_list(
            document["sections"],
            f"{label}.sections",
            allow_empty=False,
            pattern=SECTION_ID_PATTERN,
        )
        _check_nonempty_string(document["reason"], f"{label}.reason")
    if len(paths) != len(set(paths)):
        _reject("DUPLICATE_DOCUMENT", "Reading Map contains duplicate document paths")
    _check_string_list(
        reading_map["forbidden_bulk_reads"],
        "forbidden_bulk_reads",
        allow_empty=True,
    )
    digest = reading_map["binding_digest"]
    if not isinstance(digest, str) or HEX_64_PATTERN.fullmatch(digest) is None:
        _reject("INVALID_STRUCTURE", "binding_digest must be lowercase SHA-256")
    return reading_map


def check_reading_map(
    reading_map: dict[str, Any],
    *,
    expected_route_id: str,
    expected_mode: str,
    expected_milestone: str,
    expected_batch_id: str,
    repo_root: Path = PROJECT_ROOT,
    allow_roots: Iterable[Path | str] = (),
) -> None:
    validate_reading_map_structure(reading_map)
    expected = {
        "route_id": expected_route_id,
        "mode": expected_mode,
        "milestone": expected_milestone,
        "batch_id": expected_batch_id,
    }
    mismatch_codes = {
        "route_id": "ROUTE_ID_MISMATCH",
        "mode": "MODE_MISMATCH",
        "milestone": "MILESTONE_MISMATCH",
        "batch_id": "BATCH_MISMATCH",
    }
    for field, value in expected.items():
        if reading_map[field] != value:
            _reject(mismatch_codes[field], f"expected {field}={value}, got {reading_map[field]}")

    root = repo_root.resolve()
    source_commit, source_tree = current_git_binding(root)
    if reading_map["source_commit"] != source_commit:
        _reject(
            "STALE_SOURCE_COMMIT",
            f"Reading Map commit {reading_map['source_commit']} != current {source_commit}",
        )
    if reading_map["source_tree"] != source_tree:
        _reject(
            "STALE_SOURCE_TREE",
            f"Reading Map tree {reading_map['source_tree']} != current {source_tree}",
        )

    approved_roots = _normalise_allowed_roots(allow_roots)
    routed = _read_routed_documents(reading_map["documents"], root, approved_roots)
    for document, actual in zip(reading_map["documents"], routed):
        if document["sha256"] != actual["sha256"]:
            _reject("STALE_DOCUMENT", f"document SHA-256 changed: {document['path']}")
    selections = [document["sections"] for document in reading_map["documents"]]
    planned = _planned_bytes(routed, selections)
    context = reading_map["context_budget"]
    ratio = planned / context["capacity_bytes"]
    if context["planned_bytes"] != planned or context["ratio"] != ratio:
        _reject("CONTEXT_BUDGET_MISMATCH", "planned Section bytes or ratio do not recompute")
    if ratio > HARD_LIMIT or context["status"] == "HARD_BLOCKED":
        _reject("BLOCK_AND_REPLAN", "a usable Reading Map may not exceed the hard limit")
    if ratio > SOFT_LIMIT:
        _reject("SOFT_LIMIT_REPLAN", "a usable Reading Map may not remain above the soft limit")
    if context["status"] not in {"OK", "SOFT_REDUCED"}:
        _reject("INVALID_STRUCTURE", "usable Reading Map has invalid context status")

    expected_digest = calculate_binding_digest(reading_map)
    if reading_map["binding_digest"] != expected_digest:
        _reject("BINDING_DIGEST_MISMATCH", "binding_digest does not match canonical content")


def write_reading_map(
    request_path: Path,
    output_path: Path,
    *,
    repo_root: Path = PROJECT_ROOT,
    allow_roots: Iterable[Path | str] = (),
) -> dict[str, Any]:
    request = _load_json(request_path, "route request")
    reading_map = generate_reading_map(request, repo_root=repo_root, allow_roots=allow_roots)
    output = output_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(reading_map, ensure_ascii=False, indent=2) + "\n"
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8", newline="\n")
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return reading_map


def check_reading_map_file(
    map_path: Path,
    *,
    expected_route_id: str,
    expected_mode: str,
    expected_milestone: str,
    expected_batch_id: str,
    repo_root: Path = PROJECT_ROOT,
    allow_roots: Iterable[Path | str] = (),
) -> dict[str, Any]:
    reading_map = _load_json(map_path, "Reading Map")
    check_reading_map(
        reading_map,
        expected_route_id=expected_route_id,
        expected_mode=expected_mode,
        expected_milestone=expected_milestone,
        expected_batch_id=expected_batch_id,
        repo_root=repo_root,
        allow_roots=allow_roots,
    )
    return reading_map


def self_check(
    request_path: Path,
    *,
    expected_route_id: str,
    expected_mode: str,
    expected_milestone: str,
    expected_batch_id: str,
    repo_root: Path = PROJECT_ROOT,
    allow_roots: Iterable[Path | str] = (),
) -> None:
    request = _load_json(request_path, "route request")
    validate_request(request)
    with tempfile.TemporaryDirectory(prefix="rules-residue-codex-route-") as directory:
        map_path = Path(directory) / "reading-map.json"
        write_reading_map(
            request_path,
            map_path,
            repo_root=repo_root,
            allow_roots=allow_roots,
        )
        check_reading_map_file(
            map_path,
            expected_route_id=expected_route_id,
            expected_mode=expected_mode,
            expected_milestone=expected_milestone,
            expected_batch_id=expected_batch_id,
            repo_root=repo_root,
            allow_roots=allow_roots,
        )


def _add_repository_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--allow-root",
        action="append",
        default=[],
        type=Path,
        help="explicit absolute read-only root for external routed documents",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Python-native Codex Reading Map gate")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="generate a commit-bound Reading Map")
    generate.add_argument("--request", required=True, type=Path)
    generate.add_argument("--output", required=True, type=Path)
    _add_repository_arguments(generate)

    check = subparsers.add_parser("check", help="check a Reading Map against current sources")
    check.add_argument("--map", required=True, type=Path)
    check.add_argument("--route-id", required=True)
    check.add_argument("--mode", required=True, choices=sorted(MODES))
    check.add_argument("--milestone", required=True)
    check.add_argument("--batch-id", required=True)
    _add_repository_arguments(check)

    self_check_parser = subparsers.add_parser(
        "self-check", help="generate and verify the controlled baseline route in a temporary directory"
    )
    self_check_parser.add_argument(
        "--request",
        type=Path,
        default=PROJECT_ROOT / ".codex" / "routes" / "baseline-request.json",
    )
    self_check_parser.add_argument("--route-id", required=True)
    self_check_parser.add_argument("--mode", required=True, choices=sorted(MODES))
    self_check_parser.add_argument("--milestone", required=True)
    self_check_parser.add_argument("--batch-id", required=True)
    _add_repository_arguments(self_check_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "generate":
            reading_map = write_reading_map(
                args.request,
                args.output,
                repo_root=args.repo_root,
                allow_roots=args.allow_root,
            )
            print(
                "GENERATE: PASS "
                f"status={reading_map['context_budget']['status']} "
                f"planned_bytes={reading_map['context_budget']['planned_bytes']} "
                f"ratio={reading_map['context_budget']['ratio']:.6f}"
            )
            print(f"output={args.output}")
        elif args.command == "check":
            check_reading_map_file(
                args.map,
                expected_route_id=args.route_id,
                expected_mode=args.mode,
                expected_milestone=args.milestone,
                expected_batch_id=args.batch_id,
                repo_root=args.repo_root,
                allow_roots=args.allow_root,
            )
            print("CHECK: PASS")
            print("CODEX_ROUTE_FRESH=PASS")
        else:
            self_check(
                args.request,
                expected_route_id=args.route_id,
                expected_mode=args.mode,
                expected_milestone=args.milestone,
                expected_batch_id=args.batch_id,
                repo_root=args.repo_root,
                allow_roots=args.allow_root,
            )
            print("SELF-CHECK: PASS")
            print("CODEX_ROUTE_FRESH=PASS")
    except RouteError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
