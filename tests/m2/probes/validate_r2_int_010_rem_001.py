#!/usr/bin/env python3
"""Fail-closed validator for additive R2-INT-010-REM-001 Phase J evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "R2-INT-010-REM-001"
EVIDENCE_ID = "R2-INT-010-REM-001-J001"
EVIDENCE_PATH_TEXT = "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json"
EXECUTION_PATH_TEXT = "reports/m2/probes/remediations/r2-int-010-rem-001/execution-records.json"
MANIFEST_PATH_TEXT = "reports/m2/probes/remediations/r2-int-010-rem-001/evidence-manifest.json"
SCHEMA_PATH_TEXT = "docs/implementation/m2/probes/remediation-evidence-v1.schema.json"
VALIDATOR_PATH_TEXT = "tests/m2/probes/validate_r2_int_010_rem_001.py"
TEST_PATH_TEXT = "tests/m2/probes/test_r2_int_010_rem_001.py"
MANIFEST_ARTIFACT_PATHS = [
    SCHEMA_PATH_TEXT,
    EVIDENCE_PATH_TEXT,
    EXECUTION_PATH_TEXT,
    VALIDATOR_PATH_TEXT,
    TEST_PATH_TEXT,
]
EVIDENCE_PATH = ROOT / EVIDENCE_PATH_TEXT
EXECUTION_PATH = ROOT / EXECUTION_PATH_TEXT
MANIFEST_PATH = ROOT / MANIFEST_PATH_TEXT

PLATFORM_COMMIT = "1339c490bd8cae1e2a6e6607fc0f1db019faab64"
PLATFORM_TREE = "25d5645caf883a73f165db0179accbca48ddf526"
RULES_COMMIT = "c6a840b10db46dc475cd9af9e6a1a13f1e68abd4"
RULES_TREE = "cfb11378935d4b2bf380a6505e87589c18b1eaa2"
PROPOSAL_COMMIT = "a767115af691b728c60bd272dce3fc01f2258bc7"
APPROVAL_CANDIDATE_COMMIT = "608157e05e0a5beaba3c87a5f8f6f525e73a1132"
CREATOR_SHA256 = "7e31836febd753ca32dc0b81d9f9d8fc7c15fee123730fc4998ca1ee30b7e3a2"
SOURCE_ARCHIVE_SHA256 = "14eb81c8e804932c556d2e7fbe5333ba343b65542d378213db621e3dbc849776"
OUTPUT_SHA256 = "ccd11063676ea1eea382833ab970e86c355ca4eb59aa7dc447412a4449ec6650"
CREATOR_BUILD_COMMAND = "argv-v1:pnpm|--dir|apps/creator-studio/frontend|build||go|build|-trimpath|-buildvcs=false|-tags|production,webkit2_41|-o|<CREATOR_BINARY>|./apps/creator-studio"

HISTORICAL_HASHES = {
    "reports/m2/probes/probe-results.json": "154e7c0ddf8ce7b2243ad6c78d10ceb6cddf02c3aeb6592716dcc5ad8fc64218",
    "reports/m2/probes/evidence-manifest.json": "3a48da621e45980d9b2258513954e1f29480fd9e12a35dcd29c12b77015c8ca7",
    "reports/m2/probes/external-gates.json": "a8951312cb9f23cf3f999a7258900603716ea6f0b4e7f684b8f6a53ed8f13a2d",
    "reports/m2/probes/external-evidence-index.json": "b4bf268d7f9ee1627edea5c1ff87fa74774e3f5689c97cd11f0af6881178a22c",
    "reports/m2/probes/external/m2-b001-ext-001/evidence-manifest.json": "c842d67ec1f83145fdb67a33368e1f7dfbf8f8bc28cf8b9ab7b98202e813af1f",
    "reports/m2/probes/external/m2-b001-ext-001/platform-command-evidence.json": "f709a45ecee13a8ccb5722f52acc96fb3c08c662e500aaa7c26681404b73637e",
    "reports/m2/probes/external/m2-b001-ext-001/supplement.json": "d2f21f4853e5b77e2796ba3cbe3c7001b4731cdbb251661d6375ac2d5cff193c",
}

EXPECTED_TARGET_PAIR = [
    {"target": "A:rules-residue", "repository": "rules-residue", "commit": RULES_COMMIT, "tree": RULES_TREE},
    {"target": "B:TRPG_PLATFORM", "repository": "TRPG_PLATFORM", "commit": PLATFORM_COMMIT, "tree": PLATFORM_TREE},
]

TRANSITION_REASON = "Exact cross-repository execution proves that the approved generic namespaced JSON extension path preserves and round-trips the rules-residue probe through Host and Creator Tool, resolving R2-INT-010 as an adapter without claiming formal M2-B002, formal M2-B009, or aggregate readiness."
EXPECTED_PREVIOUS_EVIDENCE = [
    {"evidence_id": "M2-B001-R2-INT-010", "record_role": "STATUS_PREDECESSOR", "path": "reports/m2/probes/probe-results.json", "sha256": HISTORICAL_HASHES["reports/m2/probes/probe-results.json"], "previous_status": "FAIL", "disposition": "RETAINED_IMMUTABLE_PREVIOUS_EVIDENCE"},
    {"evidence_id": "M2-B001-EXT-001-SUPPLEMENT", "record_role": "STATUS_PREDECESSOR", "path": "reports/m2/probes/external/m2-b001-ext-001/supplement.json", "sha256": HISTORICAL_HASHES["reports/m2/probes/external/m2-b001-ext-001/supplement.json"], "previous_status": "FAIL", "disposition": "RETAINED_IMMUTABLE_PREVIOUS_EVIDENCE"},
    {"evidence_id": "M2-B001-EXT-001-MANIFEST", "record_role": "IMMUTABLE_HASH_MANIFEST", "path": "reports/m2/probes/external/m2-b001-ext-001/evidence-manifest.json", "sha256": HISTORICAL_HASHES["reports/m2/probes/external/m2-b001-ext-001/evidence-manifest.json"], "previous_status": "NOT_APPLICABLE", "disposition": "RETAINED_IMMUTABLE_PREVIOUS_EVIDENCE"},
]

EXPECTED_PHASES = [
    {
        "evidence_id": "J-E001",
        "phase": "SOURCE_ARCHIVE_HOST_IMPORT_INSPECT_EXPORT_REIMPORT",
        "execution_status": "PASS",
        "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
        "source_tree_sha256": "20daecd7a1b40e7d1e8dd6052e7935671bddd543ac991e2e99d8d8530210455b",
        "source_builds_byte_and_mode_identical": True,
        "phases": ["import", "inspect", "export", "reimport"],
    },
    {
        "evidence_id": "J-E002",
        "phase": "CREATOR_IMPORT_INSPECT_EDIT_VALIDATE_EXPORT_REIMPORT",
        "execution_status": "PASS",
        "phases": ["import", "inspect", "edit", "validate", "export", "reimport"],
    },
    {
        "evidence_id": "J-E003",
        "phase": "DETERMINISTIC_CREATOR_EXPORT",
        "execution_status": "PASS",
        "output_sha256": [OUTPUT_SHA256, OUTPUT_SHA256],
    },
    {
        "evidence_id": "J-E004",
        "phase": "HOST_PRESERVATION_AFTER_CREATOR_RELOAD",
        "execution_status": "PASS",
        "manifest_preserved": True,
        "descriptor_preserved": True,
        "schema_preserved": True,
        "other_content_preserved": True,
        "semantic_equality_after_reload": True,
    },
    {
        "evidence_id": "J-E005",
        "phase": "CREATOR_SCHEMA_INVALID_EDIT_REJECTION",
        "execution_status": "PASS",
        "observed_code": "ERR_EXTENSION_SCHEMA_VALIDATION",
    },
    {
        "evidence_id": "J-E006",
        "phase": "SIX_TYPED_HOST_PAIR_NEGATIVES",
        "execution_status": "PASS",
        "cases": [
            {"name": "schema_digest_mismatch", "observed_code": "ERR_EXTENSION_SCHEMA_DIGEST_MISMATCH"},
            {"name": "remote_schema_ref_digest_rebound", "observed_code": "ERR_EXTENSION_INVALID"},
            {"name": "cross_file_schema_ref_digest_rebound", "observed_code": "ERR_EXTENSION_INVALID"},
            {"name": "path_traversal", "observed_code": "ERR_EXTENSION_INVALID"},
            {"name": "absolute_path", "observed_code": "ERR_EXTENSION_INVALID"},
            {"name": "required_unsupported_host_api", "observed_code": "ERR_EXTENSION_REQUIRED_UNSUPPORTED"},
        ],
    },
    {
        "evidence_id": "J-E007",
        "phase": "RULES_SOURCE_SYMLINK_REJECTION",
        "execution_status": "PASS",
        "output_absent": True,
        "observed": "REJECTED_SYMBOLIC_LINK",
    },
]

EXPECTED_PROJECTIONS = {
    "probe_status": {"R2-INT-010": "RESOLVED_ADAPTER"},
    "external_gates": [
        {"gate_id": "EXT-CREATOR-EXTENSIONS", "execution_status": "BLOCKED_EXTERNAL", "blocking_probe_ids": ["R2-INT-006"]},
        {"gate_id": "EXT-RUNTIME-SAFETY", "execution_status": "BLOCKED_EXTERNAL", "blocking_probe_ids": ["R2-INT-011", "R2-INT-012"]},
    ],
    "readiness": {
        "M2-B002_READY": "NO",
        "M2-B002": "NOT_STARTED",
        "blocking_ids": ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"],
    },
}

EXPECTED_INTEGRITY_CLASSES = [
    {
        "class_id": "F001",
        "meaning": "VALIDATOR_SUPPORTED_ATTACK_CLASS",
        "validator_coverage": [
            "forged_pass", "duplicate_record", "missing_field", "wrong_repository_commit_tree",
            "missing_or_wrong_target_pair", "altered_mapping",
        ],
    },
    {
        "class_id": "F002",
        "meaning": "VALIDATOR_SUPPORTED_ATTACK_CLASS",
        "validator_coverage": [
            "stale_historical_hash_or_evidence", "proposal_as_execution", "not_run_as_pass",
            "mismatched_creator_output", "mismatched_platform_rules_pair", "historical_rewrite",
            "integrity_class_status_misuse",
        ],
    },
]

RECORD_IDS = [f"J-R{number:03d}" for number in range(1, 17)]
RECORD_COMMANDS = [
    "git rev-parse HEAD^{commit} [TRPG_PLATFORM]",
    "git rev-parse HEAD^{tree} [TRPG_PLATFORM]",
    "git rev-parse HEAD^{commit} [rules-residue]",
    "git rev-parse HEAD^{tree} [rules-residue]",
    "<CREATOR_BINARY> identity",
    "<CREATOR_BINARY> extension edit --archive <SOURCE_ARCHIVE> --namespace org.trpgplatform.rules-residue.probe --json-file <COUNT_2> --output <OUTPUT_1> --conflict-token sha256:14eb81c8e804932c556d2e7fbe5333ba343b65542d378213db621e3dbc849776",
    "<CREATOR_BINARY> extension edit --archive <SOURCE_ARCHIVE> --namespace org.trpgplatform.rules-residue.probe --json-file <COUNT_2> --output <OUTPUT_2> --conflict-token sha256:14eb81c8e804932c556d2e7fbe5333ba343b65542d378213db621e3dbc849776",
    "<HOST_ARCHIVE_BINARY> <RULES_SOURCE_1_PROJECT> <RULES_SOURCE_1_LOCK> <SOURCE_ARCHIVE> <HOST_BUILD_JSON>",
    "go run -buildvcs=false verify.go <SOURCE_ARCHIVE> <OUTPUT_1> <OUTPUT_2> <HOST_RELOAD_JSON>",
    "go run -buildvcs=false negative.go <RULES_SOURCE_1_LOCK> <HOST_NEGATIVES_JSON>",
    "python3 <RULES_SYMLINK_NEGATIVE_HARNESS>",
    "<CREATOR_BINARY> extension edit --archive <SOURCE_ARCHIVE> --namespace org.trpgplatform.rules-residue.probe --json-file <SCHEMA_INVALID> --output <MUST_NOT_EXIST> --conflict-token sha256:14eb81c8e804932c556d2e7fbe5333ba343b65542d378213db621e3dbc849776",
    "go test ./internal/package/... ./cmd/creator-cli/... ./apps/creator-studio/... ./tests/integration/package_extensions/... -count=1",
    "python3 -m unittest discover -s tests -p test_platform_v2_probe_adapter.py -v",
    "python3 tools/run_acceptance.py [exact rules archive]",
    "python3 harness/compare_source_builds.py <RULES_SOURCE_1> <RULES_SOURCE_2> <SOURCE_BUILD_COMPARISON_JSON>",
]
RECORD_EXIT_CODES = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
RECORD_CAPTURE_HASHES = [
    "489bca3b4ae03053e1b561b144b1405aed1fc49ac6e105f3db795e6c29e077d5",
    "3f4c74712d65e0db879fcb53b6eaf6c2f4d8faca87b8a3045c5e9366f8426066",
    "5910128106dd97095f601ec219f3350fca165f5dc4768e9bfbd1baad59d51428",
    "e43a0714c55445bc72b5365365df3bb5e96ae1034a3456868a9f50e845c00b5c",
    "3905414c20e0c0cd13035c3139f7e424b37f0f81407c7ac47bf8c0a8ab0290ba",
    "932a3c7fec54b224cb2bc1d9af7065120c327aacc0419e3038821860ec94a1bb",
    "02893c89dec3d8fb913c1b8baa33a464d4837114b55fd5f4a65ba1a6cdf29380",
    "f6bc8616f9b6c009fdf471b69b343d9fc2011ea1105cacf90f0819e8a0c1ecb5",
    "0a9c253eb3361ac3a730a114abc1c45ca63d9ab41a1f805061bfb9dc1eb4734a",
    "f61261745850c6b7a4fcf078d2266dfdc893e35da99da315e58ee76aa59ed433",
    "3a3a5ec434a57a3fcd012b9bedb161a858220e72a90ae2a63e2204ca3c2b61a5",
    "70a81dc517a31badea49892c100a34f5c21f72931e510cced3be8358efb4deb5",
    "8af8f98e409ce4a7ae4e7c22e92a752c94541f97c3bff4b32ca0e6fb5f29b086",
    "ea0dd9962fe7336a3f763634767c97e08c43c745aba7a662144c0cada60c48df",
    "653a3d88668c06cc55c1d6524a262b76d826a687c0be6a801f870d13256124fa",
    "1d4d173a365e43317669a8c96de5cf09d377421f64fd960b891a1c57c067e087",
]
RECORD_TEXT_HASHES = [
    "8394da4e9e66e9981d853273c86dec2a427e6241c7a2926d95d0658d3c94bbb6",
    "4cc30e0c500b467817f4deeedfafaf218a5e25aa09e29be4184b36b063f2b56b",
    "b99eda3784d84d1d998ecdf4034d6fabfc81f007b89d249975f41338553494d1",
    "bcf01f8e4d9b9891afa80618204877b3131e22b2156b61265f012ae32c2e8f00",
    "8095c2c8d3d8933a69b6a018fcbb2dda3a7b0c6d2d0042925abb06ed74ee464d",
    "f606aa068c6cb14c90d144fe98d39dbb9d4231ebec1b44696d03cd22a652ecad",
    "f606aa068c6cb14c90d144fe98d39dbb9d4231ebec1b44696d03cd22a652ecad",
    "6d463a7564bbb03f94ab2a6be55ff71e777be55b3af5e9a4ad868107ca0d9c6d",
    "0e4bb159b2561656cda76098ace4bffdf9e3d3598606125216d186fb0b0221f2",
    "387749490a010982d8bef0cacd9094660c89af3155f61f4097ab0a7f895055f1",
    "848886413ed6b96e32a8b03ad95e720296dd377702715931502a631d506ddb8e",
    "a2f1b781fd579333923ff01d57d60d1b9f3c77f24f0574ae7f4e64ca587b2a2e",
    "b2dd11b9ece76d5012b1e86123d8458c8a1be9b48d24346739d62da13d980bbf",
    "e93ce737df6ffda74232ce3da95ece3fd1360342ef681a7a3f7f14a1b449dc1d",
    "7600d1bb6fde75850f31472844da45675342d5a50e40c7ff9f29b5536ba6c61f",
    "5957f09945b68bc4c78ea74e96c8e2dca8626303b618046adad3ef9fb3380cbf",
]


class RemediationValidationError(ValueError):
    """Raised when evidence is incomplete, stale, or overclaims execution."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RemediationValidationError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_constant(value: str) -> None:
    raise RemediationValidationError(f"non-finite JSON constant is forbidden: {value}")


def load_json_text(text: str, context: str = "JSON evidence") -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise RemediationValidationError(f"cannot load {context}: {exc}") from exc
    require(isinstance(value, dict), f"{context} must be an object")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RemediationValidationError(f"cannot load JSON evidence {path}: {exc}") from exc
    return load_json_text(text, str(path))


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_historical_hashes() -> None:
    for path_text, digest in HISTORICAL_HASHES.items():
        path = ROOT / path_text
        require(path.is_file(), f"historical evidence missing: {path_text}")
        require(sha256_path(path) == digest, f"historical evidence changed: {path_text}")


def validate_execution(data: dict[str, Any]) -> None:
    require(set(data) == {"schema_version", "evidence_set_id", "task_id", "previous_status", "source_phase", "normalization", "records"}, "execution-record fields are missing or unknown")
    require(data["schema_version"] == "rules-residue.m2.remediation-execution-records/1.0", "execution-record schema version mismatch")
    require(data["evidence_set_id"] == EVIDENCE_ID and data["task_id"] == TASK_ID, "execution-record identity mismatch")
    require(data["previous_status"] == "FAIL" and data["source_phase"] == "I_CROSS_REPOSITORY_ACCEPT_RAW", "execution-record history was rewritten")
    require(data["normalization"] == "UTF8_TEXT_LF; scratch paths replaced by angle-bracket labels; JSON observations reduced to ordered decision-relevant fields; no binary bytes embedded", "execution normalization contract changed")
    records = data.get("records")
    require(isinstance(records, list) and len(records) == 16, "execution records are missing or duplicated")
    ids = [item.get("evidence_id") for item in records if isinstance(item, dict)]
    commands = [item.get("command") for item in records if isinstance(item, dict)]
    require(ids == RECORD_IDS and len(ids) == len(set(ids)), "execution evidence IDs are missing, duplicated, or reordered")
    require(commands == RECORD_COMMANDS and len(commands) == len(set(commands)), "execution commands are missing, duplicated, altered, or reordered")
    for index, record in enumerate(records):
        require(set(record) == {"evidence_id", "command", "exit_code", "source_capture_sha256", "normalized_text"}, f"execution record fields invalid: {record.get('evidence_id')}")
        require(record["exit_code"] == RECORD_EXIT_CODES[index] and type(record["exit_code"]) is int, f"execution exit code changed: {record['evidence_id']}")
        require(record["source_capture_sha256"] == RECORD_CAPTURE_HASHES[index], f"raw source capture mismatch: {record['evidence_id']}")
        normalized = record["normalized_text"]
        require(isinstance(normalized, str) and normalized.endswith("\n") and "\x00" not in normalized, f"execution record is not normalized UTF-8 text: {record['evidence_id']}")
        require("data:application/octet-stream" not in normalized and "base64," not in normalized, f"binary material embedded: {record['evidence_id']}")
        require(sha256_text(normalized) == RECORD_TEXT_HASHES[index], f"normalized execution output changed: {record['evidence_id']}")


def validate_evidence(data: dict[str, Any]) -> None:
    require(set(data) == {
        "schema_version", "evidence_id", "nature", "task_id", "previous_status", "new_status",
        "classification", "transition_reason", "previous_evidence", "formal_semantics", "route_binding", "antecedents", "exact_target_pair", "creator_tool",
        "evidence_links", "phase_results", "non_claims", "projections", "integrity_classes",
    }, "evidence fields are missing or unknown")
    require(data["schema_version"] == "rules-residue.m2.remediation-evidence/1.0", "evidence schema version mismatch")
    require(data["evidence_id"] == EVIDENCE_ID and data["nature"] == "ADDITIVE_REMEDIATION_EVIDENCE" and data["task_id"] == TASK_ID, "evidence identity mismatch")
    require(data["previous_status"] == "FAIL" and data["new_status"] == "RESOLVED_ADAPTER", "remediation transition was forged")
    require(data["classification"] == "R2_COMPATIBILITY_ADAPTER", "remediation classification changed")
    require(data["transition_reason"] == TRANSITION_REASON, "transition reason is missing or altered")
    require(data["previous_evidence"] == EXPECTED_PREVIOUS_EVIDENCE, "previous evidence chain is missing, stale, reordered, or rewritten")
    require(len({item["evidence_id"] for item in data["previous_evidence"]}) == 3, "previous evidence ID duplicated")
    require(data["formal_semantics"] == {"formal_B002": False, "formal_B009": False}, "formal B002/B009 scope boundary changed")
    require(data["route_binding"] == {
        "route_id": "R2-INT-010-REM-001-EVIDENCE-IMPLEMENT", "mode": "IMPLEMENT", "milestone": "M1",
        "batch_id": "M1-B010", "source_commit": RULES_COMMIT, "source_tree": RULES_TREE,
        "binding_digest": "0f60912817903a926e07bd7e11d6b66402d5676c2aa45ee0faa4485db70b81e6",
        "freshness_status": "PASS",
    }, "route binding is stale or altered")
    require(data["antecedents"] == {
        "platform_change_proposal": {"proposal_id": "PLATFORM-CHANGE-R2-INT-010-REM-001", "commit": PROPOSAL_COMMIT, "disposition": "ANTECEDENT_ONLY_NOT_EXECUTION_EVIDENCE"},
        "owner_governance_approval_candidate": {"owner_decision_id": "OWNER-DECISION-PLATFORM-CHANGE-R2-INT-010-REM-001", "commit": APPROVAL_CANDIDATE_COMMIT, "disposition": "ANTECEDENT_ONLY_NOT_EXECUTION_EVIDENCE"},
    }, "proposal/approval antecedent was altered or promoted to execution evidence")
    pair = data.get("exact_target_pair")
    require(pair == EXPECTED_TARGET_PAIR, "exact repository/commit/tree target pair is missing, reordered, or mismatched")
    require(len({item["target"] for item in pair}) == 2 and len({item["repository"] for item in pair}) == 2, "exact target pair is duplicated")
    require(data["creator_tool"] == {
        "platform_commit": PLATFORM_COMMIT, "platform_tree": PLATFORM_TREE, "binary_version": "0.1.0-m1",
        "build_command": CREATOR_BUILD_COMMAND, "binary_sha256": CREATOR_SHA256,
    }, "Creator identity/build/output binding mismatch")
    require(data["evidence_links"] == {"execution_records": EXECUTION_PATH_TEXT, "evidence_manifest": MANIFEST_PATH_TEXT}, "evidence links changed")
    phases = data.get("phase_results")
    require(phases == EXPECTED_PHASES, "phase results are incomplete, duplicated, reordered, or altered")
    phase_ids = [item["evidence_id"] for item in phases]
    require(len(phase_ids) == len(set(phase_ids)), "duplicate phase evidence ID")
    negative_names = [item["name"] for item in phases[5]["cases"]]
    require(len(negative_names) == 6 and len(negative_names) == len(set(negative_names)), "typed Host negative cases are missing or duplicated")
    require(data["non_claims"] == {
        "formal_B002": {"execution_status": "NOT_RUN", "claimed": False},
        "formal_B009": {"execution_status": "NOT_RUN", "claimed": False},
        "aggregate_status": "NOT_CLAIMED",
    }, "formal/aggregate non-claim was promoted")
    require(data["projections"] == EXPECTED_PROJECTIONS, "gate/readiness projection is false or altered")
    integrity = data.get("integrity_classes")
    require(integrity == EXPECTED_INTEGRITY_CLASSES, "integrity attack-class coverage changed")
    require(len({item["class_id"] for item in integrity}) == 2, "integrity class duplicated")
    for item in integrity:
        require(not ({"execution_status", "status", "result"} & set(item)), "F001/F002 attack class was misrepresented as an execution result")


def validate_manifest(data: dict[str, Any]) -> None:
    require(set(data) == {"schema_version", "evidence_set_id", "task_id", "artifacts", "immutable_historical_artifacts", "historical_mutation_policy"}, "manifest fields are missing or unknown")
    require(data["schema_version"] == "rules-residue.m2.remediation-evidence-manifest/1.0" and data["evidence_set_id"] == EVIDENCE_ID and data["task_id"] == TASK_ID, "manifest identity mismatch")
    expected_artifacts = [
        {"path": path_text, "sha256": sha256_path(ROOT / path_text)}
        for path_text in MANIFEST_ARTIFACT_PATHS
    ]
    require(data["artifacts"] == expected_artifacts, "manifest evidence/execution artifact coverage or hash is stale")
    expected_historical = [{"path": path, "sha256": digest} for path, digest in HISTORICAL_HASHES.items()]
    require(data["immutable_historical_artifacts"] == expected_historical, "historical manifest coverage, order, path, or digest changed")
    require(data["historical_mutation_policy"] == "REJECT_ANY_CURRENT_BYTE_MISMATCH; ADDITIVE_EVIDENCE_ONLY", "historical mutation policy changed")
    validate_historical_hashes()


def validate_remediation(
    evidence_data: dict[str, Any] | None = None,
    execution_data: dict[str, Any] | None = None,
    manifest_data: dict[str, Any] | None = None,
) -> None:
    validate_historical_hashes()
    validate_evidence(evidence_data if evidence_data is not None else load_json(EVIDENCE_PATH))
    validate_execution(execution_data if execution_data is not None else load_json(EXECUTION_PATH))
    validate_manifest(manifest_data if manifest_data is not None else load_json(MANIFEST_PATH))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="validate the additive remediation evidence set")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        require(args.validate, "select --validate")
        validate_remediation()
        print(json.dumps({
            "task_id": TASK_ID,
            "previous_status": "FAIL",
            "new_status": "RESOLVED_ADAPTER",
            "validation_status": "PASS",
            "formal_B002": False,
            "formal_B009": False,
            "aggregate_pass_claimed": False,
        }, sort_keys=True))
        return 0
    except (RemediationValidationError, OSError, json.JSONDecodeError) as exc:
        print(f"{TASK_ID} remediation evidence validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
