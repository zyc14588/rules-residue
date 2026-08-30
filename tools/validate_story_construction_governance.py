from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.codex_route import RouteError, generate_reading_map, validate_request
from tools.lib.common import PROJECT_ROOT, read_json, runtime_relative_paths
from tools.lib.schema_subset import validate
from tools.story_construction import (
    AUTHORITY_OVERLAY_PATH,
    BASE_COMMIT,
    BASE_TREE,
    CANONICAL_DECISIONS_PATH,
    CANONICAL_MANIFEST_PATH,
    CANON_REGISTRY_PATH,
    CHANGE_SET_ID,
    CHANGE_SET_PATH,
    DECISIONS_PATH,
    RECEIPT_PATH,
    SOURCE_INTAKE_PATH,
    SOURCE_INTEGRITY_DEFECT,
    SOURCE_MANIFEST_FILE_SHA256,
    SOURCE_METADATA_MANIFEST_SHA256,
    SOURCE_PACKAGE_ID,
    SOURCE_ZIP_SHA256,
    SUPERSESSION_PATH,
    TRACEABILITY_PATH,
    canonical_decision_document,
    canonical_sha256,
    derive_installation,
    expected_question_ids,
    read_json_document,
    validate_task_packet_pairing,
    validate_m3_route_request,
    validate_canonical_manifest_binding,
    validate_pending_receipt_binding,
    write_derived_installation,
)


SCHEMA_ROOT = Path("schemas/story-construction")
SCHEMA_FILES = {
    "canon-record-v1.schema.json",
    "reveal-contract-v1.schema.json",
    "canon-envelope-v1.schema.json",
    "change-set-v1.schema.json",
    "region-dossier-v1.schema.json",
    "text-order-v1.schema.json",
    "visual-order-v1.schema.json",
    "dab-v1.schema.json",
    "region-acceptance-v1.schema.json",
    "canonical-manifest-v1.schema.json",
    "installation-receipt-v1.schema.json",
    "candidate-approval-v1.schema.json",
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
        "governance/story-construction/approvals/candidate-approval.template.json",
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
OLD_PREDECESSORS = {
    ".codex/STORY_ARCHITECTURE_BUILD_PROMPT.md",
    ".codex/STORY_UPDATE_PROMPT.md",
    "docs/operations/PROMPT_USAGE.md",
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
        if not isinstance(version, str) or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
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
    if isinstance(registry, dict):
        if registry.get("registry_kind") != "INDEX_GOVERNANCE_VALIDATION_LAYER" or registry.get("parallel_authoring_root") is not False:
            errors.append("Canon Registry must be an index layer, not a parallel root")
        paths = registry.get("authoritative_source_paths", [])
        if not isinstance(paths, list) or paths != sorted(paths):
            errors.append("Canon Registry sources must be explicit and lexically ordered")
        elif any(not (path.startswith("authoring/") or path == "governance/r2/decisions.r2.yaml") for path in paths):
            errors.append("Canon Registry points outside existing R2/authoring authority")
    if isinstance(supersession, dict):
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
    pairs = (
        (CANONICAL_DECISIONS_PATH, expected["canonical_decisions"]),
        (CANONICAL_MANIFEST_PATH, expected["canonical_manifest"]),
        (RECEIPT_PATH, expected["receipt"]),
    )
    for relative, value in pairs:
        actual = _load(root / relative, errors, relative.as_posix())
        if actual is not None and actual != value:
            errors.append(f"derived artifact is stale or non-deterministic: {relative.as_posix()}")
    manifest = _load(root / CANONICAL_MANIFEST_PATH, errors, "canonical manifest")
    receipt = _load(root / RECEIPT_PATH, errors, "installation receipt")
    change_set = _load(root / CHANGE_SET_PATH, errors, "change set")
    approval = _load(root / "governance/story-construction/approvals/candidate-approval.template.json", errors, "candidate approval template")
    if isinstance(manifest, dict):
        _schema_instance(manifest, schemas.get("canonical-manifest-v1.schema.json"), "canonical manifest", errors)
        errors.extend(validate_canonical_manifest_binding(manifest))
    if isinstance(receipt, dict):
        _schema_instance(receipt, schemas.get("installation-receipt-v1.schema.json"), "installation receipt", errors)
        errors.extend(validate_pending_receipt_binding(receipt))
    if isinstance(change_set, dict):
        _schema_instance(change_set, schemas.get("change-set-v1.schema.json"), "change set", errors)
        expected_hashes = {
            "base_canon_hash": expected["base_canon_hash"],
            "proposed_canon_hash": expected["proposed_canon_hash"],
            "merkle_root": expected["merkle_root"],
            "receipt_candidate_payload_hash": expected["receipt_payload_hash"],
        }
        for field, value in expected_hashes.items():
            if change_set.get(field) != value:
                errors.append(f"change set {field} is stale")
        if change_set.get("candidate_binding") != {"strategy":"EXACT_HEAD_AT_VALIDATION","candidate_commit":None,"candidate_tree":None}:
            errors.append("tracked Change Set self-references/fabricates candidate identity")
        if change_set.get("approval_status") != "PENDING_OWNER_HASH_APPROVAL":
            errors.append("installation candidate approval must remain pending")
        if change_set.get("lifecycle_stage") != "CANDIDATE" or change_set.get("disposition") != "CANDIDATE_NOT_ACTIVE":
            errors.append("installation candidate was represented as active or outside CANDIDATE lifecycle")
    if isinstance(approval, dict):
        _schema_instance(approval, schemas.get("candidate-approval-v1.schema.json"), "candidate approval template", errors)


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
    print("- canonical manifest, detached receipt, and package boundary: PASS")
    if args.print_hashes and derived is not None:
        for field in ("base_canon_hash","proposed_canon_hash","merkle_root","receipt_payload_hash"):
            print(f"{field}={derived[field]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
