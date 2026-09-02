from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.codex_route import RouteError, generate_reading_map, validate_request
from tools.lib.common import PROJECT_ROOT, runtime_relative_paths
from tools.lib.schema_subset import validate
from tools.story_construction import (
    canonical_json_bytes,
    canonical_sha256,
    file_sha256,
    literary_input_hash,
    literary_order_hash,
    merkle_root,
    validate_literary_execution,
    validate_task_packet_pairing,
    validate_visual_execution,
    visual_order_hash,
)


BASE_COMMIT = "6f9f671401f5857d460ca8e0bd8a86ebe04bb0b6"
BASE_TREE = "2dfa6553770f4eedbb4def358f661b9b16b79a4d"
BASE_CANON_HASH = "d7ceea75615b57970f3b9712b73ed4c9f65a9c4406c877e9013470cb53a6141a"
CHANGE_SET_ID = "CS-SCG-PRECONTENT-READINESS-R1-001"
CANDIDATE_APPROVAL_STATUS = "PENDING_OWNER_EXACT_HASH_APPROVAL_M3_B002"
APPROVAL_STATUS = "PENDING_OWNER_ACTIVATION_HASH_APPROVAL_M3_B002"
OWNER_PLAN_APPROVAL_ID = "OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-PLAN-R2"
OWNER_PACKAGE_ID = "SCG-PRECONTENT-M3-B002-IMPLEMENT-V2"
OWNER_PACKAGE_MANIFEST_FILE_SHA256 = "760aeb0daa8db0d635b03e2f24866527b5fbc3af0b0b38f3b49d7baaeba414b9"
PLAN_READING_MAP_BINDING_DIGEST = "5081c3b31256ce5f1848a4a0007942b6f7490ec58f36c2b26fab7bd63c2f276c"
IMPLEMENT_READING_MAP_BINDING_DIGEST = "6fb42d7d098f4aeff33e540ed439abf825a36435f91aa9ebe41ec0a13b796de1"
RUNTIME_PACKAGE_SHA256 = "29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314"
IMPLEMENTATION_CANDIDATE_COMMIT = "74fecbe6984f150f83c364e5d5a5850132cfc147"
IMPLEMENTATION_CANDIDATE_TREE = "b81fa075a1b812478dbc3e196429c7392279e28f"
IMPLEMENTATION_CANDIDATE_PARENT = BASE_COMMIT
IMPLEMENTATION_OWNER_APPROVAL_ID = "OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-CANDIDATE-74FECBE6-R1"
IMPLEMENTATION_OWNER_APPROVAL_RAW_SHA256 = "f2ee360dd75b25d6e8f6869dc2a19e0dc2edb5b635cc007ff57aeacd6e5c5700"
IMPLEMENTATION_OWNER_APPROVAL_CANONICAL_SHA256 = "25908c90f0af7ce99fe736536991971c9a8cbaf2b6617fc9c4aedc8e198281d9"
IMPLEMENTATION_ACCEPT_TASK_ID = "SCG-PRECONTENT-M3-B002-ACCEPT-001"
IMPLEMENTATION_ACCEPT_RESULT = "PASS_FIXED_M3_B002_CANDIDATE_ACCEPTED"
IMPLEMENTATION_ACCEPT_VERIFIER = "CODEX-INDEPENDENT-VERIFIER-SCG-PRECONTENT-M3-B002-ACCEPT-001"
IMPLEMENTATION_ACCEPT_ROUTE = "SCG-PRECONTENT-M3-B002-ACCEPT"
IMPLEMENTATION_ACCEPT_ROUTE_DIGEST = "b08bfd965a6c8ca8515460f5507e212056ab8b6e6d65fc9d53b7976b2a95af76"
ACTIVATION_TASK_ID = "SCG-PRECONTENT-M3-B002-ACTIVATION-CLOSEOUT-IMPLEMENT-001"
ACTIVATION_MODEL = "MODEL_B_FULL_FRAMEWORK_HASH_REAPPROVAL"
ACTIVATION_PROOF_TAG = "scg-precontent-m3-b002-activation-closeout-accepted"
R1_MANIFEST_FILE_SHA256 = "891944f172236b666eb78bc641f4e7ecabf6ec3e318ab4cd0b5858f045b06b67"
R1_MERKLE_ROOT = "87c6520fe0822e29312de6c72cad95f0849aa3d0bd4fbb27f97f1f786027bf8f"
R1_RECORD_COUNT = 68
PENDING_RECEIPT_FILE_SHA256 = "1fa87cf4d7a7e2cb876f832a685d3a74c7200653428e8a0f82f0dd3f856ee206"
PENDING_RECEIPT_PAYLOAD_HASH = "c7aa1758a86df27d39b6baf153d4adb69cff81d5e496c4cdb5456659c8d28a28"
DECISION_SET_HASH = "0e01181acbc9fb95c57ed1b910a3b561545e8824f0c60d7fdc35c93cff44146d"
PARTIAL_SUPERSESSION_HASH = "45bcd35ef9c18dea5e300c163ef232692a77b42ea9b11d9b555df118f74206da"
TRACEABILITY_HASH = "a0ed82836894d8d809447aa0b5d8cb8a05dfff87b363701b719de68f90b8359a"
ORIGINAL_SCHEMA_SET_HASH = "77c8d831c2fd4b79edc597215135ca111fd76b1e00b9d126fda5a4d1a7fcdc50"
M0_FIXTURE_GRAPH_HASH = "7319d3670ae280d4a32fc2e40aa8412faeb4dc465092b067e0147574734c7807"
CONTEXT_MANIFEST_SET_HASH = "e638858d4fe7b2baa7bcbe5648ee611e13e9e54252cf43ffe51cc494c6a386df"
OMISSION_REPORT_SET_HASH = "1c8a3d062d89fe49830bb0ad43fa13e04d7fed9b997046b09a927c4179d53aa9"
STATIC_GATE_RESULT_HASH = "a5acc295f30d1b81739b4c2064ea57356900cc375736b9a20e1feb2177f07dc5"
PROVIDER_PROFILE_CONTRACT_SET_HASH = "dc1a5b37bc42f0d9f97ceac9f34460138009a79499304ac1844ef77e21ceb3e5"
PROVIDER_ZERO_CALL_EVIDENCE_HASH = "e6536a180aeb21b20ca9b65594610e65c50d72bf388b513533bed799366214f5"

REQUIRED_EXTERNAL_PROOFS = (
    "ACTIVATION_SPECIFIC_OWNER_FULL_HASH_APPROVAL",
    "PASS_FIXED_M3_B002_ACTIVATION_CANDIDATE_ACCEPTED",
    "VALID_DETACHED_ACCEPTED_ACTIVATION_ENVELOPE_TAG",
    "FINAL_FAST_FORWARD_INTEGRATION",
)

ALLOWLIST = (
    "docs/governance/story-construction/10_PRECONTENT_READINESS.md",
    "docs/operations/agents/m3/deepseek-harness/PRECONTENT_M0_PROFILE.md",
    ".grok/READING_MAP_PROFILE.yaml",
    ".grok/RETURN_CONTRACT.md",
    ".grok/PRECONTENT_M0_PROFILE.md",
    ".codex/prompts/m3/PRECONTENT/README.md",
    ".codex/prompts/m3/PRECONTENT/IMPLEMENT.md",
    ".codex/prompts/m3/PRECONTENT/ACCEPT.md",
    ".codex/prompts/m3/PRECONTENT/REPAIR.md",
    ".codex/routes/m3-precontent-b002-accept-request.json",
    ".codex/routes/m3-precontent-b002-repair-request.json",
    ".codex/routes/m3-precontent-b003-plan-request.json",
    "governance/story-construction/precontent/decisions.scg-pre-q001-q021.yaml",
    "governance/story-construction/precontent/traceability.scg-pre-r1.yaml",
    "governance/story-construction/precontent/partial-supersession.scg-pre-r1.yaml",
    "governance/story-construction/precontent/manifests/framework-manifest.r1.json",
    "governance/story-construction/change-sets/CS-SCG-PRECONTENT-READINESS-R1-001.yaml",
    "governance/story-construction/receipts/scg-precontent-readiness-r1.pending.json",
    "schemas/story-construction/precontent-decision-set-v1.schema.json",
    "schemas/story-construction/partial-supersession-v1.schema.json",
    "schemas/story-construction/test-fixture-graph-v1.schema.json",
    "schemas/story-construction/text-order-v2.schema.json",
    "schemas/story-construction/visual-order-v2.schema.json",
    "schemas/story-construction/context-manifest-v1.schema.json",
    "schemas/story-construction/omission-report-v1.schema.json",
    "schemas/story-construction/m2-dependency-classification-v1.schema.json",
    "schemas/story-construction/provider-execution-profile-v1.schema.json",
    "schemas/story-construction/provider-run-receipt-v1.schema.json",
    "schemas/story-construction/provider-certificate-v1.schema.json",
    "schemas/story-construction/profile-compatibility-preflight-v1.schema.json",
    "schemas/story-construction/fault-injection-receipt-v1.schema.json",
    "schemas/story-construction/region-content-intensity-contract-v1.schema.json",
    "schemas/story-construction/m0-acceptance-bundle-v1.schema.json",
    "schemas/story-construction/global-t1-closure-matrix-v1.schema.json",
    "schemas/story-construction/region-interface-matrix-v1.schema.json",
    "schemas/story-construction/causal-epistemic-proof-matrix-v1.schema.json",
    "schemas/story-construction/region-risk-scorecard-v1.schema.json",
    "schemas/story-construction/precontent-readiness-bundle-v1.schema.json",
    "tests/fixtures/story-construction/precontent-m0/test-fixture-graph.json",
    "tests/fixtures/story-construction/precontent-m0/test-canon-envelope.json",
    "tests/fixtures/story-construction/precontent-m0/test-reveal-contract.json",
    "tests/fixtures/story-construction/precontent-m0/test-npc-epistemic-state.json",
    "tests/fixtures/story-construction/precontent-m0/test-region-dossier.json",
    "tests/fixtures/story-construction/precontent-m0/test-region-intensity-contract.json",
    "tests/fixtures/story-construction/precontent-m0/test-context-manifest-text-001.json",
    "tests/fixtures/story-construction/precontent-m0/test-omission-report-text-001.json",
    "tests/fixtures/story-construction/precontent-m0/test-context-manifest-text-002.json",
    "tests/fixtures/story-construction/precontent-m0/test-omission-report-text-002.json",
    "tests/fixtures/story-construction/precontent-m0/test-context-manifest-visual-001.json",
    "tests/fixtures/story-construction/precontent-m0/test-omission-report-visual-001.json",
    "tests/fixtures/story-construction/precontent-m0/text-order-001.json",
    "tests/fixtures/story-construction/precontent-m0/text-order-002.json",
    "tests/fixtures/story-construction/precontent-m0/visual-order-001.json",
    "tests/fixtures/story-construction/precontent-m0/task-packet-text-001.json",
    "tests/fixtures/story-construction/precontent-m0/task-packet-text-002.json",
    "tests/fixtures/story-construction/precontent-m0/task-packet-visual-001.json",
    "tests/fixtures/story-construction/precontent-m0/cross-modal-oracle.json",
    "tests/fixtures/story-construction/precontent-m0/fault-injection-spec.json",
    "tests/fixtures/story-construction/precontent-m0/expected-static-gates.json",
    "tools/validate_precontent_readiness.py",
    "tools/run_grok_visual_order.py",
    "tools/export_harness_run_receipt.py",
    "tools/run_m0_fault_injection.py",
    "tools/build_precontent_readiness_bundle.py",
    "tools/validate_story_construction_governance.py",
    "tools/validate_deepseek_literary_task.py",
    "tools/validate_visual_order.py",
    "tools/validate_project.py",
    "tests/test_precontent_readiness.py",
    "tests/test_provider_certification_gates.py",
)

ACTIVATION_ALLOWLIST = (
    ".codex/prompts/m3/PRECONTENT/README.md",
    ".codex/prompts/m3/PRECONTENT/ACTIVATION_ACCEPT.md",
    ".codex/routes/m3-precontent-b002-activation-closeout-accept-request.json",
    "docs/governance/story-construction/10_PRECONTENT_READINESS.md",
    "governance/story-construction/change-sets/CS-SCG-PRECONTENT-READINESS-R1-001.yaml",
    "governance/story-construction/precontent/manifests/framework-manifest.r2.json",
    "governance/story-construction/approvals/OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-CANDIDATE-74FECBE6-R1.consumption.json",
    "governance/story-construction/receipts/scg-precontent-readiness-r1.final.json",
    "schemas/story-construction/precontent-change-set-v2.schema.json",
    "schemas/story-construction/precontent-final-receipt-v2.schema.json",
    "schemas/story-construction/precontent-owner-approval-consumption-v1.schema.json",
    "schemas/story-construction/precontent-activation-owner-approval-v1.schema.json",
    "schemas/story-construction/precontent-activation-closeout-envelope-v1.schema.json",
    "tests/fixtures/story-construction/precontent-lifecycle-state-v1.json",
    "tools/build_precontent_readiness_bundle.py",
    "tools/validate_precontent_readiness.py",
    "tools/validate_story_construction_governance.py",
    "tests/test_precontent_readiness.py",
)

CHANGED_OLD_PATHS = (
    ".codex/prompts/m3/PRECONTENT/README.md",
    "docs/governance/story-construction/10_PRECONTENT_READINESS.md",
    "governance/story-construction/change-sets/CS-SCG-PRECONTENT-READINESS-R1-001.yaml",
    "tools/build_precontent_readiness_bundle.py",
    "tools/validate_precontent_readiness.py",
    "tools/validate_story_construction_governance.py",
    "tests/test_precontent_readiness.py",
)

NEW_SEMANTIC_PATHS = (
    ".codex/prompts/m3/PRECONTENT/ACTIVATION_ACCEPT.md",
    ".codex/routes/m3-precontent-b002-activation-closeout-accept-request.json",
    "schemas/story-construction/precontent-change-set-v2.schema.json",
    "schemas/story-construction/precontent-final-receipt-v2.schema.json",
    "schemas/story-construction/precontent-owner-approval-consumption-v1.schema.json",
    "schemas/story-construction/precontent-activation-owner-approval-v1.schema.json",
    "schemas/story-construction/precontent-activation-closeout-envelope-v1.schema.json",
    "tests/fixtures/story-construction/precontent-lifecycle-state-v1.json",
)

AUDIT_PATHS = (
    "governance/story-construction/precontent/manifests/framework-manifest.r2.json",
    "governance/story-construction/approvals/OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-CANDIDATE-74FECBE6-R1.consumption.json",
    "governance/story-construction/receipts/scg-precontent-readiness-r1.final.json",
)

SCHEMA_FILES = (
    "precontent-decision-set-v1.schema.json",
    "partial-supersession-v1.schema.json",
    "test-fixture-graph-v1.schema.json",
    "text-order-v2.schema.json",
    "visual-order-v2.schema.json",
    "context-manifest-v1.schema.json",
    "omission-report-v1.schema.json",
    "m2-dependency-classification-v1.schema.json",
    "provider-execution-profile-v1.schema.json",
    "provider-run-receipt-v1.schema.json",
    "provider-certificate-v1.schema.json",
    "profile-compatibility-preflight-v1.schema.json",
    "fault-injection-receipt-v1.schema.json",
    "region-content-intensity-contract-v1.schema.json",
    "m0-acceptance-bundle-v1.schema.json",
    "global-t1-closure-matrix-v1.schema.json",
    "region-interface-matrix-v1.schema.json",
    "causal-epistemic-proof-matrix-v1.schema.json",
    "region-risk-scorecard-v1.schema.json",
    "precontent-readiness-bundle-v1.schema.json",
)

ACTIVATION_SCHEMA_FILES = (
    "precontent-change-set-v2.schema.json",
    "precontent-final-receipt-v2.schema.json",
    "precontent-owner-approval-consumption-v1.schema.json",
    "precontent-activation-owner-approval-v1.schema.json",
    "precontent-activation-closeout-envelope-v1.schema.json",
)

COMBINED_SCHEMA_FILES = SCHEMA_FILES + ACTIVATION_SCHEMA_FILES

FIXTURE_ROOT = Path("tests/fixtures/story-construction/precontent-m0")
TEST_FIXTURE_FILES = (
    "test-fixture-graph.json", "test-canon-envelope.json", "test-reveal-contract.json",
    "test-npc-epistemic-state.json", "test-region-dossier.json",
    "test-region-intensity-contract.json", "test-context-manifest-text-001.json",
    "test-omission-report-text-001.json", "test-context-manifest-text-002.json",
    "test-omission-report-text-002.json", "test-context-manifest-visual-001.json",
    "test-omission-report-visual-001.json", "text-order-001.json", "text-order-002.json",
    "visual-order-001.json", "task-packet-text-001.json", "task-packet-text-002.json",
    "task-packet-visual-001.json", "cross-modal-oracle.json", "fault-injection-spec.json",
    "expected-static-gates.json",
)

MANIFEST_PATH = Path("governance/story-construction/precontent/manifests/framework-manifest.r1.json")
RECEIPT_PATH = Path("governance/story-construction/receipts/scg-precontent-readiness-r1.pending.json")
R2_MANIFEST_PATH = Path("governance/story-construction/precontent/manifests/framework-manifest.r2.json")
FINAL_RECEIPT_PATH = Path("governance/story-construction/receipts/scg-precontent-readiness-r1.final.json")
APPROVAL_CONSUMPTION_PATH = Path("governance/story-construction/approvals/OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-CANDIDATE-74FECBE6-R1.consumption.json")
DECISION_PATH = Path("governance/story-construction/precontent/decisions.scg-pre-q001-q021.yaml")
TRACEABILITY_PATH = Path("governance/story-construction/precontent/traceability.scg-pre-r1.yaml")
SUPERSESSION_PATH = Path("governance/story-construction/precontent/partial-supersession.scg-pre-r1.yaml")
CHANGE_SET_PATH = Path("governance/story-construction/change-sets/CS-SCG-PRECONTENT-READINESS-R1-001.yaml")

EXPECTED_DECISIONS = (
    ("SCG-PRE-Q001", "C-REVISED"), ("SCG-PRE-Q002", "B"),
    ("SCG-PRE-Q003", "B"), ("SCG-PRE-Q004", "C"),
    ("SCG-PRE-Q005", "C"), ("SCG-PRE-Q006", "C"),
    ("SCG-PRE-Q007", "B"), ("SCG-PRE-Q008", "C"),
    ("SCG-PRE-Q009", "C"), ("SCG-PRE-Q010", "A"),
    ("SCG-PRE-Q011", "A"), ("SCG-PRE-Q012", "B"),
    ("SCG-PRE-Q013", "B"), ("SCG-PRE-Q014", "B"),
    ("SCG-PRE-Q015", "A-REVISED"), ("SCG-PRE-Q016", "C"),
    ("SCG-PRE-Q017", "B"), ("SCG-PRE-Q018", "C-REVISED"),
    ("SCG-PRE-Q019", "B"), ("SCG-PRE-Q020", "B"),
    ("SCG-PRE-Q021", "B"),
)

ROUTE_SPECS = {
    ".codex/routes/m3-precontent-b002-accept-request.json": ("SCG-PRECONTENT-M3-B002-ACCEPT", "ACCEPT", "M3-B002"),
    ".codex/routes/m3-precontent-b002-repair-request.json": ("SCG-PRECONTENT-M3-B002-REPAIR", "REPAIR", "M3-B002"),
    ".codex/routes/m3-precontent-b003-plan-request.json": ("SCG-PRECONTENT-M3-B003-PLAN", "PLAN", "M3-B003"),
    ".codex/routes/m3-precontent-b002-activation-closeout-accept-request.json": (
        "SCG-PRECONTENT-M3-B002-ACTIVATION-CLOSEOUT-ACCEPT", "ACCEPT", "M3-B002"
    ),
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def allowlist_hash() -> str:
    payload = "".join(f"{path}\n" for path in sorted(ALLOWLIST)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def activation_allowlist_hash() -> str:
    payload = "".join(f"{path}\n" for path in sorted(ACTIVATION_ALLOWLIST)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _record_set_hash(records: Iterable[dict[str, str]]) -> str:
    return canonical_sha256(sorted(records, key=lambda item: item["path"]))


def activation_path_records(root: Path = PROJECT_ROOT) -> list[dict[str, str]]:
    root = root.resolve()
    return [
        {"path": path, "sha256": file_sha256(root / path)}
        for path in sorted(ACTIVATION_ALLOWLIST)
    ]


def activation_path_set_hash(root: Path = PROJECT_ROOT) -> str:
    return _record_set_hash(activation_path_records(root))


def _schema(root: Path, name: str) -> dict[str, Any]:
    value = read_json(root / "schemas/story-construction" / name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain an object schema")
    return value


def _schema_issues(instance: Any, schema: dict[str, Any], label: str) -> list[str]:
    return [f"{label}: {issue}" for issue in validate(instance, schema)]


def validate_test_boundary(document: Any, label: str = "TEST artifact") -> list[str]:
    if not isinstance(document, dict):
        return [f"{label}: must be an object"]
    expected = {
        "namespace_prefix": "TEST-", "canon": False, "release_eligible": False,
        "promotion_allowed": False, "disposition": "TEST_EVIDENCE_ONLY",
    }
    return [f"{label}: TEST boundary drift at {field}" for field, value in expected.items() if document.get(field) != value]


def _walk_schema(value: Any, label: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object" and value.get("additionalProperties") is not False:
            errors.append(f"{label}: object schema is not closed")
        ref = value.get("$ref")
        if ref is not None and (not isinstance(ref, str) or not ref.startswith("#/")):
            errors.append(f"{label}: non-local $ref is forbidden")
        for key, child in value.items():
            _walk_schema(child, f"{label}/{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_schema(child, f"{label}/{index}", errors)


def validate_provider_run_receipt(receipt: Any, schema: dict[str, Any]) -> list[str]:
    errors = _schema_issues(receipt, schema, "provider run receipt")
    if not isinstance(receipt, dict):
        return errors
    if receipt.get("resolved_model") == receipt.get("requested_model_alias") and receipt.get("actual_fingerprint") in {None, "", "UNKNOWN", "ALIAS_ONLY"}:
        errors.append("provider run receipt: alias-only identity cannot satisfy resolved identity")
    if receipt.get("evidence_kind") != "REAL_PROVIDER_EXECUTION":
        errors.append("provider run receipt: simulated or cached evidence cannot certify a Provider")
    payload = {key: value for key, value in receipt.items() if key != "receipt_payload_hash"}
    if receipt.get("receipt_payload_hash") != canonical_sha256(payload):
        errors.append("provider run receipt: payload hash mismatch")
    return errors


def validate_profile_preflight(preflight: Any, schema: dict[str, Any]) -> list[str]:
    errors = _schema_issues(preflight, schema, "profile preflight")
    if not isinstance(preflight, dict):
        return errors
    allowed = {"COMPATIBLE", "INCOMPATIBLE", "REVALIDATION_REQUIRED"}
    if preflight.get("result") not in allowed:
        errors.append("profile preflight: invalid result")
    checks = preflight.get("capability_checks", [])
    compatible = (
        preflight.get("expected_configuration_sha256") == preflight.get("actual_configuration_sha256")
        and all(isinstance(item, dict) and item.get("match") is True for item in checks)
    )
    if preflight.get("result") == "COMPATIBLE" and not compatible:
        errors.append("profile preflight: incompatible evidence cannot claim COMPATIBLE")
    return errors


def validate_provider_certificate(
    certificate: Any,
    receipts: Iterable[dict[str, Any]],
    schema: dict[str, Any],
) -> list[str]:
    errors = _schema_issues(certificate, schema, "provider certificate")
    if not isinstance(certificate, dict):
        return errors
    receipt_list = list(receipts)
    ids = certificate.get("consecutive_real_run_ids", [])
    if len(ids) != 3 or len(set(ids)) != 3:
        errors.append("provider certificate: exactly three distinct run ids are required")
    by_id = {item.get("run_id"): item for item in receipt_list if isinstance(item, dict)}
    selected = [by_id.get(run_id) for run_id in ids]
    if any(item is None for item in selected):
        errors.append("provider certificate: missing run evidence")
        return errors
    assert all(isinstance(item, dict) for item in selected)
    for field in ("provider_id", "profile_id", "resolved_model", "provider_revision", "actual_fingerprint"):
        expected = certificate.get(field)
        if any(item.get(field) != expected for item in selected if item is not None):
            errors.append(f"provider certificate: run {field} drift")
    if any(item.get("evidence_kind") != "REAL_PROVIDER_EXECUTION" for item in selected if item is not None):
        errors.append("provider certificate: simulated or cached run evidence rejected")
    if certificate.get("drift_preflight") != "COMPATIBLE" and certificate.get("certification_result") == "CERTIFIED":
        errors.append("provider certificate: incompatible profile cannot be certified")
    payload = {key: value for key, value in certificate.items() if key != "certificate_payload_hash"}
    if certificate.get("certificate_payload_hash") != canonical_sha256(payload):
        errors.append("provider certificate: payload hash mismatch")
    return errors


def validate_m2_dependency_classification(value: Any, schema: dict[str, Any]) -> list[str]:
    errors = _schema_issues(value, schema, "M2 dependency classification")
    if not isinstance(value, dict):
        return errors
    dependency_tags = set(value.get("dependency_tags", []))
    computed: list[str] = []
    for proof in value.get("closure_proofs", []):
        if not isinstance(proof, dict):
            continue
        intersection = sorted(dependency_tags & set(proof.get("required_tags", [])))
        if proof.get("intersection") != intersection:
            errors.append(f"M2 dependency classification: invalid computed intersection for {proof.get('blocker_id')}")
        if intersection:
            computed.append(str(proof.get("blocker_id")))
        if not proof.get("proof_ref"):
            errors.append("M2 dependency classification: closure proof ref is required")
    if value.get("computed_affected_blockers") != computed:
        errors.append("M2 dependency classification: affected blockers are not machine-computed")
    if computed and value.get("result") == "INDEPENDENT_OF_CURRENT_M2_BLOCKERS":
        errors.append("M2 dependency classification: affected subject cannot claim independence")
    return errors


def validate_intensity_revision(order: Any, contract: Any) -> list[str]:
    if not isinstance(order, dict) or not isinstance(contract, dict):
        return ["intensity revision: order and contract must be objects"]
    if order.get("intensity_contract_id") != contract.get("contract_id"):
        return ["intensity revision: contract identity mismatch"]
    if order.get("intensity_contract_revision") != contract.get("revision"):
        return ["STALE_CONTRACT_REVISION"]
    return []


def compute_region_score(scorecard: Any) -> tuple[float | None, list[str]]:
    if not isinstance(scorecard, dict):
        return None, ["region scorecard must be an object"]
    if scorecard.get("formula") != "0.70*risk_coverage+0.30*controllability":
        return None, ["region scorecard formula drift"]
    risk_rows = scorecard.get("risk_coverage", [])
    if not isinstance(risk_rows, list) or not risk_rows:
        return None, ["region scorecard lacks risk rows"]
    risk_values = [row.get("score", 0) if isinstance(row, dict) and row.get("evidence_ref") else 0 for row in risk_rows]
    risk = sum(risk_values) / len(risk_values)
    controllability = scorecard.get("controllability_score", 0)
    if not isinstance(controllability, (int, float)) or isinstance(controllability, bool):
        return None, ["region scorecard controllability must be numeric"]
    return 0.70 * risk + 0.30 * controllability, []


def validate_b003_authorization(envelope: Any) -> list[str]:
    expected = {
        "authorization_kind": "OWNER_APPROVED_M3_B003_PROVIDER_EXECUTION",
        "milestone": "M3", "batch_id": "M3-B003", "status": "APPROVED",
        "synthetic_test_only": True,
    }
    if not isinstance(envelope, dict):
        return ["B003 authorization envelope is required"]
    errors = [f"B003 authorization mismatch: {field}" for field, value in expected.items() if envelope.get(field) != value]
    for field in ("owner_approval_id", "candidate_commit", "candidate_tree", "data_boundary_hash"):
        if not envelope.get(field):
            errors.append(f"B003 authorization missing {field}")
    return errors


def validate_precontent_owner_approval(approval: Any, expected_hashes: dict[str, str]) -> list[str]:
    if not isinstance(approval, dict):
        return ["pre-content Owner exact-hash approval is required"]
    errors: list[str] = []
    expected_identity = {
        "change_set_id": CHANGE_SET_ID,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH,
        "approval_status": "APPROVED",
        "single_use": True,
        "transferable": False,
        "consumed": False,
        "revoked": False,
    }
    for field, value in expected_identity.items():
        if approval.get(field) != value:
            errors.append(f"pre-content Owner approval identity/state mismatch: {field}")
    if not approval.get("approval_id") or not approval.get("candidate_commit") or not approval.get("candidate_tree"):
        errors.append("pre-content Owner approval lacks exact candidate identity")
    binding = approval.get("hash_binding")
    if not isinstance(binding, dict):
        errors.append("pre-content Owner approval lacks hash_binding")
    else:
        for field, value in expected_hashes.items():
            if binding.get(field) != value:
                errors.append(f"pre-content Owner approval hash mismatch: {field}")
        if set(binding) != set(expected_hashes):
            errors.append("pre-content Owner approval hash set is not exact")
    return errors


def validate_readiness_bundle(bundle: Any, schema: dict[str, Any]) -> list[str]:
    errors = _schema_issues(bundle, schema, "pre-content readiness bundle")
    if not isinstance(bundle, dict):
        return errors
    payload = {key: value for key, value in bundle.items() if key != "bundle_payload_hash"}
    if bundle.get("bundle_payload_hash") != canonical_sha256(payload):
        errors.append("pre-content readiness bundle hash mismatch")
    if bundle.get("result") == "READY_FOR_FORMAL_VERTICAL_SLICE":
        if bundle.get("rights_gate") != "PASS":
            errors.append("ready bundle requires final blocking rights PASS")
        if bundle.get("owner_exact_hash_approval") != "APPROVED":
            errors.append("ready bundle requires Owner exact-hash approval")
        if bundle.get("scoped_blockers"):
            errors.append("fully ready bundle cannot contain scoped blockers")
    return errors


def validate_external_cas_contract(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return ["external CAS root is absent"]
    mode = stat.S_IMODE(root.stat().st_mode)
    if mode != 0o700:
        errors.append(f"external CAS root mode must be 0700, got {mode:04o}")
    policy_path = root / "retention-policy.json"
    manifest_path = root / "manifest.jsonl"
    if not policy_path.is_file() or not manifest_path.is_file():
        errors.append("external CAS requires retention-policy.json and manifest.jsonl")
        return errors
    policy = read_json(policy_path)
    expected = {
        "manifest":"CONTENT_ADDRESSED_APPEND_ONLY",
        "raw_private_chain_of_thought":"FORBIDDEN",
        "secrets":"FORBIDDEN",
        "redacted_raw_protocol_retention":"THROUGH_M3_B004_ACCEPT_PLUS_90_DAYS",
        "post_retention_action":"OWNER_DECISION_REQUIRED",
        "normalized_test_evidence":"PERMANENT_HISTORICAL",
    }
    for field, value in expected.items():
        if not isinstance(policy, dict) or policy.get(field) != value:
            errors.append(f"external CAS retention policy drift: {field}")
    for line_no, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"external CAS manifest line {line_no} is invalid JSON")
            continue
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
            errors.append(f"external CAS manifest line {line_no} lacks content address")
        if any(key in entry for key in ("secret", "credential", "private_chain_of_thought")):
            errors.append(f"external CAS manifest line {line_no} contains forbidden field")
    return errors


def derive_framework_documents(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Load the immutable accepted R1 manifest and pending receipt without rewriting them."""

    root = root.resolve()
    manifest_bytes = (root / MANIFEST_PATH).read_bytes()
    receipt_bytes = (root / RECEIPT_PATH).read_bytes()
    manifest = json.loads(manifest_bytes)
    receipt = json.loads(receipt_bytes)
    return {
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "receipt": receipt,
        "receipt_bytes": receipt_bytes,
        "framework_merkle_root": manifest.get("merkle", {}).get("root"),
    }


def expected_approval_consumption() -> dict[str, Any]:
    return {
        "schema_version": "rules-residue.story-construction.precontent-owner-approval-consumption/1.0.0",
        "approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
        "change_set_id": CHANGE_SET_ID,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH,
        "candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
        "candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        "candidate_parent": IMPLEMENTATION_CANDIDATE_PARENT,
        "proposed_canon_hash": BASE_CANON_HASH,
        "framework_manifest_r1_file_sha256": R1_MANIFEST_FILE_SHA256,
        "framework_manifest_r1_merkle_root": R1_MERKLE_ROOT,
        "pending_receipt_file_sha256": PENDING_RECEIPT_FILE_SHA256,
        "pending_receipt_payload_hash": PENDING_RECEIPT_PAYLOAD_HASH,
        "owner_approval_raw_sha256": IMPLEMENTATION_OWNER_APPROVAL_RAW_SHA256,
        "owner_approval_canonical_sha256": IMPLEMENTATION_OWNER_APPROVAL_CANONICAL_SHA256,
        "approval": "OWNER_HASH_APPROVED_FOR_INDEPENDENT_ACCEPT",
        "single_use": True,
        "transferable": False,
        "revoked": False,
        "consumption_count": 1,
        "consumption_event": IMPLEMENTATION_ACCEPT_TASK_ID,
        "consumption_result": IMPLEMENTATION_ACCEPT_RESULT,
        "accepted_candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
        "accepted_candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        "accept_verifier": IMPLEMENTATION_ACCEPT_VERIFIER,
        "accept_route": IMPLEMENTATION_ACCEPT_ROUTE,
        "accept_route_digest": IMPLEMENTATION_ACCEPT_ROUTE_DIGEST,
        "consumed": True,
    }


def validate_implementation_approval_consumption(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["implementation approval consumption record must be an object"]
    expected = expected_approval_consumption()
    errors = [
        f"implementation approval consumption {field} mismatch"
        for field, value in expected.items()
        if record.get(field) != value
    ]
    if set(record) != set(expected):
        errors.append("implementation approval consumption field set is not exact")
    return errors


def _schema_sets(root: Path, r1_records: list[dict[str, str]]) -> dict[str, Any]:
    original_paths = {f"schemas/story-construction/{name}" for name in SCHEMA_FILES}
    original = sorted(
        (record for record in r1_records if record.get("path") in original_paths),
        key=lambda item: item["path"],
    )
    if len(original) != 20 or {item["path"] for item in original} != original_paths:
        raise ValueError("R1 manifest does not contain the exact original 20-schema set")
    for record in original:
        if file_sha256(root / record["path"]) != record["sha256"]:
            raise ValueError(f"original schema drift: {record['path']}")
    activation = [
        {"path": f"schemas/story-construction/{name}", "sha256": file_sha256(root / "schemas/story-construction" / name)}
        for name in sorted(ACTIVATION_SCHEMA_FILES)
    ]
    combined = sorted(original + activation, key=lambda item: item["path"])
    return {
        "original_records": original,
        "original_count": len(original),
        "original_set_hash": _record_set_hash(original),
        "activation_records": activation,
        "activation_count": len(activation),
        "activation_set_hash": _record_set_hash(activation),
        "combined_records": combined,
        "combined_count": len(combined),
        "combined_set_hash": _record_set_hash(combined),
    }


def derive_activation_documents(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    root = root.resolve()
    frozen = derive_framework_documents(root)
    r1_manifest = frozen["manifest"]
    r1_records = r1_manifest.get("records")
    if not isinstance(r1_records, list) or len(r1_records) != R1_RECORD_COUNT:
        raise ValueError("R1 manifest record count drift")
    if len({record.get("path") for record in r1_records if isinstance(record, dict)}) != R1_RECORD_COUNT:
        raise ValueError("R1 manifest records are missing or duplicated")
    r1_by_path = {record["path"]: record for record in r1_records}
    if not set(CHANGED_OLD_PATHS).issubset(r1_by_path):
        raise ValueError("changed-old path is absent from R1")

    unchanged_old: list[dict[str, str]] = []
    changed_old: list[dict[str, str]] = []
    r2_records: list[dict[str, str]] = []
    for old in sorted(r1_records, key=lambda item: item["path"]):
        path = old["path"]
        actual_sha256 = file_sha256(root / path)
        if path in CHANGED_OLD_PATHS:
            if actual_sha256 == old["sha256"]:
                raise ValueError(f"approved changed-old path did not change: {path}")
            changed_old.append({
                "path": path,
                "old_sha256": old["sha256"],
                "new_sha256": actual_sha256,
            })
            r2_records.append({"path": path, "sha256": actual_sha256})
        else:
            if actual_sha256 != old["sha256"]:
                raise ValueError(f"unapproved R1 semantic leaf drift: {path}")
            unchanged_old.append({"path": path, "sha256": old["sha256"]})
            r2_records.append({"path": path, "sha256": old["sha256"]})

    new_records = [
        {"path": path, "sha256": file_sha256(root / path)}
        for path in sorted(NEW_SEMANTIC_PATHS)
    ]
    r2_records = sorted(r2_records + new_records, key=lambda item: item["path"])
    if (len(unchanged_old), len(changed_old), len(new_records), len(r2_records)) != (61, 7, 8, 76):
        raise ValueError("R2 semantic transition must be exactly 61 unchanged / 7 changed / 8 new / 76 total")
    r2_root = merkle_root((record["path"], record["sha256"]) for record in r2_records)
    schemas = _schema_sets(root, r1_records)
    if schemas["original_set_hash"] != ORIGINAL_SCHEMA_SET_HASH:
        raise ValueError("original 20-schema set hash drift")
    transition = {
        "old_record_count": 68,
        "unchanged_old_count": 61,
        "changed_old_count": 7,
        "new_record_count": 8,
        "total_record_count": 76,
        "unchanged_old_leaf_set_hash": _record_set_hash(unchanged_old),
        "changed_old_leaf_transition_hash": canonical_sha256(changed_old),
        "new_leaf_set_hash": _record_set_hash(new_records),
        "r1_leaf_set_hash": _record_set_hash(r1_records),
        "r2_leaf_set_hash": _record_set_hash(r2_records),
        "changed_old_records": changed_old,
        "new_records": new_records,
    }
    request_counts = {"deepseek": 0, "grok": 0, "opencode": 0, "story_m0": 0}
    manifest = {
        "schema_version": "rules-residue.story-construction.precontent-framework-manifest/2.0.0",
        "manifest_id": "SCG-PRECONTENT-FRAMEWORK-MANIFEST-R2",
        "change_set_id": CHANGE_SET_ID,
        "machine_milestone": "M3",
        "machine_batch_id": "M3-B002",
        "lifecycle_stage": "APPROVED",
        "disposition": "ACTIVE",
        "release": "NOT_RELEASED",
        "approval_status": APPROVAL_STATUS,
        "authority_scope": "CONSTRUCTION_GOVERNANCE_ONLY",
        "r2_canon_precedence": "HIGHER",
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH,
        "proposed_canon_hash": BASE_CANON_HASH,
        "canonicalization": "UTF8_NFC_SORTED_KEYS_FINITE_NUMBERS_V1",
        "implementation_candidate_binding": {
            "strategy": "EXACT_ACCEPTED_IMPLEMENTATION_CANDIDATE",
            "candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
            "candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
            "candidate_parent": IMPLEMENTATION_CANDIDATE_PARENT,
        },
        "implementation_acceptance": {
            "owner_approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
            "task_id": IMPLEMENTATION_ACCEPT_TASK_ID,
            "result": IMPLEMENTATION_ACCEPT_RESULT,
            "verifier": IMPLEMENTATION_ACCEPT_VERIFIER,
            "route": IMPLEMENTATION_ACCEPT_ROUTE,
            "route_digest": IMPLEMENTATION_ACCEPT_ROUTE_DIGEST,
        },
        "previous_manifest": {
            "path": MANIFEST_PATH.as_posix(),
            "file_sha256": R1_MANIFEST_FILE_SHA256,
            "merkle_root": R1_MERKLE_ROOT,
            "record_count": R1_RECORD_COUNT,
        },
        "records": r2_records,
        "merkle": {
            "algorithm": "SHA-256-BINARY-PAIR-DUPLICATE-ODD-V1",
            "leaf_order": "path_lexical",
            "root": r2_root,
        },
        "transition": transition,
        "schema_sets": {
            "original_schema_count": schemas["original_count"],
            "original_schema_set_hash": schemas["original_set_hash"],
            "activation_schema_count": schemas["activation_count"],
            "activation_schema_set_hash": schemas["activation_set_hash"],
            "combined_schema_count": schemas["combined_count"],
            "combined_schema_set_hash": schemas["combined_set_hash"],
        },
        "excluded_from_merkle": [
            APPROVAL_CONSUMPTION_PATH.as_posix(),
            FINAL_RECEIPT_PATH.as_posix(),
            "FUTURE_ACTIVATION_OWNER_APPROVAL",
            "FUTURE_SECOND_INDEPENDENT_ACCEPT",
            "FUTURE_DETACHED_ENVELOPE_AND_TAG",
            "FUTURE_REMOTE_AND_INTEGRATION_STATE",
        ],
        "provider_request_counts": request_counts,
        "runtime_projection": "EXCLUDED",
        "self_reference": False,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_file_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    consumption_sha256 = file_sha256(root / APPROVAL_CONSUMPTION_PATH)
    payload = {
        "schema_version": "rules-residue.story-construction.precontent-final-receipt/2.0.0",
        "receipt_id": "SCG-PRECONTENT-READINESS-R1-FINAL-001",
        "receipt_status": APPROVAL_STATUS,
        "change_set_id": CHANGE_SET_ID,
        "machine_milestone": "M3",
        "machine_batch_id": "M3-B002",
        "activation_model": ACTIVATION_MODEL,
        "lifecycle_stage": "APPROVED",
        "disposition": "ACTIVE",
        "release": "NOT_RELEASED",
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH,
        "proposed_canon_hash": BASE_CANON_HASH,
        "implementation_candidate": {
            "commit": IMPLEMENTATION_CANDIDATE_COMMIT,
            "tree": IMPLEMENTATION_CANDIDATE_TREE,
            "parent": IMPLEMENTATION_CANDIDATE_PARENT,
        },
        "implementation_owner_approval": {
            "approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
            "raw_sha256": IMPLEMENTATION_OWNER_APPROVAL_RAW_SHA256,
            "canonical_sha256": IMPLEMENTATION_OWNER_APPROVAL_CANONICAL_SHA256,
            "consumed": True,
            "single_use": True,
            "transferable": False,
        },
        "implementation_acceptance": {
            "task_id": IMPLEMENTATION_ACCEPT_TASK_ID,
            "result": IMPLEMENTATION_ACCEPT_RESULT,
            "verifier": IMPLEMENTATION_ACCEPT_VERIFIER,
            "route": IMPLEMENTATION_ACCEPT_ROUTE,
            "route_digest": IMPLEMENTATION_ACCEPT_ROUTE_DIGEST,
        },
        "approval_consumption_record": {
            "path": APPROVAL_CONSUMPTION_PATH.as_posix(),
            "file_sha256": consumption_sha256,
        },
        "framework_manifest_r1": {
            "path": MANIFEST_PATH.as_posix(),
            "file_sha256": R1_MANIFEST_FILE_SHA256,
            "merkle_root": R1_MERKLE_ROOT,
            "record_count": R1_RECORD_COUNT,
        },
        "framework_manifest_r2": {
            "path": R2_MANIFEST_PATH.as_posix(),
            "file_sha256": manifest_file_sha256,
            "merkle_root": r2_root,
            "record_count": len(r2_records),
            "transition": {key: transition[key] for key in (
                "old_record_count", "unchanged_old_count", "changed_old_count",
                "new_record_count", "total_record_count", "unchanged_old_leaf_set_hash",
                "changed_old_leaf_transition_hash", "new_leaf_set_hash",
                "r1_leaf_set_hash", "r2_leaf_set_hash",
            )},
        },
        "schema_sets": {
            "original_schema_count": schemas["original_count"],
            "original_schema_set_hash": schemas["original_set_hash"],
            "activation_schema_count": schemas["activation_count"],
            "activation_schema_set_hash": schemas["activation_set_hash"],
            "combined_schema_count": schemas["combined_count"],
            "combined_schema_set_hash": schemas["combined_set_hash"],
        },
        "fixed_preservation": {
            "decision_set_hash": DECISION_SET_HASH,
            "partial_supersession_hash": PARTIAL_SUPERSESSION_HASH,
            "traceability_hash": TRACEABILITY_HASH,
            "pending_receipt_file_sha256": PENDING_RECEIPT_FILE_SHA256,
            "pending_receipt_payload_hash": PENDING_RECEIPT_PAYLOAD_HASH,
            "m0_fixture_graph_hash": M0_FIXTURE_GRAPH_HASH,
            "context_manifest_set_hash": CONTEXT_MANIFEST_SET_HASH,
            "omission_report_set_hash": OMISSION_REPORT_SET_HASH,
            "static_gate_result_hash": STATIC_GATE_RESULT_HASH,
            "provider_profile_contract_set_hash": PROVIDER_PROFILE_CONTRACT_SET_HASH,
            "provider_zero_call_evidence_hash": PROVIDER_ZERO_CALL_EVIDENCE_HASH,
            "canon_hash": BASE_CANON_HASH,
            "runtime_package_sha256": RUNTIME_PACKAGE_SHA256,
        },
        "activation_path_allowlist": {
            "path_count": len(ACTIVATION_ALLOWLIST),
            "sha256": activation_allowlist_hash(),
        },
        "provider_request_counts": request_counts,
        "activation_state": {
            "tracked_target_state": "TRACKED_B002_TARGET_STATE_ACTIVE",
            "active_wip": True,
            "authoritative_activation_effective": False,
            "required_external_proofs": list(REQUIRED_EXTERNAL_PROOFS),
        },
    }
    receipt = {
        "schema_version": "rules-residue.story-construction.precontent-final-receipt/2.0.0",
        "receipt_kind": "TRACKED_INNER_ACTIVATION_RECEIPT",
        "outer_envelope_schema": "schemas/story-construction/precontent-activation-closeout-envelope-v1.schema.json",
        "payload": payload,
        "payload_hash": canonical_sha256(payload),
    }
    return {
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "manifest_file_sha256": manifest_file_sha256,
        "framework_merkle_root": r2_root,
        "transition": transition,
        "schemas": schemas,
        "receipt": receipt,
        "receipt_bytes": canonical_json_bytes(receipt),
        "receipt_payload_hash": receipt["payload_hash"],
        "consumption_sha256": consumption_sha256,
    }


def validate_framework_manifest_transition(manifest: Any, r1_manifest: Any) -> list[str]:
    if not isinstance(manifest, dict) or not isinstance(r1_manifest, dict):
        return ["R1 and R2 framework manifests must be objects"]
    errors: list[str] = []
    records = manifest.get("records")
    old_records = r1_manifest.get("records")
    if not isinstance(records, list) or not isinstance(old_records, list):
        return ["framework manifest records must be arrays"]
    paths = [item.get("path") for item in records if isinstance(item, dict)]
    if len(records) != 76 or len(paths) != 76 or len(set(paths)) != 76:
        errors.append("R2 framework manifest must contain 76 unique records")
    forbidden = {R2_MANIFEST_PATH.as_posix(), APPROVAL_CONSUMPTION_PATH.as_posix(), FINAL_RECEIPT_PATH.as_posix()}
    if forbidden & set(paths):
        errors.append("R2 framework manifest contains self/audit record")
    try:
        computed_root = merkle_root((item["path"], item["sha256"]) for item in records)
    except (KeyError, TypeError, ValueError):
        errors.append("R2 framework manifest contains malformed leaf records")
        computed_root = None
    if manifest.get("merkle", {}).get("root") != computed_root:
        errors.append("R2 framework manifest Merkle root mismatch")
    transition = manifest.get("transition")
    if not isinstance(transition, dict):
        return errors + ["R2 framework manifest transition is missing"]
    exact_counts = {
        "old_record_count": 68, "unchanged_old_count": 61, "changed_old_count": 7,
        "new_record_count": 8, "total_record_count": 76,
    }
    for field, value in exact_counts.items():
        if transition.get(field) != value:
            errors.append(f"R2 Merkle transition count mismatch: {field}")
    changed = transition.get("changed_old_records", [])
    new = transition.get("new_records", [])
    if [item.get("path") for item in changed if isinstance(item, dict)] != sorted(CHANGED_OLD_PATHS):
        errors.append("R2 changed-old path set mismatch")
    if [item.get("path") for item in new if isinstance(item, dict)] != sorted(NEW_SEMANTIC_PATHS):
        errors.append("R2 new semantic path set mismatch")
    old_by_path = {item.get("path"): item.get("sha256") for item in old_records if isinstance(item, dict)}
    new_by_path = {item.get("path"): item.get("sha256") for item in records if isinstance(item, dict)}
    expected_unchanged = [
        {"path": path, "sha256": digest}
        for path, digest in sorted(old_by_path.items())
        if path not in CHANGED_OLD_PATHS
    ]
    if transition.get("unchanged_old_leaf_set_hash") != _record_set_hash(expected_unchanged):
        errors.append("R2 unchanged-old leaf set hash mismatch")
    if transition.get("changed_old_leaf_transition_hash") != canonical_sha256(changed):
        errors.append("R2 changed-old transition hash mismatch")
    if transition.get("new_leaf_set_hash") != _record_set_hash(new):
        errors.append("R2 new leaf set hash mismatch")
    if transition.get("r1_leaf_set_hash") != _record_set_hash(old_records):
        errors.append("R2 R1 leaf set hash mismatch")
    if transition.get("r2_leaf_set_hash") != _record_set_hash(records):
        errors.append("R2 leaf set hash mismatch")
    for item in changed:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if item.get("old_sha256") != old_by_path.get(path) or item.get("new_sha256") != new_by_path.get(path):
            errors.append(f"R2 changed-old leaf binding mismatch: {path}")
    return errors


def validate_final_receipt_binding(receipt: Any, expected: Any | None = None) -> list[str]:
    if not isinstance(receipt, dict):
        return ["final inner receipt must be an object"]
    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        return ["final inner receipt payload must be an object"]
    errors: list[str] = []
    if receipt.get("payload_hash") != canonical_sha256(payload):
        errors.append("final inner receipt payload hash mismatch")
    forbidden_tokens = {
        "payload_hash", "receipt_payload_hash", "final_inner_receipt_file_sha256",
        "activation_candidate_commit", "activation_candidate_tree", "activation_owner_approval_id",
        "activation_accept_task_id", "activation_accept_route_digest", "tag_name", "tag_object_id",
        "authoritative_remote_after_activation", "integration_commit",
    }
    present = sorted(forbidden_tokens & set(payload))
    if present:
        errors.append(f"final inner receipt contains forbidden self/future fields: {present}")
    if expected is not None and receipt != expected:
        errors.append("final inner receipt differs from deterministic derivation")
    return errors


def write_framework_documents(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Compatibility entry: R1 is immutable, so this performs no write."""

    return derive_framework_documents(root)


def write_activation_documents(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    root = root.resolve()
    derived = derive_activation_documents(root)
    (root / R2_MANIFEST_PATH).write_bytes(derived["manifest_bytes"])
    (root / FINAL_RECEIPT_PATH).write_bytes(derived["receipt_bytes"])
    return derived


def _validate_schemas_and_instances(root: Path, errors: list[str]) -> None:
    schemas: dict[str, dict[str, Any]] = {}
    for name in COMBINED_SCHEMA_FILES:
        path = root / "schemas/story-construction" / name
        try:
            schema = _schema(root, name)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{name}: invalid schema JSON: {exc}")
            continue
        schemas[name] = schema
        if not name.endswith("-v1.schema.json") and name not in {
            "text-order-v2.schema.json", "visual-order-v2.schema.json",
            "precontent-change-set-v2.schema.json", "precontent-final-receipt-v2.schema.json",
        }:
            errors.append(f"{name}: schema filename is not versioned")
        if schema.get("additionalProperties") is not False:
            errors.append(f"{name}: root schema is not closed")
        _walk_schema(schema, name, errors)
    bindings = {
        "precontent-decision-set-v1.schema.json": [DECISION_PATH],
        "partial-supersession-v1.schema.json": [SUPERSESSION_PATH],
        "test-fixture-graph-v1.schema.json": [FIXTURE_ROOT / "test-fixture-graph.json"],
        "text-order-v2.schema.json": [FIXTURE_ROOT / "text-order-001.json", FIXTURE_ROOT / "text-order-002.json"],
        "visual-order-v2.schema.json": [FIXTURE_ROOT / "visual-order-001.json"],
        "context-manifest-v1.schema.json": [FIXTURE_ROOT / "test-context-manifest-text-001.json", FIXTURE_ROOT / "test-context-manifest-text-002.json", FIXTURE_ROOT / "test-context-manifest-visual-001.json"],
        "omission-report-v1.schema.json": [FIXTURE_ROOT / "test-omission-report-text-001.json", FIXTURE_ROOT / "test-omission-report-text-002.json", FIXTURE_ROOT / "test-omission-report-visual-001.json"],
        "region-content-intensity-contract-v1.schema.json": [FIXTURE_ROOT / "test-region-intensity-contract.json"],
        "causal-epistemic-proof-matrix-v1.schema.json": [FIXTURE_ROOT / "cross-modal-oracle.json"],
        "precontent-change-set-v2.schema.json": [CHANGE_SET_PATH],
        "precontent-final-receipt-v2.schema.json": [FINAL_RECEIPT_PATH],
        "precontent-owner-approval-consumption-v1.schema.json": [APPROVAL_CONSUMPTION_PATH],
    }
    for schema_name, paths in bindings.items():
        schema = schemas.get(schema_name)
        if schema is None:
            continue
        for relative in paths:
            try:
                instance = read_json(root / relative)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{relative}: invalid JSON: {exc}")
                continue
            errors.extend(_schema_issues(instance, schema, relative.as_posix()))


def _validate_decision_binding(root: Path, errors: list[str]) -> None:
    decision_set = read_json(root / DECISION_PATH)
    actual = tuple((item.get("id"), item.get("option")) for item in decision_set.get("decisions", []) if isinstance(item, dict))
    if actual != EXPECTED_DECISIONS:
        errors.append("SCG-PRE-Q001--Q021 identity/order/option drift")
    if decision_set.get("decision_count") != len(EXPECTED_DECISIONS):
        errors.append("pre-content decision count drift")
    traceability = read_json(root / TRACEABILITY_PATH)
    trace_ids = tuple(item.get("decision_id") for item in traceability.get("entries", []) if isinstance(item, dict))
    if trace_ids != tuple(item[0] for item in EXPECTED_DECISIONS):
        errors.append("pre-content bidirectional traceability drift")
    supersession = read_json(root / SUPERSESSION_PATH)
    actual_supersession = {
        item.get("source_decision_id"): item.get("replacement_decision_ids")
        for item in supersession.get("entries", []) if isinstance(item, dict)
    }
    expected_supersession = {
        "Q093": ["SCG-PRE-Q015"],
        "Q099": ["SCG-PRE-Q010", "SCG-PRE-Q011", "SCG-PRE-Q013"],
        "Q129": ["SCG-PRE-Q015"],
    }
    if actual_supersession != expected_supersession or supersession.get("no_other_supersessions") is not True:
        errors.append("approved partial supersession drift")


def validate_precontent_lifecycle_state(change_set: Any) -> list[str]:
    if not isinstance(change_set, dict):
        return ["pre-content Change Set must be an object"]
    version = change_set.get("schema_version")
    if version == "rules-residue.story-construction.precontent-change-set/1.0.0":
        expected = {
            "lifecycle_stage": "CANDIDATE",
            "disposition": "CANDIDATE_NOT_ACTIVE",
            "release": "NOT_RELEASED",
            "approval_status": CANDIDATE_APPROVAL_STATUS,
            "active_wip": True,
        }
    elif version == "rules-residue.story-construction.precontent-change-set/2.0.0":
        expected = {
            "lifecycle_stage": "APPROVED",
            "disposition": "ACTIVE",
            "release": "NOT_RELEASED",
            "approval_status": APPROVAL_STATUS,
            "implementation_approval_status": "CONSUMED_BY_INDEPENDENT_ACCEPT",
            "active_wip": True,
        }
    else:
        return [f"unsupported pre-content Change Set schema: {version!r}"]
    errors = [
        f"pre-content Change Set {field} invalid for {version}"
        for field, value in expected.items()
        if change_set.get(field) != value
    ]
    if version.endswith("/2.0.0"):
        expected_activation = {
            "tracked_target_state": "TRACKED_B002_TARGET_STATE_ACTIVE",
            "authoritative_activation_effective": False,
            "required_external_proofs": list(REQUIRED_EXTERNAL_PROOFS),
        }
        if change_set.get("activation_state") != expected_activation:
            errors.append("pre-content active-state proof separation drift")
        if change_set.get("release") == "RELEASED":
            errors.append("early WIP release is forbidden")
    return errors


def validate_activation_owner_approval(approval: Any, expected: dict[str, Any]) -> list[str]:
    if not isinstance(approval, dict):
        return ["activation-specific Owner full-hash approval is missing"]
    errors: list[str] = []
    for field, value in expected.items():
        if approval.get(field) != value:
            errors.append(f"activation Owner approval {field} mismatch")
    if not approval.get("approval_id") or approval.get("approval_id") == IMPLEMENTATION_OWNER_APPROVAL_ID:
        errors.append("implementation approval ID cannot serve as activation approval")
    if approval.get("approval_model") != ACTIVATION_MODEL:
        errors.append("activation Owner approval model mismatch")
    if approval.get("approval_status") != "APPROVED":
        errors.append("activation Owner approval status is not APPROVED")
    if approval.get("single_use") is not True or approval.get("transferable") is not False:
        errors.append("activation Owner approval replay/transfer boundary mismatch")
    if approval.get("consumed") is not False or approval.get("revoked") is not False:
        errors.append("activation Owner approval is unavailable")
    records = approval.get("activation_path_hashes")
    if not isinstance(records, list) or len(records) != len(ACTIVATION_ALLOWLIST):
        errors.append("activation Owner approval must bind exactly 18 path hashes")
    else:
        if {item.get("path") for item in records if isinstance(item, dict)} != set(ACTIVATION_ALLOWLIST):
            errors.append("activation Owner approval path set mismatch")
        if approval.get("activation_path_set_hash") != _record_set_hash(records):
            errors.append("activation Owner approval 18-path set hash mismatch")
    if approval.get("activation_path_allowlist_sha256") != activation_allowlist_hash():
        errors.append("activation Owner approval allowlist hash mismatch")
    if approval.get("activation_candidate_parent") != IMPLEMENTATION_CANDIDATE_COMMIT:
        errors.append("activation Owner approval candidate parent mismatch")
    return errors


def validate_activation_closeout_envelope(envelope: Any, expected: dict[str, Any]) -> list[str]:
    if not isinstance(envelope, dict):
        return ["detached accepted activation envelope is missing"]
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return ["detached accepted activation envelope payload is missing"]
    errors = [
        f"activation closeout envelope {field} mismatch"
        for field, value in expected.items()
        if payload.get(field) != value
    ]
    if envelope.get("payload_hash") != canonical_sha256(payload):
        errors.append("activation closeout envelope payload hash mismatch")
    if payload.get("tag_name") != ACTIVATION_PROOF_TAG:
        errors.append("activation closeout envelope tag mismatch")
    if payload.get("binding_strategy") != "DETACHED_ANNOTATED_TAG_EXACT_COMMIT_TREE":
        errors.append("activation closeout envelope binding strategy mismatch")
    if payload.get("tag_target_commit") != payload.get("activation_candidate_commit"):
        errors.append("activation closeout envelope tag target commit mismatch")
    if payload.get("tag_target_tree") != payload.get("activation_candidate_tree"):
        errors.append("activation closeout envelope tag target tree mismatch")
    if payload.get("accepted_candidate_commit") != payload.get("activation_candidate_commit"):
        errors.append("activation closeout envelope accepted commit mismatch")
    if payload.get("accepted_candidate_tree") != payload.get("activation_candidate_tree"):
        errors.append("activation closeout envelope accepted tree mismatch")
    if payload.get("activation_candidate_parent") != IMPLEMENTATION_CANDIDATE_COMMIT:
        errors.append("activation closeout envelope lineage parent mismatch")
    if payload.get("candidate_to_activation_commit_count") != 1 or payload.get("base_to_activation_commit_count") != 2:
        errors.append("activation closeout envelope lineage count mismatch")
    if payload.get("authoritative_remote_before_activation") != BASE_COMMIT:
        errors.append("activation closeout envelope remote baseline mismatch")
    if payload.get("activation_accept_task_id") != "SCG-PRECONTENT-M3-B002-ACTIVATION-CLOSEOUT-ACCEPT-001":
        errors.append("activation closeout envelope second ACCEPT task mismatch")
    if payload.get("activation_accept_result") != "PASS_FIXED_M3_B002_ACTIVATION_CANDIDATE_ACCEPTED":
        errors.append("activation closeout envelope second ACCEPT result mismatch")
    if payload.get("activation_accept_route") != "SCG-PRECONTENT-M3-B002-ACTIVATION-CLOSEOUT-ACCEPT":
        errors.append("activation closeout envelope second ACCEPT route mismatch")
    if payload.get("integration_mode") != "FAST_FORWARD_ONLY":
        errors.append("activation closeout envelope integration mode mismatch")
    if payload.get("producer_id") == payload.get("verifier_id"):
        errors.append("activation builder self-ACCEPT is forbidden")
    if payload.get("verifier_worktree_state") != "CLEAN":
        errors.append("activation verifier worktree must be clean")
    return errors


def authoritative_precontent_activation_status(
    *,
    tracked_active: bool,
    activation_approval: Any | None,
    expected_activation_approval: dict[str, Any],
    envelope: Any | None,
    expected_envelope: dict[str, Any],
    integration: Any | None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not tracked_active:
        errors.append("tracked B002 target is not ACTIVE")
    errors.extend(validate_activation_owner_approval(activation_approval, expected_activation_approval))
    errors.extend(validate_activation_closeout_envelope(envelope, expected_envelope))
    if not isinstance(integration, dict):
        errors.append("final fast-forward integration proof is missing")
    else:
        if integration.get("integrated") is not True:
            errors.append("activation candidate is not integrated")
        if integration.get("mode") != "FAST_FORWARD_ONLY":
            errors.append("activation integration mode mismatch")
        if integration.get("remote_commit") != expected_envelope.get("activation_candidate_commit"):
            errors.append("activation integration remote commit mismatch")
        if integration.get("remote_tree") != expected_envelope.get("activation_candidate_tree"):
            errors.append("activation integration remote tree mismatch")
    return not errors, errors


def _validate_change_set(root: Path, errors: list[str]) -> None:
    change_set = read_json(root / CHANGE_SET_PATH)
    errors.extend(validate_precontent_lifecycle_state(change_set))
    expected = {
        "change_set_id": CHANGE_SET_ID,
        "machine_milestone": "M3",
        "machine_batch_id": "M3-B002",
        "batch_semantics": "SCG_PRECONTENT_DECISION_BINDING_AND_M0_FRAMEWORK",
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH,
        "proposed_canon_hash": BASE_CANON_HASH,
    }
    for field, value in expected.items():
        if change_set.get(field) != value:
            errors.append(f"pre-content Change Set drift: {field}")
    if change_set.get("implementation_candidate_binding") != {
        "strategy": "EXACT_ACCEPTED_IMPLEMENTATION_CANDIDATE",
        "candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
        "candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        "candidate_parent": IMPLEMENTATION_CANDIDATE_PARENT,
    }:
        errors.append("pre-content implementation candidate binding drift")
    expected_acceptance = {
        "owner_approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
        "task_id": IMPLEMENTATION_ACCEPT_TASK_ID,
        "result": IMPLEMENTATION_ACCEPT_RESULT,
        "verifier": IMPLEMENTATION_ACCEPT_VERIFIER,
        "route": IMPLEMENTATION_ACCEPT_ROUTE,
        "route_digest": IMPLEMENTATION_ACCEPT_ROUTE_DIGEST,
    }
    if change_set.get("implementation_acceptance") != expected_acceptance:
        errors.append("pre-content first independent ACCEPT binding drift")
    counts = change_set.get("provider_request_counts")
    if counts != {"deepseek": 0, "grok": 0, "opencode": 0, "story_m0": 0}:
        errors.append("Provider, worker, or Story M0 request count is not zero")
    serialized = json.dumps(change_set, sort_keys=True)
    for forbidden in (
        "activation_candidate_commit", "activation_candidate_tree", "activation_owner_approval_id",
        "activation_accept_route_digest", "tag_object_id", "remote_activation_commit",
    ):
        if forbidden in serialized:
            errors.append(f"tracked Change Set predicts future external proof: {forbidden}")


def _validate_test_fixtures(root: Path, errors: list[str]) -> None:
    for name in TEST_FIXTURE_FILES:
        path = root / FIXTURE_ROOT / name
        try:
            value = read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: invalid fixture JSON: {exc}")
            continue
        errors.extend(validate_test_boundary(value, name))
    graph = read_json(root / FIXTURE_ROOT / "test-fixture-graph.json")
    node_ids = {item.get("id") for item in graph.get("nodes", []) if isinstance(item, dict)}
    required = {
        "TEST-T1-ANCHOR-PHASE-001", "TEST-T2-SIGNAL-TO-MARK-001",
        "TEST-T3-ENVELOPE-SCG-M0-001", "TEST-ABSOLUTE-RULE-SCG-M0-001",
        "TEST-NPC-OBSERVER-SCG-M0-001", "TEST-C1-REVEAL-SCG-M0-001",
        "TEST-ROUTE-NORMAL-SCG-M0-001", "TEST-ROUTE-RETREAT-SCG-M0-001",
        "TEST-SCG-M0-DAB-001", "TEST-SCG-M0-ACCEPTANCE-BUNDLE-001",
    }
    if not required.issubset(node_ids):
        errors.append(f"M0 fixture graph lacks nodes: {sorted(required - node_ids)}")
    canon_envelope = read_json(root / FIXTURE_ROOT / "test-canon-envelope.json")
    absolute_rule = canon_envelope.get("absolute_rule", {})
    if absolute_rule.get("ordinary_exemption") != "NONE" or absolute_rule.get("defer_r2_c14_dependency") != "NONE":
        errors.append("absolute TEST rule exemption/deferred dependency drift")
    if canon_envelope.get("promotion_policy") != "REJECT_RENAME_COPY_OR_DIRECT_PROMOTION":
        errors.append("TEST identity rename/promotion is not rejected")
    dossier = read_json(root / FIXTURE_ROOT / "test-region-dossier.json")
    route_ids = {item.get("id") for item in dossier.get("routes", []) if isinstance(item, dict)}
    if route_ids != {"TEST-ROUTE-NORMAL-SCG-M0-001", "TEST-ROUTE-RETREAT-SCG-M0-001"}:
        errors.append("normal/retreat route coverage drift")
    npc = read_json(root / FIXTURE_ROOT / "test-npc-epistemic-state.json")
    if "TEST-HIDDEN-CAUSE-001" not in npc.get("unknowns", []) or "TEST-HIDDEN-CAUSE-001" in npc.get("knowledge", []):
        errors.append("NPC epistemic boundary leaks hidden cause")
    reveal = read_json(root / FIXTURE_ROOT / "test-reveal-contract.json")
    if reveal.get("owner_reveal_authority_created") is not False:
        errors.append("synthetic Reveal fixture creates Owner authority")
    oracle = read_json(root / FIXTURE_ROOT / "cross-modal-oracle.json")
    if oracle.get("combined_modal_reveal_within_contract") is not True or oracle.get("result") != "NOT_RUN":
        errors.append("cross-modal oracle boundary/result drift")


def _validate_context_orders_and_packets(root: Path, errors: list[str]) -> None:
    context_schema = _schema(root, "context-manifest-v1.schema.json")
    omission_schema = _schema(root, "omission-report-v1.schema.json")
    task_schema = read_json(root / "workflow/task-packet.schema.json")
    contract = read_json(root / FIXTURE_ROOT / "test-region-intensity-contract.json")
    triples = (
        ("text-order-001.json", "test-context-manifest-text-001.json", "test-omission-report-text-001.json", "task-packet-text-001.json", "literary"),
        ("text-order-002.json", "test-context-manifest-text-002.json", "test-omission-report-text-002.json", "task-packet-text-002.json", "literary"),
        ("visual-order-001.json", "test-context-manifest-visual-001.json", "test-omission-report-visual-001.json", "task-packet-visual-001.json", "visual"),
    )
    for order_name, context_name, omission_name, packet_name, kind in triples:
        order = read_json(root / FIXTURE_ROOT / order_name)
        context = read_json(root / FIXTURE_ROOT / context_name)
        omission = read_json(root / FIXTURE_ROOT / omission_name)
        packet_envelope = read_json(root / FIXTURE_ROOT / packet_name)
        packet = packet_envelope.get("task_packet") if isinstance(packet_envelope, dict) else None
        errors.extend(_schema_issues(context, context_schema, context_name))
        errors.extend(_schema_issues(omission, omission_schema, omission_name))
        for source in context.get("sources", []):
            if not isinstance(source, dict):
                continue
            source_path = root / str(source.get("path"))
            if not source_path.is_file() or source.get("sha256") != file_sha256(source_path):
                errors.append(f"{context_name}: source hash mismatch for {source.get('path')}")
        if context.get("combined_source_hash") != canonical_sha256(context.get("sources")):
            errors.append(f"{context_name}: combined source hash mismatch")
        omission_payload = {key: value for key, value in omission.items() if key != "report_hash"}
        if omission.get("report_hash") != canonical_sha256(omission_payload):
            errors.append(f"{omission_name}: report hash mismatch")
        if omission.get("required_dependency_omitted") is not False or omission.get("closure_complete") is not True:
            errors.append(f"{omission_name}: dependency closure is incomplete")
        if order.get("context_manifest_sha256") != file_sha256(root / FIXTURE_ROOT / context_name):
            errors.append(f"{order_name}: context manifest file hash mismatch")
        if order.get("omission_report_sha256") != file_sha256(root / FIXTURE_ROOT / omission_name):
            errors.append(f"{order_name}: omission report file hash mismatch")
        errors.extend(validate_intensity_revision(order, contract))
        if not isinstance(packet, dict):
            errors.append(f"{packet_name}: nested Task Packet missing")
            continue
        errors.extend(_schema_issues(packet, task_schema, packet_name))
        errors.extend(f"{packet_name}: {issue}" for issue in validate_task_packet_pairing(packet))
        if packet_envelope.get("execution_authorized_in_m3_b002") is not False:
            errors.append(f"{packet_name}: B002 worker execution became authorized")
        if kind == "literary":
            if order.get("input_hash") != literary_input_hash(order):
                errors.append(f"{order_name}: input hash mismatch")
            if order.get("order_hash") != literary_order_hash(order):
                errors.append(f"{order_name}: order hash mismatch")
            errors.extend(validate_literary_execution(packet, order, [f"workflow/returns/literary/{order['order_id']}/candidate.json"]))
        else:
            if order.get("order_hash") != visual_order_hash(order):
                errors.append(f"{order_name}: order hash mismatch")
            errors.extend(validate_visual_execution(packet, order, [f"workflow/returns/visual/{order['order_id']}/candidate.json"]))
            if not order.get("must_objects"):
                errors.append("visual order: required must-object list is empty")


def _validate_profiles_and_controls(root: Path, errors: list[str]) -> None:
    required_markers = {
        "docs/operations/agents/m3/deepseek-harness/PRECONTENT_M0_PROFILE.md": ["DEEPSEEK-HARNESS", "deepseek-v4-pro", "reasoning_effort: high", "120000", "24000", "CONTRACT_ONLY_NO_CALL", "NOT_CERTIFIED"],
        ".grok/PRECONTENT_M0_PROFILE.md": ["XAI-GROK-CLI", "grok-4.6", "grok-imagine-image-2.0", "xhigh", "1K", "low", '"1:1"', "CONTRACT_ONLY_NO_CALL", "NOT_CERTIFIED"],
        ".grok/READING_MAP_PROFILE.yaml": ["VALIDATED_VISUAL_ORDER_PACKAGE_ONLY", "SYNTHETIC", "m3_b002_execution"],
        ".grok/RETURN_CONTRACT.md": ["resolved_model", "actual_fingerprint", "rights_obligations", "private_chain_of_thought_recorded"],
        "docs/governance/story-construction/10_PRECONTENT_READINESS.md": ["0.70 * risk_coverage + 0.30 * controllability", "Missing", "90 days", "PENDING_OWNER_ACTIVATION_HASH_APPROVAL_M3_B002", "AUTHORITATIVE_ACTIVATION_EFFECTIVE = FALSE"],
    }
    for relative, markers in required_markers.items():
        text = (root / relative).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative}: missing contract marker {marker!r}")
    expected = read_json(root / FIXTURE_ROOT / "expected-static-gates.json")
    if expected.get("request_counts") != {"deepseek": 0, "grok": 0, "opencode": 0, "story_m0": 0}:
        errors.append("static Provider request-count proof drift")
    m2_schema = _schema(root, "m2-dependency-classification-v1.schema.json")
    errors.extend(validate_m2_dependency_classification(expected.get("m2_dependency_classification"), m2_schema))
    if expected.get("allowlist_count") != 70 or expected.get("allowlist_sha256") != allowlist_hash():
        errors.append("frozen 70-path allowlist identity drift")
    for relative, expected_hash in expected.get("immutable_sha256", {}).items():
        path = root / relative
        if not path.is_file() or file_sha256(path) != expected_hash:
            errors.append(f"immutable accepted source drift: {relative}")


def _validate_routes(root: Path, errors: list[str]) -> None:
    for relative, (route_id, mode, batch_id) in ROUTE_SPECS.items():
        try:
            request = read_json(root / relative)
            validate_request(request)
            reading_map = generate_reading_map(request, repo_root=root)
        except (OSError, json.JSONDecodeError, RouteError) as exc:
            errors.append(f"{relative}: invalid pre-content route: {exc}")
            continue
        expected = {"route_id": route_id, "mode": mode, "milestone": "M3", "batch_id": batch_id, "capacity_bytes": 196608}
        for field, value in expected.items():
            if request.get(field) != value:
                errors.append(f"{relative}: route {field} drift")
        if reading_map.get("context_budget", {}).get("ratio", 1) > 0.55:
            errors.append(f"{relative}: context ratio exceeds 0.55")


def _git_output(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    return result.stdout.rstrip("\n")


def changed_paths(root: Path) -> set[str]:
    head = _git_output(root, "rev-parse", "HEAD")
    committed = set(filter(None, _git_output(root, "diff", "--name-only", f"{IMPLEMENTATION_CANDIDATE_COMMIT}..{head}").splitlines())) if head != IMPLEMENTATION_CANDIDATE_COMMIT else set()
    status = _git_output(root, "status", "--porcelain", "--untracked-files=all")
    working: set[str] = set()
    for line in status.splitlines():
        if not line:
            continue
        raw = line[3:]
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        working.add(raw)
    return committed | working


def _validate_git_and_runtime_boundary(root: Path, errors: list[str]) -> None:
    try:
        actual = changed_paths(root)
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"cannot compute changed paths: {exc}")
        return
    expected = set(ACTIVATION_ALLOWLIST)
    outside = sorted(actual - expected)
    missing = sorted(expected - actual)
    if outside or missing:
        errors.append(f"activation diff is not the exact 18-path allowlist: missing={missing}, extra={outside}")
    runtime_paths = runtime_relative_paths(root / "game-package")
    leaked = sorted(path for path in runtime_paths if "precontent" in path.lower() or "test-scg-m0" in path.lower())
    if leaked:
        errors.append(f"TEST pre-content artifact enters runtime package: {leaked}")
    for forbidden in ("authoring", "game-package", "governance/r2", "TRPG_PLATFORM"):
        prefix = forbidden + "/"
        changed = sorted(path for path in actual if path == forbidden or path.startswith(prefix))
        if changed:
            errors.append(f"forbidden authority/runtime scope changed: {changed}")


def _validate_derived(root: Path, errors: list[str]) -> None:
    _validate_immutable_r1(root, errors)
    try:
        derived = derive_activation_documents(root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cannot derive deterministic activation outputs: {exc}")
        return
    try:
        actual_manifest = read_json(root / R2_MANIFEST_PATH)
        actual_receipt = read_json(root / FINAL_RECEIPT_PATH)
        consumption = read_json(root / APPROVAL_CONSUMPTION_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"activation manifest/receipt/consumption missing or invalid: {exc}")
        return
    if actual_manifest != derived["manifest"]:
        errors.append("R2 framework manifest is stale or nondeterministic")
    if actual_receipt != derived["receipt"]:
        errors.append("final inner receipt is stale or nondeterministic")
    errors.extend(validate_framework_manifest_transition(actual_manifest, derive_framework_documents(root)["manifest"]))
    errors.extend(validate_final_receipt_binding(actual_receipt, derived["receipt"]))
    errors.extend(validate_implementation_approval_consumption(consumption))
    records = actual_manifest.get("records", [])
    record_paths = [item.get("path") for item in records if isinstance(item, dict)]
    if R2_MANIFEST_PATH.as_posix() in record_paths or any(path in record_paths for path in AUDIT_PATHS[1:]):
        errors.append("R2 manifest contains a self/audit Merkle leaf")
    transition = actual_manifest.get("transition", {})
    exact_counts = {
        "old_record_count": 68,
        "unchanged_old_count": 61,
        "changed_old_count": 7,
        "new_record_count": 8,
        "total_record_count": 76,
    }
    for field, value in exact_counts.items():
        if not isinstance(transition, dict) or transition.get(field) != value:
            errors.append(f"R2 Merkle transition count drift: {field}")
    if [item.get("path") for item in transition.get("changed_old_records", [])] != sorted(CHANGED_OLD_PATHS):
        errors.append("R2 changed-old semantic leaf set drift")
    if [item.get("path") for item in transition.get("new_records", [])] != sorted(NEW_SEMANTIC_PATHS):
        errors.append("R2 new semantic leaf set drift")
    payload = actual_receipt.get("payload")
    if not isinstance(payload, dict) or actual_receipt.get("payload_hash") != canonical_sha256(payload):
        errors.append("final inner receipt payload hash mismatch")
    forbidden_receipt_tokens = (
        "activation_candidate_commit", "activation_candidate_tree", "activation_owner_approval_id",
        "activation_accept_task_id", "activation_accept_route_digest", "tag_object_id",
        "authoritative_remote_after_activation", "integration_commit",
    )
    serialized = json.dumps(payload, sort_keys=True) if isinstance(payload, dict) else ""
    for token in forbidden_receipt_tokens:
        if token in serialized:
            errors.append(f"final inner receipt contains future/self binding: {token}")


def _validate_immutable_r1(root: Path, errors: list[str]) -> None:
    fixed_files = {
        MANIFEST_PATH: R1_MANIFEST_FILE_SHA256,
        RECEIPT_PATH: PENDING_RECEIPT_FILE_SHA256,
        DECISION_PATH: DECISION_SET_HASH,
        SUPERSESSION_PATH: PARTIAL_SUPERSESSION_HASH,
        TRACEABILITY_PATH: TRACEABILITY_HASH,
        FIXTURE_ROOT / "test-fixture-graph.json": M0_FIXTURE_GRAPH_HASH,
        FIXTURE_ROOT / "expected-static-gates.json": STATIC_GATE_RESULT_HASH,
    }
    for relative, expected_sha256 in fixed_files.items():
        if not (root / relative).is_file() or file_sha256(root / relative) != expected_sha256:
            errors.append(f"fixed R1 preservation hash drift: {relative.as_posix()}")
    try:
        frozen = derive_framework_documents(root)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load immutable R1 framework: {exc}")
        return
    manifest = frozen["manifest"]
    receipt = frozen["receipt"]
    records = manifest.get("records", [])
    if len(records) != R1_RECORD_COUNT or manifest.get("merkle", {}).get("root") != R1_MERKLE_ROOT:
        errors.append("immutable R1 manifest count/root drift")
    elif merkle_root((item["path"], item["sha256"]) for item in records) != R1_MERKLE_ROOT:
        errors.append("immutable R1 manifest leaf/root mismatch")
    if receipt.get("payload_hash") != PENDING_RECEIPT_PAYLOAD_HASH:
        errors.append("immutable pending receipt payload hash drift")
    if receipt.get("payload", {}).get("approval_status") != CANDIDATE_APPROVAL_STATUS:
        errors.append("immutable pending receipt candidate status drift")
    original_schema_records = [
        item for item in records
        if item.get("path") in {f"schemas/story-construction/{name}" for name in SCHEMA_FILES}
    ]
    if len(original_schema_records) != 20 or _record_set_hash(original_schema_records) != ORIGINAL_SCHEMA_SET_HASH:
        errors.append("immutable original 20-schema set hash drift")
    context_records = [item for item in records if "test-context-manifest-" in item.get("path", "")]
    omission_records = [item for item in records if "test-omission-report-" in item.get("path", "")]
    profile_paths = {
        "docs/operations/agents/m3/deepseek-harness/PRECONTENT_M0_PROFILE.md",
        ".grok/READING_MAP_PROFILE.yaml", ".grok/RETURN_CONTRACT.md", ".grok/PRECONTENT_M0_PROFILE.md",
    }
    profile_records = [item for item in records if item.get("path") in profile_paths]
    if _record_set_hash(context_records) != CONTEXT_MANIFEST_SET_HASH:
        errors.append("immutable context manifest set hash drift")
    if _record_set_hash(omission_records) != OMISSION_REPORT_SET_HASH:
        errors.append("immutable omission report set hash drift")
    if _record_set_hash(profile_records) != PROVIDER_PROFILE_CONTRACT_SET_HASH:
        errors.append("immutable Provider profile contract set hash drift")
    if canonical_sha256({"deepseek": 0, "grok": 0, "opencode": 0, "story_m0": 0}) != PROVIDER_ZERO_CALL_EVIDENCE_HASH:
        errors.append("Provider zero-call evidence hash algorithm drift")


def _git_show_json(root: Path, revision: str, relative: Path) -> Any:
    data = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{relative.as_posix()}"],
        check=True,
        capture_output=True,
    ).stdout
    return json.loads(data)


def _validate_implementation_candidate_object(root: Path, errors: list[str]) -> None:
    try:
        tree = _git_output(root, "rev-parse", f"{IMPLEMENTATION_CANDIDATE_COMMIT}^{{tree}}")
        parent = _git_output(root, "rev-parse", f"{IMPLEMENTATION_CANDIDATE_COMMIT}^")
        candidate = _git_show_json(root, IMPLEMENTATION_CANDIDATE_COMMIT, CHANGE_SET_PATH)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load fixed implementation candidate object: {exc}")
        return
    if tree != IMPLEMENTATION_CANDIDATE_TREE or parent != IMPLEMENTATION_CANDIDATE_PARENT:
        errors.append("fixed implementation candidate commit/tree/parent mismatch")
    errors.extend(validate_precontent_lifecycle_state(candidate))
    if candidate.get("candidate_binding") != {"strategy": "EXACT_HEAD_AT_VALIDATION"}:
        errors.append("implementation candidate self-binding strategy drift")
    if "candidate_commit" in json.dumps(candidate, sort_keys=True):
        errors.append("implementation candidate predicts its own commit/tree")


def _validate_invalid_mixed_state(root: Path, errors: list[str]) -> None:
    try:
        fixture = read_json(root / "tests/fixtures/story-construction/precontent-lifecycle-state-v1.json")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid lifecycle fixture: {exc}")
        return
    attacks = fixture.get("invalid_mixed_states", []) if isinstance(fixture, dict) else []
    if not isinstance(attacks, list) or len(attacks) < 4:
        errors.append("lifecycle fixture lacks mixed-state and early-release attacks")
        return
    for index, attack in enumerate(attacks):
        if not validate_precontent_lifecycle_state(attack):
            errors.append(f"invalid lifecycle fixture unexpectedly accepted: {index}")


def _validate_authoritative_effect(root: Path, errors: list[str]) -> None:
    change_set = read_json(root / CHANGE_SET_PATH)
    tracked_active = not validate_precontent_lifecycle_state(change_set)
    effective, proof_errors = authoritative_precontent_activation_status(
        tracked_active=tracked_active,
        activation_approval=None,
        expected_activation_approval={},
        envelope=None,
        expected_envelope={},
        integration=None,
    )
    if effective or len(proof_errors) < 3:
        errors.append("authoritative activation did not fail closed without external proofs")
    if change_set.get("activation_state", {}).get("authoritative_activation_effective") is not False:
        errors.append("tracked ACTIVE incorrectly claims authoritative activation")


def collect_errors(
    project_root: Path = PROJECT_ROOT,
    *,
    check_git: bool = True,
    check_derived: bool = True,
    phase: str = "all",
) -> list[str]:
    root = project_root.resolve()
    errors: list[str] = []
    if phase == "implementation-candidate-object":
        _validate_implementation_candidate_object(root, errors)
        _validate_immutable_r1(root, errors)
        return errors
    if phase == "invalid-mixed-state":
        _validate_invalid_mixed_state(root, errors)
        return errors
    for relative in tuple(dict.fromkeys(ALLOWLIST + ACTIVATION_ALLOWLIST)):
        if not (root / relative).is_file():
            errors.append(f"missing mandatory B002 artifact: {relative}")
    if errors:
        return errors
    _validate_schemas_and_instances(root, errors)
    _validate_decision_binding(root, errors)
    _validate_change_set(root, errors)
    _validate_test_fixtures(root, errors)
    _validate_context_orders_and_packets(root, errors)
    _validate_profiles_and_controls(root, errors)
    _validate_routes(root, errors)
    if check_derived:
        _validate_derived(root, errors)
    if phase in {"all", "authoritative-effect"}:
        _validate_authoritative_effect(root, errors)
    if check_git:
        _validate_git_and_runtime_boundary(root, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SCG Pre-Content Readiness framework")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--phase",
        choices=("framework", "implementation-candidate-object", "tracked-active-candidate", "authoritative-effect", "invalid-mixed-state"),
        default="framework",
    )
    parser.add_argument("--skip-derived", action="store_true")
    parser.add_argument("--print-hashes", action="store_true")
    args = parser.parse_args(argv)
    phase = "tracked-active-candidate" if args.phase == "framework" else args.phase
    errors = collect_errors(args.project_root, check_derived=not args.skip_derived, phase=phase)
    if errors:
        print("PRECONTENT_READINESS: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    derived = derive_activation_documents(args.project_root)
    print("PRECONTENT_READINESS: PASS")
    print(f"- phase={args.phase}: PASS")
    print("- 21 Owner decisions and three partial supersessions: PASS")
    print("- TEST namespace, non-promotion, routes, Reveal/NPC and cross-modal boundaries: PASS")
    print("- closed schemas, context/omission hashes and M2 capability isolation: PASS")
    print("- Provider profiles, data/rights controls and request counts=0: PASS")
    print("- immutable R1/pending plus deterministic R2/final receipt and runtime exclusion: PASS")
    print("- tracked_active_wip=true")
    print("- authoritative_activation_effective=false")
    if args.print_hashes:
        receipt = derived["receipt"]
        transition = derived["transition"]
        schemas = derived["schemas"]
        print(f"activation_allowlist_sha256={activation_allowlist_hash()}")
        print(f"activation_path_set_hash={activation_path_set_hash(args.project_root)}")
        print(f"framework_manifest_r1_file_sha256={R1_MANIFEST_FILE_SHA256}")
        print(f"framework_manifest_r1_merkle_root={R1_MERKLE_ROOT}")
        print(f"framework_manifest_r1_record_count={R1_RECORD_COUNT}")
        print(f"framework_manifest_r2_file_sha256={derived['manifest_file_sha256']}")
        print(f"framework_manifest_r2_merkle_root={derived['framework_merkle_root']}")
        for field in (
            "old_record_count", "unchanged_old_count", "changed_old_count", "new_record_count",
            "total_record_count", "unchanged_old_leaf_set_hash", "changed_old_leaf_transition_hash",
            "new_leaf_set_hash", "r1_leaf_set_hash", "r2_leaf_set_hash",
        ):
            print(f"{field}={transition[field]}")
        print(f"original_schema_count={schemas['original_count']}")
        print(f"original_schema_set_hash={schemas['original_set_hash']}")
        print(f"activation_schema_count={schemas['activation_count']}")
        print(f"activation_schema_set_hash={schemas['activation_set_hash']}")
        print(f"combined_schema_count={schemas['combined_count']}")
        print(f"combined_schema_set_hash={schemas['combined_set_hash']}")
        print(f"approval_consumption_record_sha256={derived['consumption_sha256']}")
        print(f"final_receipt_file_sha256={hashlib.sha256(derived['receipt_bytes']).hexdigest()}")
        print(f"final_receipt_payload_hash={receipt['payload_hash']}")
        print(f"pending_receipt_file_sha256={PENDING_RECEIPT_FILE_SHA256}")
        print(f"pending_receipt_payload_hash={PENDING_RECEIPT_PAYLOAD_HASH}")
        print(f"decision_set_hash={DECISION_SET_HASH}")
        print(f"partial_supersession_hash={PARTIAL_SUPERSESSION_HASH}")
        print(f"traceability_hash={TRACEABILITY_HASH}")
        print(f"canon_hash={BASE_CANON_HASH}")
        print(f"runtime_package_sha256={RUNTIME_PACKAGE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
