#!/usr/bin/env python3
"""Fail-closed validator for M2-B001 recovery closeout Attempt 002."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]

TASK_ID = "RULES-RESIDUE-M2-B001-RECOVERY-CLOSEOUT-IMPLEMENT-002"
EVIDENCE_ID = "M2-B001-RECOVERY-CLOSEOUT-001-E002"
CLOSEOUT_ID = "M2-B001-RECOVERY-CLOSEOUT-001"
ATTEMPT_NUMBER = 2

SOURCE_COMMIT = "be1f8dca3c694c9b93a3193348772ae750fc77e1"
SOURCE_TREE = "e4ad6e4f5ad4f672c827b1f37c1980b7655353d6"
ROUTE_ID = "M2-B001-RECOVERY-CLOSEOUT-IMPLEMENT-002"
ROUTE_DIGEST = "f4b61ceab917a056ce392318319635c74b54a9375bb8ea0e78f2b67c1dc33cc6"
OWNER_PACKAGE_ID = "RR-M2-B001-RECOVERY-ATTEMPT-002-V1"
OWNER_MANIFEST_SHA256 = "dff66863f19d85f5f22f2453181f14c0c5ce484c8825a15ee7a95b7e0ea38989"

FORMAL_COMMIT = "fdc1f4c9d8bc565888f33b44684cd6ccbe80c127"
FORMAL_TREE = "f37e15cdd65e0a39eebcddb21f56a2c58ae6939e"
RULES_PAIR_COMMIT = "455cd5d66c683565a4aad7ef8d6523421d37db71"
RULES_PAIR_TREE = "d74aae0baf791566a770ef1aaed2da7562f681d5"
PLATFORM_COMMIT = "1339c490bd8cae1e2a6e6607fc0f1db019faab64"
PLATFORM_TREE = "25d5645caf883a73f165db0179accbca48ddf526"
PLATFORM_CLOSEOUT_COMMIT = "cde53640e143b7adb9e36d7d8bc4fedb6f0ed401"
PLATFORM_CLOSEOUT_TREE = "52ddf06463b01b1e0c5532af3796d4592d4ddea8"
EXACT_PAIR_SHA256 = "099aaa7244b4a443e31bcdb733bbef2728de11b5129382328b4274ffe2534185"

ATTEMPT_001_COMMIT = "854b43980f0633a4b2e01e61d326d7526cb11c8e"
ATTEMPT_001_TREE = "411565bc632e24806f67e39d9c6100d0cdb321f9"

SCHEMA_PATH_TEXT = "docs/implementation/m2/probes/m2-b001-recovery-closeout-v1.schema.json"
CLOSEOUT_DIR = "reports/m2/probes/closeouts/m2-b001-recovery-closeout-001"
EVIDENCE_PATH_TEXT = f"{CLOSEOUT_DIR}/evidence.json"
EXECUTION_PATH_TEXT = f"{CLOSEOUT_DIR}/execution-records.json"
MANIFEST_PATH_TEXT = f"{CLOSEOUT_DIR}/evidence-manifest.json"
INDEX_V2_PATH_TEXT = "reports/m2/probes/external-evidence-index-v2.json"
VALIDATOR_PATH_TEXT = "tests/m2/probes/validate_m2_b001_recovery_closeout.py"
PROBE_TEST_PATH_TEXT = "tests/m2/probes/test_m2_b001_recovery_closeout.py"
BRIDGE_TEST_PATH_TEXT = "tests/test_m2_b001_recovery_closeout.py"
PLAN_VALIDATOR_PATH_TEXT = "tools/validate_m2_plan.py"
PLAN_TEST_PATH_TEXT = "tests/test_m2_plan.py"
INDEX_V1_PATH_TEXT = "reports/m2/probes/external-evidence-index.json"

SCHEMA_PATH = ROOT / SCHEMA_PATH_TEXT
EVIDENCE_PATH = ROOT / EVIDENCE_PATH_TEXT
EXECUTION_PATH = ROOT / EXECUTION_PATH_TEXT
MANIFEST_PATH = ROOT / MANIFEST_PATH_TEXT
INDEX_V2_PATH = ROOT / INDEX_V2_PATH_TEXT

SCHEMA_SHA256 = "217289ec44f7f721e1060776ee035744c8600107dc3cddf647f94edac6ea934e"
EVIDENCE_SHA256 = "42c7b840fae52caa0b5dc4e0a4f8c939a730352ece6915435b660984f247bd77"
INDEX_V1_SHA256 = "b4bf268d7f9ee1627edea5c1ff87fa74774e3f5689c97cd11f0af6881178a22c"

IMMUTABLE_HASHES = {
    "reports/m2/probes/probe-results.json": "154e7c0ddf8ce7b2243ad6c78d10ceb6cddf02c3aeb6592716dcc5ad8fc64218",
    "reports/m2/probes/external-gates.json": "a8951312cb9f23cf3f999a7258900603716ea6f0b4e7f684b8f6a53ed8f13a2d",
    "reports/m2/probes/evidence-manifest.json": "3a48da621e45980d9b2258513954e1f29480fd9e12a35dcd29c12b77015c8ca7",
    "reports/m2/probes/external-evidence-index.json": INDEX_V1_SHA256,
    "reports/m2/probes/external/m2-b001-ext-001/supplement.json": "d2f21f4853e5b77e2796ba3cbe3c7001b4731cdbb251661d6375ac2d5cff193c",
    "reports/m2/probes/external/m2-b001-ext-001/evidence-manifest.json": "c842d67ec1f83145fdb67a33368e1f7dfbf8f8bc28cf8b9ab7b98202e813af1f",
    "reports/m2/probes/external/m2-b001-ext-001/platform-command-evidence.json": "f709a45ecee13a8ccb5722f52acc96fb3c08c662e500aaa7c26681404b73637e",
    "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json": "287708242e1418a7e8a88d4918e049dafdb31ecd498819a5e5b6cd7ce40d81f9",
    "reports/m2/probes/remediations/r2-int-010-rem-001/execution-records.json": "9d3bc8c8e5681d14740fcccf525bcf42087dfe5e7e6287bf50852f43c17475c4",
    "reports/m2/probes/remediations/r2-int-010-rem-001/evidence-manifest.json": "eb5e811122efc10cdd1350b2c44031b9bdd58690482df2105ad35f0c62d1b03e",
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json": "f2e9c48517cd9437aa464041f28b15e8ff96c8df8533c58fa8afb001d22fdd18",
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/execution-records.json": "dc98a5c7f48a8325ba7312c9082f0d514d121e4dba4f931ae66d7c59b1f0db06",
    "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence-manifest.json": "02c10c84c64959e3c186c4aabde3fb82f129ce1c30f788eeaa13b8ff6745c480",
}

ARTIFACT_PATHS = [
    SCHEMA_PATH_TEXT,
    EVIDENCE_PATH_TEXT,
    EXECUTION_PATH_TEXT,
    INDEX_V2_PATH_TEXT,
    VALIDATOR_PATH_TEXT,
    PROBE_TEST_PATH_TEXT,
    BRIDGE_TEST_PATH_TEXT,
    PLAN_VALIDATOR_PATH_TEXT,
    PLAN_TEST_PATH_TEXT,
]
ALLOWED_CHANGED_PATHS = ARTIFACT_PATHS + [MANIFEST_PATH_TEXT]

BLOCKING_IDS = ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"]

EXPECTED_SOURCE_BINDING = {"commit": SOURCE_COMMIT, "tree": SOURCE_TREE}
EXPECTED_ROUTE_BINDING = {
    "route_id": ROUTE_ID,
    "mode": "IMPLEMENT",
    "milestone": "M2",
    "batch_id": "M2-B001",
    "source_commit": SOURCE_COMMIT,
    "source_tree": SOURCE_TREE,
    "binding_digest": ROUTE_DIGEST,
    "owner_package_id": OWNER_PACKAGE_ID,
    "owner_manifest_sha256": OWNER_MANIFEST_SHA256,
}
EXPECTED_CANDIDATE_BINDING = {
    "strategy": "EXACT_HEAD_AT_VALIDATION",
    "execution_status": "NOT_RUN",
    "required_phase": "INDEPENDENT_ACCEPT",
    "must_bind_exact_commit_tree": True,
    "clean_worktree_required": True,
}

EXPECTED_NON_AUTHORITATIVE = [
    {
        "identity": "c6a840b10db46dc475cd9af9e6a1a13f1e68abd4",
        "category": "PRE_PLATFORM_RULES_COMMIT",
        "disposition": "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED",
        "may_be_used_as_execution_evidence": False,
    },
    {
        "identity": "65a0a1671720345425e0368136793754567187cc",
        "category": "PRE_PLATFORM_RULES_COMMIT",
        "disposition": "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED",
        "may_be_used_as_execution_evidence": False,
    },
    {
        "identity": "PLATFORM_CHANGE_PROPOSAL",
        "category": "PROPOSAL",
        "disposition": "ANTECEDENT_ONLY_NOT_EXECUTION_EVIDENCE",
        "may_be_used_as_execution_evidence": False,
    },
    {
        "identity": "OWNER_APPROVAL_ANTECEDENT",
        "category": "OWNER_APPROVAL",
        "disposition": "ANTECEDENT_ONLY_NOT_EXECUTION_EVIDENCE",
        "may_be_used_as_execution_evidence": False,
    },
    {
        "identity": "EARLY_PHASE_J",
        "category": "PRE_PLATFORM_EXECUTION",
        "disposition": "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED",
        "may_be_used_as_execution_evidence": False,
    },
    {
        "identity": "ATTEMPT_001",
        "category": "QUARANTINED_CANDIDATE",
        "disposition": "QUARANTINED_UNACCEPTED_LOCAL_CANDIDATE",
        "may_be_used_as_execution_evidence": False,
    },
    {
        "identity": "OWNER_ROUTE_AUTHORITY",
        "category": "ROUTING_PROJECTION",
        "disposition": "ROUTING_ONLY_NON_AUTHORITATIVE_PROJECTION",
        "may_be_used_as_execution_evidence": False,
    },
]

EXPECTED_RECORD_COMMANDS = [
    [
        "python3",
        "tools/codex_route.py",
        "check",
        "--map",
        ".codex/routes/generated/m2-b001-recovery-closeout-implement-002.reading-map.json",
        "--route-id",
        ROUTE_ID,
        "--mode",
        "IMPLEMENT",
        "--milestone",
        "M2",
        "--batch-id",
        "M2-B001",
        "--repo-root",
        "/home/zyc14588/worktrees/rules-residue-m2-b001-recovery-implement-v2",
        "--allow-root",
        "/home/zyc14588/secs/owner-inputs/RR-M2-B001-RECOVERY-ATTEMPT-002-V1",
    ],
    ["python3", "tests/m2/probes/validate_m2_b001.py", "--all"],
    ["python3", "tests/m2/probes/validate_m2_b001_external_supplement.py", "--supplement"],
    ["python3", "tests/m2/probes/validate_r2_int_010_rem_001.py", "--validate"],
    ["python3", "tests/m2/probes/validate_r2_int_010_post_platform_transition.py", "--validate"],
    ["python3", "tools/validate_m2_plan.py"],
    ["git", "diff", "--check"],
    [
        "git",
        "-C",
        "/home/zyc14588/worktrees/TRPG_PLATFORM_M1_B010_CLOSEOUT",
        "show",
        "--no-patch",
        "--format=%H %T",
        PLATFORM_CLOSEOUT_COMMIT,
    ],
    ["git", "show", "--no-patch", "--format=%H %T %P", ATTEMPT_001_COMMIT],
]

HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class RecoveryValidationError(ValueError):
    """Raised when recovery evidence is incomplete, stale, or overclaims."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecoveryValidationError(message)


def require_exact_keys(value: Any, keys: Iterable[str], context: str) -> None:
    require(isinstance(value, dict), f"{context} must be an object")
    expected = set(keys)
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    require(not missing, f"{context} required field missing: {missing}")
    require(not unknown, f"{context} unknown field: {unknown}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_constant(value: str) -> None:
    raise RecoveryValidationError(f"non-finite JSON constant is forbidden: {value}")


def load_json_text(text: str, context: str = "JSON evidence") -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise RecoveryValidationError(f"cannot load {context}: {exc}") from exc
    require(isinstance(value, dict), f"{context} must be an object")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_text(path.read_text(encoding="utf-8"), str(path))
    except (OSError, UnicodeDecodeError) as exc:
        raise RecoveryValidationError(f"cannot load JSON evidence {path}: {exc}") from exc


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_objects_are_closed(value: Any, context: str = "schema") -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            require(value.get("additionalProperties") is False, f"{context} object schema is not closed")
        for key, child in value.items():
            _schema_objects_are_closed(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _schema_objects_are_closed(child, f"{context}[{index}]")


def validate_schema(root: Path, schema: dict[str, Any]) -> None:
    path = root / SCHEMA_PATH_TEXT
    require(path.is_file(), f"recovery Schema missing: {SCHEMA_PATH_TEXT}")
    require(sha256_path(path) == SCHEMA_SHA256, "recovery Schema bytes changed")
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "recovery Schema draft changed")
    require(schema.get("$id") == "https://rules-residue.invalid/schemas/m2-b001-recovery-closeout-v1.schema.json", "recovery Schema identity changed")
    require(schema.get("additionalProperties") is False, "recovery Schema permits unknown top-level fields")
    expected_fields = {
        "schema_version",
        "evidence_id",
        "task_id",
        "closeout_id",
        "attempt_number",
        "nature",
        "source_binding",
        "route_binding",
        "formal_m2_b001",
        "historical_projection",
        "effective_projection",
        "accepted_post_platform_pair",
        "rules_transition",
        "platform_closeout",
        "prior_attempts",
        "non_authoritative_antecedents",
        "non_claims",
        "readiness",
        "lifecycle",
        "candidate_binding",
        "evidence_links",
    }
    require(set(schema.get("required", [])) == expected_fields, "recovery Schema required fields changed")
    require(set(schema.get("properties", {})) == expected_fields, "recovery Schema properties changed")
    properties = schema["properties"]
    require(properties["evidence_id"].get("const") == EVIDENCE_ID, "Schema evidence_id changed")
    require(properties["task_id"].get("const") == TASK_ID, "Schema task_id changed")
    require(properties["closeout_id"].get("const") == CLOSEOUT_ID, "Schema closeout_id changed")
    require(properties["attempt_number"].get("const") == ATTEMPT_NUMBER, "Schema attempt number changed")
    _schema_objects_are_closed(schema)


def _reject_manifest_digest_cycle(value: Any, context: str = "evidence") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"evidence_manifest_sha256", "closeout_manifest_sha256", "manifest_digest"}:
                raise RecoveryValidationError(f"circular manifest digest binding is forbidden at {context}.{key}")
            _reject_manifest_digest_cycle(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_manifest_digest_cycle(child, f"{context}[{index}]")


def validate_evidence(root: Path, data: dict[str, Any]) -> None:
    _reject_manifest_digest_cycle(data)
    require_exact_keys(
        data,
        [
            "schema_version",
            "evidence_id",
            "task_id",
            "closeout_id",
            "attempt_number",
            "nature",
            "source_binding",
            "route_binding",
            "formal_m2_b001",
            "historical_projection",
            "effective_projection",
            "accepted_post_platform_pair",
            "rules_transition",
            "platform_closeout",
            "prior_attempts",
            "non_authoritative_antecedents",
            "non_claims",
            "readiness",
            "lifecycle",
            "candidate_binding",
            "evidence_links",
        ],
        "recovery evidence",
    )
    require(data["schema_version"] == "rules-residue.m2.m2-b001-recovery-closeout/1.0", "evidence schema_version changed")
    require(data["evidence_id"] == EVIDENCE_ID, "wrong evidence_id")
    require(data["task_id"] == TASK_ID, "wrong task_id")
    require(data["closeout_id"] == CLOSEOUT_ID, "wrong closeout_id")
    require(data["attempt_number"] == ATTEMPT_NUMBER and not isinstance(data["attempt_number"], bool), "wrong attempt_number")
    require(data["nature"] == "ADDITIVE_RECOVERY_CLOSEOUT_EVIDENCE_CANDIDATE", "recovery evidence nature changed")
    require(data["source_binding"] == EXPECTED_SOURCE_BINDING, "source commit/tree binding changed")
    require(data["route_binding"] == EXPECTED_ROUTE_BINDING, "wrong route_id or route digest")
    require(data["formal_m2_b001"] == {
        "status": "ACCEPTED_UNCHANGED",
        "commit": FORMAL_COMMIT,
        "tree": FORMAL_TREE,
        "result_path": "reports/m2/probes/probe-results.json",
        "result_sha256": IMMUTABLE_HASHES["reports/m2/probes/probe-results.json"],
    }, "formal M2-B001 identity changed")
    require(data["historical_projection"] == {
        "R2-INT-010": "FAIL",
        "source_path": "reports/m2/probes/probe-results.json",
        "source_sha256": IMMUTABLE_HASHES["reports/m2/probes/probe-results.json"],
    }, "historical R2-INT-010 FAIL was rewritten")
    require(data["effective_projection"] == {
        "R2-INT-010": "RESOLVED_ADAPTER",
        "transition_path": "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json",
        "transition_sha256": IMMUTABLE_HASHES["reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json"],
    }, "effective R2-INT-010 projection changed")
    require(data["accepted_post_platform_pair"] == {
        "rules": {"commit": RULES_PAIR_COMMIT, "tree": RULES_PAIR_TREE},
        "platform": {"commit": PLATFORM_COMMIT, "tree": PLATFORM_TREE},
        "verdict": "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED",
        "verdict_sha256": EXACT_PAIR_SHA256,
    }, "accepted post-platform exact pair changed")
    require(data["rules_transition"] == {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "status": "RESOLVED_ADAPTER",
    }, "Rules transition identity changed")
    require(data["platform_closeout"] == {
        "commit": PLATFORM_CLOSEOUT_COMMIT,
        "tree": PLATFORM_CLOSEOUT_TREE,
        "batch_id": "M1-B010",
        "state": "COMPLETED",
        "active_implementation_wip": "NONE",
    }, "platform closeout identity or state changed")
    require(data["prior_attempts"] == [{
        "task_id": "RULES-RESIDUE-M2-B001-RECOVERY-CLOSEOUT-IMPLEMENT-001",
        "commit": ATTEMPT_001_COMMIT,
        "tree": ATTEMPT_001_TREE,
        "disposition": "QUARANTINED_UNACCEPTED_LOCAL_CANDIDATE",
    }], "Attempt 001 identity or quarantine disposition changed")
    require(data["non_authoritative_antecedents"] == EXPECTED_NON_AUTHORITATIVE, "non-authoritative antecedent was promoted or changed")
    require(data["non_claims"] == {
        "formal_B002": False,
        "formal_B009": False,
        "aggregate_M2_pass": False,
        "aggregate_external_capability_pass": False,
    }, "formal or aggregate scope was promoted")
    require(data["readiness"] == {
        "M2-B002": "NOT_STARTED",
        "M2-B002_READY": "NO",
        "blocking_ids": BLOCKING_IDS,
    }, "M2-B002 readiness or blocker ordering changed")
    require(data["lifecycle"] == {
        "candidate_state": "FROZEN_WITH_RECOVERY_EVIDENCE_PENDING_LIFECYCLE_CLOSEOUT",
        "lifecycle_closeout_executed": False,
        "independent_acceptance": "NOT_RUN",
    }, "lifecycle closeout or independent acceptance was forged")
    require(data["candidate_binding"] == EXPECTED_CANDIDATE_BINDING, "candidate binding is not EXACT_HEAD_AT_VALIDATION / NOT_RUN")
    require("commit" not in data["candidate_binding"] and "tree" not in data["candidate_binding"], "candidate commit/tree self-reference is forbidden")
    require("candidate_validation_recorded" not in data, "candidate validation cannot be recorded in tracked evidence")
    require(data["evidence_links"] == {
        "execution_records": EXECUTION_PATH_TEXT,
        "evidence_manifest": MANIFEST_PATH_TEXT,
        "external_evidence_index_v2": INDEX_V2_PATH_TEXT,
    }, "recovery evidence links changed")
    require(sha256_path(root / EVIDENCE_PATH_TEXT) == EVIDENCE_SHA256, "recovery evidence bytes changed")


def validate_immutable_predecessors(root: Path) -> None:
    for path_text, digest in IMMUTABLE_HASHES.items():
        path = root / path_text
        require(path.is_file(), f"immutable predecessor missing: {path_text}")
        require(sha256_path(path) == digest, f"immutable predecessor evidence hash drift: {path_text}")

    probe_results = load_json(root / "reports/m2/probes/probe-results.json")
    probe = next((item for item in probe_results.get("probes", []) if item.get("probe_id") == "R2-INT-010"), None)
    require(isinstance(probe, dict), "historical R2-INT-010 record missing")
    require(probe.get("execution_status") == "FAIL", "historical R2-INT-010 FAIL was rewritten")

    transition = load_json(root / "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json")
    require(transition.get("previous_status") == "FAIL", "post-platform transition lost historical FAIL")
    require(transition.get("new_status") == "RESOLVED_ADAPTER", "post-platform effective transition changed")
    require(transition.get("execution_authority", {}).get("sha256") == EXACT_PAIR_SHA256, "exact-pair verdict digest changed")
    require(transition.get("readiness_projection", {}).get("blocking_ids") == BLOCKING_IDS, "post-platform blockers changed")

    early = load_json(root / "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json")
    require(early.get("route_binding", {}).get("source_commit") == "c6a840b10db46dc475cd9af9e6a1a13f1e68abd4", "early provisional identity changed")
    require(early.get("antecedents", {}).get("platform_change_proposal", {}).get("disposition") == "ANTECEDENT_ONLY_NOT_EXECUTION_EVIDENCE", "proposal was promoted to execution evidence")


def _parse_timestamp(value: Any, context: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{context} must be an actual UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RecoveryValidationError(f"{context} is not an ISO-8601 timestamp") from exc
    require(parsed.tzinfo is not None, f"{context} lacks timezone")
    return parsed


def validate_execution_records(data: dict[str, Any]) -> None:
    require_exact_keys(
        data,
        [
            "schema_version",
            "evidence_id",
            "task_id",
            "closeout_id",
            "attempt_number",
            "source_binding",
            "route_binding",
            "candidate_binding",
            "recording_policy",
            "records",
        ],
        "execution records",
    )
    require(data["schema_version"] == "rules-residue.m2.m2-b001-recovery-closeout-execution/1.0", "execution schema_version changed")
    require((data["evidence_id"], data["task_id"], data["closeout_id"], data["attempt_number"]) == (EVIDENCE_ID, TASK_ID, CLOSEOUT_ID, ATTEMPT_NUMBER), "execution record identity mismatch")
    require(data["source_binding"] == EXPECTED_SOURCE_BINDING, "execution source binding changed")
    require(data["route_binding"] == EXPECTED_ROUTE_BINDING, "execution route binding changed")
    require(data["candidate_binding"] == EXPECTED_CANDIDATE_BINDING, "execution candidate binding changed")
    require(data["recording_policy"] == {
        "stdout_stderr_bytes": "CAPTURED_SEPARATELY",
        "combined_output_encoding": "STDOUT_BYTES_THEN_STDERR_BYTES",
        "closure_results_location": "IMPLEMENT_FINAL_REPORT_ONLY",
    }, "execution recording policy changed")
    records = data["records"]
    require(isinstance(records, list) and len(records) == len(EXPECTED_RECORD_COMMANDS), "execution records are missing or duplicated")
    expected_ids = [f"A2-R{index:03d}" for index in range(1, len(EXPECTED_RECORD_COMMANDS) + 1)]
    require([item.get("command_id") for item in records if isinstance(item, dict)] == expected_ids, "execution command IDs are missing, duplicated, or reordered")
    for index, (record, expected_argv) in enumerate(zip(records, EXPECTED_RECORD_COMMANDS, strict=True)):
        require_exact_keys(record, ["command_id", "argv", "cwd", "started_at", "finished_at", "exit_code", "stdout_sha256", "stderr_sha256", "combined_output_sha256", "result"], f"execution record {index + 1}")
        require(record["argv"] == expected_argv, f"execution record {record['command_id']} argv changed")
        require(record["cwd"] == "/home/zyc14588/worktrees/rules-residue-m2-b001-recovery-implement-v2", f"execution record {record['command_id']} cwd changed")
        started = _parse_timestamp(record["started_at"], f"{record['command_id']}.started_at")
        finished = _parse_timestamp(record["finished_at"], f"{record['command_id']}.finished_at")
        require(finished >= started, f"{record['command_id']} finished before it started")
        require(record["exit_code"] == 0 and record["result"] == "PASS", f"execution record {record['command_id']} did not PASS")
        for field in ("stdout_sha256", "stderr_sha256", "combined_output_sha256"):
            require(isinstance(record[field], str) and HEX_64.fullmatch(record[field]) is not None, f"{record['command_id']}.{field} is not SHA-256")


def validate_index(root: Path, data: dict[str, Any]) -> None:
    _reject_manifest_digest_cycle(data, "index v2")
    require_exact_keys(
        data,
        [
            "schema_version",
            "index_id",
            "batch_id",
            "ordinal",
            "predecessor_index",
            "formal_batch",
            "evidence_chain",
            "authority_bindings",
            "projections",
            "execution_evidence_exclusions",
            "candidate_binding",
            "resolution_rule",
            "formal_batch_reopened",
            "lifecycle_closeout_executed",
            "independent_acceptance_required",
        ],
        "external evidence index v2",
    )
    require((data["schema_version"], data["index_id"], data["batch_id"], data["ordinal"]) == (
        "rules-residue.m2.external-evidence-index/2.0",
        "M2-B001-EXTERNAL-EVIDENCE-INDEX-V2",
        "M2-B001",
        2,
    ), "external evidence index v2 identity changed")
    require(data["predecessor_index"] == {
        "path": INDEX_V1_PATH_TEXT,
        "sha256": INDEX_V1_SHA256,
        "schema_version": "rules-residue.m2.external-evidence-index/1.0",
        "last_evidence_ordinal": 1,
        "disposition": "IMMUTABLE_ORDINAL_PREDECESSOR",
    }, "ordinal predecessor hash or identity changed")
    require(sha256_path(root / INDEX_V1_PATH_TEXT) == INDEX_V1_SHA256, "v1 external evidence index was rewritten")
    require(data["formal_batch"] == {
        "status": "ACCEPTED_UNCHANGED",
        "commit": FORMAL_COMMIT,
        "tree": FORMAL_TREE,
        "result_path": "reports/m2/probes/probe-results.json",
        "result_sha256": IMMUTABLE_HASHES["reports/m2/probes/probe-results.json"],
    }, "index formal M2-B001 identity changed")

    expected_chain = [
        (0, "M2-B001", "FORMAL_BATCH_EVIDENCE", "reports/m2/probes/probe-results.json", IMMUTABLE_HASHES["reports/m2/probes/probe-results.json"], "IMMUTABLE_FORMAL_BASE"),
        (1, "M2-B001-EXT-001", "EXTERNAL_EVIDENCE_SUPPLEMENT", "reports/m2/probes/external/m2-b001-ext-001/supplement.json", IMMUTABLE_HASHES["reports/m2/probes/external/m2-b001-ext-001/supplement.json"], "IMMUTABLE_HISTORICAL_FAIL_SUPPLEMENT"),
        (2, "R2-INT-010-REM-001-J001", "PRE_PLATFORM_PROVISIONAL_EVIDENCE", "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json", IMMUTABLE_HASHES["reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json"], "SUPERSEDED_PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED"),
        (3, "R2-INT-010-POST-PLATFORM-TRANSITION-T001", "ACCEPTED_POST_PLATFORM_STATUS_TRANSITION", "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json", IMMUTABLE_HASHES["reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json"], "EFFECTIVE_RESOLVED_ADAPTER_PROJECTION"),
        (4, EVIDENCE_ID, "ADDITIVE_RECOVERY_CLOSEOUT_EVIDENCE_CANDIDATE", EVIDENCE_PATH_TEXT, EVIDENCE_SHA256, "PENDING_INDEPENDENT_ACCEPT_AND_LIFECYCLE_CLOSEOUT"),
    ]
    chain = data["evidence_chain"]
    require(isinstance(chain, list) and len(chain) == len(expected_chain), "evidence chain item is missing or duplicated")
    observed_chain = [
        (item.get("ordinal"), item.get("evidence_id"), item.get("nature"), item.get("path"), item.get("sha256"), item.get("disposition"))
        for item in chain if isinstance(item, dict)
    ]
    require(observed_chain == expected_chain, "evidence chain ordinal, digest, identity, or disposition changed")
    require(len({item[0] for item in observed_chain}) == len(observed_chain), "duplicate evidence ordinal")

    require(data["authority_bindings"] == {
        "accepted_post_platform_pair": {
            "rules_commit": RULES_PAIR_COMMIT,
            "rules_tree": RULES_PAIR_TREE,
            "platform_commit": PLATFORM_COMMIT,
            "platform_tree": PLATFORM_TREE,
            "verdict": "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED",
            "verdict_sha256": EXACT_PAIR_SHA256,
        },
        "rules_transition": {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "effective_R2-INT-010": "RESOLVED_ADAPTER",
        },
        "platform_closeout": {
            "commit": PLATFORM_CLOSEOUT_COMMIT,
            "tree": PLATFORM_CLOSEOUT_TREE,
            "batch_id": "M1-B010",
            "state": "COMPLETED",
            "active_implementation_wip": "NONE",
        },
        "prior_attempt": {
            "task_id": "RULES-RESIDUE-M2-B001-RECOVERY-CLOSEOUT-IMPLEMENT-001",
            "commit": ATTEMPT_001_COMMIT,
            "tree": ATTEMPT_001_TREE,
            "disposition": "QUARANTINED_UNACCEPTED_LOCAL_CANDIDATE",
        },
    }, "index authority bindings changed")
    require(data["projections"] == {
        "historical_R2-INT-010": "FAIL",
        "effective_R2-INT-010": "RESOLVED_ADAPTER",
        "formal_B002": False,
        "formal_B009": False,
        "M2-B002": "NOT_STARTED",
        "M2-B002_READY": "NO",
        "aggregate_M2_pass": False,
        "aggregate_external_capability_pass": False,
        "blocking_ids": BLOCKING_IDS,
    }, "index projection or blocker ordering changed")
    require(data["execution_evidence_exclusions"] == [
        {"identity": "OWNER_ROUTE_AUTHORITY", "reason": "ROUTING_AUTHORIZATION_ONLY_NON_AUTHORITATIVE_PROJECTION"},
        {"identity": "PLATFORM_CHANGE_PROPOSAL", "reason": "ANTECEDENT_ONLY_NOT_EXECUTION_EVIDENCE"},
        {"identity": "OWNER_APPROVAL_ANTECEDENT", "reason": "ANTECEDENT_ONLY_NOT_EXECUTION_EVIDENCE"},
        {"identity": "EARLY_PHASE_J", "reason": "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED"},
        {"identity": "ATTEMPT_001", "reason": "QUARANTINED_UNACCEPTED_LOCAL_CANDIDATE"},
    ], "owner/proposal/provisional evidence exclusion changed")
    require(data["candidate_binding"] == EXPECTED_CANDIDATE_BINDING, "index candidate binding changed")
    require(data["formal_batch_reopened"] is False, "formal M2-B001 was reopened")
    require(data["lifecycle_closeout_executed"] is False, "lifecycle closeout was falsely claimed")
    require(data["independent_acceptance_required"] is True, "independent ACCEPT requirement was removed")


def validate_manifest(root: Path, data: dict[str, Any]) -> None:
    require_exact_keys(
        data,
        [
            "schema_version",
            "evidence_id",
            "task_id",
            "closeout_id",
            "attempt_number",
            "artifacts",
            "immutable_predecessors",
            "predecessor_index",
            "prior_attempt",
            "self",
            "policies",
        ],
        "recovery evidence manifest",
    )
    require((data["schema_version"], data["evidence_id"], data["task_id"], data["closeout_id"], data["attempt_number"]) == (
        "rules-residue.m2.m2-b001-recovery-closeout-manifest/1.0",
        EVIDENCE_ID,
        TASK_ID,
        CLOSEOUT_ID,
        ATTEMPT_NUMBER,
    ), "recovery manifest identity changed")
    artifacts = data["artifacts"]
    require(isinstance(artifacts, list), "recovery manifest artifacts must be an array")
    artifact_paths = [item.get("path") for item in artifacts if isinstance(item, dict)]
    require(len(artifact_paths) == len(set(artifact_paths)), "manifest duplicate item")
    require(MANIFEST_PATH_TEXT not in artifact_paths, "manifest self-binding is forbidden")
    expected_artifacts = [{"path": path_text, "sha256": sha256_path(root / path_text)} for path_text in ARTIFACT_PATHS]
    require(artifacts == expected_artifacts, "manifest item missing, reordered, or forged digest")
    expected_predecessors = [{"path": path_text, "sha256": digest} for path_text, digest in IMMUTABLE_HASHES.items()]
    require(data["immutable_predecessors"] == expected_predecessors, "manifest immutable predecessor coverage or digest changed")
    require(data["predecessor_index"] == {
        "path": INDEX_V1_PATH_TEXT,
        "sha256": INDEX_V1_SHA256,
        "disposition": "IMMUTABLE_ORDINAL_PREDECESSOR",
    }, "manifest ordinal predecessor binding changed")
    require(data["prior_attempt"] == {
        "commit": ATTEMPT_001_COMMIT,
        "tree": ATTEMPT_001_TREE,
        "disposition": "QUARANTINED_UNACCEPTED_LOCAL_CANDIDATE",
    }, "manifest Attempt 001 binding changed")
    require(data["self"] == {
        "path": MANIFEST_PATH_TEXT,
        "included_in_artifacts": False,
        "reason": "NON_CIRCULAR_MANIFEST_SELF_EXCLUSION",
    }, "manifest self-exclusion changed")
    require(data["policies"] == {
        "manifest_self_binding": False,
        "metadata_manifest_digest_cycle": False,
        "owner_authority_execution_evidence": False,
        "candidate_commit_tree_embedded": False,
        "candidate_binding_strategy": "EXACT_HEAD_AT_VALIDATION",
        "closure_results_embedded": False,
    }, "manifest circularity, authority, or candidate policy changed")


def _git(root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    require(result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def collect_changed_paths(root: Path, source_ref: str = SOURCE_COMMIT) -> list[str]:
    tracked = _git(root, ["diff", "--name-only", source_ref, "--"])
    untracked = _git(root, ["ls-files", "--others", "--exclude-standard"])
    return sorted({line for text in (tracked, untracked) for line in text.splitlines() if line})


def validate_changed_paths(paths: Iterable[str], require_complete: bool = True) -> None:
    normalized: list[str] = []
    for path_text in paths:
        path = PurePosixPath(path_text)
        require(not path.is_absolute() and ".." not in path.parts, f"invalid changed path: {path_text}")
        normalized.append(path.as_posix())
    actual = set(normalized)
    allowed = set(ALLOWED_CHANGED_PATHS)
    outside = sorted(actual - allowed)
    require(not outside, f"allowed-path outside diff: {outside}")
    if require_complete:
        missing = sorted(allowed - actual)
        require(not missing, f"approved recovery artifact missing from diff: {missing}")


def validate_candidate_checkout(
    root: Path,
    candidate: str,
    candidate_tree: str,
    source_commit: str = SOURCE_COMMIT,
) -> None:
    require(re.fullmatch(r"[0-9a-f]{40}", candidate) is not None, "candidate commit must be full SHA-1")
    require(re.fullmatch(r"[0-9a-f]{40}", candidate_tree) is not None, "candidate tree must be full SHA-1")
    require(_git(root, ["rev-parse", "HEAD"]) == candidate, "candidate validation wrong commit")
    require(_git(root, ["rev-parse", "HEAD^{tree}"]) == candidate_tree, "candidate validation wrong tree")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, candidate],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    require(ancestry.returncode == 0, "candidate does not descend from fixed source")
    require(_git(root, ["status", "--porcelain", "--untracked-files=all"]) == "", "dirty candidate worktree")


def validate_recovery(
    project_root: Path = ROOT,
    *,
    candidate: str | None = None,
    candidate_tree: str | None = None,
    check_git: bool = True,
) -> None:
    root = project_root.resolve()
    schema = load_json(root / SCHEMA_PATH_TEXT)
    evidence = load_json(root / EVIDENCE_PATH_TEXT)
    execution = load_json(root / EXECUTION_PATH_TEXT)
    index = load_json(root / INDEX_V2_PATH_TEXT)
    manifest = load_json(root / MANIFEST_PATH_TEXT)

    validate_schema(root, schema)
    validate_evidence(root, evidence)
    validate_immutable_predecessors(root)
    validate_execution_records(execution)
    validate_index(root, index)
    validate_manifest(root, manifest)

    require((candidate is None) == (candidate_tree is None), "candidate commit and tree must be supplied together")
    if candidate is not None and candidate_tree is not None:
        validate_candidate_checkout(root, candidate, candidate_tree)
    if check_git:
        validate_changed_paths(collect_changed_paths(root))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="validate Attempt 002 recovery closeout evidence")
    parser.add_argument("--candidate", help="exact candidate commit for independent ACCEPT")
    parser.add_argument("--candidate-tree", help="exact candidate tree for independent ACCEPT")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        require(args.validate, "select --validate")
        validate_recovery(candidate=args.candidate, candidate_tree=args.candidate_tree)
        print(json.dumps({
            "task_id": TASK_ID,
            "evidence_id": EVIDENCE_ID,
            "attempt_number": ATTEMPT_NUMBER,
            "validation_status": "PASS",
            "historical_R2-INT-010": "FAIL",
            "effective_R2-INT-010": "RESOLVED_ADAPTER",
            "lifecycle_state": "FROZEN_WITH_RECOVERY_EVIDENCE_PENDING_LIFECYCLE_CLOSEOUT",
            "candidate_binding_strategy": "EXACT_HEAD_AT_VALIDATION",
            "independent_acceptance": "PASS" if args.candidate else "NOT_RUN",
            "formal_B002": False,
            "formal_B009": False,
            "M2-B002": "NOT_STARTED",
            "M2-B002_READY": "NO",
            "blocking_ids": BLOCKING_IDS,
        }, sort_keys=True))
        return 0
    except (RecoveryValidationError, OSError, UnicodeError, ValueError) as exc:
        print(f"{TASK_ID} recovery closeout validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
