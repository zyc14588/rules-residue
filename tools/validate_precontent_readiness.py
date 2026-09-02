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
APPROVAL_STATUS = "PENDING_OWNER_EXACT_HASH_APPROVAL_M3_B002"
OWNER_PLAN_APPROVAL_ID = "OWNER-APPROVAL-SCG-PRECONTENT-M3-B002-PLAN-R2"
OWNER_PACKAGE_ID = "SCG-PRECONTENT-M3-B002-IMPLEMENT-V2"
OWNER_PACKAGE_MANIFEST_FILE_SHA256 = "760aeb0daa8db0d635b03e2f24866527b5fbc3af0b0b38f3b49d7baaeba414b9"
PLAN_READING_MAP_BINDING_DIGEST = "5081c3b31256ce5f1848a4a0007942b6f7490ec58f36c2b26fab7bd63c2f276c"
IMPLEMENT_READING_MAP_BINDING_DIGEST = "6fb42d7d098f4aeff33e540ed439abf825a36435f91aa9ebe41ec0a13b796de1"
RUNTIME_PACKAGE_SHA256 = "29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314"

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
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def allowlist_hash() -> str:
    payload = "".join(f"{path}\n" for path in sorted(ALLOWLIST)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def _framework_record_paths() -> tuple[str, ...]:
    excluded = {MANIFEST_PATH.as_posix(), RECEIPT_PATH.as_posix()}
    return tuple(sorted(path for path in ALLOWLIST if path not in excluded))


def derive_framework_documents(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    root = root.resolve()
    records = [
        {"path": path, "sha256": file_sha256(root / path)}
        for path in _framework_record_paths()
    ]
    root_hash = merkle_root((record["path"], record["sha256"]) for record in records)
    schema_records = [record for record in records if record["path"].startswith("schemas/story-construction/")]
    context_records = [record for record in records if "test-context-manifest-" in record["path"]]
    omission_records = [record for record in records if "test-omission-report-" in record["path"]]
    profile_paths = {
        "docs/operations/agents/m3/deepseek-harness/PRECONTENT_M0_PROFILE.md",
        ".grok/READING_MAP_PROFILE.yaml", ".grok/RETURN_CONTRACT.md", ".grok/PRECONTENT_M0_PROFILE.md",
    }
    profile_records = [record for record in records if record["path"] in profile_paths]
    request_counts = {"deepseek": 0, "grok": 0, "opencode": 0, "story_m0": 0}
    manifest = {
        "schema_version": "rules-residue.story-construction.precontent-framework-manifest/1.0.0",
        "manifest_id": "SCG-PRECONTENT-FRAMEWORK-MANIFEST-R1",
        "change_set_id": CHANGE_SET_ID,
        "machine_milestone": "M3", "machine_batch_id": "M3-B002",
        "authority_scope": "CONSTRUCTION_GOVERNANCE_ONLY", "r2_canon_precedence": "HIGHER",
        "base_commit": BASE_COMMIT, "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH, "proposed_canon_hash": BASE_CANON_HASH,
        "canonicalization": "UTF8_NFC_SORTED_KEYS_FINITE_NUMBERS_V1",
        "candidate_binding": {"strategy": "EXACT_HEAD_AT_VALIDATION"},
        "allowlist": {"path_count": len(ALLOWLIST), "sha256": allowlist_hash()},
        "records": records,
        "merkle": {"algorithm": "SHA-256-BINARY-PAIR-DUPLICATE-ODD-V1", "leaf_order": "path_lexical", "root": root_hash},
        "provider_request_counts": request_counts,
        "runtime_projection": "EXCLUDED",
        "self_reference": False,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_file_hash = hashlib.sha256(manifest_bytes).hexdigest()
    payload = {
        "receipt_id": "SCG-PRECONTENT-READINESS-R1-PENDING-001",
        "receipt_status": APPROVAL_STATUS,
        "change_set_id": CHANGE_SET_ID,
        "machine_milestone": "M3", "machine_batch_id": "M3-B002",
        "batch_semantics": "SCG_PRECONTENT_DECISION_BINDING_AND_M0_FRAMEWORK",
        "base_commit": BASE_COMMIT, "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH, "proposed_canon_hash": BASE_CANON_HASH,
        "owner_plan_approval_id": OWNER_PLAN_APPROVAL_ID,
        "owner_package_id": OWNER_PACKAGE_ID,
        "owner_package_manifest_file_sha256": OWNER_PACKAGE_MANIFEST_FILE_SHA256,
        "plan_reading_map_binding_digest": PLAN_READING_MAP_BINDING_DIGEST,
        "implement_reading_map_binding_digest": IMPLEMENT_READING_MAP_BINDING_DIGEST,
        "decision_set_count": len(EXPECTED_DECISIONS),
        "decision_set_hash": file_sha256(root / DECISION_PATH),
        "partial_supersession_hash": file_sha256(root / SUPERSESSION_PATH),
        "traceability_hash": file_sha256(root / TRACEABILITY_PATH),
        "framework_manifest_path": MANIFEST_PATH.as_posix(),
        "framework_manifest_file_sha256": manifest_file_hash,
        "framework_merkle_root": root_hash,
        "schema_set_hash": canonical_sha256(schema_records),
        "m0_fixture_graph_hash": file_sha256(root / FIXTURE_ROOT / "test-fixture-graph.json"),
        "context_manifest_set_hash": canonical_sha256(context_records),
        "omission_report_set_hash": canonical_sha256(omission_records),
        "static_gate_result_hash": file_sha256(root / FIXTURE_ROOT / "expected-static-gates.json"),
        "provider_profile_contract_set_hash": canonical_sha256(profile_records),
        "provider_request_count_evidence_hash": canonical_sha256(request_counts),
        "runtime_package_sha256": RUNTIME_PACKAGE_SHA256,
        "candidate_binding": {"strategy": "EXACT_HEAD_AT_VALIDATION"},
        "approval_status": APPROVAL_STATUS,
    }
    receipt = {
        "schema_version": "rules-residue.story-construction.precontent-pending-receipt/1.0.0",
        "receipt_kind": "NON_AUTHORITATIVE_PENDING_OWNER_EXACT_HASH_APPROVAL",
        "payload": payload,
        "payload_hash": canonical_sha256(payload),
    }
    return {
        "manifest": manifest, "manifest_bytes": manifest_bytes,
        "receipt": receipt, "receipt_bytes": canonical_json_bytes(receipt),
        "framework_merkle_root": root_hash,
    }


def write_framework_documents(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    derived = derive_framework_documents(root)
    manifest_path = root / MANIFEST_PATH
    receipt_path = root / RECEIPT_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(derived["manifest_bytes"])
    receipt_path.write_bytes(derived["receipt_bytes"])
    return derived


def _validate_schemas_and_instances(root: Path, errors: list[str]) -> None:
    schemas: dict[str, dict[str, Any]] = {}
    for name in SCHEMA_FILES:
        path = root / "schemas/story-construction" / name
        try:
            schema = _schema(root, name)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{name}: invalid schema JSON: {exc}")
            continue
        schemas[name] = schema
        if not name.endswith("-v1.schema.json") and name not in {"text-order-v2.schema.json", "visual-order-v2.schema.json"}:
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


def _validate_change_set(root: Path, errors: list[str]) -> None:
    change_set = read_json(root / CHANGE_SET_PATH)
    expected = {
        "change_set_id": CHANGE_SET_ID, "machine_milestone": "M3", "machine_batch_id": "M3-B002",
        "batch_semantics": "SCG_PRECONTENT_DECISION_BINDING_AND_M0_FRAMEWORK",
        "lifecycle_stage": "CANDIDATE", "disposition": "CANDIDATE_NOT_ACTIVE",
        "release": "NOT_RELEASED", "approval_status": APPROVAL_STATUS,
        "base_commit": BASE_COMMIT, "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH, "proposed_canon_hash": BASE_CANON_HASH,
        "active_wip": True,
    }
    for field, value in expected.items():
        if change_set.get(field) != value:
            errors.append(f"pre-content Change Set drift: {field}")
    binding = change_set.get("candidate_binding")
    if binding != {"strategy": "EXACT_HEAD_AT_VALIDATION"}:
        errors.append("pre-content Change Set must use non-self-referential EXACT_HEAD_AT_VALIDATION")
    serialized = json.dumps(change_set, sort_keys=True)
    if "candidate_commit" in serialized or "candidate_tree" in serialized:
        errors.append("tracked Change Set predicts its future candidate identity")
    counts = change_set.get("provider_request_counts")
    if counts != {"deepseek": 0, "grok": 0, "opencode": 0, "story_m0": 0}:
        errors.append("Provider or worker request count is not zero")


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
        "docs/governance/story-construction/10_PRECONTENT_READINESS.md": ["0.70 * risk_coverage + 0.30 * controllability", "Missing", "90 days", "PENDING_OWNER_EXACT_HASH_APPROVAL_M3_B002"],
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
    committed = set(filter(None, _git_output(root, "diff", "--name-only", f"{BASE_COMMIT}..{head}").splitlines())) if head != BASE_COMMIT else set()
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
    outside = sorted(actual - set(ALLOWLIST))
    if outside:
        errors.append(f"tracked/untracked changes outside 70-path allowlist: {outside}")
    runtime_paths = runtime_relative_paths(root / "game-package")
    leaked = sorted(path for path in runtime_paths if "precontent" in path.lower() or "test-scg-m0" in path.lower())
    if leaked:
        errors.append(f"TEST pre-content artifact enters runtime package: {leaked}")
    for forbidden in ("authoring", "game-package", "governance/r2"):
        prefix = forbidden + "/"
        changed = sorted(path for path in actual if path == forbidden or path.startswith(prefix))
        if changed:
            errors.append(f"forbidden authority/runtime scope changed: {changed}")


def _validate_derived(root: Path, errors: list[str]) -> None:
    try:
        derived = derive_framework_documents(root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cannot derive deterministic framework outputs: {exc}")
        return
    try:
        actual_manifest = read_json(root / MANIFEST_PATH)
        actual_receipt = read_json(root / RECEIPT_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"framework manifest/receipt missing or invalid: {exc}")
        return
    if actual_manifest != derived["manifest"]:
        errors.append("framework manifest is stale or nondeterministic")
    if actual_receipt != derived["receipt"]:
        errors.append("pending receipt is stale or nondeterministic")
    if "manifest_sha256" in actual_manifest or "receipt_sha256" in actual_manifest:
        errors.append("framework manifest contains forbidden self/receipt reference")
    if actual_receipt.get("payload", {}).get("approval_status") != APPROVAL_STATUS:
        errors.append("pending receipt approval status drift")


def collect_errors(project_root: Path = PROJECT_ROOT, *, check_git: bool = True, check_derived: bool = True) -> list[str]:
    root = project_root.resolve()
    errors: list[str] = []
    for relative in ALLOWLIST:
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
    if check_git:
        _validate_git_and_runtime_boundary(root, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SCG Pre-Content Readiness framework")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--phase", choices=("framework",), default="framework")
    parser.add_argument("--skip-derived", action="store_true")
    parser.add_argument("--print-hashes", action="store_true")
    args = parser.parse_args(argv)
    errors = collect_errors(args.project_root, check_derived=not args.skip_derived)
    if errors:
        print("PRECONTENT_READINESS: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    derived = derive_framework_documents(args.project_root)
    print("PRECONTENT_READINESS: PASS")
    print("- 21 Owner decisions and three partial supersessions: PASS")
    print("- TEST namespace, non-promotion, routes, Reveal/NPC and cross-modal boundaries: PASS")
    print("- closed schemas, context/omission hashes and M2 capability isolation: PASS")
    print("- Provider profiles, data/rights controls and request counts=0: PASS")
    print("- deterministic manifest/receipt and runtime exclusion: PASS")
    if args.print_hashes:
        receipt = derived["receipt"]
        print(f"allowlist_sha256={allowlist_hash()}")
        print(f"framework_merkle_root={derived['framework_merkle_root']}")
        print(f"framework_manifest_file_sha256={hashlib.sha256(derived['manifest_bytes']).hexdigest()}")
        print(f"pending_receipt_file_sha256={hashlib.sha256(derived['receipt_bytes']).hexdigest()}")
        print(f"pending_receipt_payload_hash={receipt['payload_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
