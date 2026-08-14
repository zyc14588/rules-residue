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

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.lib.common import GAME_PACKAGE_ROOT, PROJECT_ROOT
from tools.lib.schema_subset import validate


PROBE_SOURCE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "r2-int-010-rem-001"
ADAPTER_SOURCE_PATH = PurePosixPath("platform-v2-probe.json")
ADAPTER_PATH = PurePosixPath("adapters/platform-v2-probe.json")
PROBE_SUFFIX = "probe"
PROBE_ID = "R2-INT-010-REM-001"
PROBE_SCOPE_LABEL = (
    "R2-INT-010-REM-001 minimal capability probe / "
    "NOT formal M2-B002 semantics"
)
ADAPTER_SCHEMA_VERSION = "rules-residue.platform-v2-probe-adapter/1.0"
ADAPTER_ALGORITHM = "stable-package-id-dot-namespace-plus-probe-v1"
SOURCE_LOCK_NAME = "source-exact-lock.json"
MAX_ADAPTER_BYTES = 64 << 10
MAX_LEGACY_MANIFEST_BYTES = 64 << 10
MAX_SCHEMA_BYTES = 1 << 20
MAX_PAYLOAD_BYTES = 4 << 20
MAX_JSON_DEPTH = 64
MAX_JSON_NUMBER_BYTES = 128
MAX_JSON_EXPONENT = 308

_NAMESPACE_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?"
NAMESPACE_PATTERN = re.compile(rf"^{_NAMESPACE_LABEL}(?:\.{_NAMESPACE_LABEL}){{2,7}}$")
NAMESPACE_LABEL_PATTERN = re.compile(rf"^{_NAMESPACE_LABEL}$")
PLATFORM_PACKAGE_ID_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9.-]{0,126}[a-z0-9])?/"
    r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$"
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
JSON_EXPONENT_PATTERN = re.compile(r"[eE]([+-]?)([0-9]+)$")

_ADAPTER_KEYS = {
    "schema_version",
    "adapter_id",
    "artifact_role",
    "source_package_id",
    "platform_package_id",
    "namespace_derivation",
    "v2_manifest",
    "scope",
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
    pass


@dataclass(frozen=True)
class AdapterInputs:
    definition: dict[str, Any]
    legacy_manifest: dict[str, Any]
    schema: dict[str, Any]
    payload: dict[str, Any]
    adapter_bytes: bytes
    schema_bytes: bytes
    payload_bytes: bytes


@dataclass(frozen=True)
class BuildResult:
    output_root: Path
    project_root: Path
    source_lock: Path
    source_tree_sha256: str
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
    if exponent_match is not None:
        exponent = int(exponent_match.group(2))
        if exponent > MAX_JSON_EXPONENT:
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


def _guard_json_tree(value: Any, depth: int = 0) -> None:
    if isinstance(value, str):
        _reject_surrogates(value)
        return
    if isinstance(value, dict):
        if depth >= MAX_JSON_DEPTH:
            raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
        for key, child in value.items():
            _reject_surrogates(key)
            _guard_json_tree(child, depth + 1)
        return
    if isinstance(value, list):
        if depth >= MAX_JSON_DEPTH:
            raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH}")
        for child in value:
            _guard_json_tree(child, depth + 1)


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
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"{label} keys differ; missing={missing}, unknown={unknown}")
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
        dotted = stable_package_id.replace("/", ".")
    else:
        parts = stable_package_id.split(".")
        if len(parts) < 2 or any(not NAMESPACE_LABEL_PATTERN.fullmatch(part) for part in parts):
            raise ValueError("stable dotted package ID is not canonical")
        dotted = stable_package_id
    return dotted


def derive_extension_namespace(
    stable_package_id: str,
    suffix: str = PROBE_SUFFIX,
) -> str:
    """Derive a generic extension namespace without consulting package identity tables."""

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
    """Map a canonical stable dotted/slash identity to the generic v2 slash form."""

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
    if len(base) == 4 and base[:3] in {"COM", "LPT"}:
        return base[3] in "123456789\u00b9\u00b2\u00b3"
    return False


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
    segments = text.split("/")
    for segment in segments:
        if segment in {"", ".", ".."}:
            raise ValueError(f"{label} contains an empty, dot, or parent segment")
        if segment.strip() != segment:
            raise ValueError(f"{label} segment has leading or trailing whitespace")
        if segment.endswith("."):
            raise ValueError(f"{label} segment has a trailing dot")
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


def _audit_schema_references(value: Any) -> None:
    if isinstance(value, dict):
        for keyword in ("$dynamicRef", "$recursiveRef"):
            if keyword in value:
                raise ValueError(f"probe schema forbids {keyword}")
        if "$ref" in value:
            reference = value["$ref"]
            if not isinstance(reference, str) or not reference.startswith("#"):
                raise ValueError("probe schema $ref must be a same-document fragment")
        for child in value.values():
            _audit_schema_references(child)
    elif isinstance(value, list):
        for child in value:
            _audit_schema_references(child)


def _validate_v2_manifest_source(value: Any) -> dict[str, Any]:
    manifest = _require_exact_keys(
        value,
        {"package_kind", "display_name", "build", "rights", "capabilities"},
        "adapter v2_manifest",
    )
    if manifest["package_kind"] != "library":
        raise ValueError("minimal probe v2 package_kind must remain library")
    _require_nonblank(manifest["display_name"], "adapter v2 display_name")
    build = _require_exact_keys(
        manifest["build"], {"source", "revision", "builder"}, "adapter v2 build"
    )
    for key in sorted(build):
        _require_nonblank(build[key], f"adapter v2 build.{key}")
    rights = _require_exact_keys(
        manifest["rights"],
        {"authors", "source", "license_expression"},
        "adapter v2 rights",
    )
    authors = rights["authors"]
    if (
        not isinstance(authors, list)
        or not authors
        or any(not isinstance(item, str) or not item.strip() for item in authors)
        or authors != sorted(set(authors))
    ):
        raise ValueError("adapter v2 rights.authors must be a sorted unique nonempty string array")
    _require_nonblank(rights["source"], "adapter v2 rights.source")
    _require_nonblank(rights["license_expression"], "adapter v2 rights.license_expression")
    capabilities = _require_exact_keys(
        manifest["capabilities"], {"required"}, "adapter v2 capabilities"
    )
    if capabilities["required"] != []:
        raise ValueError("minimal probe must not request Host runtime capabilities")
    return manifest


def load_adapter_inputs(
    source_root: Path = PROBE_SOURCE_ROOT,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> AdapterInputs:
    root = _validated_real_directory(source_root, "probe fixture root")
    legacy_root = _validated_real_directory(game_package_root, "game-package root")
    definition_value, adapter_bytes = _load_json_file(
        root,
        ADAPTER_SOURCE_PATH,
        "platform v2 probe adapter",
        MAX_ADAPTER_BYTES,
    )
    definition = _require_exact_keys(definition_value, _ADAPTER_KEYS, "probe adapter")
    if definition["schema_version"] != ADAPTER_SCHEMA_VERSION:
        raise ValueError("probe adapter schema_version changed")
    if definition["adapter_id"] != PROBE_ID:
        raise ValueError("probe adapter identity changed")
    if definition["artifact_role"] != "MINIMAL_CAPABILITY_PROBE_SOURCE_NOT_CREATOR_EVIDENCE":
        raise ValueError("probe adapter artifact role is not a source-only boundary")

    legacy_value, _ = _load_json_file(
        legacy_root,
        PurePosixPath("manifest.json"),
        "legacy package manifest",
        MAX_LEGACY_MANIFEST_BYTES,
    )
    if not isinstance(legacy_value, dict):
        raise ValueError("legacy package manifest must be an object")
    legacy_manifest = legacy_value
    source_package_id = _require_nonblank(
        definition["source_package_id"], "adapter source_package_id"
    )
    if legacy_manifest.get("id") != source_package_id:
        raise ValueError("adapter source_package_id does not match the stable legacy manifest ID")

    namespace_source = _require_exact_keys(
        definition["namespace_derivation"],
        {"algorithm", "suffix", "derived_namespace"},
        "namespace derivation",
    )
    if namespace_source["algorithm"] != ADAPTER_ALGORITHM:
        raise ValueError("namespace derivation algorithm changed")
    suffix = _require_nonblank(namespace_source["suffix"], "namespace derivation suffix")
    derived_namespace = derive_extension_namespace(source_package_id, suffix)
    if namespace_source["derived_namespace"] != derived_namespace:
        raise ValueError("declared namespace does not match generic deterministic derivation")
    if definition["platform_package_id"] != derive_platform_package_id(source_package_id):
        raise ValueError("declared platform package ID does not match deterministic derivation")

    scope = _require_exact_keys(
        definition["scope"], {"label", "formal_B002", "formal_B009"}, "probe scope"
    )
    if scope != {
        "label": PROBE_SCOPE_LABEL,
        "formal_B002": False,
        "formal_B009": False,
    }:
        raise ValueError("probe scope must remain explicitly non-formal B002/B009")
    _validate_v2_manifest_source(definition["v2_manifest"])

    descriptor = _require_exact_keys(
        definition["extension_descriptor"], _DESCRIPTOR_KEYS, "extension descriptor"
    )
    if descriptor["namespace"] != derived_namespace:
        raise ValueError("extension descriptor namespace differs from derived namespace")
    if descriptor["required"] is not True:
        raise ValueError("minimal editable probe extension must be required")
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
    if _portable_collision_key(schema_path.as_posix()) == _portable_collision_key(
        payload_path.as_posix()
    ):
        raise ValueError("schema_path and payload_path collide under portable comparison")
    prefix = PurePosixPath("extensions") / derived_namespace
    if schema_path.parent != prefix or schema_path.suffixes[-2:] != [".schema", ".json"]:
        raise ValueError("schema_path must be a local schema under the derived namespace")
    if payload_path.parent != prefix or payload_path.suffix != ".json" or payload_path == schema_path:
        raise ValueError("payload_path must be distinct local JSON under the derived namespace")

    schema_value, schema_bytes = _load_json_file(
        root, PurePosixPath(schema_path.name), "probe schema", MAX_SCHEMA_BYTES
    )
    payload_value, payload_bytes = _load_json_file(
        root, PurePosixPath(payload_path.name), "probe payload", MAX_PAYLOAD_BYTES
    )
    if not isinstance(schema_value, dict) or not isinstance(payload_value, dict):
        raise ValueError("probe schema and payload must be JSON objects")
    schema = schema_value
    payload = payload_value
    exact_digest = "sha256:" + hashlib.sha256(schema_bytes).hexdigest()
    if descriptor["schema_sha256"] != exact_digest:
        raise ValueError("extension descriptor digest does not match exact raw schema bytes")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("probe schema must declare Draft 2020-12")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError("probe schema must be a closed object")
    _audit_schema_references(schema)
    if PROBE_SCOPE_LABEL not in str(schema.get("title", "")):
        raise ValueError("probe schema is missing the explicit non-formal scope label")
    issues = validate(payload, schema)
    if issues:
        raise ValueError("probe payload does not match its local schema: " + "; ".join(map(str, issues)))
    if payload.get("probe_id") != PROBE_ID:
        raise ValueError("probe payload identity changed")
    if payload.get("formal_B002") is not False or payload.get("formal_B009") is not False:
        raise ValueError("probe payload must keep formal_B002=false and formal_B009=false")
    forbidden_fields = {"equipment", "semantic_kind", "short_rule", "long_rule", "lua", "runtime"}
    if forbidden_fields.intersection(payload):
        raise ValueError("probe payload contains a forbidden formal/runtime field")

    return AdapterInputs(
        definition=definition,
        legacy_manifest=legacy_manifest,
        schema=schema,
        payload=payload,
        adapter_bytes=adapter_bytes,
        schema_bytes=schema_bytes,
        payload_bytes=payload_bytes,
    )


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_string_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def render_platform_v2_manifest(inputs: AdapterInputs) -> bytes:
    definition = inputs.definition
    source = definition["v2_manifest"]
    descriptor = definition["extension_descriptor"]
    version = _require_nonblank(inputs.legacy_manifest.get("version"), "legacy package version")
    lines = [
        "schema_version = 2",
        'artifact_type = "package"',
        f"package_id = {_toml_string(definition['platform_package_id'])}",
        f"package_kind = {_toml_string(source['package_kind'])}",
        f"version = {_toml_string(version)}",
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


def source_project_files(
    source_root: Path = PROBE_SOURCE_ROOT,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> tuple[dict[str, bytes], bytes]:
    inputs = load_adapter_inputs(source_root, game_package_root)
    descriptor = inputs.definition["extension_descriptor"]
    files = {
        "package.toml": render_platform_v2_manifest(inputs),
        ADAPTER_PATH.as_posix(): inputs.adapter_bytes,
        descriptor["schema_path"]: inputs.schema_bytes,
        descriptor["payload_path"]: inputs.payload_bytes,
    }
    version = inputs.legacy_manifest["version"]
    platform_package_id = inputs.definition["platform_package_id"]
    source_lock = {
        "schema_version": 1,
        "root": platform_package_id,
        "packages": [
            {
                "package_id": platform_package_id,
                "version": version,
                "content_hash": "sha256:" + "0" * 64,
                "features": [],
                "dependencies": [],
            }
        ],
    }
    lock_bytes = json.dumps(source_lock, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return dict(sorted(files.items())), lock_bytes


def compute_source_tree_sha256(files: dict[str, bytes], lock_bytes: bytes) -> str:
    entries = {f"project/{path}": data for path, data in files.items()}
    entries[SOURCE_LOCK_NAME] = lock_bytes
    digest = hashlib.sha256()
    for path in sorted(entries):
        data = entries[path]
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_source_fixture(
    output_root: Path,
    source_root: Path = PROBE_SOURCE_ROOT,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> BuildResult:
    if output_root.exists() or output_root.is_symlink():
        raise ValueError(f"output root already exists: {output_root}")
    files, lock_bytes = source_project_files(source_root, game_package_root)
    project_root = output_root / "project"
    project_root.mkdir(parents=True, exist_ok=False)
    for relative, data in files.items():
        path = project_root / PurePosixPath(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o644)
    source_lock = output_root / SOURCE_LOCK_NAME
    source_lock.write_bytes(lock_bytes)
    source_lock.chmod(0o644)
    return BuildResult(
        output_root=output_root,
        project_root=project_root,
        source_lock=source_lock,
        source_tree_sha256=compute_source_tree_sha256(files, lock_bytes),
        project_files=tuple(files),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-only R2-INT-010-REM-001 platform v2 probe fixture"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
        help="new directory for project/ and source-exact-lock.json",
    )
    args = parser.parse_args()
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = PROJECT_ROOT / output_root
    try:
        result = build_source_fixture(output_root)
    except (OSError, ValueError) as error:
        print(f"platform v2 probe source build failed: {error}", file=sys.stderr)
        return 1
    print("artifact_kind: SOURCE_PROJECT_AND_EXACT_LOCK_SEED_NOT_PLATFORM_ARCHIVE")
    print("creator_or_host_evidence: false")
    print(f"project: {result.project_root}")
    print(f"source exact-lock seed: {result.source_lock}")
    print(f"source tree sha256: {result.source_tree_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
