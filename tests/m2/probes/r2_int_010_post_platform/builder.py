#!/usr/bin/env python3
"""Deterministic source-only builder for the post-platform R2-INT-010 probe.

The builder intentionally reads only the four declared data files below its own
source root.  Platform acceptance reports are validated by ``validator.py``;
they are not implicit builder inputs and cannot redirect source reads.
"""

from __future__ import annotations

import argparse
import decimal
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


SOURCE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SOURCE_ROOT.parents[3]

TASK_ID = "R2-INT-010-POST-PLATFORM-ADAPTER-RECONSTRUCT-001"
ADAPTER_ID = "R2-INT-010-POST-PLATFORM-ADAPTER-001"
PROBE_ID = "R2-INT-010-POST-PLATFORM-001"
ACCEPTANCE_BINDING_ID = "R2-INT-010-PLATFORM-ACCEPTANCE-001"
PROBE_SCOPE_LABEL = "R2-INT-010 post-platform minimal capability probe only / NOT formal M2-B002 or M2-B009"

PLATFORM_CODE_COMMIT = "1339c490bd8cae1e2a6e6607fc0f1db019faab64"
PLATFORM_CODE_TREE = "25d5645caf883a73f165db0179accbca48ddf526"
PLATFORM_AUTHORITY_COMMIT = "65731845177d1657e9f192f3e7c56969ebe81bc5"
PLATFORM_AUTHORITY_TREE = "3c176856c7ded8858e9771c94c9f06e1f1cb8da3"
CREATOR_BINARY_SHA256 = "7e31836febd753ca32dc0b81d9f9d8fc7c15fee123730fc4998ca1ee30b7e3a2"

METADATA_SOURCE = PurePosixPath("source-metadata.json")
ADAPTER_SOURCE = PurePosixPath("platform-v2-adapter.json")
SCHEMA_SOURCE = PurePosixPath("minimal-capability-probe.schema.json")
PAYLOAD_SOURCE = PurePosixPath("minimal-capability-probe.json")
SOURCE_LOCK_NAME = "source-exact-lock.json"
ADAPTER_OUTPUT = PurePosixPath("adapters/platform-v2-adapter.json")
METADATA_OUTPUT = PurePosixPath("adapters/post-platform-source-metadata.json")

MAX_METADATA_BYTES = 64 << 10
MAX_ADAPTER_BYTES = 64 << 10
MAX_SCHEMA_BYTES = 1 << 20
MAX_PAYLOAD_BYTES = 4 << 20
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 4096
MAX_JSON_NUMBER_BYTES = 128
MAX_JSON_EXPONENT = 308
MAX_PROJECT_FILES = 8

_NAMESPACE_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?"
NAMESPACE_PATTERN = re.compile(rf"^{_NAMESPACE_LABEL}(?:\.{_NAMESPACE_LABEL}){{2,7}}$")
NAMESPACE_LABEL_PATTERN = re.compile(rf"^{_NAMESPACE_LABEL}$")
PLATFORM_PACKAGE_ID_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9.-]{0,126}[a-z0-9])?/"
    r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$"
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
JSON_EXPONENT_PATTERN = re.compile(r"[eE]([+-]?)([0-9]+)$")

_METADATA_KEYS = {
    "schema_version",
    "task_id",
    "adapter_id",
    "artifact_role",
    "package",
    "scope",
    "platform_acceptance",
    "governance",
}
_ADAPTER_KEYS = {
    "schema_version",
    "adapter_id",
    "artifact_role",
    "acceptance_binding_id",
    "platform_package_id",
    "namespace_derivation",
    "v2_manifest",
    "source_files",
    "extension_descriptor",
}
_DESCRIPTOR_KEYS = {
    "namespace",
    "required",
    "contract_version",
    "schema_path",
    "schema_sha256",
    "payload_path",
    "host_api_major",
    "host_api_min_minor",
    "host_api_max_minor",
}


class DuplicateJSONKey(ValueError):
    """Raised when strict JSON contains duplicate object keys."""


@dataclass(frozen=True)
class AdapterInputs:
    metadata: dict[str, Any]
    definition: dict[str, Any]
    schema: dict[str, Any]
    payload: dict[str, Any]
    metadata_bytes: bytes
    adapter_bytes: bytes
    schema_bytes: bytes
    payload_bytes: bytes


@dataclass(frozen=True)
class BuildResult:
    output_root: Path
    project_root: Path
    source_lock: Path
    source_tree_sha256: str
    candidate_identity_sha256: str
    project_files: tuple[str, ...]


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKey(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _validate_number_token(token: str) -> None:
    if len(token.encode("ascii")) > MAX_JSON_NUMBER_BYTES:
        raise ValueError(f"JSON number token exceeds {MAX_JSON_NUMBER_BYTES} bytes")
    exponent_match = JSON_EXPONENT_PATTERN.search(token)
    if exponent_match is not None and int(exponent_match.group(2)) > MAX_JSON_EXPONENT:
        raise ValueError(f"JSON number exponent exceeds absolute {MAX_JSON_EXPONENT}")
    try:
        expanded = format(decimal.Decimal(token), "f")
    except decimal.InvalidOperation as error:
        raise ValueError("JSON number token is invalid") from error
    if len(expanded.encode("ascii")) > MAX_JSON_NUMBER_BYTES:
        raise ValueError(f"canonical JSON number exceeds {MAX_JSON_NUMBER_BYTES} bytes")


def _parse_json_int(token: str) -> int:
    _validate_number_token(token)
    return int(token)


def _parse_json_decimal(token: str) -> decimal.Decimal:
    _validate_number_token(token)
    return decimal.Decimal(token)


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"non-finite JSON constant {token!r} is unavailable")


def _reject_surrogates(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("JSON string contains an unpaired surrogate")


def _guard_json_tree(value: Any, depth: int = 0, nodes: list[int] | None = None) -> None:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_JSON_NODES:
        raise ValueError(f"JSON node count exceeds {MAX_JSON_NODES}")
    if isinstance(value, str):
        _reject_surrogates(value)
        return
    if isinstance(value, dict):
        if depth >= MAX_JSON_DEPTH:
            raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
        for key, child in value.items():
            _reject_surrogates(key)
            _guard_json_tree(child, depth + 1, nodes)
        return
    if isinstance(value, list):
        if depth >= MAX_JSON_DEPTH:
            raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
        for child in value:
            _guard_json_tree(child, depth + 1, nodes)


def _load_json_bytes(data: bytes, label: str) -> Any:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{label} must not contain a UTF-8 BOM")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} is not UTF-8: {error}") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_int=_parse_json_int,
            parse_float=_parse_json_decimal,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, DuplicateJSONKey, ValueError) as error:
        raise ValueError(f"{label} is not strict JSON: {error}") from error
    try:
        _guard_json_tree(value)
    except ValueError as error:
        raise ValueError(f"{label} is outside the bounded JSON contract: {error}") from error
    return value


def _validated_real_directory(directory: Path, label: str) -> Path:
    root = Path(os.path.abspath(os.fspath(directory)))
    try:
        metadata = os.lstat(root)
    except OSError as error:
        raise ValueError(f"{label} is unavailable: {root}: {error}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{label} must be a real directory, not a symlink")
    return root


def _confined_file_bytes(
    root: Path,
    relative: PurePosixPath,
    label: str,
    maximum_bytes: int,
) -> bytes:
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError(f"{label} path escapes its source root")
    current = root
    metadata = os.lstat(root)
    for index, part in enumerate(relative.parts):
        current = current / part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise ValueError(f"{label} path is unavailable: {relative}: {error}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"{label} path contains a symbolic link: {relative}")
        if index < len(relative.parts) - 1:
            if not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(f"{label} parent is not a directory: {relative}")
        elif not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label} must be a regular file: {relative}")
    if metadata.st_size < 0 or metadata.st_size > maximum_bytes:
        raise ValueError(f"{label} exceeds {maximum_bytes} bytes before read")
    resolved_root = root.resolve(strict=True)
    resolved_file = current.resolve(strict=True)
    if not resolved_file.is_relative_to(resolved_root):
        raise ValueError(f"{label} path escapes its source root")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(current, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_size != metadata.st_size
        ):
            raise ValueError(f"{label} changed before read")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read(maximum_bytes + 1)
        if len(data) > maximum_bytes:
            raise ValueError(f"{label} exceeds {maximum_bytes} bytes during read")
        if len(data) != opened.st_size:
            raise ValueError(f"{label} changed during read")
        after = os.lstat(current)
        if (
            stat.S_ISLNK(after.st_mode)
            or after.st_dev != opened.st_dev
            or after.st_ino != opened.st_ino
            or after.st_size != opened.st_size
            or after.st_mtime_ns != opened.st_mtime_ns
        ):
            raise ValueError(f"{label} changed during read")
    finally:
        os.close(descriptor)
    return data


def _load_json_file(
    root: Path,
    relative: PurePosixPath,
    label: str,
    maximum_bytes: int,
) -> tuple[Any, bytes]:
    data = _confined_file_bytes(root, relative, label, maximum_bytes)
    return _load_json_bytes(data, label), data


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{label} keys differ; missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )
    return value


def _require_nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonblank string")
    return value


def _require_ascii_lower(value: str, label: str) -> None:
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError(f"{label} must use lower-case ASCII") from error
    if value.casefold() != value or value.lower() != value:
        raise ValueError(f"{label} must use lower-case ASCII without case folding")
    if len(encoded) > 255:
        raise ValueError(f"{label} exceeds 255 bytes")


def _stable_id_as_dotted(stable_package_id: str) -> str:
    _require_ascii_lower(stable_package_id, "stable package ID")
    if "/" in stable_package_id:
        if stable_package_id.count("/") != 1 or not PLATFORM_PACKAGE_ID_PATTERN.fullmatch(
            stable_package_id
        ):
            raise ValueError("stable slash package ID is not canonical")
        return stable_package_id.replace("/", ".")
    parts = stable_package_id.split(".")
    if len(parts) < 2 or any(not NAMESPACE_LABEL_PATTERN.fullmatch(part) for part in parts):
        raise ValueError("stable dotted package ID is not canonical")
    return stable_package_id


def derive_extension_namespace(stable_package_id: str, suffix: str = "probe") -> str:
    """Derive a namespace from any canonical package ID, without identity tables."""

    if not isinstance(stable_package_id, str) or not isinstance(suffix, str):
        raise ValueError("package ID and namespace suffix must be strings")
    _require_ascii_lower(suffix, "namespace suffix")
    if not NAMESPACE_LABEL_PATTERN.fullmatch(suffix):
        raise ValueError("namespace suffix is not one canonical namespace segment")
    namespace = f"{_stable_id_as_dotted(stable_package_id)}.{suffix}"
    if len(namespace.encode("ascii")) > 128 or not NAMESPACE_PATTERN.fullmatch(namespace):
        raise ValueError("derived extension namespace is outside the platform boundary")
    if namespace == "trpg.platform" or namespace.startswith("trpg.platform."):
        raise ValueError("derived extension namespace uses the reserved platform prefix")
    return namespace


def derive_platform_package_id(stable_package_id: str) -> str:
    """Map any canonical dotted/slash identity to the generic v2 slash form."""

    if not isinstance(stable_package_id, str):
        raise ValueError("stable package ID must be a string")
    _require_ascii_lower(stable_package_id, "stable package ID")
    if "/" in stable_package_id:
        candidate = stable_package_id
    else:
        dotted = _stable_id_as_dotted(stable_package_id)
        publisher, name = dotted.rsplit(".", 1)
        candidate = f"{publisher}/{name}"
    if len(candidate.encode("ascii")) > 255 or not PLATFORM_PACKAGE_ID_PATTERN.fullmatch(candidate):
        raise ValueError("derived platform package ID is not canonical")
    return candidate


def _windows_device_name(segment: str) -> bool:
    base = segment.split(".", 1)[0].rstrip(" .").upper()
    if base in {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"}:
        return True
    return len(base) == 4 and base[:3] in {"COM", "LPT"} and base[3] in "123456789¹²³"


def _portable_collision_key(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    return unicodedata.normalize("NFC", normalized.casefold())


def _validated_relative_path(value: Any, label: str) -> PurePosixPath:
    text = _require_nonblank(value, label)
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"{label} is not valid UTF-8") from error
    if not 1 <= len(encoded) <= 240:
        raise ValueError(f"{label} is outside the platform path boundary")
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError(f"{label} is not NFC-normalized")
    if text.startswith("/") or text.startswith("//"):
        raise ValueError(f"{label} must be relative")
    if "\\" in text or ":" in text or "\x00" in text:
        raise ValueError(f"{label} contains a forbidden separator, drive marker, or NUL")
    for segment in text.split("/"):
        if segment in {"", ".", ".."}:
            raise ValueError(f"{label} contains an empty, dot, or parent segment")
        if segment.strip() != segment or segment.endswith("."):
            raise ValueError(f"{label} segment has unsafe edge characters")
        if any(character in '<>"|?*' for character in segment):
            raise ValueError(f"{label} contains a Windows-forbidden character")
        if _windows_device_name(segment):
            raise ValueError(f"{label} contains a reserved device name")
        if any(unicodedata.category(character) == "Cc" for character in segment):
            raise ValueError(f"{label} contains a control character")
    path = PurePosixPath(text)
    if path.is_absolute() or str(path) != text:
        raise ValueError(f"{label} is not a canonical relative path")
    return path


def _validated_source_name(value: Any, label: str) -> PurePosixPath:
    path = _validated_relative_path(value, label)
    if len(path.parts) != 1 or path.suffix != ".json":
        raise ValueError(f"{label} must name one local JSON source file")
    return path


def _ensure_unique_portable_paths(paths: list[str] | tuple[str, ...]) -> None:
    seen: dict[str, str] = {}
    for path in paths:
        validated = _validated_relative_path(path, "project path").as_posix()
        key = _portable_collision_key(validated)
        if key in seen:
            raise ValueError(f"project paths collide under portable normalization: {seen[key]} / {path}")
        seen[key] = path


def _audit_schema_references(value: Any) -> None:
    if isinstance(value, dict):
        for keyword in ("$dynamicRef", "$recursiveRef"):
            if keyword in value:
                raise ValueError(f"probe schema forbids {keyword}")
        if "$id" in value:
            raise ValueError("probe schema forbids base-URI-changing $id")
        if "$ref" in value:
            reference = value["$ref"]
            if not isinstance(reference, str) or not reference.startswith("#/"):
                raise ValueError("probe schema $ref must be a same-document JSON Pointer fragment")
        for child in value.values():
            _audit_schema_references(child)
    elif isinstance(value, list):
        for child in value:
            _audit_schema_references(child)


def _resolve_local_ref(schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ValueError("schema reference is not a local JSON Pointer fragment")
    current: Any = schema
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise ValueError(f"schema local reference is unresolved: {reference}")
        current = current[token]
    if not isinstance(current, dict):
        raise ValueError(f"schema local reference does not resolve to an object: {reference}")
    return current


def _validate_schema_shape(schema: dict[str, Any]) -> None:
    expected_keys = {
        "$schema", "title", "$comment", "type", "required", "properties",
        "additionalProperties", "$defs",
    }
    _require_exact_keys(schema, expected_keys, "probe schema")
    if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("probe schema must declare Draft 2020-12")
    if schema["type"] != "object" or schema["additionalProperties"] is not False:
        raise ValueError("probe schema must be a closed object")
    if PROBE_SCOPE_LABEL not in str(schema["title"]):
        raise ValueError("probe schema is missing the non-formal scope label")
    fields = ["probe_id", "formal_B002", "formal_B009", "count", "enabled"]
    if schema["required"] != fields:
        raise ValueError("probe schema required fields changed")
    properties = _require_exact_keys(schema["properties"], set(fields), "probe properties")
    definitions = _require_exact_keys(schema["$defs"], {"bounded_count"}, "probe definitions")
    if properties["probe_id"] != {"const": PROBE_ID}:
        raise ValueError("probe schema identity changed")
    if properties["formal_B002"] != {"const": False} or properties["formal_B009"] != {"const": False}:
        raise ValueError("probe schema formal scope changed")
    if properties["count"] != {"$ref": "#/$defs/bounded_count"}:
        raise ValueError("probe count must use the local bounded-count definition")
    if definitions["bounded_count"] != {"type": "integer", "minimum": 0, "maximum": 1000000}:
        raise ValueError("probe bounded-count definition changed")
    if properties["enabled"] != {"type": "boolean"}:
        raise ValueError("probe enabled contract changed")


def _schema_issue(value: Any, rule: dict[str, Any], schema: dict[str, Any], path: str) -> list[str]:
    if "$ref" in rule:
        return _schema_issue(value, _resolve_local_ref(schema, rule["$ref"]), schema, path)
    if "const" in rule and value != rule["const"]:
        return [f"{path}: value differs from const"]
    expected_type = rule.get("type")
    if expected_type == "integer":
        if type(value) is not int:
            return [f"{path}: expected integer"]
        issues = []
        if value < rule.get("minimum", value):
            issues.append(f"{path}: below minimum")
        if value > rule.get("maximum", value):
            issues.append(f"{path}: above maximum")
        return issues
    if expected_type == "boolean" and type(value) is not bool:
        return [f"{path}: expected boolean"]
    return []


def validate_payload(payload: Any, schema: dict[str, Any]) -> list[str]:
    """Validate the deliberately small payload against the exact local schema."""

    if not isinstance(payload, dict):
        return ["$: expected object"]
    required = schema["required"]
    properties = schema["properties"]
    issues = [f"$.{key}: required property missing" for key in required if key not in payload]
    issues.extend(f"$.{key}: unknown property" for key in payload if key not in properties)
    for key in required:
        if key in payload:
            issues.extend(_schema_issue(payload[key], properties[key], schema, f"$.{key}"))
    return issues


def _validate_metadata(value: Any) -> dict[str, Any]:
    metadata = _require_exact_keys(value, _METADATA_KEYS, "source metadata")
    if metadata["schema_version"] != "rules-residue.r2-int-010-post-platform-source/1.0":
        raise ValueError("source metadata schema version changed")
    if metadata["task_id"] != TASK_ID or metadata["adapter_id"] != ADAPTER_ID:
        raise ValueError("source metadata identity changed")
    if metadata["artifact_role"] != "SOURCE_ONLY_MINIMAL_COMPATIBILITY_ADAPTER_CANDIDATE_NOT_ACCEPTED":
        raise ValueError("source metadata artifact role overclaims acceptance")
    package = _require_exact_keys(metadata["package"], {"stable_id", "version"}, "source package")
    _require_nonblank(package["stable_id"], "source package stable_id")
    _require_nonblank(package["version"], "source package version")
    scope = _require_exact_keys(
        metadata["scope"],
        {
            "capability", "formal_B002", "formal_B009", "equipment_runtime", "lua",
            "rule_engine", "privileged_package_identity", "official_game_special_case",
        },
        "adapter scope",
    )
    if scope != {
        "capability": "MINIMAL_CAPABILITY_PROBE_ONLY",
        "formal_B002": False,
        "formal_B009": False,
        "equipment_runtime": False,
        "lua": False,
        "rule_engine": False,
        "privileged_package_identity": False,
        "official_game_special_case": False,
    }:
        raise ValueError("adapter scope exceeds the minimal non-formal probe")
    acceptance = _require_exact_keys(
        metadata["platform_acceptance"],
        {
            "binding_id", "status", "platform_code_commit", "platform_code_tree",
            "acceptance_authority_commit", "acceptance_authority_tree", "creator_binary_sha256",
        },
        "platform acceptance binding",
    )
    expected_acceptance = {
        "binding_id": ACCEPTANCE_BINDING_ID,
        "status": "PASS",
        "platform_code_commit": PLATFORM_CODE_COMMIT,
        "platform_code_tree": PLATFORM_CODE_TREE,
        "acceptance_authority_commit": PLATFORM_AUTHORITY_COMMIT,
        "acceptance_authority_tree": PLATFORM_AUTHORITY_TREE,
        "creator_binary_sha256": CREATOR_BINARY_SHA256,
    }
    if acceptance != expected_acceptance:
        raise ValueError("platform PASS antecedent is absent, provisional, or mismatched")
    governance = _require_exact_keys(
        metadata["governance"],
        {"rules_adapter_acceptance", "cross_repository_acceptance", "r2_int_010", "m2_b002_started"},
        "candidate governance",
    )
    if governance != {
        "rules_adapter_acceptance": "NOT_RUN",
        "cross_repository_acceptance": "NOT_RUN",
        "r2_int_010": "FAIL",
        "m2_b002_started": False,
    }:
        raise ValueError("candidate governance overclaims a downstream gate")
    return metadata


def _validate_v2_manifest_source(value: Any) -> dict[str, Any]:
    manifest = _require_exact_keys(
        value,
        {"package_kind", "display_name", "build", "rights", "capabilities"},
        "adapter v2_manifest",
    )
    if manifest["package_kind"] != "library":
        raise ValueError("minimal probe package_kind must remain library")
    _require_nonblank(manifest["display_name"], "adapter display_name")
    build = _require_exact_keys(manifest["build"], {"source", "revision", "builder"}, "adapter build")
    for key in sorted(build):
        _require_nonblank(build[key], f"adapter build.{key}")
    rights = _require_exact_keys(
        manifest["rights"], {"authors", "source", "license_expression"}, "adapter rights"
    )
    authors = rights["authors"]
    if (
        not isinstance(authors, list)
        or not authors
        or any(not isinstance(item, str) or not item.strip() for item in authors)
        or authors != sorted(set(authors))
    ):
        raise ValueError("adapter authors must be a sorted unique nonempty string array")
    _require_nonblank(rights["source"], "adapter rights.source")
    _require_nonblank(rights["license_expression"], "adapter rights.license_expression")
    capabilities = _require_exact_keys(manifest["capabilities"], {"required"}, "adapter capabilities")
    if capabilities["required"] != []:
        raise ValueError("minimal probe must not request Host runtime capabilities")
    return manifest


def load_adapter_inputs(source_root: Path = SOURCE_ROOT) -> AdapterInputs:
    root = _validated_real_directory(source_root, "post-platform probe source root")
    metadata_value, metadata_bytes = _load_json_file(
        root, METADATA_SOURCE, "post-platform source metadata", MAX_METADATA_BYTES
    )
    metadata = _validate_metadata(metadata_value)
    definition_value, adapter_bytes = _load_json_file(
        root, ADAPTER_SOURCE, "post-platform platform-v2 descriptor source", MAX_ADAPTER_BYTES
    )
    definition = _require_exact_keys(definition_value, _ADAPTER_KEYS, "platform-v2 descriptor source")
    if definition["schema_version"] != "rules-residue.platform-v2-post-platform-adapter/1.0":
        raise ValueError("adapter descriptor schema version changed")
    if definition["adapter_id"] != ADAPTER_ID:
        raise ValueError("adapter descriptor identity changed")
    if definition["artifact_role"] != "GENERIC_PLATFORM_V2_DESCRIPTOR_SOURCE_NOT_ACCEPTANCE_EVIDENCE":
        raise ValueError("adapter descriptor role overclaims evidence")
    if definition["acceptance_binding_id"] != ACCEPTANCE_BINDING_ID:
        raise ValueError("adapter descriptor is not bound to the accepted platform antecedent")

    stable_id = metadata["package"]["stable_id"]
    namespace_source = _require_exact_keys(
        definition["namespace_derivation"],
        {"algorithm", "suffix", "derived_namespace"},
        "namespace derivation",
    )
    if namespace_source["algorithm"] != "stable-package-id-dot-namespace-plus-suffix-v1":
        raise ValueError("namespace derivation algorithm changed")
    suffix = _require_nonblank(namespace_source["suffix"], "namespace suffix")
    namespace = derive_extension_namespace(stable_id, suffix)
    if namespace_source["derived_namespace"] != namespace:
        raise ValueError("declared namespace does not match generic deterministic derivation")
    platform_package_id = derive_platform_package_id(stable_id)
    if definition["platform_package_id"] != platform_package_id:
        raise ValueError("declared platform package ID does not match deterministic derivation")
    _validate_v2_manifest_source(definition["v2_manifest"])

    source_files = _require_exact_keys(
        definition["source_files"], {"schema", "payload"}, "adapter source files"
    )
    schema_source = _validated_source_name(source_files["schema"], "schema source")
    payload_source = _validated_source_name(source_files["payload"], "payload source")
    if schema_source != SCHEMA_SOURCE or payload_source != PAYLOAD_SOURCE:
        raise ValueError("adapter source file mapping changed")

    descriptor = _require_exact_keys(
        definition["extension_descriptor"], _DESCRIPTOR_KEYS, "extension descriptor"
    )
    if descriptor["namespace"] != namespace or descriptor["required"] is not True:
        raise ValueError("extension descriptor namespace/required contract changed")
    for key, expected in {
        "contract_version": 1,
        "host_api_major": 1,
        "host_api_min_minor": 0,
        "host_api_max_minor": 0,
    }.items():
        if type(descriptor[key]) is not int or descriptor[key] != expected:
            raise ValueError(f"extension descriptor {key} must equal {expected}")
    if not isinstance(descriptor["schema_sha256"], str) or not SHA256_PATTERN.fullmatch(
        descriptor["schema_sha256"]
    ):
        raise ValueError("extension descriptor schema_sha256 is not canonical")
    schema_path = _validated_relative_path(descriptor["schema_path"], "schema_path")
    payload_path = _validated_relative_path(descriptor["payload_path"], "payload_path")
    _ensure_unique_portable_paths((schema_path.as_posix(), payload_path.as_posix()))
    prefix = PurePosixPath("extensions") / namespace
    if schema_path.parent != prefix or schema_path.suffixes[-2:] != [".schema", ".json"]:
        raise ValueError("schema_path must be one local schema under the derived namespace")
    if payload_path.parent != prefix or payload_path.suffix != ".json":
        raise ValueError("payload_path must be one local JSON file under the derived namespace")

    schema_value, schema_bytes = _load_json_file(root, schema_source, "probe schema", MAX_SCHEMA_BYTES)
    payload_value, payload_bytes = _load_json_file(root, payload_source, "probe payload", MAX_PAYLOAD_BYTES)
    if not isinstance(schema_value, dict) or not isinstance(payload_value, dict):
        raise ValueError("probe schema and payload must be JSON objects")
    schema = schema_value
    payload = payload_value
    exact_digest = "sha256:" + hashlib.sha256(schema_bytes).hexdigest()
    if descriptor["schema_sha256"] != exact_digest:
        raise ValueError("extension descriptor digest does not match exact raw schema bytes")
    _audit_schema_references(schema)
    _validate_schema_shape(schema)
    issues = validate_payload(payload, schema)
    if issues:
        raise ValueError("probe payload does not match its local schema: " + "; ".join(issues))
    forbidden_fields = {"equipment", "semantic_kind", "short_rule", "long_rule", "lua", "runtime"}
    if forbidden_fields.intersection(payload):
        raise ValueError("probe payload contains a forbidden formal/runtime field")
    return AdapterInputs(
        metadata=metadata,
        definition=definition,
        schema=schema,
        payload=payload,
        metadata_bytes=metadata_bytes,
        adapter_bytes=adapter_bytes,
        schema_bytes=schema_bytes,
        payload_bytes=payload_bytes,
    )


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_string_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def render_platform_v2_manifest(inputs: AdapterInputs) -> bytes:
    source = inputs.definition["v2_manifest"]
    descriptor = inputs.definition["extension_descriptor"]
    lines = [
        "schema_version = 2",
        'artifact_type = "package"',
        f"package_id = {_toml_string(inputs.definition['platform_package_id'])}",
        f"package_kind = {_toml_string(source['package_kind'])}",
        f"version = {_toml_string(inputs.metadata['package']['version'])}",
        f"display_name = {_toml_string(source['display_name'])}",
        "",
        "[build]",
        f"source = {_toml_string(source['build']['source'])}",
        f"revision = {_toml_string(source['build']['revision'])}",
        f"builder = {_toml_string(source['build']['builder'])}",
        "",
        "[rights]",
        f"authors = {_toml_string_array(source['rights']['authors'])}",
        f"source = {_toml_string(source['rights']['source'])}",
        f"license_expression = {_toml_string(source['rights']['license_expression'])}",
        "",
        "[capabilities]",
        f"required = {_toml_string_array(source['capabilities']['required'])}",
        "",
        "[[extensions]]",
        f"namespace = {_toml_string(descriptor['namespace'])}",
        f"required = {str(descriptor['required']).lower()}",
        f"contract_version = {descriptor['contract_version']}",
        f"schema_path = {_toml_string(descriptor['schema_path'])}",
        f"schema_sha256 = {_toml_string(descriptor['schema_sha256'])}",
        f"payload_path = {_toml_string(descriptor['payload_path'])}",
        f"host_api_major = {descriptor['host_api_major']}",
        f"host_api_min_minor = {descriptor['host_api_min_minor']}",
        f"host_api_max_minor = {descriptor['host_api_max_minor']}",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def compute_source_tree_sha256(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        data = files[path]
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def source_project_files(source_root: Path = SOURCE_ROOT) -> tuple[dict[str, bytes], bytes, str, str]:
    inputs = load_adapter_inputs(source_root)
    descriptor = inputs.definition["extension_descriptor"]
    files = {
        "package.toml": render_platform_v2_manifest(inputs),
        ADAPTER_OUTPUT.as_posix(): inputs.adapter_bytes,
        METADATA_OUTPUT.as_posix(): inputs.metadata_bytes,
        descriptor["schema_path"]: inputs.schema_bytes,
        descriptor["payload_path"]: inputs.payload_bytes,
    }
    if len(files) > MAX_PROJECT_FILES:
        raise ValueError(f"project file count exceeds {MAX_PROJECT_FILES}")
    _ensure_unique_portable_paths(tuple(files))
    files = dict(sorted(files.items()))
    source_tree = compute_source_tree_sha256(files)
    lock = {
        "schema_version": "rules-residue.source-exact-lock/1.0",
        "candidate_kind": "SOURCE_ONLY_MINIMAL_COMPATIBILITY_ADAPTER_NOT_ACCEPTED",
        "adapter_id": ADAPTER_ID,
        "platform_acceptance": inputs.metadata["platform_acceptance"],
        "governance": inputs.metadata["governance"],
        "source_tree_sha256": source_tree,
        "project_files": [
            {
                "path": path,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "mode": "0644",
            }
            for path, data in files.items()
        ],
    }
    lock_bytes = _canonical_json_bytes(lock)
    candidate_identity = hashlib.sha256(
        b"R2-INT-010-POST-PLATFORM\0" + source_tree.encode("ascii") + b"\0" + hashlib.sha256(lock_bytes).hexdigest().encode("ascii")
    ).hexdigest()
    return files, lock_bytes, source_tree, candidate_identity


def build_source_fixture(output_root: Path, source_root: Path = SOURCE_ROOT) -> BuildResult:
    output_root = Path(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise ValueError(f"output root already exists: {output_root}")
    files, lock_bytes, source_tree, candidate_identity = source_project_files(source_root)
    project_root = output_root / "project"
    project_root.mkdir(parents=True, exist_ok=False, mode=0o755)
    project_root.chmod(0o755)
    for relative, data in files.items():
        path = project_root / PurePosixPath(relative)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        current = path.parent
        while current.is_relative_to(output_root) and current != output_root:
            current.chmod(0o755)
            current = current.parent
        path.write_bytes(data)
        path.chmod(0o644)
    source_lock = output_root / SOURCE_LOCK_NAME
    source_lock.write_bytes(lock_bytes)
    source_lock.chmod(0o644)
    output_root.chmod(0o755)
    return BuildResult(
        output_root=output_root,
        project_root=project_root,
        source_lock=source_lock,
        source_tree_sha256=source_tree,
        candidate_identity_sha256=candidate_identity,
        project_files=tuple(files),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the source-only post-platform R2-INT-010 adapter candidate")
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = REPOSITORY_ROOT / output_root
    try:
        result = build_source_fixture(output_root)
    except (OSError, ValueError) as error:
        print(f"post-platform adapter source build failed: {error}", file=sys.stderr)
        return 1
    print("artifact_kind: SOURCE_ONLY_MINIMAL_COMPATIBILITY_ADAPTER_CANDIDATE_NOT_ACCEPTED")
    print("platform_acceptance: PASS")
    print("rules_adapter_independent_acceptance: NOT_RUN")
    print("cross_repository_acceptance: NOT_RUN")
    print("r2_int_010: FAIL")
    print(f"project: {result.project_root}")
    print(f"source exact lock: {result.source_lock}")
    print(f"source tree sha256: {result.source_tree_sha256}")
    print(f"candidate identity sha256: {result.candidate_identity_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
