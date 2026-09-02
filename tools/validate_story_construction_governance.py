from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.codex_route import RouteError, generate_reading_map, validate_request
from tools.lib.common import PROJECT_ROOT, read_json, runtime_relative_paths
from tools.lib.schema_subset import validate
from tools.story_construction import (
    ACTIVATION_CHANGED_LEAF_IDS,
    APPROVAL_CONSUMPTION_PATH,
    AUTHORITY_OVERLAY_PATH,
    BASE_CANON_HASH,
    BASE_COMMIT,
    BASE_TREE,
    CANONICAL_DECISIONS_SHA256,
    CANONICAL_DECISIONS_PATH,
    CANONICAL_MANIFEST_PATH,
    CANON_REGISTRY_PATH,
    CHANGE_SET_ID,
    CHANGE_SET_PATH,
    DECISIONS_PATH,
    FINAL_RECEIPT_PATH,
    IMPLEMENTATION_CANDIDATE_COMMIT,
    IMPLEMENTATION_CANDIDATE_PARENT,
    IMPLEMENTATION_CANDIDATE_TREE,
    PREVIOUS_GOVERNANCE_MERKLE_ROOT,
    RECEIPT_PATH,
    SOURCE_INTAKE_PATH,
    SOURCE_INTEGRITY_DEFECT,
    SOURCE_MANIFEST_FILE_SHA256,
    SOURCE_METADATA_MANIFEST_SHA256,
    SOURCE_PACKAGE_ID,
    SOURCE_ZIP_SHA256,
    SUPERSESSION_PATH,
    TRACEABILITY_PATH,
    authoritative_activation_status,
    canonical_decision_document,
    canonical_sha256,
    derive_installation,
    expected_question_ids,
    file_sha256,
    read_json_document,
    tracked_target_state_active,
    validate_canon_hash_invariants,
    validate_final_receipt_binding,
    validate_implementation_approval_consumption,
    validate_lifecycle_state,
    validate_merkle_transition,
    validate_task_packet_pairing,
    validate_m3_route_request,
    validate_canonical_manifest_binding,
    validate_pending_receipt_binding,
    write_derived_installation,
)
from tools.validate_precontent_readiness import (
    ALLOWLIST as PRECONTENT_ALLOWLIST,
    BASE_COMMIT as PRECONTENT_BASE_COMMIT,
    changed_paths as precontent_changed_paths,
    collect_errors as validate_precontent_readiness,
)


SCHEMA_ROOT = Path("schemas/story-construction")
SCHEMA_FILES = {
    "activation-closeout-envelope-v1.schema.json",
    "activation-owner-approval-v1.schema.json",
    "canon-record-v1.schema.json",
    "reveal-contract-v1.schema.json",
    "canon-envelope-v1.schema.json",
    "change-set-v1.schema.json",
    "change-set-v2.schema.json",
    "region-dossier-v1.schema.json",
    "text-order-v1.schema.json",
    "visual-order-v1.schema.json",
    "dab-v1.schema.json",
    "region-acceptance-v1.schema.json",
    "canonical-manifest-v1.schema.json",
    "installation-receipt-v1.schema.json",
    "installation-receipt-v2.schema.json",
    "owner-approval-consumption-v1.schema.json",
    "candidate-approval-v1.schema.json",
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
}

PRECONTENT_SCHEMA_FILES = {
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
}

GOVERNANCE_DOCS = [
    f"docs/governance/story-construction/{index:02d}_{name}.md"
    for index, name in enumerate(
        (
            "AUTHORITY_AND_PRECEDENCE",
            "GOVERNANCE_MODEL",
            "CHANGE_SET_AND_LIFECYCLE",
            "CANON_REGISTRY",
            "REVEAL_AND_EPISTEMIC",
            "REGION_CONSTRUCTION",
            "TEXT_ORDER_SYSTEM",
            "VISUAL_ORDER_SYSTEM",
            "VALIDATION_V0_V6",
            "DAB_AND_ACCEPTANCE",
        )
    )
]
GOVERNANCE_DOCS.append("docs/governance/story-construction/10_PRECONTENT_READINESS.md")

PROMPT_FILES = [
    f".codex/prompts/m3/STORY-CONSTRUCTION/{name}.md"
    for name in ("README", "PLAN", "IMPLEMENT", "ACCEPT", "REPAIR", "LITERARY_WORKER")
]

ROUTE_IDENTITIES = {
    ".codex/routes/m3-story-construction-plan-request.json": (
        "M3-STORY-CONSTRUCTION-PLAN",
        "PLAN",
    ),
    ".codex/routes/m3-story-construction-implement-request.json": (
        "M3-STORY-CONSTRUCTION-IMPLEMENT",
        "IMPLEMENT",
    ),
    ".codex/routes/m3-story-construction-accept-request.json": (
        "M3-STORY-CONSTRUCTION-ACCEPT",
        "ACCEPT",
    ),
    ".codex/routes/m3-story-construction-repair-request.json": (
        "M3-STORY-CONSTRUCTION-REPAIR",
        "REPAIR",
    ),
    ".codex/routes/m3-story-construction-activation-closeout-accept-request.json": (
        "R2-SC-GOV-INSTALL-ACTIVATION-CLOSEOUT-ACCEPT",
        "ACCEPT",
    ),
}

AGENT_FILES = [
    f"docs/operations/agents/m3/deepseek-harness/{name}"
    for name in (
        "README.md",
        "SESSION_START.md",
        "READING_MAP_PROFILE.yaml",
        "LITERARY_PRODUCE.md",
        "LITERARY_REPAIR.md",
        "RETURN_CONTRACT.md",
    )
]
AGENT_FILES.append("docs/operations/agents/m3/deepseek-harness/PRECONTENT_M0_PROFILE.md")

REQUIRED_FILES = (
    GOVERNANCE_DOCS
    + PROMPT_FILES
    + list(ROUTE_IDENTITIES)
    + AGENT_FILES
    + [
        DECISIONS_PATH.as_posix(),
        TRACEABILITY_PATH.as_posix(),
        SOURCE_INTAKE_PATH.as_posix(),
        AUTHORITY_OVERLAY_PATH.as_posix(),
        CANON_REGISTRY_PATH.as_posix(),
        SUPERSESSION_PATH.as_posix(),
        CHANGE_SET_PATH.as_posix(),
        CANONICAL_DECISIONS_PATH.as_posix(),
        CANONICAL_MANIFEST_PATH.as_posix(),
        RECEIPT_PATH.as_posix(),
        FINAL_RECEIPT_PATH.as_posix(),
        APPROVAL_CONSUMPTION_PATH.as_posix(),
        "governance/story-construction/approvals/candidate-approval.template.json",
        "tests/fixtures/story-construction/lifecycle-state-v1.json",
        "workflow/examples/m3-literary-task-packet.json",
        "workflow/examples/m3-visual-order-task-packet.json",
        "tools/story_construction.py",
        "tools/validate_deepseek_literary_task.py",
        "tools/validate_visual_order.py",
    ]
    + [(SCHEMA_ROOT / name).as_posix() for name in sorted(SCHEMA_FILES)]
)

BASELINE_PREDECESSOR_HASHES = {
    ".codex/STORY_ARCHITECTURE_BUILD_PROMPT.md": "81297200685467558af891e58c6bfd00d997e901be62833031805db1a689bc1e",
    ".codex/STORY_UPDATE_PROMPT.md": "82a5b02658b4e838a21654f3dba62cec0f3d3c3c2314384077f61a8c11c09c5d",
    "docs/operations/PROMPT_USAGE.md": "5f681ce914ed28ecc8e72289d5f720cc872d2f041341c9e34056faf6ec6eb108",
    "docs/operations/CONTENT_AUTHORING_PIPELINE.md": "aac56dd126edbce58ab4d94b019b31132d8e2ff872f13522953661f6eb70e4fe",
    "docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md": "a1de1bad6dfcd42dac8c3f340446e4f527708aac7bdb56d1957c89c94affc6e1",
    "docs/operations/HYBRID_PIPELINE.md": "7a6117699a8391a07057ef3c12e7aa896b3b098fda7f2535b43e5b6f100b8e27",
    ".codex/BUILD_AND_INTEGRATION_PROMPT.md": "b91e2da8e8ce2fb9053482f0b2d08e113f2081c39e186bceb4ef115b5fa0f42e",
    ".codex/TASK_PLANNER_PROMPT.md": "741f3d198a85d6e2518df7bf0857c13f89ebc302528e840c0003ce1c5e838725",
    ".grok/ART_TASK_PROMPT.md": "28cb53c4cb312db0eb5634898f057257213400c54ba97295316fd6ef720ef240",
    ".opencode/SCRIPT_TASK_PROMPT.md": "b7b8b2b8b5c4a96355353b4d4b4dc487d7f3e525897abf53d87db724fd120662",
}

EXPECTED_SUPERSESSION_DISPOSITIONS = {
    ".codex/STORY_ARCHITECTURE_BUILD_PROMPT.md": "HISTORICAL_ONLY",
    ".codex/STORY_UPDATE_PROMPT.md": "SUPERSEDED",
    "docs/operations/PROMPT_USAGE.md": "PARTIALLY_RETAINED",
    "docs/operations/CONTENT_AUTHORING_PIPELINE.md": "PARTIALLY_RETAINED",
    "docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md": "PARTIALLY_RETAINED",
    "docs/operations/HYBRID_PIPELINE.md": "PARTIALLY_RETAINED",
    ".codex/BUILD_AND_INTEGRATION_PROMPT.md": "PARTIALLY_RETAINED",
    ".codex/TASK_PLANNER_PROMPT.md": "PARTIALLY_RETAINED",
    ".grok/ART_TASK_PROMPT.md": "PARTIALLY_RETAINED",
    ".opencode/SCRIPT_TASK_PROMPT.md": "KEEP_ACTIVE",
}

EXPECTED_M2_BLOCKERS = ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"]
V1_SCHEMA_SHA256 = {
    "candidate-approval-v1.schema.json": "f317758d3eee1518b1921436643deb84b573d89aa28808617f7b487dc3885ab7",
    "change-set-v1.schema.json": "e0aa88c72e9b6b792740acfadbaf61f458fcee102bf5955c442fba1ad1b42dd0",
    "installation-receipt-v1.schema.json": "2273e43d9e4a6876c4deccd24f91f119eb11cbfce536320e6f42084ab53e727e",
}
OLD_PREDECESSORS = {
    ".codex/STORY_ARCHITECTURE_BUILD_PROMPT.md",
    ".codex/STORY_UPDATE_PROMPT.md",
    "docs/operations/PROMPT_USAGE.md",
}
APPROVED_ACTIVATION_PATHS = {
    "README.md",
    "docs/governance/story-construction/00_AUTHORITY_AND_PRECEDENCE.md",
    "docs/governance/story-construction/02_CHANGE_SET_AND_LIFECYCLE.md",
    "docs/governance/story-construction/03_CANON_REGISTRY.md",
    "docs/governance/story-construction/09_DAB_AND_ACCEPTANCE.md",
    AUTHORITY_OVERLAY_PATH.as_posix(),
    CANON_REGISTRY_PATH.as_posix(),
    DECISIONS_PATH.as_posix(),
    SUPERSESSION_PATH.as_posix(),
    CHANGE_SET_PATH.as_posix(),
    CANONICAL_MANIFEST_PATH.as_posix(),
    "tools/story_construction.py",
    "tools/validate_story_construction_governance.py",
    "tools/validate_project.py",
    "tests/test_story_construction_governance.py",
    APPROVAL_CONSUMPTION_PATH.as_posix(),
    FINAL_RECEIPT_PATH.as_posix(),
    "schemas/story-construction/change-set-v2.schema.json",
    "schemas/story-construction/installation-receipt-v2.schema.json",
    "schemas/story-construction/owner-approval-consumption-v1.schema.json",
    "schemas/story-construction/activation-owner-approval-v1.schema.json",
    "schemas/story-construction/activation-closeout-envelope-v1.schema.json",
    "tests/fixtures/story-construction/lifecycle-state-v1.json",
    ".codex/routes/m3-story-construction-activation-closeout-accept-request.json",
}


def _load(path: Path, errors: list[str], label: str) -> Any | None:
    try:
        return read_json_document(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: cannot read JSON-compatible YAML/JSON: {exc}")
        return None


def _check_required_files(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing Story Construction file: {relative}")


def _check_human_docs(root: Path, errors: list[str]) -> None:
    for relative in GOVERNANCE_DOCS:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "AUTHORITY_SCOPE = CONSTRUCTION_GOVERNANCE_ONLY" not in text:
            errors.append(f"{relative}: authority scope marker missing")
        if "R2_CANON_PRECEDENCE = HIGHER" not in text:
            errors.append(f"{relative}: R2 precedence marker missing")


def _check_schemas(root: Path, errors: list[str]) -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    actual = {path.name for path in (root / SCHEMA_ROOT).glob("*.schema.json")}
    if actual != SCHEMA_FILES:
        errors.append(
            f"Story Construction schema set mismatch: missing={sorted(SCHEMA_FILES-actual)}, extra={sorted(actual-SCHEMA_FILES)}"
        )
    for name in sorted(SCHEMA_FILES):
        path = root / SCHEMA_ROOT / name
        frozen_digest = V1_SCHEMA_SHA256.get(name)
        if frozen_digest is not None and file_sha256(path) != frozen_digest:
            errors.append(f"{name}: frozen v1 schema bytes changed")
        try:
            schema = read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(root)}: invalid JSON Schema: {exc}")
            continue
        schemas[name] = schema
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{name}: must declare draft 2020-12")
        if schema.get("additionalProperties") is not False:
            errors.append(f"{name}: root unknown fields must be rejected")
        version = schema.get("properties", {}).get("schema_version", {}).get("const")
        if name in PRECONTENT_SCHEMA_FILES:
            valid_version = isinstance(version, str) and re.search(
                r"(?:^|/)[0-9]+\.[0-9]+\.[0-9]+$", version
            ) is not None
        else:
            valid_version = isinstance(version, str) and re.fullmatch(
                r"[0-9]+\.[0-9]+\.[0-9]+", version
            ) is not None
        if not valid_version:
            errors.append(f"{name}: explicit SemVer schema_version const missing")
    return schemas


def _schema_instance(
    instance: Any,
    schema: dict[str, Any] | None,
    label: str,
    errors: list[str],
) -> None:
    if schema is None:
        errors.append(f"{label}: schema unavailable")
        return
    for issue in validate(instance, schema):
        errors.append(f"{label}: {issue}")


def _check_source_intake(root: Path, errors: list[str]) -> None:
    data = _load(root / SOURCE_INTAKE_PATH, errors, "source intake")
    if not isinstance(data, dict):
        return
    source = data.get("source_package", {})
    expected = {
        "package_id": SOURCE_PACKAGE_ID,
        "zip_sha256": SOURCE_ZIP_SHA256,
        "source_manifest_file_sha256": SOURCE_MANIFEST_FILE_SHA256,
        "metadata_declared_manifest_sha256": SOURCE_METADATA_MANIFEST_SHA256,
        "integrity_defect": SOURCE_INTEGRITY_DEFECT,
        "defect_disposition": "PRESERVED_NOT_REPAIRED",
        "repository_copy": "FORBIDDEN",
        "manifest_check": "26_OF_26_PASS",
    }
    for field, value in expected.items():
        if not isinstance(source, dict) or source.get(field) != value:
            errors.append(f"source intake {field} drift")
    if source.get("source_manifest_file_sha256") == source.get("metadata_declared_manifest_sha256"):
        errors.append("source circular-manifest defect was incorrectly repaired")
    files = data.get("source_files")
    if not isinstance(files, list) or len(files) != 26:
        errors.append("source intake must preserve exactly 26 source manifest entries")
    elif len({item.get("path") for item in files if isinstance(item, dict)}) != 26:
        errors.append("source intake source file paths are duplicated")
    copied_zips = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "governance/story-construction").rglob("*.zip")
    )
    if copied_zips:
        errors.append(f"Owner source ZIP must not be committed: {copied_zips}")


def _check_decisions_and_traceability(root: Path, errors: list[str]) -> None:
    decisions = _load(root / DECISIONS_PATH, errors, "Q001-Q130 register")
    trace = _load(root / TRACEABILITY_PATH, errors, "Q001-Q130 traceability")
    if not isinstance(decisions, dict) or not isinstance(trace, dict):
        return
    if decisions.get("source_status") != "FROZEN_BY_OWNER_QA_BOUND_TO_REPOSITORY":
        errors.append("Q001-Q130 repository binding is not active/bound")
    records = decisions.get("decisions")
    entries = trace.get("entries")
    if not isinstance(records, list) or not isinstance(entries, list):
        errors.append("Q001-Q130 decisions and trace entries must be arrays")
        return
    expected_ids = expected_question_ids()
    ids = [record.get("source_question_id") for record in records if isinstance(record, dict)]
    trace_ids = [entry.get("source_question_id") for entry in entries if isinstance(entry, dict)]
    if len(records) != 130 or decisions.get("decision_count") != 130 or ids != expected_ids:
        errors.append("Q001-Q130 installed decision identity/count/order drift")
    if len(entries) != 130 or trace.get("entry_count") != 130 or trace_ids != expected_ids:
        errors.append("Q001-Q130 bidirectional trace identity/count/order drift")
    if len(ids) != len(set(ids)) or len(trace_ids) != len(set(trace_ids)):
        errors.append("Q001-Q130 duplicate identity detected")
    expected_record_keys = {
        "source_question_id",
        "owner_answer",
        "decision_status",
        "source_package",
        "change_set_id",
        "human_source_ref",
        "machine_source_ref",
        "trace_refs",
    }
    for index, (record, entry) in enumerate(zip(records, entries)):
        if not isinstance(record, dict) or not isinstance(entry, dict):
            errors.append(f"Q{index+1:03d}: record/trace must be objects")
            continue
        if set(record) != expected_record_keys:
            errors.append(f"{record.get('source_question_id')}: decision record is not closed")
        if set(record.get("owner_answer", {})) != {"option", "title", "statement"}:
            errors.append(f"{record.get('source_question_id')}: owner answer fields drift")
        if record.get("decision_status") != "FROZEN_BY_OWNER_QA":
            errors.append(f"{record.get('source_question_id')}: owner QA status drift")
        if record.get("source_package") != SOURCE_PACKAGE_ID or record.get("change_set_id") != CHANGE_SET_ID:
            errors.append(f"{record.get('source_question_id')}: source/change-set binding drift")
        if entry.get("owner_answer_sha256") != canonical_sha256(record.get("owner_answer")):
            errors.append(f"{record.get('source_question_id')}: owner answer trace hash mismatch")
        expected_pointer = f"governance/story-construction/decisions.q001-q130.yaml#/decisions/{index}"
        if entry.get("installed_record_ref") != expected_pointer:
            errors.append(f"{record.get('source_question_id')}: forward trace pointer mismatch")
        if entry.get("reverse_lookup_key") != record.get("source_question_id"):
            errors.append(f"{record.get('source_question_id')}: reverse trace pointer mismatch")


def _check_authority_and_supersession(root: Path, errors: list[str]) -> None:
    overlay = _load(root / AUTHORITY_OVERLAY_PATH, errors, "authority overlay")
    registry = _load(root / CANON_REGISTRY_PATH, errors, "canon registry")
    supersession = _load(root / SUPERSESSION_PATH, errors, "supersession manifest")
    if isinstance(overlay, dict):
        if overlay.get("authority_scope") != "CONSTRUCTION_GOVERNANCE_ONLY" or overlay.get("r2_canon_precedence") != "HIGHER":
            errors.append("Story Construction authority precedence drift")
        if set(overlay.get("forbidden_definitions", [])) != {
            "WORLD_TRUTH","RULE_TRUTH","STORY_TRUTH","BOSS_TRUTH","ENDING_TRUTH","FORMAL_REGION_CONTENT"
        }:
            errors.append("Story Construction forbidden truth-definition boundary drift")
        roles = overlay.get("roles", {})
        if roles.get("opencode") != ["LUA_GAME_SCRIPTING_ONLY"]:
            errors.append("OpenCode script-only role was not preserved")
        if roles.get("deepseek_harness") != ["OFFICIAL_LITERARY_TEXT_WORKER"]:
            errors.append("DeepSeek literary worker role drift")
        hierarchy = overlay.get("hierarchy", [])
        story_layer = next(
            (
                item
                for item in hierarchy
                if isinstance(item, dict)
                and item.get("authority") == "STORY_CONSTRUCTION_GOVERNANCE"
            ),
            {},
        )
        if overlay.get("story_construction_governance_status") != "ACTIVE" or story_layer.get("status") != "ACTIVE":
            errors.append("active authority overlay still represents pending governance")
        if overlay.get("activation_state") != {
            "tracked_target_state": "TRACKED_TARGET_STATE_ACTIVE",
            "authoritative_activation_effective": False,
            "required_external_proofs": [
                "ACTIVATION_SPECIFIC_OWNER_FULL_HASH_APPROVAL",
                "PASS_FIXED_ACTIVATION_CANDIDATE_ACCEPTED",
                "VALID_DETACHED_ACCEPTED_ACTIVATION_ENVELOPE_TAG",
                "FINAL_FAST_FORWARD_INTEGRATION",
            ],
        }:
            errors.append("authority overlay activation proof separation drift")
    if isinstance(registry, dict):
        if registry.get("registry_kind") != "INDEX_GOVERNANCE_VALIDATION_LAYER" or registry.get("parallel_authoring_root") is not False:
            errors.append("Canon Registry must be an index layer, not a parallel root")
        paths = registry.get("authoritative_source_paths", [])
        if not isinstance(paths, list) or paths != sorted(paths):
            errors.append("Canon Registry sources must be explicit and lexically ordered")
        elif any(not (path.startswith("authoring/") or path == "governance/r2/decisions.r2.yaml") for path in paths):
            errors.append("Canon Registry points outside existing R2/authoring authority")
        if registry.get("framework_status") != "ACTIVE":
            errors.append("active Canon Registry still represents candidate framework")
    if isinstance(supersession, dict):
        expected_effective = {
            "effective_candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
            "effective_candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
            "effective_state": "ACTIVE",
            "release": "NOT_RELEASED",
        }
        for field, value in expected_effective.items():
            if supersession.get(field) != value:
                errors.append(f"supersession active binding drift: {field}")
        discovery = supersession.get("discovery_binding", {})
        if discovery.get("reading_map_digest") != "95a9774e317b5aebcc8bad50849c66b2d7cf7882c7c0446dc67738937645cb5e" or discovery.get("evidence_set_digest") != "9a112d9e805c58f3766b559c3a8122fe3cee80264e3399ad58c845427c11f6ef":
            errors.append("supersession discovery binding drift")
        entries = supersession.get("entries", [])
        by_path = {entry.get("predecessor_path"): entry for entry in entries if isinstance(entry, dict)}
        if set(by_path) != set(BASELINE_PREDECESSOR_HASHES):
            errors.append("supersession manifest predecessor set incomplete")
        for path, digest in BASELINE_PREDECESSOR_HASHES.items():
            entry = by_path.get(path, {})
            required = {"predecessor_id","predecessor_path","predecessor_section","predecessor_sha256","old_authority","new_authority","disposition","retained_scope","removed_scope","replacement","change_set_id","candidate_binding"}
            if set(entry) != required:
                errors.append(f"supersession entry is incomplete: {path}")
                continue
            if entry.get("predecessor_sha256") != digest:
                errors.append(f"supersession baseline hash drift: {path}")
            if entry.get("disposition") != EXPECTED_SUPERSESSION_DISPOSITIONS[path]:
                errors.append(f"supersession disposition drift: {path}")
            binding = entry.get("candidate_binding", {})
            if binding != {"strategy":"EXACT_HEAD_AT_VALIDATION","effective_candidate_commit":None}:
                errors.append(f"supersession candidate binding is not pending/exact: {path}")
        story_update = by_path.get(".codex/STORY_UPDATE_PROMPT.md", {})
        if set(story_update.get("removed_scope", [])) != {
            "LITERARY_TASK_ISSUANCE",
            "AUTHORING_EXECUTION",
            "ORACLE_AUTHORITY",
            "RELEASE_AUTHORITY",
        }:
            errors.append("old Story Update oracle/release authority was not removed")
        prompt_usage = by_path.get("docs/operations/PROMPT_USAGE.md", {})
        if "OLD_STORY_EXECUTION_ROUTE" not in prompt_usage.get("removed_scope", []):
            errors.append("PROMPT_USAGE old story execution route was not removed")
        aliases = supersession.get("external_aliases", [])
        if aliases != [{"alias":"rules_residue_launch_content_construction_v1_0","disposition":"HISTORICAL_ALIAS_ONLY","repository_path":None,"sha256":None}]:
            errors.append("historical external alias path/hash was fabricated or drifted")


def _git_output(root: Path, args: list[str], errors: list[str], label: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        errors.append(f"{label}: git command failed: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def _git_show_bytes(
    root: Path, revision: str, relative: Path, errors: list[str], label: str
) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{relative.as_posix()}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        errors.append(f"{label}: cannot read fixed Git object")
        return None
    return result.stdout


def _git_show_json(
    root: Path, revision: str, relative: Path, errors: list[str], label: str
) -> Any | None:
    data = _git_show_bytes(root, revision, relative, errors, label)
    if data is None:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: fixed Git object is invalid JSON: {exc}")
        return None


def _check_implementation_candidate_identity(root: Path, errors: list[str]) -> None:
    tree = _git_output(
        root,
        ["rev-parse", f"{IMPLEMENTATION_CANDIDATE_COMMIT}^{{tree}}"],
        errors,
        "implementation candidate tree",
    )
    parent = _git_output(
        root,
        ["rev-parse", f"{IMPLEMENTATION_CANDIDATE_COMMIT}^"],
        errors,
        "implementation candidate parent",
    )
    count = _git_output(
        root,
        [
            "rev-list",
            "--count",
            f"{IMPLEMENTATION_CANDIDATE_PARENT}..{IMPLEMENTATION_CANDIDATE_COMMIT}",
        ],
        errors,
        "implementation candidate lineage",
    )
    if tree is not None and tree != IMPLEMENTATION_CANDIDATE_TREE:
        errors.append("accepted implementation candidate tree identity mismatch")
    if parent is not None and parent != IMPLEMENTATION_CANDIDATE_PARENT:
        errors.append("accepted implementation candidate parent identity mismatch")
    if count is not None and count != "1":
        errors.append("accepted implementation candidate lineage is not exactly one commit")


def validate_activation_changed_paths(changed: set[str]) -> list[str]:
    errors: list[str] = []
    outside = sorted(changed - APPROVED_ACTIVATION_PATHS)
    if outside:
        errors.append(f"activation changed paths exceed approved scope: {outside}")
    forbidden_prefixes = (
        "game-package/",
        "authoring/",
        "governance/r2/",
        "schemas/r2/",
        ".codex/state/",
        ".codex/plans/m2-vertical-slice/",
        "docs/implementation/m2/",
        "reports/m2/",
        "tests/m2/probes/",
        "TRPG_PLATFORM/",
    )
    forbidden_exact = {
        "governance/decisions.json",
        SOURCE_INTAKE_PATH.as_posix(),
        TRACEABILITY_PATH.as_posix(),
        CANONICAL_DECISIONS_PATH.as_posix(),
        RECEIPT_PATH.as_posix(),
        "governance/story-construction/approvals/candidate-approval.template.json",
        "schemas/story-construction/change-set-v1.schema.json",
        "schemas/story-construction/installation-receipt-v1.schema.json",
        "schemas/story-construction/candidate-approval-v1.schema.json",
    }
    forbidden = sorted(
        path
        for path in changed
        if path in forbidden_exact or path.startswith(forbidden_prefixes)
    )
    if forbidden:
        errors.append(f"activation modified forbidden preservation paths: {forbidden}")
    return errors


def _check_activation_git_scope(root: Path, errors: list[str]) -> None:
    precontent_change_set = root / "governance/story-construction/change-sets/CS-SCG-PRECONTENT-READINESS-R1-001.yaml"
    if precontent_change_set.is_file():
        try:
            changed = precontent_changed_paths(root)
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(f"pre-content changed paths: {exc}")
            return
        outside = sorted(changed - set(PRECONTENT_ALLOWLIST))
        if outside:
            errors.append(f"pre-content changed paths exceed approved scope: {outside}")
        head = _git_output(root, ["rev-parse", "HEAD"], errors, "pre-content HEAD")
        if head is not None and head != PRECONTENT_BASE_COMMIT:
            parent = _git_output(root, ["rev-parse", "HEAD^"], errors, "pre-content parent")
            count = _git_output(
                root,
                ["rev-list", "--count", f"{PRECONTENT_BASE_COMMIT}..HEAD"],
                errors,
                "pre-content lineage count",
            )
            if parent != PRECONTENT_BASE_COMMIT or count != "1":
                errors.append("pre-content lineage is non-FF, rebased, amended, or multi-commit")
        return
    changed_output = _git_output(
        root,
        ["diff", "--name-only", IMPLEMENTATION_CANDIDATE_COMMIT, "--"],
        errors,
        "activation changed paths",
    )
    status_output = _git_output(
        root,
        ["status", "--porcelain", "--untracked-files=all"],
        errors,
        "activation worktree status",
    )
    changed = set(changed_output.splitlines()) if changed_output else set()
    if status_output:
        for line in status_output.splitlines():
            if line.startswith("?? "):
                changed.add(line[3:])
    errors.extend(validate_activation_changed_paths(changed))
    head = _git_output(root, ["rev-parse", "HEAD"], errors, "activation HEAD")
    if head is not None and head != IMPLEMENTATION_CANDIDATE_COMMIT:
        parent = _git_output(root, ["rev-parse", "HEAD^"], errors, "activation parent")
        count = _git_output(
            root,
            ["rev-list", "--count", f"{IMPLEMENTATION_CANDIDATE_COMMIT}..HEAD"],
            errors,
            "activation lineage count",
        )
        if parent != IMPLEMENTATION_CANDIDATE_COMMIT or count != "1":
            errors.append("activation lineage is non-FF, rebased, amended, or multi-commit")


def _check_derived_and_instances(
    root: Path,
    schemas: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    try:
        expected = derive_installation(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"cannot derive deterministic Story Construction installation: {exc}")
        return
    if expected.get("tracked_target_state_active") is not True:
        errors.append("repository does not express TRACKED_TARGET_STATE_ACTIVE")
    pairs = (
        (CANONICAL_DECISIONS_PATH, expected["canonical_decisions"]),
        (CANONICAL_MANIFEST_PATH, expected["canonical_manifest"]),
        (FINAL_RECEIPT_PATH, expected["receipt"]),
    )
    for relative, value in pairs:
        actual = _load(root / relative, errors, relative.as_posix())
        if actual is not None and actual != value:
            errors.append(f"derived artifact is stale or non-deterministic: {relative.as_posix()}")
    manifest = _load(root / CANONICAL_MANIFEST_PATH, errors, "canonical manifest")
    pending_receipt = _load(root / RECEIPT_PATH, errors, "pending installation receipt")
    receipt = _load(root / FINAL_RECEIPT_PATH, errors, "final inner receipt")
    change_set = _load(root / CHANGE_SET_PATH, errors, "change set")
    consumption = _load(root / APPROVAL_CONSUMPTION_PATH, errors, "implementation approval consumption")
    approval = _load(root / "governance/story-construction/approvals/candidate-approval.template.json", errors, "candidate approval template")
    fixture = _load(
        root / "tests/fixtures/story-construction/lifecycle-state-v1.json",
        errors,
        "lifecycle state fixture",
    )
    if isinstance(manifest, dict):
        _schema_instance(manifest, schemas.get("canonical-manifest-v1.schema.json"), "canonical manifest", errors)
        errors.extend(validate_canonical_manifest_binding(manifest))
        if manifest.get("canon", {}).get("base_canon_hash") != BASE_CANON_HASH or manifest.get("canon", {}).get("proposed_canon_hash") != BASE_CANON_HASH:
            errors.append("Canon hash invariant drift during activation")
        if len(manifest.get("records", [])) != 135:
            errors.append("active canonical manifest must contain exactly 135 Merkle leaves")
    if isinstance(pending_receipt, dict):
        _schema_instance(
            pending_receipt,
            schemas.get("installation-receipt-v1.schema.json"),
            "immutable pending installation receipt",
            errors,
        )
        errors.extend(validate_pending_receipt_binding(pending_receipt))
        if pending_receipt.get("payload_hash") != "5d348a937de063ba66922258c54a8bfc4a83fc3539d559916afb7f6a9bb2fb9e":
            errors.append("immutable implementation pending receipt payload hash drift")
    if isinstance(receipt, dict):
        _schema_instance(
            receipt,
            schemas.get("installation-receipt-v2.schema.json"),
            "final inner receipt",
            errors,
        )
        errors.extend(
            validate_final_receipt_binding(
                receipt,
                expected_new_merkle_root=expected["merkle_root"],
                expected_consumption_sha256=file_sha256(root / APPROVAL_CONSUMPTION_PATH),
            )
        )
    if isinstance(consumption, dict):
        _schema_instance(
            consumption,
            schemas.get("owner-approval-consumption-v1.schema.json"),
            "implementation approval consumption",
            errors,
        )
        errors.extend(validate_implementation_approval_consumption(consumption))
    if isinstance(change_set, dict):
        _schema_instance(change_set, schemas.get("change-set-v2.schema.json"), "active change set", errors)
        errors.extend(validate_lifecycle_state(change_set))
        expected_hashes = {
            "base_canon_hash": expected["base_canon_hash"],
            "proposed_canon_hash": expected["proposed_canon_hash"],
            "merkle_root": expected["merkle_root"],
            "previous_governance_merkle_root": PREVIOUS_GOVERNANCE_MERKLE_ROOT,
            "final_inner_receipt_payload_hash": expected["receipt_payload_hash"],
            "approval_consumption_record_sha256": file_sha256(
                root / APPROVAL_CONSUMPTION_PATH
            ),
        }
        for field, value in expected_hashes.items():
            if change_set.get(field) != value:
                errors.append(f"change set {field} is stale")
        if change_set.get("implementation_candidate_binding") != {
            "strategy": "EXACT_ACCEPTED_IMPLEMENTATION_CANDIDATE",
            "candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
            "candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        }:
            errors.append("active Change Set implementation candidate binding drift")
        if change_set.get("merkle_transition") != expected.get("merkle_transition"):
            errors.append("active Change Set Merkle transition is stale")
    if isinstance(approval, dict):
        _schema_instance(approval, schemas.get("candidate-approval-v1.schema.json"), "candidate approval template", errors)
    if isinstance(fixture, dict):
        candidate = fixture.get("candidate_change_set")
        _schema_instance(
            candidate,
            schemas.get("change-set-v1.schema.json"),
            "v1 Candidate fixture",
            errors,
        )
        errors.extend(f"v1 Candidate fixture: {item}" for item in validate_lifecycle_state(candidate))
        active_fixture_path = fixture.get("active_change_set_fixture_path")
        if active_fixture_path != CHANGE_SET_PATH.as_posix():
            errors.append("v2 Active fixture path drift")
        else:
            _schema_instance(
                change_set,
                schemas.get("change-set-v2.schema.json"),
                "v2 Active fixture",
                errors,
            )
            errors.extend(
                f"v2 Active fixture: {item}"
                for item in validate_lifecycle_state(change_set)
            )
        mixed = fixture.get("invalid_mixed_states", [])
        if not isinstance(mixed, list) or len(mixed) < 3:
            errors.append("lifecycle fixture must contain Candidate/Active/RELEASED mixed attacks")
        else:
            for index, state in enumerate(mixed):
                if not validate_lifecycle_state(state):
                    errors.append(f"mixed lifecycle fixture unexpectedly accepted: {index}")

    previous_manifest = _git_show_json(
        root,
        IMPLEMENTATION_CANDIDATE_COMMIT,
        CANONICAL_MANIFEST_PATH,
        errors,
        "implementation canonical manifest",
    )
    if isinstance(previous_manifest, dict) and isinstance(manifest, dict) and isinstance(change_set, dict):
        errors.extend(
            validate_merkle_transition(
                previous_manifest,
                manifest,
                change_set.get("merkle_transition"),
            )
        )

    candidate_decision_bytes = _git_show_bytes(
        root,
        IMPLEMENTATION_CANDIDATE_COMMIT,
        CANONICAL_DECISIONS_PATH,
        errors,
        "implementation canonical decisions",
    )
    if candidate_decision_bytes is not None:
        current_bytes = (root / CANONICAL_DECISIONS_PATH).read_bytes()
        if current_bytes != candidate_decision_bytes:
            errors.append("canonical Q001-Q130 decision bytes changed during activation")
        errors.extend(
            validate_canon_hash_invariants(
                base_canon_hash=expected["base_canon_hash"],
                proposed_canon_hash=expected["proposed_canon_hash"],
                canonical_decisions_hash=hashlib.sha256(current_bytes).hexdigest(),
            )
        )
    for immutable in (SOURCE_INTAKE_PATH, TRACEABILITY_PATH, RECEIPT_PATH):
        original = _git_show_bytes(
            root,
            IMPLEMENTATION_CANDIDATE_COMMIT,
            immutable,
            errors,
            f"immutable activation input {immutable.as_posix()}",
        )
        if original is not None and (root / immutable).read_bytes() != original:
            errors.append(f"immutable activation input drift: {immutable.as_posix()}")

    effective, _proof_errors = authoritative_activation_status(
        tracked_target_state_active=tracked_target_state_active(root),
        activation_approval=None,
        expected_activation_approval={},
        envelope=None,
        expected_envelope={},
        integration=None,
    )
    if effective:
        errors.append("tracked ACTIVE became authoritative without external activation proof")


def _check_routes_and_predecessors(root: Path, errors: list[str]) -> None:
    for relative, (route_id, mode) in ROUTE_IDENTITIES.items():
        try:
            request = read_json(root / relative)
            validate_request(request)
            reading_map = generate_reading_map(request, repo_root=root)
        except (OSError, json.JSONDecodeError, RouteError) as exc:
            errors.append(f"{relative}: invalid M3 route: {exc}")
            continue
        errors.extend(
            f"{relative}: {issue}"
            for issue in validate_m3_route_request(request, route_id, mode)
        )
        selected = {document.get("path") for document in request.get("documents", [])}
        selected_map = {document.get("path") for document in reading_map.get("documents", [])}
        old = sorted((selected | selected_map) & OLD_PREDECESSORS)
        if old:
            errors.append(f"{relative}: old predecessor selected as authority: {old}")
        if reading_map.get("context_budget", {}).get("ratio", 1) > 0.55:
            errors.append(f"{relative}: required route ratio exceeds 0.55")

    required_prompt_markers = {
        ".codex/STORY_ARCHITECTURE_BUILD_PROMPT.md": ["HISTORICAL_ONLY", "EXECUTION_AUTHORITY=NONE"],
        ".codex/STORY_UPDATE_PROMPT.md": ["SUPERSEDED", "LITERARY_TASK_ISSUANCE=FORBIDDEN"],
        "docs/operations/PROMPT_USAGE.md": ["M3-STORY-CONSTRUCTION", "STORY_UPDATE_PROMPT.md` is historical"],
        ".codex/BUILD_AND_INTEGRATION_PROMPT.md": ["M3 Story Construction", "must not invoke `.codex/STORY_UPDATE_PROMPT.md`"],
        ".grok/ART_TASK_PROMPT.md": ["VALIDATED_VISUAL_ORDER_PACKAGE", "RAW_ART_REQUEST=NOT_PRODUCTION_AUTHORITY"],
    }
    for relative, markers in required_prompt_markers.items():
        text = (root / relative).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative}: missing supersession marker {marker!r}")


def _check_role_migration(root: Path, errors: list[str]) -> None:
    decisions = read_json(root / "governance/decisions.json")
    by_id = {item.get("id"): item for item in decisions.get("decisions", [])}
    revision = by_id.get("RR-D024")
    if not isinstance(revision, dict) or revision.get("status") != "ACCEPTED" or revision.get("supersedes") != ["RR-D023"]:
        errors.append("RR-D023 role migration revision RR-D024 is missing or invalid")
    schema = read_json(root / "workflow/task-packet.schema.json")
    versions = set(schema.get("properties", {}).get("schema_version", {}).get("enum", []))
    owners = set(schema.get("properties", {}).get("owner", {}).get("enum", []))
    types = set(schema.get("properties", {}).get("task_type", {}).get("enum", []))
    if versions != {"rules-residue.task-packet/1.0","rules-residue.task-packet/1.1"}:
        errors.append("Task Packet compatible minor version adapter drift")
    if "deepseek_harness" not in owners or "literary" not in types:
        errors.append("Task Packet cannot express DeepSeek literary tasks")
    for relative in ("workflow/examples/m3-literary-task-packet.json", "workflow/examples/m3-visual-order-task-packet.json"):
        packet = read_json(root / relative)
        for issue in validate(packet, schema):
            errors.append(f"{relative}: {issue}")
        errors.extend(f"{relative}: {issue}" for issue in validate_task_packet_pairing(packet))


def _check_m2_preservation(root: Path, errors: list[str]) -> None:
    milestone = read_json(root / ".codex/state/MILESTONE_PLAN.yaml")
    projection = milestone.get("active_plan", {}).get("lifecycle_projection", {})
    expected = {
        "state":"ACCEPTED_WITH_DOWNSTREAM_BLOCKERS",
        "effective_R2-INT-010":"RESOLVED_ADAPTER",
        "formal_B002":False,
        "formal_B009":False,
        "blocking_ids":EXPECTED_M2_BLOCKERS,
        "global_active_WIP":0,
    }
    for field, value in expected.items():
        if projection.get(field) != value:
            errors.append(f"M2 preservation drift: {field}")
    b002 = projection.get("M2-B002", {})
    if b002 != {"state":"PLANNED","implementation_state":"NOT_STARTED","ready":"NO"}:
        errors.append("M2 preservation drift: M2-B002")
    if milestone.get("state") != "ACCEPTED" or milestone.get("batch_id") != "M2-B001":
        errors.append("M2-B001 lifecycle acceptance drift")
    if milestone.get("active_plan", {}).get("next_allowed_action") != "PLAN_REMAINING_M2_B002_BLOCKERS_R2_INT_011_R2_INT_012_DEFER_R2_C14_001":
        errors.append("M2 pending action drift")


def _check_package_and_roots(root: Path, errors: list[str]) -> None:
    runtime_paths = set(runtime_relative_paths(root / "game-package"))
    leaked = sorted(
        path for path in runtime_paths
        if any(token in path.lower() for token in ("story-construction", "literary-order", "visual-order", "candidate-approval", "installation-receipt"))
    )
    if leaked:
        errors.append(f"governance/order/approval artifacts enter runtime package: {leaked}")
    forbidden_roots = ["canon", "story-construction", "story-governance"]
    present = [name for name in forbidden_roots if (root / name).exists()]
    if present:
        errors.append(f"parallel Canon/authoring root detected: {present}")
    if any((root / path).exists() for path in ("governance/story-construction/orders", "governance/story-construction/regions")):
        errors.append("installation must not issue orders or create formal Region Dossiers")


def collect_errors(project_root: Path = PROJECT_ROOT) -> list[str]:
    root = project_root.resolve()
    errors: list[str] = []
    _check_required_files(root, errors)
    if errors:
        return errors
    _check_implementation_candidate_identity(root, errors)
    _check_activation_git_scope(root, errors)
    _check_human_docs(root, errors)
    schemas = _check_schemas(root, errors)
    _check_source_intake(root, errors)
    _check_decisions_and_traceability(root, errors)
    _check_authority_and_supersession(root, errors)
    _check_derived_and_instances(root, schemas, errors)
    _check_routes_and_predecessors(root, errors)
    _check_role_migration(root, errors)
    _check_m2_preservation(root, errors)
    _check_package_and_roots(root, errors)
    errors.extend(
        f"Pre-Content Readiness: {error}"
        for error in validate_precontent_readiness(root, check_git=False)
    )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Story Construction Governance")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--write-derived", action="store_true")
    parser.add_argument("--print-hashes", action="store_true")
    args = parser.parse_args(argv)
    if args.write_derived:
        derived = write_derived_installation(args.project_root.resolve())
    else:
        try:
            derived = derive_installation(args.project_root.resolve())
        except Exception as exc:  # reported again with structured validation context
            derived = None
            print(f"STORY_CONSTRUCTION_DERIVATION: FAIL: {exc}")
    errors = collect_errors(args.project_root)
    if errors:
        print("STORY_CONSTRUCTION_GOVERNANCE: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("STORY_CONSTRUCTION_GOVERNANCE: PASS")
    print("- authority precedence and construction-only scope: PASS")
    print("- Q001-Q130 source/traceability and source defect preservation: PASS")
    print("- schemas, role/order gates, supersession, routes, and M2 preservation: PASS")
    print("- canonical manifest, approval consumption, inner receipt, and package boundary: PASS")
    print("- TRACKED_TARGET_STATE_ACTIVE=true")
    print("- AUTHORITATIVE_ACTIVATION_EFFECTIVE=false (external activation proof absent)")
    if args.print_hashes and derived is not None:
        for field in ("base_canon_hash","proposed_canon_hash","merkle_root","receipt_payload_hash"):
            print(f"{field}={derived[field]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
