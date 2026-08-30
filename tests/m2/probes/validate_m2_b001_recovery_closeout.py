#!/usr/bin/env python3
"""Fail-closed validator for M2-B001 recovery closeout Attempt 002."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable


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

RECOVERY_CANDIDATE_COMMIT = "f5964d4c0b02e5969747a628dae64a02f87b8417"
RECOVERY_CANDIDATE_TREE = "75ec646592260f764fa1862b20c164e8ecb46f1d"
LIFECYCLE_CLOSEOUT_COMMIT = "e90a717d3863e4fb0e5e1a0fcc01661f24d2157d"
LIFECYCLE_CLOSEOUT_TREE = "7a1ce74ad0b82c7c288b94c47c966028e916137d"

RECOVERY_CANDIDATE = "RECOVERY_CANDIDATE"
LIFECYCLE_CLOSEOUT_ANCHOR = "LIFECYCLE_CLOSEOUT_ANCHOR"
POST_ACCEPTED_NON_M2_DESCENDANT = "POST_ACCEPTED_NON_M2_DESCENDANT"

# Compatibility names are retained because the repository-level bridge predates
# the three-way historical classification. They dispatch to the strict modes
# above; neither name is a bypass.
CURRENT_RECOVERY_CANDIDATE = "CURRENT_RECOVERY_CANDIDATE"
HISTORICAL_ACCEPTED_RECOVERY = "HISTORICAL_ACCEPTED_RECOVERY"
VALIDATION_MODES = {
    RECOVERY_CANDIDATE,
    LIFECYCLE_CLOSEOUT_ANCHOR,
    POST_ACCEPTED_NON_M2_DESCENDANT,
    CURRENT_RECOVERY_CANDIDATE,
    HISTORICAL_ACCEPTED_RECOVERY,
}

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

CANDIDATE_B_ALLOWED_CHANGED_PATHS = [
    ".codex/state/MILESTONE_PLAN.yaml",
    ".codex/plans/m2-vertical-slice/M2_VERTICAL_SLICE_PLAN.md",
    ".codex/plans/m2-vertical-slice/batches.json",
    ".codex/plans/m2-vertical-slice/capability-probes.json",
    ".codex/plans/m2-vertical-slice/controls.json",
    ".codex/plans/m2-vertical-slice/READING_MAP_REQUESTS.md",
    "tools/validate_project.py",
    PLAN_TEST_PATH_TEXT,
    VALIDATOR_PATH_TEXT,
    PROBE_TEST_PATH_TEXT,
    BRIDGE_TEST_PATH_TEXT,
]

LIFECYCLE_STATE_PATHS = [
    ".codex/state/MILESTONE_PLAN.yaml",
    ".codex/plans/m2-vertical-slice/M2_VERTICAL_SLICE_PLAN.md",
    ".codex/plans/m2-vertical-slice/batches.json",
    ".codex/plans/m2-vertical-slice/capability-probes.json",
    ".codex/plans/m2-vertical-slice/controls.json",
    ".codex/plans/m2-vertical-slice/READING_MAP_REQUESTS.md",
]

# These paths are preservation evidence, not a scope allowlist for later
# batches. The two recovery validator paths authorized by the Owner amendment
# are intentionally absent; their historical A2 bytes are still read from the
# fixed A2 object.
DESCENDANT_PROTECTED_PATHS = [
    *LIFECYCLE_STATE_PATHS,
    "tests/test_m2_b001_recovery_closeout.py",
    "tests/test_m2_plan.py",
    PLAN_VALIDATOR_PATH_TEXT,
    "docs/implementation/m2/probes",
    "reports/m2/probes",
]

EVOLVABLE_HISTORICAL_ARTIFACT_PATHS = {
    VALIDATOR_PATH_TEXT,
    PROBE_TEST_PATH_TEXT,
    BRIDGE_TEST_PATH_TEXT,
    PLAN_TEST_PATH_TEXT,
}

CURRENTLY_IMMUTABLE_RECOVERY_ARTIFACT_PATHS = [
    EVIDENCE_PATH_TEXT,
    EXECUTION_PATH_TEXT,
    MANIFEST_PATH_TEXT,
    INDEX_V2_PATH_TEXT,
]

BLOCKING_IDS = ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"]
NEXT_ALLOWED_ACTION = (
    "PLAN_REMAINING_M2_B002_BLOCKERS_"
    "R2_INT_011_R2_INT_012_DEFER_R2_C14_001"
)

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


ArtifactReader = Callable[[str], bytes]


def _filesystem_reader(root: Path) -> ArtifactReader:
    return lambda path_text: (root / path_text).read_bytes()


def _artifact_bytes(
    root: Path,
    path_text: str,
    artifact_reader: ArtifactReader | None = None,
) -> bytes:
    reader = artifact_reader or _filesystem_reader(root)
    try:
        return reader(path_text)
    except (OSError, UnicodeError) as exc:
        raise RecoveryValidationError(
            f"cannot read validation artifact {path_text}: {exc}"
        ) from exc


def _artifact_json(
    root: Path,
    path_text: str,
    artifact_reader: ArtifactReader | None = None,
) -> dict[str, Any]:
    raw = _artifact_bytes(root, path_text, artifact_reader)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RecoveryValidationError(
            f"cannot decode validation artifact {path_text}: {exc}"
        ) from exc
    return load_json_text(text, path_text)


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


def validate_schema(
    root: Path,
    schema: dict[str, Any],
    *,
    artifact_reader: ArtifactReader | None = None,
) -> None:
    path = root / SCHEMA_PATH_TEXT
    if artifact_reader is None:
        require(path.is_file(), f"recovery Schema missing: {SCHEMA_PATH_TEXT}")
    require(
        hashlib.sha256(
            _artifact_bytes(root, SCHEMA_PATH_TEXT, artifact_reader)
        ).hexdigest()
        == SCHEMA_SHA256,
        "recovery Schema bytes changed",
    )
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


def validate_evidence(
    root: Path,
    data: dict[str, Any],
    *,
    artifact_reader: ArtifactReader | None = None,
) -> None:
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
    require(
        hashlib.sha256(
            _artifact_bytes(root, EVIDENCE_PATH_TEXT, artifact_reader)
        ).hexdigest()
        == EVIDENCE_SHA256,
        "recovery evidence bytes changed",
    )


def validate_immutable_predecessors(
    root: Path,
    *,
    artifact_reader: ArtifactReader | None = None,
) -> None:
    for path_text, digest in IMMUTABLE_HASHES.items():
        path = root / path_text
        if artifact_reader is None:
            require(path.is_file(), f"immutable predecessor missing: {path_text}")
        require(
            hashlib.sha256(
                _artifact_bytes(root, path_text, artifact_reader)
            ).hexdigest()
            == digest,
            f"immutable predecessor evidence hash drift: {path_text}",
        )

    probe_results = _artifact_json(
        root,
        "reports/m2/probes/probe-results.json",
        artifact_reader,
    )
    probe = next((item for item in probe_results.get("probes", []) if item.get("probe_id") == "R2-INT-010"), None)
    require(isinstance(probe, dict), "historical R2-INT-010 record missing")
    require(probe.get("execution_status") == "FAIL", "historical R2-INT-010 FAIL was rewritten")

    transition = _artifact_json(
        root,
        "reports/m2/probes/remediations/r2-int-010-post-platform-transition/evidence.json",
        artifact_reader,
    )
    require(transition.get("previous_status") == "FAIL", "post-platform transition lost historical FAIL")
    require(transition.get("new_status") == "RESOLVED_ADAPTER", "post-platform effective transition changed")
    require(transition.get("execution_authority", {}).get("sha256") == EXACT_PAIR_SHA256, "exact-pair verdict digest changed")
    require(transition.get("readiness_projection", {}).get("blocking_ids") == BLOCKING_IDS, "post-platform blockers changed")

    early = _artifact_json(
        root,
        "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json",
        artifact_reader,
    )
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


def validate_index(
    root: Path,
    data: dict[str, Any],
    *,
    artifact_reader: ArtifactReader | None = None,
) -> None:
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
    require(
        hashlib.sha256(
            _artifact_bytes(root, INDEX_V1_PATH_TEXT, artifact_reader)
        ).hexdigest()
        == INDEX_V1_SHA256,
        "v1 external evidence index was rewritten",
    )
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


def validate_manifest(
    root: Path,
    data: dict[str, Any],
    *,
    artifact_reader: Callable[[str], bytes] | None = None,
) -> None:
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
    if artifact_reader is None:
        artifact_reader = lambda path_text: (root / path_text).read_bytes()
    expected_artifacts = [
        {"path": path_text, "sha256": hashlib.sha256(artifact_reader(path_text)).hexdigest()}
        for path_text in ARTIFACT_PATHS
    ]
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
    environment = dict(os.environ)
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    require(result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _git_bytes(root: Path, args: list[str]) -> bytes:
    environment = dict(os.environ)
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        check=False,
        env=environment,
    )
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    require(result.returncode == 0, f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def _validate_historical_anchor_identity(
    root: Path,
    historical_commit: str,
    historical_tree: str,
) -> None:
    require(
        re.fullmatch(r"[0-9a-f]{40}", historical_commit) is not None,
        "historical recovery commit must be full SHA-1",
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", historical_tree) is not None,
        "historical recovery tree must be full SHA-1",
    )
    require(
        _git(root, ["cat-file", "-t", historical_commit]) == "commit",
        "historical recovery object is not a commit",
    )
    require(
        _git(root, ["rev-parse", f"{historical_commit}^{{commit}}"])
        == historical_commit,
        "historical recovery commit identity changed",
    )
    require(
        _git(root, ["rev-parse", f"{historical_commit}^{{tree}}"])
        == historical_tree,
        "historical recovery tree identity changed",
    )


def validate_historical_anchor(root: Path) -> None:
    _validate_historical_anchor_identity(
        root,
        RECOVERY_CANDIDATE_COMMIT,
        RECOVERY_CANDIDATE_TREE,
    )


def read_git_blob(root: Path, commit: str, path_text: str) -> bytes:
    path = PurePosixPath(path_text)
    require(
        not path.is_absolute() and ".." not in path.parts,
        f"invalid historical manifest path: {path_text}",
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
        "historical blob commit must be full SHA-1",
    )
    # `git show <commit>:<path>` is the sole source for historical bytes.
    # There is intentionally no filesystem or working-tree fallback.
    return _git_bytes(
        root,
        ["show", f"{commit}:{path.as_posix()}"],
    )


def read_historical_blob(root: Path, path_text: str) -> bytes:
    return read_git_blob(root, RECOVERY_CANDIDATE_COMMIT, path_text)


def validate_historical_manifest_entries(
    root: Path,
    manifest: dict[str, Any],
    *,
    artifact_reader: ArtifactReader | None = None,
) -> None:
    reader = artifact_reader or (
        lambda path_text: read_historical_blob(root, path_text)
    )
    seen: set[str] = set()
    for group in ("artifacts", "immutable_predecessors"):
        entries = manifest.get(group)
        require(isinstance(entries, list), f"recovery manifest {group} must be an array")
        for index, item in enumerate(entries):
            require_exact_keys(item, ["path", "sha256"], f"recovery manifest {group}[{index}]")
            path_text = item["path"]
            digest = item["sha256"]
            require(isinstance(path_text, str), f"recovery manifest {group}[{index}].path must be text")
            require(isinstance(digest, str) and HEX_64.fullmatch(digest) is not None, f"recovery manifest {group}[{index}].sha256 is invalid")
            require(path_text not in seen, f"recovery manifest tracked path is duplicated: {path_text}")
            seen.add(path_text)
            actual = hashlib.sha256(reader(path_text)).hexdigest()
            require(actual == digest, f"historical recovery manifest hash mismatch: {path_text}")


def validate_current_recovery_artifacts_are_historical(root: Path) -> None:
    for path_text in CURRENTLY_IMMUTABLE_RECOVERY_ARTIFACT_PATHS:
        path = root / path_text
        require(path.is_file(), f"immutable recovery artifact missing: {path_text}")
        require(
            path.read_bytes() == read_historical_blob(root, path_text),
            f"immutable recovery artifact changed after Candidate A2: {path_text}",
        )


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


def validate_candidate_b_changed_paths(
    paths: Iterable[str],
    require_complete: bool = True,
) -> None:
    normalized: list[str] = []
    for path_text in paths:
        path = PurePosixPath(path_text)
        require(not path.is_absolute() and ".." not in path.parts, f"invalid changed path: {path_text}")
        normalized.append(path.as_posix())
    actual = set(normalized)
    allowed = set(CANDIDATE_B_ALLOWED_CHANGED_PATHS)
    outside = sorted(actual - allowed)
    require(not outside, f"Candidate B changed path outside owner allowlist: {outside}")
    changed_historical_artifacts = actual & set(ARTIFACT_PATHS)
    non_evolvable = sorted(
        changed_historical_artifacts - EVOLVABLE_HISTORICAL_ARTIFACT_PATHS
    )
    require(
        not non_evolvable,
        f"historical manifest artifact is not evolvable in Candidate B: {non_evolvable}",
    )
    if require_complete:
        missing = sorted(allowed - actual)
        require(not missing, f"Candidate B approved lifecycle path missing from diff: {missing}")


def _validate_lifecycle_anchor_structure(
    *,
    parent: str,
    commit_count: int,
    changed_paths: Iterable[str],
) -> None:
    require(
        parent == RECOVERY_CANDIDATE_COMMIT,
        "accepted lifecycle anchor parent is not fixed Candidate A2",
    )
    require(commit_count == 1, "A2 to lifecycle anchor must be exactly one commit")
    validate_candidate_b_changed_paths(changed_paths)


def _git_object_reader(root: Path, commit: str) -> ArtifactReader:
    return lambda path_text: read_git_blob(root, commit, path_text)


def validate_a2_historical_recovery(root: Path) -> None:
    """Revalidate A2 exclusively from its fixed Git object graph."""

    validate_historical_anchor(root)
    reader = _git_object_reader(root, RECOVERY_CANDIDATE_COMMIT)
    schema = _artifact_json(root, SCHEMA_PATH_TEXT, reader)
    evidence = _artifact_json(root, EVIDENCE_PATH_TEXT, reader)
    execution = _artifact_json(root, EXECUTION_PATH_TEXT, reader)
    index = _artifact_json(root, INDEX_V2_PATH_TEXT, reader)
    manifest = _artifact_json(root, MANIFEST_PATH_TEXT, reader)

    validate_schema(root, schema, artifact_reader=reader)
    validate_evidence(root, evidence, artifact_reader=reader)
    validate_immutable_predecessors(root, artifact_reader=reader)
    validate_execution_records(execution)
    validate_index(root, index, artifact_reader=reader)
    validate_manifest(root, manifest, artifact_reader=reader)
    validate_historical_manifest_entries(
        root,
        manifest,
        artifact_reader=reader,
    )


def _require_fields(
    value: Any,
    expected: dict[str, Any],
    context: str,
) -> None:
    require(isinstance(value, dict), f"{context} must be an object")
    for key, expected_value in expected.items():
        require(
            value.get(key) == expected_value,
            f"{context}.{key} preservation drift",
        )


def validate_lifecycle_preservation_state(
    root: Path,
    *,
    artifact_reader: ArtifactReader,
) -> None:
    """Validate the accepted M2 projection without trusting summaries."""

    milestone = _artifact_json(
        root,
        ".codex/state/MILESTONE_PLAN.yaml",
        artifact_reader,
    )
    require(milestone.get("state") == "ACCEPTED", "M2 plan state is not ACCEPTED")
    active_plan = milestone.get("active_plan")
    _require_fields(
        active_plan,
        {
            "batch_id": "M2-B001",
            "state": "ACCEPTED",
            "implementation_state": "ACCEPTED",
            "next_allowed_action": NEXT_ALLOWED_ACTION,
        },
        "M2 milestone active_plan",
    )
    _require_fields(
        active_plan.get("lifecycle_projection") if isinstance(active_plan, dict) else None,
        {
            "state": "ACCEPTED_WITH_DOWNSTREAM_BLOCKERS",
            "accepted_candidate": {
                "commit": RECOVERY_CANDIDATE_COMMIT,
                "tree": RECOVERY_CANDIDATE_TREE,
            },
            "independent_acceptance": "PASS",
            "historical_R2-INT-010": "FAIL",
            "effective_R2-INT-010": "RESOLVED_ADAPTER",
            "formal_B002": False,
            "formal_B009": False,
            "aggregate_M2_pass": False,
            "aggregate_external_capability_pass": False,
            "M2-B002": {
                "state": "PLANNED",
                "implementation_state": "NOT_STARTED",
                "ready": "NO",
            },
            "blocking_ids": BLOCKING_IDS,
            "global_active_WIP": 0,
        },
        "M2 milestone lifecycle_projection",
    )

    batches = _artifact_json(
        root,
        ".codex/plans/m2-vertical-slice/batches.json",
        artifact_reader,
    )
    _require_fields(
        batches.get("lifecycle_projection"),
        {
            "state": "ACCEPTED_WITH_DOWNSTREAM_BLOCKERS",
            "M2-B001": "ACCEPTED",
            "M2-B002": "PLANNED",
            "M2-B002_implementation": "NOT_STARTED",
            "M2-B002_READY": "NO",
            "formal_B002": False,
            "formal_B009": False,
            "aggregate_M2_pass": False,
            "aggregate_external_capability_pass": False,
            "effective_R2-INT-010": "RESOLVED_ADAPTER",
            "blocking_ids": BLOCKING_IDS,
            "active_WIP": 0,
            "next_allowed_action": NEXT_ALLOWED_ACTION,
        },
        "M2 batches lifecycle_projection",
    )
    batch_items = batches.get("batches")
    require(isinstance(batch_items, list), "M2 batches registry is not an array")
    b001 = next(
        (item for item in batch_items if isinstance(item, dict) and item.get("id") == "M2-B001"),
        None,
    )
    b002 = next(
        (item for item in batch_items if isinstance(item, dict) and item.get("id") == "M2-B002"),
        None,
    )
    _require_fields(
        b001,
        {
            "state": "FROZEN",
            "lifecycle_state": "ACCEPTED",
            "accepted_candidate": {
                "commit": RECOVERY_CANDIDATE_COMMIT,
                "tree": RECOVERY_CANDIDATE_TREE,
            },
        },
        "M2-B001 batch",
    )
    _require_fields(
        b002,
        {
            "state": "PLANNED",
            "implementation_state": "NOT_STARTED",
            "ready": "NO",
            "blocking_ids": BLOCKING_IDS,
        },
        "M2-B002 batch",
    )

    controls = _artifact_json(
        root,
        ".codex/plans/m2-vertical-slice/controls.json",
        artifact_reader,
    )
    _require_fields(
        controls.get("lifecycle_projection"),
        {
            "state": "ACCEPTED_WITH_DOWNSTREAM_BLOCKERS",
            "accepted_batches": ["M2-B001"],
            "M2-B002": "PLANNED",
            "M2-B002_implementation": "NOT_STARTED",
            "M2-B002_READY": "NO",
            "historical_R2-INT-010": "FAIL",
            "effective_R2-INT-010": "RESOLVED_ADAPTER",
            "formal_B002": False,
            "formal_B009": False,
            "aggregate_M2_pass": False,
            "aggregate_external_capability_pass": False,
            "blocking_ids": BLOCKING_IDS,
            "active_WIP": 0,
            "next_allowed_action": NEXT_ALLOWED_ACTION,
        },
        "M2 controls lifecycle_projection",
    )

    probes = _artifact_json(
        root,
        ".codex/plans/m2-vertical-slice/capability-probes.json",
        artifact_reader,
    )
    _require_fields(
        probes.get("lifecycle_projection"),
        {
            "M2-B001": "ACCEPTED",
            "M2-B002": "PLANNED",
            "M2-B002_implementation": "NOT_STARTED",
            "M2-B002_READY": "NO",
            "historical_R2-INT-010": "FAIL",
            "effective_R2-INT-010": "RESOLVED_ADAPTER",
            "formal_B002": False,
            "formal_B009": False,
            "aggregate_M2_pass": False,
            "aggregate_external_capability_pass": False,
            "blocking_ids": BLOCKING_IDS,
            "next_allowed_action": NEXT_ALLOWED_ACTION,
        },
        "M2 capability lifecycle_projection",
    )


def validate_lifecycle_closeout_anchor(root: Path) -> None:
    """Validate the accepted lifecycle boundary only at A2 -> e90."""

    validate_a2_historical_recovery(root)
    _validate_historical_anchor_identity(
        root,
        LIFECYCLE_CLOSEOUT_COMMIT,
        LIFECYCLE_CLOSEOUT_TREE,
    )
    parent = _git(root, ["rev-parse", f"{LIFECYCLE_CLOSEOUT_COMMIT}^"])
    commit_count_text = _git(
        root,
        [
            "rev-list",
            "--count",
            f"{RECOVERY_CANDIDATE_COMMIT}..{LIFECYCLE_CLOSEOUT_COMMIT}",
        ],
    )
    require(commit_count_text.isdigit(), "lifecycle commit count is not numeric")
    changed_paths = _git(
        root,
        [
            "diff",
            "--name-only",
            RECOVERY_CANDIDATE_COMMIT,
            LIFECYCLE_CLOSEOUT_COMMIT,
            "--",
        ],
    ).splitlines()
    _validate_lifecycle_anchor_structure(
        parent=parent,
        commit_count=int(commit_count_text),
        changed_paths=changed_paths,
    )
    validate_lifecycle_preservation_state(
        root,
        artifact_reader=_git_object_reader(root, LIFECYCLE_CLOSEOUT_COMMIT),
    )


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"},
    )
    return result.returncode == 0


def collect_descendant_protected_changes(
    root: Path,
    target: str,
    *,
    include_worktree: bool,
) -> list[str]:
    changes = set(
        _git(
            root,
            [
                "diff",
                "--name-only",
                LIFECYCLE_CLOSEOUT_COMMIT,
                target,
                "--",
                *DESCENDANT_PROTECTED_PATHS,
            ],
        ).splitlines()
    )
    if include_worktree:
        changes.update(
            _git(
                root,
                [
                    "diff",
                    "--name-only",
                    target,
                    "--",
                    *DESCENDANT_PROTECTED_PATHS,
                ],
            ).splitlines()
        )
        changes.update(
            _git(
                root,
                [
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "--",
                    *DESCENDANT_PROTECTED_PATHS,
                ],
            ).splitlines()
        )
    return sorted(path for path in changes if path)


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
    require(
        _is_ancestor(root, source_commit, candidate),
        "candidate does not descend from fixed source",
    )
    require(_git(root, ["status", "--porcelain", "--untracked-files=all"]) == "", "dirty candidate worktree")


def validate_post_accepted_descendant(
    root: Path,
    candidate: str | None = None,
    candidate_tree: str | None = None,
) -> None:
    require(
        (candidate is None) == (candidate_tree is None),
        "candidate commit and tree must be supplied together",
    )
    include_worktree = candidate is None
    if candidate is not None and candidate_tree is not None:
        validate_candidate_checkout(
            root,
            candidate,
            candidate_tree,
            source_commit=LIFECYCLE_CLOSEOUT_COMMIT,
        )
        target = candidate
        reader = _git_object_reader(root, target)
    else:
        target = _git(root, ["rev-parse", "HEAD"])
        target_tree = _git(root, ["rev-parse", "HEAD^{tree}"])
        require(
            re.fullmatch(r"[0-9a-f]{40}", target) is not None,
            "current descendant commit must be full SHA-1",
        )
        require(
            re.fullmatch(r"[0-9a-f]{40}", target_tree) is not None,
            "current descendant tree must be full SHA-1",
        )
        reader = _filesystem_reader(root)

    require(
        _is_ancestor(root, LIFECYCLE_CLOSEOUT_COMMIT, target),
        "current target is not a descendant of the accepted lifecycle anchor",
    )
    dirty = _git(root, ["status", "--porcelain", "--untracked-files=all"]) != ""
    require(
        target != LIFECYCLE_CLOSEOUT_COMMIT or (include_worktree and dirty),
        "post-accepted descendant mode cannot classify a clean lifecycle anchor",
    )
    protected_changes = collect_descendant_protected_changes(
        root,
        target,
        include_worktree=include_worktree,
    )
    require(
        not protected_changes,
        f"post-accepted descendant changed protected M2 state/evidence: {protected_changes}",
    )
    validate_lifecycle_preservation_state(root, artifact_reader=reader)


def validate_historical_candidate_checkout(
    root: Path,
    candidate: str | None = None,
    candidate_tree: str | None = None,
) -> None:
    validate_lifecycle_closeout_anchor(root)
    validate_post_accepted_descendant(root, candidate, candidate_tree)


def _resolve_semantic_mode(
    root: Path,
    mode: str,
    candidate: str | None,
) -> str:
    if mode == CURRENT_RECOVERY_CANDIDATE:
        return RECOVERY_CANDIDATE
    if mode != HISTORICAL_ACCEPTED_RECOVERY:
        return mode

    target = candidate or _git(root, ["rev-parse", "HEAD"])
    clean = _git(root, ["status", "--porcelain", "--untracked-files=all"]) == ""
    if target == LIFECYCLE_CLOSEOUT_COMMIT and clean:
        return LIFECYCLE_CLOSEOUT_ANCHOR
    return POST_ACCEPTED_NON_M2_DESCENDANT


def validate_recovery(
    project_root: Path = ROOT,
    *,
    mode: str,
    candidate: str | None = None,
    candidate_tree: str | None = None,
    check_git: bool = True,
) -> str:
    root = project_root.resolve()
    require(mode in VALIDATION_MODES, f"unknown recovery validation mode: {mode}")
    require((candidate is None) == (candidate_tree is None), "candidate commit and tree must be supplied together")
    semantic_mode = _resolve_semantic_mode(root, mode, candidate)
    require(
        check_git or semantic_mode == RECOVERY_CANDIDATE,
        "historical and descendant modes cannot disable Git-object validation",
    )

    if semantic_mode == RECOVERY_CANDIDATE:
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
        if check_git:
            require(candidate is not None and candidate_tree is not None, "current recovery mode requires exact Candidate A2 commit/tree")
            require(candidate == RECOVERY_CANDIDATE_COMMIT, "current recovery mode target is not Candidate A2")
            require(candidate_tree == RECOVERY_CANDIDATE_TREE, "current recovery mode tree is not Candidate A2")
            validate_candidate_checkout(
                root,
                candidate,
                candidate_tree,
                source_commit=SOURCE_COMMIT,
            )
            validate_changed_paths(collect_changed_paths(root))
        return semantic_mode

    if semantic_mode == LIFECYCLE_CLOSEOUT_ANCHOR:
        validate_lifecycle_closeout_anchor(root)
        if check_git:
            if candidate is not None and candidate_tree is not None:
                require(
                    candidate == LIFECYCLE_CLOSEOUT_COMMIT,
                    "lifecycle anchor mode target is not fixed e90",
                )
                require(
                    candidate_tree == LIFECYCLE_CLOSEOUT_TREE,
                    "lifecycle anchor mode tree is not fixed e90 tree",
                )
                validate_candidate_checkout(
                    root,
                    candidate,
                    candidate_tree,
                    source_commit=RECOVERY_CANDIDATE_COMMIT,
                )
            else:
                require(
                    _git(root, ["rev-parse", "HEAD"])
                    == LIFECYCLE_CLOSEOUT_COMMIT,
                    "lifecycle anchor mode checkout is not fixed e90",
                )
                require(
                    _git(root, ["rev-parse", "HEAD^{tree}"])
                    == LIFECYCLE_CLOSEOUT_TREE,
                    "lifecycle anchor mode checkout tree is not fixed e90 tree",
                )
        return semantic_mode

    require(
        semantic_mode == POST_ACCEPTED_NON_M2_DESCENDANT,
        f"unimplemented recovery validation mode: {semantic_mode}",
    )
    validate_lifecycle_closeout_anchor(root)
    if check_git:
        validate_post_accepted_descendant(root, candidate, candidate_tree)
    return semantic_mode


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="validate Attempt 002 recovery closeout evidence")
    parser.add_argument("--mode", choices=sorted(VALIDATION_MODES), required=True)
    parser.add_argument("--candidate", help="exact candidate commit for independent ACCEPT")
    parser.add_argument("--candidate-tree", help="exact candidate tree for independent ACCEPT")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        require(args.validate, "select --validate")
        semantic_mode = validate_recovery(
            mode=args.mode,
            candidate=args.candidate,
            candidate_tree=args.candidate_tree,
        )
        if semantic_mode != RECOVERY_CANDIDATE:
            print("HISTORICAL_RECOVERY_MANIFEST_VALID=PASS")
        print(json.dumps({
            "task_id": TASK_ID,
            "evidence_id": EVIDENCE_ID,
            "attempt_number": ATTEMPT_NUMBER,
            "requested_validation_mode": args.mode,
            "validation_mode": semantic_mode,
            "validation_status": "PASS",
            "historical_R2-INT-010": "FAIL",
            "effective_R2-INT-010": "RESOLVED_ADAPTER",
            "lifecycle_state": (
                "FROZEN_WITH_RECOVERY_EVIDENCE_PENDING_LIFECYCLE_CLOSEOUT"
                if semantic_mode == RECOVERY_CANDIDATE
                else "ACCEPTED_WITH_DOWNSTREAM_BLOCKERS"
            ),
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
