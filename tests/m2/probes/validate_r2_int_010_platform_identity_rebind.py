#!/usr/bin/env python3
"""Fail-closed validator for the fresh M1-B011 Platform identity rebind."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]

TASK_ID = "M1-B011-RULES-PLATFORM-IDENTITY-REBIND-RETRY-002"
EVIDENCE_ID = "R2-INT-010-PLATFORM-IDENTITY-REBIND-B011-RETRY-002"
SOURCE_COMMIT = "1aede3667cd9bebee759ca8edab4289f5129e43e"
SOURCE_TREE = "5cab85e4a1d7547288982b03e0a65f20c51d65c2"
RULES_ADAPTER_COMMIT = "455cd5d66c683565a4aad7ef8d6523421d37db71"
RULES_ADAPTER_TREE = "d74aae0baf791566a770ef1aaed2da7562f681d5"
TRANSITION_COMMIT = "be1f8dca3c694c9b93a3193348772ae750fc77e1"
TRANSITION_TREE = "e4ad6e4f5ad4f672c827b1f37c1980b7655353d6"
OLD_PLATFORM_COMMIT = "1339c490bd8cae1e2a6e6607fc0f1db019faab64"
OLD_PLATFORM_TREE = "25d5645caf883a73f165db0179accbca48ddf526"
NEW_PLATFORM_COMMIT = "b82d52571287d9d0ebcfa589fd575125ac578476"
NEW_PLATFORM_TREE = "b9be959f22a8b15080a1035fba0fb46c256edf62"
NEW_PLATFORM_PARENT = "54f5dea3438d32a04a14f8888347aa3dfc222ee9"
VERIFYING_COMMIT = "412111c05c087ed066a297304bed728870f03fc8"
VERIFYING_TREE = "a77015feee62564ec8ec9744391a3b5de83e4217"
FRESH_ACCEPT_TASK = "M1-B011-PLATFORM-ACCEPTANCE-EVIDENCE-REISSUE-001"
FRESH_ACCEPT_RESULT = "PASS_M1_B011_PLATFORM_ACCEPTANCE_EVIDENCE_REISSUED"
HISTORICAL_ACCEPT_RESULT = "PASS_M1_B011_PLATFORM_ACCEPTED"
PLATFORM_ACCEPT_ROUTE = "aee21ae041faad20ba96379d7d2c9ecfae0cef372d40e3265cd08f03e7a1f081"
FRESH_EVIDENCE_ROOT = "865a244e234dadb0f919fd42645b44ee74129c1e01b81d4736615bbe0659ea40"
HISTORICAL_EVIDENCE_ROOT = "112dfdd0d93ba936fba31108006c166ae21ea86a2e090b9dbac611fcca93e9a9"
FRESH_ARCHIVE_SHA256 = "21ecfa011cee94197670e12f13c94201276585362e66fbed1c96a7c485f5d5dd"
FRESH_CREATOR_SHA256 = "5b54b2d5c9db302baf965da0e5061b427652e2a7c58a2f647bf5d8a98e36bb55"
HISTORICAL_CREATOR_SHA256 = "6158fe53646fc3d53f87f48ef675d0dc727806e24a0ee195d0992dd28681af87"
DETERMINISTIC_PRODUCT_SHA256 = "35de290d80f307b19548595c6e26b160b34cda012e1dd0343aa88c522a0810cc"
HISTORICAL_VERDICT_SHA256 = "099aaa7244b4a443e31bcdb733bbef2728de11b5129382328b4274ffe2534185"
BASE_ROUTE_BINDING = "df9b03d0fbbdbcfbf330b43b8f40640b9ce1053135798c4c7b5b05c8c7185dac"
BLOCKING_IDS = ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"]

AUDIT_ROOT = Path(
    "/home/zyc14588/secs/audit/"
    "TRPG_PLATFORM-M1-B011-PLATFORM-ACCEPTANCE-REISSUE-001"
)
PLATFORM_ARCHIVE_OVERRIDE = os.environ.get("M1_B011_PLATFORM_ACCEPTANCE_ARCHIVE")
PLATFORM_AUTHORITY_ARCHIVE_PATH = (
    AUDIT_ROOT / "TRPG_PLATFORM-M1-B011-PLATFORM-ACCEPTANCE-REISSUE-001.zip"
)
PLATFORM_ARCHIVE_PATH = (
    Path(PLATFORM_ARCHIVE_OVERRIDE)
    if PLATFORM_ARCHIVE_OVERRIDE
    else PLATFORM_AUTHORITY_ARCHIVE_PATH
)
PLATFORM_MANIFEST_PATH = AUDIT_ROOT / "payload-manifest.json"
SIGNING_PUBLIC_KEY_PATH = Path("/home/zyc14588/.ssh/id_ed25519.pub")
SIGNING_KEY_FINGERPRINT = "SHA256:zR55HATrI3+mzVZW3uc8MsCxE+g5fyImXdD8X7WKkt4"

SCHEMA_PATH_TEXT = "docs/implementation/m2/probes/r2-int-010-platform-identity-rebind-v1.schema.json"
EVIDENCE_DIR = "reports/m2/probes/external/r2-int-010-platform-identity-rebind"
PLATFORM_PATH_TEXT = f"{EVIDENCE_DIR}/platform-acceptance.json"
REBIND_PATH_TEXT = f"{EVIDENCE_DIR}/rebind.json"
MANIFEST_PATH_TEXT = f"{EVIDENCE_DIR}/evidence-manifest.json"
EXECUTION_PATH_TEXT = f"{EVIDENCE_DIR}/execution-records.json"
INDEX_V2_PATH_TEXT = "reports/m2/probes/external-evidence-index-v2.json"
INDEX_V3_PATH_TEXT = "reports/m2/probes/external-evidence-index-v3.json"
VALIDATOR_PATH_TEXT = "tests/m2/probes/validate_r2_int_010_platform_identity_rebind.py"
TEST_PATH_TEXT = "tests/m2/probes/test_r2_int_010_platform_identity_rebind.py"
M2_CLOSEOUT_TEST_PATH_TEXT = "tests/m2/probes/test_m2_b001_recovery_closeout.py"
M2_CLOSEOUT_VALIDATOR_PATH_TEXT = "tests/m2/probes/validate_m2_b001_recovery_closeout.py"
PRECONTENT_VALIDATOR_PATH_TEXT = "tools/validate_precontent_readiness.py"
STORY_TEST_PATH_TEXT = "tests/test_story_construction_governance.py"
STORY_VALIDATOR_PATH_TEXT = "tools/validate_story_construction_governance.py"

SCHEMA_PATH = ROOT / SCHEMA_PATH_TEXT
PLATFORM_PATH = ROOT / PLATFORM_PATH_TEXT
REBIND_PATH = ROOT / REBIND_PATH_TEXT
MANIFEST_PATH = ROOT / MANIFEST_PATH_TEXT
EXECUTION_PATH = ROOT / EXECUTION_PATH_TEXT
INDEX_V2_PATH = ROOT / INDEX_V2_PATH_TEXT
INDEX_V3_PATH = ROOT / INDEX_V3_PATH_TEXT

PROTECTED_SIX_PATHS = (
    SCHEMA_PATH_TEXT,
    PLATFORM_PATH_TEXT,
    REBIND_PATH_TEXT,
    MANIFEST_PATH_TEXT,
    EXECUTION_PATH_TEXT,
    INDEX_V3_PATH_TEXT,
)
ALLOWED_NEW_PATHS = [
    *PROTECTED_SIX_PATHS,
    M2_CLOSEOUT_TEST_PATH_TEXT,
    VALIDATOR_PATH_TEXT,
    TEST_PATH_TEXT,
    M2_CLOSEOUT_VALIDATOR_PATH_TEXT,
    STORY_TEST_PATH_TEXT,
    PRECONTENT_VALIDATOR_PATH_TEXT,
    STORY_VALIDATOR_PATH_TEXT,
]
EXPECTED_CHANGE_TYPES = {
    path_text: "A" for path_text in (*PROTECTED_SIX_PATHS, VALIDATOR_PATH_TEXT, TEST_PATH_TEXT)
}
EXPECTED_CHANGE_TYPES.update(
    {
        path_text: "M"
        for path_text in (
            M2_CLOSEOUT_TEST_PATH_TEXT,
            M2_CLOSEOUT_VALIDATOR_PATH_TEXT,
            STORY_TEST_PATH_TEXT,
            PRECONTENT_VALIDATOR_PATH_TEXT,
            STORY_VALIDATOR_PATH_TEXT,
        )
    }
)
MANIFEST_ARTIFACT_PATHS = [
    SCHEMA_PATH_TEXT,
    PLATFORM_PATH_TEXT,
    REBIND_PATH_TEXT,
    EXECUTION_PATH_TEXT,
    INDEX_V3_PATH_TEXT,
    VALIDATOR_PATH_TEXT,
    TEST_PATH_TEXT,
]

HISTORICAL_HASHES = {
    INDEX_V2_PATH_TEXT: "0dd20ad375a40eb3854b3a5426b6666d7eca93ffd75cfb3a9be99c47f21c2627",
    "reports/m2/probes/external/r2-int-010-platform-acceptance/platform-acceptance.json": "bba1b6f68f30143938c2e22b7bc4a0366549ca1f90a0b81af477f13bd142841e",
    "reports/m2/probes/external/r2-int-010-platform-acceptance/evidence-manifest.json": "bfa8cd4c45f9ea183883798f5e3e35bed36306a44972ee807ac1248f345e988e",
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/cross-accept-verdict.json": HISTORICAL_VERDICT_SHA256,
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/cross-accept-verdict.manifest.json": "11e484b44776af6f5f845e5082185ee8fa61868e7610b4947013de9252aac060",
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json": "f2e9c48517cd9437aa464041f28b15e8ff96c8df8533c58fa8afb001d22fdd18",
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence-manifest.json": "02c10c84c64959e3c186c4aabde3fb82f129ce1c30f788eeaa13b8ff6745c480",
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/execution-records.json": "dc98a5c7f48a8325ba7312c9082f0d514d121e4dba4f931ae66d7c59b1f0db06",
    ".codex/state/MILESTONE_PLAN.yaml": "74da7cc866e0b3b1f3580d86df18c8c6d9724ff6131e5d35c155fc33a2f71c17",
}

# Canonical JSON digests are filled from the final checked-in records. They are
# semantic locks, while evidence-manifest.json supplies byte-level locks.
CANONICAL_SHA256 = {
    SCHEMA_PATH_TEXT: "b2cde23de70cd1907eb63dbfd805f0918e2338991cc6c09ca2c069940a31bc13",
    PLATFORM_PATH_TEXT: "491bf715f1571e7877d2ab5346a12c8b82b41041e2aae05361976dd18bb9dac5",
    REBIND_PATH_TEXT: "2463b1e1b15ed25d24b377468917369907c6cd5c89dfed617cbfb2ff76989352",
    EXECUTION_PATH_TEXT: "c961cd19efa4b5fc3a6a4d71503afef77170a8847fcadd5a092c38ca2b7e4a95",
    INDEX_V3_PATH_TEXT: "6b76c2c7d6986ef990e967c311d5ca491a70252e7a7e79284771059bc503f726",
}

REQUIRED_EXECUTION_OPERATIONS = [
    "VERIFY_RETRY_WORKTREE_IDENTITY",
    "VERIFY_FRESH_ARCHIVE_SHA_AND_REPORTED_ROOT",
    "VERIFY_ARCHIVE_ONLY_EVIDENCE_ROOT_AND_PAYLOAD",
    "VERIFY_NATIVE_RULES_IMPLEMENT_ROUTE",
    "VERIFY_CURRENT_R4_AUTHORITY_BASELINE",
    "VALIDATE_REBIND_CANDIDATE",
    "RUN_REBIND_ADVERSARIAL_SUITE",
    "VALIDATE_HISTORICAL_TRANSITION",
    "RUN_M2_CLOSEOUT_PROBE_SUITE",
    "RUN_DIRTY_REPOSITORY_BRIDGE",
    "VALIDATE_STORY_GOVERNANCE",
    "RUN_JUST_VALIDATE",
    "RUN_JUST_TEST",
    "RUN_JUST_CODEX_CHECK",
    "RUN_GIT_DIFF_CHECK",
]


class RebindValidationError(ValueError):
    """Raised when rebind evidence is stale, mutable, or overclaims."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RebindValidationError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_constant(value: str) -> None:
    raise RebindValidationError(f"non-finite JSON constant is forbidden: {value}")


def load_json_text(text: str, context: str = "JSON evidence") -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise RebindValidationError(f"cannot load {context}: {exc}") from exc
    require(isinstance(value, dict), f"{context} must be an object")
    return value


def load_json_bytes(raw: bytes, context: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise RebindValidationError(f"cannot decode {context} as UTF-8: {exc}") from exc
    return load_json_text(text, context)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_text(path.read_text(encoding="utf-8"), str(path))
    except (OSError, UnicodeError) as exc:
        raise RebindValidationError(f"cannot load {path}: {exc}") from exc


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_path(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise RebindValidationError(f"cannot hash {path}: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def exact_keys(value: dict[str, Any], expected: Iterable[str], context: str) -> None:
    require(set(value) == set(expected), f"{context} fields are missing or unknown")


def full_sha1(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def full_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _schema_objects_are_closed(value: Any, context: str = "schema") -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            require(value.get("additionalProperties") is False, f"{context} object schema is not closed")
        for key, child in value.items():
            _schema_objects_are_closed(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _schema_objects_are_closed(child, f"{context}[{index}]")


def _resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    require(reference.startswith("#/"), f"non-local schema ref forbidden: {reference}")
    value: Any = root_schema
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        require(isinstance(value, dict) and token in value, f"unresolved schema ref: {reference}")
        value = value[token]
    require(isinstance(value, dict), f"schema ref does not resolve to object: {reference}")
    return value


def _json_equal(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":")
    )


def validate_schema_instance(
    schema: dict[str, Any],
    instance: Any,
    root_schema: dict[str, Any],
    context: str = "$",
) -> None:
    if "$ref" in schema:
        validate_schema_instance(_resolve_ref(root_schema, schema["$ref"]), instance, root_schema, context)
        return
    if "const" in schema:
        require(_json_equal(instance, schema["const"]), f"{context} violates const")
    if "enum" in schema:
        require(any(_json_equal(instance, item) for item in schema["enum"]), f"{context} violates enum")
    schema_type = schema.get("type")
    if schema_type == "object":
        require(isinstance(instance, dict), f"{context} must be object")
        required = schema.get("required", [])
        require(set(required).issubset(instance), f"{context} required fields missing")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            require(set(instance).issubset(properties), f"{context} contains unknown fields")
        for key, child in properties.items():
            if key in instance:
                validate_schema_instance(child, instance[key], root_schema, f"{context}.{key}")
    elif schema_type == "array":
        require(isinstance(instance, list), f"{context} must be array")
        require(len(instance) >= schema.get("minItems", 0), f"{context} has too few items")
        if "maxItems" in schema:
            require(len(instance) <= schema["maxItems"], f"{context} has too many items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in instance]
            require(len(encoded) == len(set(encoded)), f"{context} items are not unique")
        prefix = schema.get("prefixItems", [])
        for index, child in enumerate(prefix):
            if index < len(instance):
                validate_schema_instance(child, instance[index], root_schema, f"{context}[{index}]")
        items = schema.get("items")
        if items is False:
            require(len(instance) <= len(prefix), f"{context} has forbidden trailing items")
        elif isinstance(items, dict):
            for index in range(len(prefix), len(instance)):
                validate_schema_instance(items, instance[index], root_schema, f"{context}[{index}]")
    elif schema_type == "string":
        require(isinstance(instance, str), f"{context} must be string")
        if "pattern" in schema:
            require(re.fullmatch(schema["pattern"], instance) is not None, f"{context} violates pattern")
    elif schema_type == "boolean":
        require(isinstance(instance, bool), f"{context} must be boolean")
    elif schema_type == "integer":
        require(isinstance(instance, int) and not isinstance(instance, bool), f"{context} must be integer")


def validate_schema(schema: dict[str, Any]) -> None:
    require(canonical_sha256(schema) == CANONICAL_SHA256[SCHEMA_PATH_TEXT], "rebind Schema semantics changed")
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "Schema draft changed")
    require(
        schema.get("$id")
        == "https://rules-residue.invalid/schemas/r2-int-010-platform-identity-rebind-v1.schema.json",
        "Schema identity changed",
    )
    require(schema.get("additionalProperties") is False, "Schema top-level is not fail-closed")
    _schema_objects_are_closed(schema)
    require(schema["$defs"]["sha1"] == {"type": "string", "pattern": "^[0-9a-f]{40}$"}, "SHA-1 schema format changed")
    require(schema["$defs"]["sha256"] == {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "SHA-256 schema format changed")


def _safe_archive_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and "\\" not in name and "\x00" not in name and not path.is_absolute() and ".." not in path.parts and path.as_posix() == name


def validate_platform_archive(
    archive_path: Path = PLATFORM_ARCHIVE_PATH,
    *,
    expected_archive_sha256: str = FRESH_ARCHIVE_SHA256,
) -> dict[str, Any]:
    require(archive_path.is_absolute(), "persistent Platform archive path must be absolute")
    try:
        archive_mode = archive_path.lstat().st_mode
    except OSError as exc:
        raise RebindValidationError(f"cannot stat persistent Platform archive: {exc}") from exc
    require(stat.S_ISREG(archive_mode) and not archive_path.is_symlink(), "persistent Platform archive is not a regular file")
    raw_archive = archive_path.read_bytes()
    actual_archive_sha256 = sha256_bytes(raw_archive)
    require(actual_archive_sha256 == expected_archive_sha256, "fresh Platform archive SHA-256 changed")

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw_archive), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise RebindValidationError(f"cannot open persistent Platform archive: {exc}") from exc

    with archive:
        infos = archive.infolist()
        names: list[str] = []
        info_by_name: dict[str, zipfile.ZipInfo] = {}
        for info in infos:
            name = info.filename
            require(_safe_archive_name(name), f"unsafe archive member path: {name}")
            require(name not in info_by_name, f"duplicate archive member: {name}")
            mode = info.external_attr >> 16
            require(not info.is_dir() and stat.S_ISREG(mode), f"archive member is symlink or nonregular: {name}")
            info_by_name[name] = info
            names.append(name)

        control_names = {"ROOT_SHA256", "payload-manifest.json", "summary.md"}
        require(control_names.issubset(info_by_name), "archive control payload is incomplete")
        manifest_raw = archive.read("payload-manifest.json")
        manifest = load_json_bytes(manifest_raw, "archive payload-manifest.json")
        exact_keys(
            manifest,
            {"schema_version", "task_id", "product_commit", "product_tree", "verifying_commit", "artifacts"},
            "archive payload manifest",
        )
        require(manifest["schema_version"] == "trpg-platform.acceptance-evidence-manifest/1.0", "Platform manifest schema changed")
        require(manifest["task_id"] == FRESH_ACCEPT_TASK, "Platform manifest task changed")
        require(manifest["product_commit"] == NEW_PLATFORM_COMMIT, "Platform manifest product commit changed")
        require(manifest["product_tree"] == NEW_PLATFORM_TREE, "Platform manifest product tree changed")
        require(manifest["verifying_commit"] == VERIFYING_COMMIT, "Platform manifest verifying commit changed")

        artifacts = manifest["artifacts"]
        require(isinstance(artifacts, list) and artifacts, "Platform manifest artifacts are empty")
        registered: dict[str, dict[str, Any]] = {}
        for item in artifacts:
            require(isinstance(item, dict), "Platform manifest artifact entry must be object")
            exact_keys(item, {"path", "sha256", "size"}, "Platform manifest artifact")
            path_text = item["path"]
            require(isinstance(path_text, str) and path_text.startswith("payload/"), "Platform manifest artifact is outside payload/")
            require(_safe_archive_name(path_text), f"unsafe Platform manifest path: {path_text}")
            require(path_text not in registered, f"duplicate Platform manifest path: {path_text}")
            require(full_sha256(item["sha256"]), f"invalid Platform manifest SHA-256: {path_text}")
            require(isinstance(item["size"], int) and not isinstance(item["size"], bool) and item["size"] >= 0, f"invalid Platform manifest size: {path_text}")
            require(path_text in info_by_name, f"registered Platform payload missing: {path_text}")
            payload = archive.read(path_text)
            require(len(payload) == item["size"], f"Platform payload size mismatch: {path_text}")
            require(sha256_bytes(payload) == item["sha256"], f"Platform payload hash mismatch: {path_text}")
            registered[path_text] = item
        require(list(registered) == sorted(registered), "Platform manifest artifacts are not path-sorted")
        require(set(names) == set(registered) | control_names, "Platform archive contains unregistered payload")

        manifest_root = sha256_bytes(manifest_raw)
        try:
            reported_root = archive.read("ROOT_SHA256").decode("ascii").strip()
        except UnicodeError as exc:
            raise RebindValidationError("archive ROOT_SHA256 is not ASCII") from exc
        require(full_sha256(reported_root), "archive ROOT_SHA256 format is invalid")
        require(manifest_root == reported_root == FRESH_EVIDENCE_ROOT, "fresh Platform manifest root changed")

        def payload_json(path_text: str) -> dict[str, Any]:
            require(path_text in registered, f"identity payload is not manifest-registered: {path_text}")
            return load_json_bytes(archive.read(path_text), f"archive {path_text}")

        identity = payload_json("payload/identity.json")
        result = payload_json("payload/result-core.json")
        route = payload_json("payload/route.json")
        creator = payload_json("payload/creator/binary-identity.json")
        determinism = payload_json("payload/determinism.json")
        roundtrip = payload_json("payload/creator/roundtrip-result.json")

        require(identity["product_commit"] == NEW_PLATFORM_COMMIT, "archive product commit changed")
        require(identity["product_tree"] == NEW_PLATFORM_TREE, "archive product tree changed")
        require(identity["verifying_commit"] == VERIFYING_COMMIT, "archive verifying commit changed")
        require(identity["verifying_tree"] == VERIFYING_TREE, "archive verifying tree changed")
        require(identity["route_binding_sha256"] == PLATFORM_ACCEPT_ROUTE, "archive ACCEPT route binding changed")
        require(identity["historical_acceptance"] == {
            "original_payload_available": False,
            "reported_evidence_root": HISTORICAL_EVIDENCE_ROOT,
            "reported_root_reverified": False,
            "result": HISTORICAL_ACCEPT_RESULT,
        }, "archive historical acceptance disposition changed")
        require(result["task_id"] == FRESH_ACCEPT_TASK and result["result"] == "PASS", "archive reissuance result changed")
        require(result["fresh_reissuance"] is True, "archive is not marked as fresh reissuance")
        require(result["fresh_creator_binary_sha256"] == FRESH_CREATOR_SHA256, "archive fresh Creator changed")
        require(result["historical_creator_binary_sha256"] == HISTORICAL_CREATOR_SHA256, "archive historical Creator changed")
        require(result["creator_binary_reproducibility"] == "DIFFERENT", "archive binary reproducibility was overclaimed")
        require(result["source_identity_exact"] is True, "archive source identity is not exact")
        require(result["creator_roundtrip"] == "PASS" and result["full_regression"] == "PASS", "archive behavioral acceptance changed")
        require(route == {
            "batch": "M1-B011",
            "binding_digest": PLATFORM_ACCEPT_ROUTE,
            "check": "PASS",
            "milestone": "M1",
            "mode": "ACCEPT",
            "product_target": NEW_PLATFORM_COMMIT,
            "reading_map_sha256": "1e1b0e85b1080f2071a507933221ced5d95fbc00032103905d20002febab2090",
            "schema_version": "trpg-platform.acceptance-route/1.0",
            "source_commit": VERIFYING_COMMIT,
            "source_tree": VERIFYING_TREE,
            "state": "VERIFYING",
        }, "archive route identity changed")
        require(creator["binary_sha256_hex"] == FRESH_CREATOR_SHA256, "Creator payload SHA changed")
        require(creator["historical_binary_sha256"] == HISTORICAL_CREATOR_SHA256, "historical Creator payload SHA changed")
        require(creator["binary_reproducibility"] == "DIFFERENT", "Creator payload reproducibility changed")
        require(creator["source_identity_exact"] is True, "Creator source identity changed")
        require(registered["payload/creator/binary"]["sha256"] == FRESH_CREATOR_SHA256, "Creator binary artifact hash changed")
        require(determinism["run_1_sha256"] == DETERMINISTIC_PRODUCT_SHA256, "deterministic run 1 changed")
        require(determinism["run_2_sha256"] == DETERMINISTIC_PRODUCT_SHA256, "deterministic run 2 changed")
        require(determinism["historical_output_sha256"] == DETERMINISTIC_PRODUCT_SHA256, "historical deterministic output changed")
        require(determinism["run_bytes_identical"] is True and determinism["historical_output_match"] is True, "determinism disposition changed")
        require(roundtrip["result"] == "PASS" and roundtrip["run_bytes_identical"] is True, "Creator roundtrip changed")
        require(roundtrip["run_1_sha256"] == DETERMINISTIC_PRODUCT_SHA256, "roundtrip run 1 changed")
        require(roundtrip["run_2_sha256"] == DETERMINISTIC_PRODUCT_SHA256, "roundtrip run 2 changed")

    return {
        "archive_path": str(archive_path),
        "archive_sha256": actual_archive_sha256,
        "manifest_root_sha256": manifest_root,
        "artifact_count": len(registered),
        "product_commit": NEW_PLATFORM_COMMIT,
        "product_tree": NEW_PLATFORM_TREE,
        "verifying_commit": VERIFYING_COMMIT,
        "verifying_tree": VERIFYING_TREE,
        "route_binding": PLATFORM_ACCEPT_ROUTE,
        "fresh_creator_sha256": FRESH_CREATOR_SHA256,
        "deterministic_product_sha256": DETERMINISTIC_PRODUCT_SHA256,
    }


def validate_platform_acceptance(data: dict[str, Any], archive: dict[str, Any]) -> None:
    require(canonical_sha256(data) == CANONICAL_SHA256[PLATFORM_PATH_TEXT], "platform acceptance semantics changed")
    exact_keys(
        data,
        {
            "schema_version",
            "record_id",
            "task_id",
            "record_role",
            "historical_acceptance",
            "fresh_reissuance",
            "current_platform_identity",
            "creator_identity",
            "deterministic_product",
            "fresh_exact_pair_acceptance",
            "cross_repository_acceptance",
            "m1_b011_completion",
        },
        "platform acceptance",
    )
    require(data["schema_version"] == "rules-residue.m2.platform-acceptance-antecedent/3.0", "platform record schema changed")
    require(data["record_id"] == "M1-B011-PLATFORM-ACCEPTANCE-REISSUANCE-ANTECEDENT-001", "platform record ID changed")
    require(data["task_id"] == TASK_ID, "platform record task changed")
    require(data["record_role"] == "FRESH_PLATFORM_ACCEPTANCE_REISSUANCE_ANTECEDENT_ONLY", "platform record role changed")
    require(data["historical_acceptance"] == {
        "result": HISTORICAL_ACCEPT_RESULT,
        "reported_evidence_root": HISTORICAL_EVIDENCE_ROOT,
        "original_payload_available": False,
        "reported_root_reverified": False,
        "disposition": "HISTORICAL_REFERENCE_ONLY",
    }, "historical acceptance was reclassified or reverified")
    require(data["fresh_reissuance"] == {
        "task_id": FRESH_ACCEPT_TASK,
        "result": FRESH_ACCEPT_RESULT,
        "evidence_root_sha256": archive["manifest_root_sha256"],
        "evidence_root_definition": "SHA256_OF_PAYLOAD_MANIFEST_JSON_BYTES",
        "archive_path": str(PLATFORM_AUTHORITY_ARCHIVE_PATH),
        "archive_sha256": archive["archive_sha256"],
        "manifest_path": str(PLATFORM_MANIFEST_PATH),
        "archive_only_roundtrip": "PASS",
        "manifest_entry_hashes_verified": True,
    }, "fresh Platform reissuance binding changed")
    require(data["current_platform_identity"] == {
        "product": {
            "commit": NEW_PLATFORM_COMMIT,
            "tree": NEW_PLATFORM_TREE,
            "parent": NEW_PLATFORM_PARENT,
            "signature_verified": True,
        },
        "verifying_governance": {
            "commit": VERIFYING_COMMIT,
            "tree": VERIFYING_TREE,
            "parent": NEW_PLATFORM_COMMIT,
            "state": "VERIFYING",
            "signature_verified": True,
        },
        "accept_route_binding_digest": PLATFORM_ACCEPT_ROUTE,
    }, "platform product and VERIFYING governance identities changed or were swapped")
    require(data["creator_identity"] == {
        "current_creator_sha": FRESH_CREATOR_SHA256,
        "current_creator_role": "FRESH_CURRENT_AUTHORITY",
        "historical_creator_sha": HISTORICAL_CREATOR_SHA256,
        "historical_creator_role": "HISTORICAL_REFERENCE_ONLY",
        "binary_reproducibility": "DIFFERENT",
        "source_identity_exact": True,
        "fresh_behavioral_acceptance": "PASS",
        "creator_roundtrip": "PASS",
        "full_regression": "PASS",
    }, "fresh/historical Creator roles or behavioral acceptance changed")
    require(data["deterministic_product"] == {
        "run_1_sha256": DETERMINISTIC_PRODUCT_SHA256,
        "run_2_sha256": DETERMINISTIC_PRODUCT_SHA256,
        "historical_output_sha256": DETERMINISTIC_PRODUCT_SHA256,
        "runs_byte_identical": True,
        "historical_output_match": True,
    }, "deterministic product identity changed")
    require(data["fresh_exact_pair_acceptance"] == "NOT_RUN", "fresh exact-pair acceptance was overclaimed")
    require(data["cross_repository_acceptance"] == "NOT_RUN", "cross-repository acceptance was overclaimed")
    require(data["m1_b011_completion"] == "NOT_AUTHORIZED", "M1-B011 completion was overclaimed")


def validate_rebind(schema: dict[str, Any], data: dict[str, Any], archive: dict[str, Any]) -> None:
    require(canonical_sha256(data) == CANONICAL_SHA256[REBIND_PATH_TEXT], "rebind semantics changed")
    validate_schema_instance(schema, data, schema)
    require(data["rules_governance_authority"] == {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "interlock_repair": "ACCEPTED_UNCHANGED",
    }, "Rules governance authority changed")
    require(data["rules_adapter"]["commit"] == RULES_ADAPTER_COMMIT, "Rules adapter commit changed")
    require(data["rules_adapter"]["tree"] == RULES_ADAPTER_TREE, "Rules adapter tree changed")
    require(data["rules_adapter"]["commit"] != SOURCE_COMMIT, "current Rules governance HEAD substituted as adapter identity")
    require(data["effective_transition"] == {
        "commit": TRANSITION_COMMIT,
        "tree": TRANSITION_TREE,
        "effective_status": "RESOLVED_ADAPTER",
    }, "effective transition identity changed")
    require(data["previous_platform_identity"] == {"commit": OLD_PLATFORM_COMMIT, "tree": OLD_PLATFORM_TREE}, "historical platform identity changed")
    require(data["new_platform_identity"] == {"commit": NEW_PLATFORM_COMMIT, "tree": NEW_PLATFORM_TREE}, "new platform identity changed")
    roots = data["evidence_roots"]
    require(roots["current_evidence_root"] == archive["manifest_root_sha256"], "current evidence root is not the fresh archive root")
    require(roots["current_evidence_root"] != roots["historical_prior_evidence_root"], "current and historical evidence roots were collapsed")
    require(roots["historical_prior_evidence_root"] == HISTORICAL_EVIDENCE_ROOT, "historical evidence root changed")
    require(roots["historical_reported_root_reverified"] is False, "historical root was falsely claimed reverified")
    require(roots["historical_original_payload_available"] is False, "historical payload availability was falsely claimed")
    require(roots["current_archive_sha256"] == archive["archive_sha256"], "current archive binding changed")
    creators = data["creator_identities"]
    require(creators["current_creator_sha"] == archive["fresh_creator_sha256"], "current Creator is not fresh authority")
    require(creators["current_creator_sha"] != creators["historical_creator_sha"], "fresh and historical Creator identities were collapsed")
    require(creators["historical_creator_sha"] == HISTORICAL_CREATOR_SHA256, "historical Creator identity changed")
    require(creators["binary_reproducibility"] == "DIFFERENT", "Creator binary difference was falsely recorded as MATCH")
    require(creators["source_identity_exact"] is True and creators["fresh_behavioral_acceptance"] == "PASS", "fresh Creator behavioral evidence changed")
    require(data["deterministic_product"]["run_1_sha256"] == archive["deterministic_product_sha256"], "rebind deterministic product changed")
    require(data["effective_status_before"] == data["effective_status_after"] == "RESOLVED_ADAPTER", "status transition was forged")
    require(data["platform_identity_rebind"] == "RECORDED_NOT_CROSS_ACCEPTED", "rebind disposition overclaims acceptance")


def observed_historical_hashes() -> dict[str, str]:
    return {path_text: sha256_path(ROOT / path_text) for path_text in HISTORICAL_HASHES}


def validate_historical_artifacts(observed: dict[str, str] | None = None) -> None:
    hashes = observed if observed is not None else observed_historical_hashes()
    require(hashes == HISTORICAL_HASHES, "immutable historical artifact bytes changed")
    old_platform = load_json(ROOT / "reports/m2/probes/external/r2-int-010-platform-acceptance/platform-acceptance.json")
    require(old_platform["platform"]["code_commit"] == OLD_PLATFORM_COMMIT, "old platform antecedent commit changed")
    require(old_platform["platform"]["code_tree"] == OLD_PLATFORM_TREE, "old platform antecedent tree changed")
    verdict = load_json(ROOT / "reports/m2/probes/remediations/r2-int-010-post-platform-transition/cross-accept-verdict.json")
    require(verdict["result"] == "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED", "historical verdict changed")
    require(verdict["identity"]["rules_commit"] == RULES_ADAPTER_COMMIT, "historical pair Rules commit changed")
    require(verdict["identity"]["rules_tree"] == RULES_ADAPTER_TREE, "historical pair Rules tree changed")
    require(verdict["identity"]["platform_commit"] == OLD_PLATFORM_COMMIT, "historical pair Platform commit changed")
    require(verdict["identity"]["platform_tree"] == OLD_PLATFORM_TREE, "historical pair Platform tree changed")
    transition = load_json(ROOT / "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json")
    require(transition["new_status"] == "RESOLVED_ADAPTER", "historical transition status changed")
    state = load_json(ROOT / ".codex/state/MILESTONE_PLAN.yaml")
    require(state["state"] == "ACCEPTED", "M2-B001 lifecycle changed")
    projection = state["active_plan"]["lifecycle_projection"]
    require(projection["effective_R2-INT-010"] == "RESOLVED_ADAPTER", "effective R2-INT-010 changed")
    require(projection["formal_B002"] is False and projection["formal_B009"] is False, "formal B002/B009 changed")
    require(projection["M2-B002"] == {"state": "PLANNED", "implementation_state": "NOT_STARTED", "ready": "NO"}, "M2-B002 lifecycle/readiness changed")
    require(projection["blocking_ids"] == BLOCKING_IDS, "remaining blocker set changed")
    require(projection["global_active_WIP"] == 0, "global active WIP changed")


def validate_execution(data: dict[str, Any]) -> None:
    require(canonical_sha256(data) == CANONICAL_SHA256[EXECUTION_PATH_TEXT], "execution-record semantics changed")
    exact_keys(
        data,
        {
            "schema_version",
            "evidence_set_id",
            "task_id",
            "source_binding",
            "route_binding",
            "platform_archive_authority",
            "artifact_bindings",
            "records",
            "non_executions",
        },
        "execution records",
    )
    require(data["schema_version"] == "rules-residue.m2.r2-int-010-platform-identity-rebind-execution/2.0", "execution schema changed")
    require(data["evidence_set_id"] == EVIDENCE_ID and data["task_id"] == TASK_ID, "execution identity changed")
    require(data["source_binding"] == {"commit": SOURCE_COMMIT, "tree": SOURCE_TREE}, "execution source binding changed")
    require(data["route_binding"] == {
        "route_id": "M2-B001-EXTERNAL-PROBE-UPDATE-001",
        "mode": "IMPLEMENT",
        "milestone": "M2",
        "batch_id": "M2-B001",
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "binding_digest": BASE_ROUTE_BINDING,
        "check": "PASS",
    }, "IMPLEMENT route binding changed")
    require(data["platform_archive_authority"] == {
        "task_id": FRESH_ACCEPT_TASK,
        "result": FRESH_ACCEPT_RESULT,
        "archive_path": str(PLATFORM_AUTHORITY_ARCHIVE_PATH),
        "archive_sha256": FRESH_ARCHIVE_SHA256,
        "manifest_root_sha256": FRESH_EVIDENCE_ROOT,
        "validation_source": "PERSISTENT_ARCHIVE_ONLY",
    }, "execution archive authority changed")
    require(data["artifact_bindings"] == {
        "platform_acceptance_path": PLATFORM_PATH_TEXT,
        "platform_acceptance_sha256": sha256_path(PLATFORM_PATH),
        "rebind_path": REBIND_PATH_TEXT,
        "rebind_sha256": sha256_path(REBIND_PATH),
    }, "execution artifact binding changed")
    records = data["records"]
    require(isinstance(records, list) and len(records) == len(REQUIRED_EXECUTION_OPERATIONS), "execution records are incomplete")
    require([item.get("evidence_id") for item in records] == [f"REBIND-R{number:03d}" for number in range(1, len(records) + 1)], "execution record IDs are missing, duplicated, or reordered")
    require([item.get("operation") for item in records] == REQUIRED_EXECUTION_OPERATIONS, "required execution operation is missing or reordered")
    for item in records:
        exact_keys(item, {"evidence_id", "operation", "command", "exit_code", "execution_status", "observed"}, item.get("evidence_id", "execution record"))
        require(isinstance(item["command"], str) and item["command"], f"{item['evidence_id']} command missing")
        require(isinstance(item["observed"], dict) and item["observed"], f"{item['evidence_id']} observation missing")
        if item["operation"] == "VERIFY_CURRENT_R4_AUTHORITY_BASELINE":
            require(item["exit_code"] == 0, "current R4 authority baseline did not pass")
            require(item["execution_status"] == "PASS", "current R4 authority baseline was misclassified")
            require(item["observed"] == {
                "tests_run": 247,
                "failures": 0,
                "errors": 0,
                "r4_acceptance_regression_proof": "PASS",
                "prior_relevant_defect": "REPAIRED_BY_CURRENT_R4_AUTHORITY",
            }, "current R4 authority baseline observation changed")
        else:
            require(item["exit_code"] == 0 and item["execution_status"] == "PASS", f"{item['evidence_id']} did not pass")
    require(data["non_executions"] == {
        "fresh_exact_pair_acceptance": "NOT_RUN",
        "cross_repository_acceptance": "NOT_RUN",
        "m1_b011_completion": "NOT_AUTHORIZED",
        "formal_M2_B001_reopened": False,
    }, "execution records overclaim a non-executed gate")


def validate_index(v2: dict[str, Any], v3: dict[str, Any]) -> None:
    require(canonical_sha256(v3) == CANONICAL_SHA256[INDEX_V3_PATH_TEXT], "v3 index semantics changed")
    exact_keys(v3, {"schema_version", "index_id", "batch_id", "ordinal", "predecessor_index", "formal_batch", "evidence_chain", "authority_bindings", "projections", "policies", "resolution_rule"}, "v3 index")
    require(v3["predecessor_index"] == {
        "path": INDEX_V2_PATH_TEXT,
        "sha256": HISTORICAL_HASHES[INDEX_V2_PATH_TEXT],
        "schema_version": "rules-residue.m2.external-evidence-index/2.0",
        "last_evidence_ordinal": 4,
        "disposition": "IMMUTABLE_PREDECESSOR",
    }, "v2 predecessor binding changed")
    require(v3["formal_batch"] == v2["formal_batch"], "formal batch projection changed")
    require(v3["evidence_chain"][:-1] == v2["evidence_chain"], "v3 did not preserve the v2 evidence chain")
    require(v3["evidence_chain"][-1] == {
        "ordinal": 5,
        "evidence_id": EVIDENCE_ID,
        "nature": "ADDITIVE_PLATFORM_IDENTITY_REBIND",
        "path": REBIND_PATH_TEXT,
        "sha256": sha256_path(REBIND_PATH),
        "rules_adapter": {"commit": RULES_ADAPTER_COMMIT, "tree": RULES_ADAPTER_TREE},
        "platform": {"commit": NEW_PLATFORM_COMMIT, "tree": NEW_PLATFORM_TREE},
        "fresh_platform_evidence_root_sha256": FRESH_EVIDENCE_ROOT,
        "fresh_platform_evidence_archive_sha256": FRESH_ARCHIVE_SHA256,
        "fresh_creator_sha256": FRESH_CREATOR_SHA256,
        "disposition": "PENDING_FRESH_EXACT_PAIR_ACCEPTANCE",
    }, "v3 additive rebind entry changed")
    require(v3["authority_bindings"]["historical"] == v2["authority_bindings"], "historical authority binding changed")
    require(v3["authority_bindings"]["fresh_platform_identity_rebind"] == {
        "nature": "ADDITIVE_PLATFORM_IDENTITY_REBIND",
        "rules_adapter": {"commit": RULES_ADAPTER_COMMIT, "tree": RULES_ADAPTER_TREE},
        "previous_platform": {"commit": OLD_PLATFORM_COMMIT, "tree": OLD_PLATFORM_TREE},
        "new_platform": {"commit": NEW_PLATFORM_COMMIT, "tree": NEW_PLATFORM_TREE},
        "platform_verifying_governance": {"commit": VERIFYING_COMMIT, "tree": VERIFYING_TREE, "state": "VERIFYING"},
        "platform_acceptance": {
            "path": PLATFORM_PATH_TEXT,
            "sha256": sha256_path(PLATFORM_PATH),
            "task_id": FRESH_ACCEPT_TASK,
            "result": FRESH_ACCEPT_RESULT,
            "current_evidence_root_sha256": FRESH_EVIDENCE_ROOT,
            "archive_sha256": FRESH_ARCHIVE_SHA256,
        },
        "creator_identity": {
            "current_creator_sha256": FRESH_CREATOR_SHA256,
            "historical_creator_sha256": HISTORICAL_CREATOR_SHA256,
            "binary_reproducibility": "DIFFERENT",
            "source_identity_exact": True,
            "fresh_behavioral_acceptance": "PASS",
        },
        "deterministic_product_sha256": DETERMINISTIC_PRODUCT_SHA256,
    }, "fresh rebind authority binding changed")
    require(v3["projections"] == {
        "historical_R2_INT_010": "FAIL",
        "effective_R2_INT_010": "RESOLVED_ADAPTER",
        "fresh_platform_identity_rebind": "RECORDED_NOT_CROSS_ACCEPTED",
        "fresh_exact_pair_acceptance": "NOT_RUN",
        "formal_B002": False,
        "formal_B009": False,
        "M2_B002": "NOT_STARTED",
        "M2_B002_READY": "NO",
        "aggregate_M2_pass": False,
        "aggregate_external_capability_pass": False,
        "blocking_ids": BLOCKING_IDS,
    }, "v3 projection changed or overclaimed")
    require(v3["policies"] == {
        "formal_batch_reopened": False,
        "rules_adapter_product_identity": "UNCHANGED",
        "cross_repository_acceptance": "NOT_RUN",
        "m1_b011_completion": "NOT_AUTHORIZED",
        "evidence_evolution": "ADDITIVE_ONLY",
    }, "v3 policy changed or overclaimed")


def validate_manifest(data: dict[str, Any], archive: dict[str, Any]) -> None:
    exact_keys(data, {"schema_version", "evidence_set_id", "task_id", "external_authority", "artifacts", "immutable_historical_artifacts", "policies"}, "evidence manifest")
    require(data["schema_version"] == "rules-residue.m2.r2-int-010-platform-identity-rebind-manifest/2.0", "manifest schema changed")
    require(data["evidence_set_id"] == EVIDENCE_ID and data["task_id"] == TASK_ID, "manifest identity changed")
    require(data["external_authority"] == {
        "task_id": FRESH_ACCEPT_TASK,
        "result": FRESH_ACCEPT_RESULT,
        "archive_path": str(PLATFORM_AUTHORITY_ARCHIVE_PATH),
        "archive_sha256": archive["archive_sha256"],
        "manifest_root_sha256": archive["manifest_root_sha256"],
        "validation_source": "PERSISTENT_ARCHIVE_ONLY",
    }, "manifest external authority changed")
    expected_artifacts = [
        {
            "path": path_text,
            "sha256": sha256_path(ROOT / path_text),
            "size": (ROOT / path_text).stat().st_size,
        }
        for path_text in MANIFEST_ARTIFACT_PATHS
    ]
    require(data["artifacts"] == expected_artifacts, "new artifact missing, reordered, wrongly sized, or wrongly hashed")
    require(all(item["path"] != MANIFEST_PATH_TEXT for item in data["artifacts"]), "manifest contains a self-hash cycle")
    expected_historical = [
        {"path": path_text, "sha256": digest, "disposition": "IMMUTABLE_PREDECESSOR"}
        for path_text, digest in HISTORICAL_HASHES.items()
    ]
    require(data["immutable_historical_artifacts"] == expected_historical, "historical manifest coverage changed")
    require(data["policies"] == {
        "historical_mutation": "REJECT_ANY_CURRENT_BYTE_MISMATCH",
        "evidence_evolution": "ADDITIVE_ONLY",
        "formal_batch_reopened": False,
        "fresh_exact_pair_acceptance": "NOT_RUN",
        "cross_repository_acceptance": "NOT_RUN",
        "m1_b011_completion": "NOT_AUTHORIZED",
    }, "manifest policy changed or overclaimed")


def _git(args: list[str], *, check: bool = True) -> str:
    env = dict(os.environ)
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode != 0:
        raise RebindValidationError(
            f"git {' '.join(args)} failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return completed.stdout.rstrip("\n")


def _require_existing_new_files_are_regular() -> None:
    for path_text in ALLOWED_NEW_PATHS:
        path = ROOT / path_text
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            raise RebindValidationError(f"cannot stat candidate artifact {path_text}: {exc}") from exc
        require(stat.S_ISREG(mode) and not path.is_symlink(), f"candidate artifact is symlink or nonregular: {path_text}")


def verify_candidate_commit_signature(commit: str) -> None:
    try:
        key_mode = SIGNING_PUBLIC_KEY_PATH.lstat().st_mode
        public_key = SIGNING_PUBLIC_KEY_PATH.read_text(encoding="ascii").strip().split()
    except (OSError, UnicodeError) as exc:
        raise RebindValidationError(f"cannot read trusted signing public key: {exc}") from exc
    require(stat.S_ISREG(key_mode) and not SIGNING_PUBLIC_KEY_PATH.is_symlink(), "trusted signing public key is not a regular file")
    require(len(public_key) >= 2 and public_key[0] == "ssh-ed25519", "trusted signing public key format changed")
    fingerprint = subprocess.run(
        ["ssh-keygen", "-lf", str(SIGNING_PUBLIC_KEY_PATH), "-E", "sha256"],
        text=True,
        capture_output=True,
        check=False,
    )
    require(fingerprint.returncode == 0, f"cannot fingerprint trusted signing key: {fingerprint.stderr.strip()}")
    require(SIGNING_KEY_FINGERPRINT in fingerprint.stdout.split(), "trusted signing key fingerprint changed")
    with tempfile.NamedTemporaryFile("w", encoding="ascii", prefix="rules-rebind-allowed-signers-") as allowed:
        allowed.write(f"rules-rebind {public_key[0]} {public_key[1]}\n")
        allowed.flush()
        verify = subprocess.run(
            [
                "git",
                "-c",
                f"gpg.ssh.allowedSignersFile={allowed.name}",
                "verify-commit",
                commit,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    require(verify.returncode == 0, f"candidate commit signature verification failed: {verify.stderr.strip()}")


def validate_git_objects_and_scope() -> None:
    require(_git(["show", "-s", "--format=%T", SOURCE_COMMIT]) == SOURCE_TREE, "source tree object changed")
    require(_git(["show", "-s", "--format=%T", RULES_ADAPTER_COMMIT]) == RULES_ADAPTER_TREE, "Rules adapter Git object does not match")
    require(_git(["show", "-s", "--format=%T", TRANSITION_COMMIT]) == TRANSITION_TREE, "transition Git object does not match")
    head = _git(["rev-parse", "HEAD"])
    _require_existing_new_files_are_regular()
    if head == SOURCE_COMMIT:
        status = _git(["status", "--porcelain=v1", "--untracked-files=all"])
        entries: list[tuple[str, str]] = []
        for line in status.splitlines():
            require(len(line) >= 4, "malformed Git status entry")
            entries.append((line[:2], line[3:]))
        require(len(entries) == 13, "precommit change count is not exactly thirteen")
        require({path for _, path in entries} == set(ALLOWED_NEW_PATHS), "precommit changed paths are not exactly the thirteen allowed files")
        for code, path in entries:
            expected = EXPECTED_CHANGE_TYPES[path]
            allowed_codes = {"??", "A ", " A"} if expected == "A" else {" M", "M ", "MM"}
            require(code in allowed_codes, f"precommit change type for {path} is {code!r}, expected {expected}")
    else:
        require(_git(["rev-list", "--count", f"{SOURCE_COMMIT}..{head}"]) == "1", "candidate is not exactly one commit after source")
        parents = _git(["rev-list", "--parents", "-n", "1", head]).split()
        require(len(parents) == 2 and parents[1] == SOURCE_COMMIT, "candidate parent is not the fixed Rules governance authority")
        diff = _git(["diff", "--name-status", "--no-renames", SOURCE_COMMIT, head])
        entries = [line.split("\t", 1) for line in diff.splitlines() if line]
        require(len(entries) == 13 and all(len(item) == 2 for item in entries), "candidate change count is not exactly thirteen")
        require({item[1] for item in entries} == set(ALLOWED_NEW_PATHS), "candidate paths are not exactly the thirteen allowed files")
        require(
            all(item[0] == EXPECTED_CHANGE_TYPES[item[1]] for item in entries),
            "candidate change types do not match the sealed thirteen-path add/modify matrix",
        )
        require(_git(["status", "--porcelain=v1", "--untracked-files=all"]) == "", "postcommit worktree is not clean")
        verify_candidate_commit_signature(head)
    require(_git(["diff", "--name-only", SOURCE_COMMIT, "--", ".codex/state", ".codex/plans"]) == "", "state or frozen plans changed")


def validate_candidate(
    *,
    schema_data: dict[str, Any] | None = None,
    platform_data: dict[str, Any] | None = None,
    rebind_data: dict[str, Any] | None = None,
    execution_data: dict[str, Any] | None = None,
    index_data: dict[str, Any] | None = None,
    manifest_data: dict[str, Any] | None = None,
    historical_hashes: dict[str, str] | None = None,
    archive_observation: dict[str, Any] | None = None,
    check_git: bool = True,
) -> None:
    archive = archive_observation if archive_observation is not None else validate_platform_archive()
    schema = schema_data if schema_data is not None else load_json(SCHEMA_PATH)
    platform = platform_data if platform_data is not None else load_json(PLATFORM_PATH)
    rebind = rebind_data if rebind_data is not None else load_json(REBIND_PATH)
    execution = execution_data if execution_data is not None else load_json(EXECUTION_PATH)
    v2 = load_json(INDEX_V2_PATH)
    v3 = index_data if index_data is not None else load_json(INDEX_V3_PATH)
    manifest = manifest_data if manifest_data is not None else load_json(MANIFEST_PATH)

    validate_historical_artifacts(historical_hashes)
    validate_schema(schema)
    validate_platform_acceptance(platform, archive)
    validate_rebind(schema, rebind, archive)
    validate_execution(execution)
    validate_index(v2, v3)
    validate_manifest(manifest, archive)
    if check_git:
        validate_git_objects_and_scope()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true", help="validate the additive Platform identity rebind")
    mode.add_argument("--verify-platform-archive", action="store_true", help="validate only the persistent fresh Platform archive")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.verify_platform_archive:
            observation = validate_platform_archive()
            print(json.dumps({
                "task_id": TASK_ID,
                "validation_status": "PASS",
                "validation_source": "PERSISTENT_ARCHIVE_ONLY",
                **observation,
            }, sort_keys=True))
            return 0
        validate_candidate()
        print(json.dumps({
            "task_id": TASK_ID,
            "validation_status": "PASS",
            "formal_M2_B001": "ACCEPTED_UNCHANGED",
            "rules_adapter_product_identity": "UNCHANGED",
            "effective_status_before": "RESOLVED_ADAPTER",
            "effective_status_after": "RESOLVED_ADAPTER",
            "platform_identity_rebind": "RECORDED_NOT_CROSS_ACCEPTED",
            "fresh_platform_evidence_root": FRESH_EVIDENCE_ROOT,
            "fresh_platform_archive_sha256": FRESH_ARCHIVE_SHA256,
            "fresh_exact_pair_acceptance": "NOT_RUN",
            "cross_repository_acceptance": "NOT_RUN",
            "formal_B002": False,
            "formal_B009": False,
            "M2_B002": "NOT_STARTED",
            "M2_B002_READY": "NO",
            "m1_b011_completion": "NOT_AUTHORIZED",
        }, sort_keys=True))
        return 0
    except (
        RebindValidationError,
        OSError,
        UnicodeError,
        ValueError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        print(f"{TASK_ID} platform identity rebind validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
