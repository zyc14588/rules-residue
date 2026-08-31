from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHANGE_SET_ID = "CS-R2-SC-GOV-INSTALL-001"
SOURCE_PACKAGE_ID = "RR-SC-GOV-V2-Q001-Q130"
SOURCE_ZIP_SHA256 = "158e6e82e50ae4a411b780e718f16353dd668b6f94320c685a95d20d766d0e36"
SOURCE_MANIFEST_FILE_SHA256 = "721ef281e1a25cbd85d4979264498e207582e1d8f43e01845ca7b8e9bbd1bc88"
SOURCE_METADATA_MANIFEST_SHA256 = "d705f9c4b650831ad5af8eac05549609e6e033dc6e435c1226885683eef694f4"
SOURCE_INTEGRITY_DEFECT = "CIRCULAR_MANIFEST_METADATA_BINDING"
BASE_COMMIT = "e90a717d3863e4fb0e5e1a0fcc01661f24d2157d"
BASE_TREE = "7a1ce74ad0b82c7c288b94c47c966028e916137d"
CANONICALIZATION_VERSION = "1.0.0"
IMPLEMENTATION_CANDIDATE_COMMIT = "7305a9decacf4a6361692fe9359a1afa96801722"
IMPLEMENTATION_CANDIDATE_TREE = "e5969a0464a7e73d7d1da546da83afea9015fdba"
IMPLEMENTATION_CANDIDATE_PARENT = BASE_COMMIT
IMPLEMENTATION_OWNER_APPROVAL_ID = (
    "OWNER-APPROVAL-R2-SC-GOV-INSTALL-001-CANDIDATE-7305A9DE-R1"
)
IMPLEMENTATION_OWNER_APPROVAL_TRANSPORT_SHA256 = (
    "87bc960d75b1fd38106ee4e545d4960c0e0d8751141ccfcaa126b30142236ed9"
)
IMPLEMENTATION_ACCEPT_TASK_ID = "R2-SC-GOV-INSTALL-001-ACCEPT-001"
IMPLEMENTATION_ACCEPT_RESULT = "PASS_FIXED_CANDIDATE_ACCEPTED"
IMPLEMENTATION_ACCEPT_ROUTE_DIGEST = (
    "706cd9195ef483ddc47a76774780059d46b24b813e948ab28b532a613e9f1cd6"
)
ACTIVATION_CLOSEOUT_TASK_ID = (
    "R2-SC-GOV-INSTALL-ACTIVATION-CLOSEOUT-IMPLEMENT-001"
)
BASE_CANON_HASH = "d7ceea75615b57970f3b9712b73ed4c9f65a9c4406c877e9013470cb53a6141a"
CANONICAL_DECISIONS_SHA256 = (
    "01fdebbd338a8abdbc0226d0290b1bc2b02366cb615a22182f0df0a5f75fa7b2"
)
PREVIOUS_GOVERNANCE_MERKLE_ROOT = (
    "5b9e417209beab3dc88ed305a79b8945512d4c0e842397e5494885ac4dd3a23e"
)
IMPLEMENTATION_RECEIPT_PAYLOAD_HASH = (
    "5d348a937de063ba66922258c54a8bfc4a83fc3539d559916afb7f6a9bb2fb9e"
)
PACKAGE_SHA256 = "29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314"
ACTIVATION_BINDING_STRATEGY = "DETACHED_ANNOTATED_TAG_EXACT_COMMIT_TREE"
ACTIVATION_CHANGED_LEAF_IDS = (
    "SCG-AUTHORITY-OVERLAY",
    "SCG-CANON-REGISTRY",
    "SCG-SUPERSESSION",
)
ACTIVATION_OLD_LEAF_HASHES = {
    "SCG-AUTHORITY-OVERLAY": "710f0f9a331158a6aca604385f0dd60d35e8d04e50c758933414e76cee3e6a26",
    "SCG-CANON-REGISTRY": "15fc4a3c2bc1a0e85f15070fdfa4c116e97360e08fb415ad3867bd577ee2130f",
    "SCG-SUPERSESSION": "61f4865b106bae72b3945e17234eb2d6ec0da6fc55527038c3ea9137d030d054",
}

DECISIONS_PATH = Path("governance/story-construction/decisions.q001-q130.yaml")
TRACEABILITY_PATH = Path("governance/story-construction/traceability.yaml")
SOURCE_INTAKE_PATH = Path("governance/story-construction/source-intake.yaml")
AUTHORITY_OVERLAY_PATH = Path("governance/story-construction/authority-overlay.yaml")
CANON_REGISTRY_PATH = Path("governance/story-construction/canon-registry.yaml")
SUPERSESSION_PATH = Path(
    "governance/story-construction/supersession/supersession-manifest.v1.yaml"
)
CHANGE_SET_PATH = Path(
    "governance/story-construction/change-sets/CS-R2-SC-GOV-INSTALL-001.yaml"
)
CANONICAL_DECISIONS_PATH = Path(
    "governance/story-construction/generated/decisions.q001-q130.canonical.json"
)
CANONICAL_MANIFEST_PATH = Path(
    "governance/story-construction/canonical-manifest.json"
)
RECEIPT_PATH = Path(
    "governance/story-construction/receipts/installation-receipt.pending.json"
)
FINAL_RECEIPT_PATH = Path(
    "governance/story-construction/receipts/installation-receipt.final.json"
)
APPROVAL_CONSUMPTION_PATH = Path(
    "governance/story-construction/approvals/"
    "OWNER-APPROVAL-R2-SC-GOV-INSTALL-001-CANDIDATE-7305A9DE-R1.consumption.json"
)

SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
HEX_40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
QUESTION_ID_PATTERN = re.compile(r"^Q(?:00[1-9]|0[1-9][0-9]|1[0-2][0-9]|130)$")

LITERARY_RETURN_PREFIX = "workflow/returns/literary/"
VISUAL_RETURN_PREFIX = "workflow/returns/visual/"
FORBIDDEN_WORKER_PREFIXES = (
    "authoring/",
    "docs/authority/",
    "docs/governance/",
    "governance/",
    "schemas/",
    "game-package/",
    ".codex/",
    ".opencode/",
    ".grok/",
    "tools/",
    "tests/",
    "TRPG_PLATFORM/",
)

FORBIDDEN_VISUAL_FACT_CLASSES = {
    "WORLD_TRUTH",
    "RULE_TRUTH",
    "STORY_TRUTH",
    "BOSS_TRUTH",
    "ENDING_TRUTH",
    "PUZZLE_ANSWER",
    "MECHANICAL_VALUE",
    "MAP_TOPOLOGY",
}

OLD_STORY_PREDECESSORS = {
    ".codex/STORY_ARCHITECTURE_BUILD_PROMPT.md",
    ".codex/STORY_UPDATE_PROMPT.md",
    "docs/operations/PROMPT_USAGE.md",
}


class StoryConstructionError(ValueError):
    """A deterministic Story Construction contract failure."""


def read_json_document(path: Path) -> Any:
    """Read JSON or JSON-compatible YAML using only the standard library."""

    return json.loads(path.read_text(encoding="utf-8"))


def _normalise(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StoryConstructionError("canonical JSON rejects non-finite numbers")
        if value == 0:
            return 0
        if value.is_integer():
            return int(value)
        return value
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    if isinstance(value, dict):
        normalised: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise StoryConstructionError("canonical JSON object keys must be strings")
            key = unicodedata.normalize("NFC", raw_key)
            if key in normalised:
                raise StoryConstructionError(f"canonical key collision after NFC: {key!r}")
            normalised[key] = _normalise(raw_value)
        return normalised
    raise StoryConstructionError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable UTF-8 RFC-8259 bytes with NFC strings and ordered keys."""

    return (
        json.dumps(
            _normalise(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_canon_hash_invariants(
    *,
    base_canon_hash: str,
    proposed_canon_hash: str,
    canonical_decisions_hash: str,
) -> list[str]:
    errors: list[str] = []
    if base_canon_hash != BASE_CANON_HASH:
        errors.append("base Canon hash drift")
    if proposed_canon_hash != BASE_CANON_HASH:
        errors.append("proposed Canon hash drift")
    if canonical_decisions_hash != CANONICAL_DECISIONS_SHA256:
        errors.append("canonical Q001-Q130 decisions hash drift")
    return errors


def expected_question_ids() -> list[str]:
    return [f"Q{index:03d}" for index in range(1, 131)]


def load_decision_register(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    value = read_json_document(project_root / DECISIONS_PATH)
    if not isinstance(value, dict):
        raise StoryConstructionError("decision register must be an object")
    return value


def canonical_decision_document(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    source = load_decision_register(project_root)
    decisions = source.get("decisions")
    if not isinstance(decisions, list):
        raise StoryConstructionError("decision register decisions must be an array")
    ordered = sorted(decisions, key=lambda item: item.get("source_question_id", ""))
    return {
        "schema_version": "rules-residue.story-construction.decisions/1.0.0",
        "canonicalization_version": CANONICALIZATION_VERSION,
        "authority_scope": "CONSTRUCTION_GOVERNANCE_ONLY",
        "r2_canon_precedence": "HIGHER",
        "source_package": SOURCE_PACKAGE_ID,
        "change_set_id": CHANGE_SET_ID,
        "decision_count": len(ordered),
        "decisions": ordered,
    }


def _canonical_source_index(project_root: Path) -> tuple[dict[str, Any], str]:
    registry = read_json_document(project_root / CANON_REGISTRY_PATH)
    source_paths = registry.get("authoritative_source_paths")
    if not isinstance(source_paths, list) or not source_paths:
        raise StoryConstructionError("canon registry must list authoritative_source_paths")
    if source_paths != sorted(source_paths):
        raise StoryConstructionError("canon source paths must use stable lexical ordering")
    records: list[dict[str, str]] = []
    for relative in source_paths:
        if not isinstance(relative, str):
            raise StoryConstructionError("canon source path must be a string")
        path = project_root / relative
        if not path.is_file():
            raise StoryConstructionError(f"canon source is missing: {relative}")
        text = path.read_text(encoding="utf-8")
        nfc_bytes = unicodedata.normalize("NFC", text).encode("utf-8")
        records.append(
            {
                "path": relative,
                "source_sha256": file_sha256(path),
                "nfc_utf8_sha256": hashlib.sha256(nfc_bytes).hexdigest(),
            }
        )
    document = {
        "schema_version": "rules-residue.story-construction.canon-source-index/1.0.0",
        "canonicalization_version": CANONICALIZATION_VERSION,
        "authority_scope": "R2_CANON_INDEX_ONLY",
        "sources": records,
    }
    return document, canonical_sha256(document)


def merkle_root(leaves: Iterable[tuple[str, str]]) -> str:
    ordered = sorted(leaves, key=lambda item: item[0])
    level = [bytes.fromhex(digest) for _, digest in ordered]
    if not level:
        return hashlib.sha256(b"").hexdigest()
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[index] + level[index + 1]).digest()
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()


def _governance_records(project_root: Path) -> list[dict[str, str]]:
    canonical_decisions = canonical_decision_document(project_root)
    records: list[dict[str, str]] = []
    for decision in canonical_decisions["decisions"]:
        records.append(
            {
                "record_id": decision["source_question_id"],
                "record_type": "OWNER_QA_DECISION",
                "source_path": DECISIONS_PATH.as_posix(),
                "canonical_sha256": canonical_sha256(decision),
            }
        )
    controls = (
        ("SCG-SOURCE-INTAKE", "SOURCE_INTAKE", SOURCE_INTAKE_PATH),
        ("SCG-AUTHORITY-OVERLAY", "AUTHORITY_OVERLAY", AUTHORITY_OVERLAY_PATH),
        ("SCG-CANON-REGISTRY", "CANON_REGISTRY_INDEX", CANON_REGISTRY_PATH),
        ("SCG-TRACEABILITY", "TRACEABILITY", TRACEABILITY_PATH),
        ("SCG-SUPERSESSION", "SUPERSESSION", SUPERSESSION_PATH),
    )
    for record_id, record_type, relative in controls:
        value = read_json_document(project_root / relative)
        records.append(
            {
                "record_id": record_id,
                "record_type": record_type,
                "source_path": relative.as_posix(),
                "canonical_sha256": canonical_sha256(value),
            }
        )
    return sorted(records, key=lambda item: item["record_id"])


def tracked_target_state_active(project_root: Path = PROJECT_ROOT) -> bool:
    try:
        change_set = read_json_document(project_root / CHANGE_SET_PATH)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(change_set, dict)
        and change_set.get("schema_version") == "2.0.0"
        and change_set.get("lifecycle_stage") == "APPROVED"
        and change_set.get("disposition") == "ACTIVE"
        and change_set.get("approval_status")
        == "PENDING_OWNER_ACTIVATION_HASH_APPROVAL"
        and change_set.get("release") == "NOT_RELEASED"
    )


def activation_merkle_transition(
    records: list[dict[str, str]], new_root: str
) -> dict[str, Any]:
    current = {record["record_id"]: record["canonical_sha256"] for record in records}
    changed = [
        {
            "record_id": record_id,
            "old_canonical_sha256": ACTIVATION_OLD_LEAF_HASHES[record_id],
            "new_canonical_sha256": current[record_id],
        }
        for record_id in ACTIVATION_CHANGED_LEAF_IDS
    ]
    return {
        "algorithm": "SHA-256-BINARY-PAIR-DUPLICATE-ODD-V1",
        "leaf_count": len(records),
        "previous_root": PREVIOUS_GOVERNANCE_MERKLE_ROOT,
        "new_root": new_root,
        "changed_leaves": changed,
        "unchanged_groups": {
            "owner_qa_decisions": "Q001-Q130",
            "source_intake": "SCG-SOURCE-INTAKE",
            "traceability": "SCG-TRACEABILITY",
        },
        "excluded_from_merkle": [
            "IMPLEMENTATION_APPROVAL_CONSUMPTION",
            "IMPLEMENTATION_ACCEPT",
            "FINAL_INNER_RECEIPT",
            "ACTIVATION_OWNER_APPROVAL",
            "ACTIVATION_ACCEPT",
            "ACTIVATION_OUTER_ENVELOPE",
        ],
    }


def _pending_receipt(canon_hash: str, root_hash: str) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0.0",
        "receipt_id": "RR-SC-GOV-INSTALL-RECEIPT-001",
        "change_set_id": CHANGE_SET_ID,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": canon_hash,
        "proposed_canon_hash": canon_hash,
        "merkle_root": root_hash,
        "source_package_id": SOURCE_PACKAGE_ID,
        "source_package_sha256": SOURCE_ZIP_SHA256,
        "candidate_binding": {
            "strategy": "EXACT_HEAD_AT_VALIDATION",
            "candidate_commit": None,
            "candidate_tree": None,
        },
        "approval_status": "PENDING_OWNER_HASH_APPROVAL",
    }
    return {
        "schema_version": "1.0.0",
        "payload": payload,
        "payload_hash": canonical_sha256(payload),
        "owner_approval": None,
    }


def _final_inner_receipt(
    project_root: Path, canon_hash: str, root_hash: str
) -> dict[str, Any]:
    consumption_path = project_root / APPROVAL_CONSUMPTION_PATH
    if not consumption_path.is_file():
        raise StoryConstructionError(
            f"approval consumption record is missing: {APPROVAL_CONSUMPTION_PATH.as_posix()}"
        )
    payload = {
        "schema_version": "2.0.0",
        "receipt_id": "RR-SC-GOV-INSTALL-RECEIPT-FINAL-001",
        "source_package_id": SOURCE_PACKAGE_ID,
        "source_zip_sha256": SOURCE_ZIP_SHA256,
        "source_manifest_file_sha256": SOURCE_MANIFEST_FILE_SHA256,
        "source_integrity_defect": SOURCE_INTEGRITY_DEFECT,
        "change_set_id": CHANGE_SET_ID,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": canon_hash,
        "implementation_candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
        "implementation_candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        "implementation_owner_approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
        "implementation_accept_task_id": IMPLEMENTATION_ACCEPT_TASK_ID,
        "implementation_accept_result": IMPLEMENTATION_ACCEPT_RESULT,
        "implementation_accept_route_digest": IMPLEMENTATION_ACCEPT_ROUTE_DIGEST,
        "proposed_canon_hash": canon_hash,
        "previous_governance_merkle_root": PREVIOUS_GOVERNANCE_MERKLE_ROOT,
        "new_activation_merkle_root": root_hash,
        "approval_consumption_record_path": APPROVAL_CONSUMPTION_PATH.as_posix(),
        "approval_consumption_record_sha256": file_sha256(consumption_path),
        "activation_binding": {
            "strategy": ACTIVATION_BINDING_STRATEGY,
            "authoritative_effect_requires_external_proof": True,
        },
    }
    return {
        "schema_version": "2.0.0",
        "receipt_kind": "TRACKED_INNER_ACTIVATION_RECEIPT",
        "outer_envelope_schema": (
            "schemas/story-construction/activation-closeout-envelope-v1.schema.json"
        ),
        "payload": payload,
        "payload_hash": canonical_sha256(payload),
    }


def derive_installation(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    source_index, canon_hash = _canonical_source_index(project_root)
    records = _governance_records(project_root)
    root_hash = merkle_root(
        (record["record_id"], record["canonical_sha256"]) for record in records
    )
    canonical_manifest = {
        "schema_version": "1.0.0",
        "canonicalization_version": CANONICALIZATION_VERSION,
        "manifest_id": "RR-SC-GOV-CANONICAL-MANIFEST-001",
        "authority_scope": "CONSTRUCTION_GOVERNANCE_ONLY",
        "r2_canon_precedence": "HIGHER",
        "change_set_id": CHANGE_SET_ID,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "source_package": {
            "package_id": SOURCE_PACKAGE_ID,
            "zip_sha256": SOURCE_ZIP_SHA256,
            "source_manifest_file_sha256": SOURCE_MANIFEST_FILE_SHA256,
            "metadata_declared_manifest_sha256": SOURCE_METADATA_MANIFEST_SHA256,
            "integrity_defect": SOURCE_INTEGRITY_DEFECT,
        },
        "canon": {
            "source_index_sha256": canonical_sha256(source_index),
            "base_canon_hash": canon_hash,
            "proposed_canon_hash": canon_hash,
            "change_kind": "NONE_CONSTRUCTION_GOVERNANCE_ONLY",
        },
        "records": records,
        "merkle": {
            "algorithm": "SHA-256-BINARY-PAIR-DUPLICATE-ODD-V1",
            "leaf_order": "record_id_lexical",
            "root": root_hash,
        },
        "candidate_binding": {"strategy": "EXACT_HEAD_AT_VALIDATION"},
    }
    active = tracked_target_state_active(project_root)
    receipt = (
        _final_inner_receipt(project_root, canon_hash, root_hash)
        if active
        else _pending_receipt(canon_hash, root_hash)
    )
    return {
        "canonical_decisions": canonical_decision_document(project_root),
        "canonical_manifest": canonical_manifest,
        "receipt": receipt,
        "receipt_path": FINAL_RECEIPT_PATH if active else RECEIPT_PATH,
        "tracked_target_state_active": active,
        "base_canon_hash": canon_hash,
        "proposed_canon_hash": canon_hash,
        "merkle_root": root_hash,
        "receipt_payload_hash": receipt["payload_hash"],
        "merkle_transition": activation_merkle_transition(records, root_hash)
        if active
        else None,
    }


def write_derived_installation(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    derived = derive_installation(project_root)
    outputs = {
        CANONICAL_DECISIONS_PATH: derived["canonical_decisions"],
        CANONICAL_MANIFEST_PATH: derived["canonical_manifest"],
        derived["receipt_path"]: derived["receipt"],
    }
    for relative, value in outputs.items():
        path = project_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(value))

    change_set_path = project_root / CHANGE_SET_PATH
    change_set = read_json_document(change_set_path)
    change_set["base_canon_hash"] = derived["base_canon_hash"]
    change_set["proposed_canon_hash"] = derived["proposed_canon_hash"]
    change_set["merkle_root"] = derived["merkle_root"]
    if derived["tracked_target_state_active"]:
        change_set["previous_governance_merkle_root"] = (
            PREVIOUS_GOVERNANCE_MERKLE_ROOT
        )
        change_set["final_inner_receipt_payload_hash"] = derived[
            "receipt_payload_hash"
        ]
        change_set["approval_consumption_record_sha256"] = file_sha256(
            project_root / APPROVAL_CONSUMPTION_PATH
        )
        change_set["merkle_transition"] = derived["merkle_transition"]
    else:
        change_set["receipt_candidate_payload_hash"] = derived[
            "receipt_payload_hash"
        ]
    change_set_path.write_bytes(canonical_json_bytes(change_set))
    return derived


def _canonical_relative_path(raw_path: Any, label: str) -> tuple[str | None, str | None]:
    if not isinstance(raw_path, str) or not raw_path:
        return None, f"{label} must be a non-empty repository-relative path"
    if "\x00" in raw_path or "\\" in raw_path:
        return None, f"{label} must use canonical POSIX separators"
    posix = PurePosixPath(raw_path)
    if (
        posix.is_absolute()
        or PureWindowsPath(raw_path).is_absolute()
        or ".." in posix.parts
        or posix.as_posix() != raw_path
    ):
        return None, f"{label} escapes or is not canonical: {raw_path}"
    return raw_path, None


def _validate_worker_targets(
    targets: Iterable[str],
    required_prefix: str,
) -> list[str]:
    errors: list[str] = []
    target_list = list(targets)
    if not target_list:
        return ["at least one worker return target is required"]
    for index, raw_target in enumerate(target_list):
        target, issue = _canonical_relative_path(raw_target, f"target[{index}]")
        if issue is not None:
            errors.append(issue)
            continue
        assert target is not None
        if target.startswith(FORBIDDEN_WORKER_PREFIXES):
            errors.append(f"worker target is an authority/schema/runtime write: {target}")
        elif not target.startswith(required_prefix):
            errors.append(f"worker target is outside controlled return scope: {target}")
    return errors


def validate_task_packet_pairing(packet: Any) -> list[str]:
    if not isinstance(packet, dict):
        return ["Task Packet must be an object"]
    owner = packet.get("owner")
    task_type = packet.get("task_type")
    allowed = {
        "codex": {"spec", "integration", "acceptance"},
        "opencode": {"script"},
        "grok": {"art"},
        "deepseek_harness": {"literary"},
    }
    if owner not in allowed:
        return [f"unsupported Task Packet owner: {owner!r}"]
    if task_type not in allowed[owner]:
        return [f"owner={owner} cannot execute task_type={task_type}"]
    return []


def literary_input_hash(order: dict[str, Any]) -> str:
    components = order.get("input_components")
    if not isinstance(components, dict):
        raise StoryConstructionError("literary order lacks input_components")
    return canonical_sha256(components)


def literary_order_hash(order: dict[str, Any]) -> str:
    payload = {key: value for key, value in order.items() if key != "order_hash"}
    return canonical_sha256(payload)


def validate_literary_execution(
    packet: Any,
    order: Any,
    target_paths: Iterable[str],
    return_bundle: Any | None = None,
) -> list[str]:
    errors = validate_task_packet_pairing(packet)
    if not isinstance(packet, dict) or packet.get("owner") != "deepseek_harness":
        errors.append("literary execution requires owner=deepseek_harness")
    if not isinstance(packet, dict) or packet.get("task_type") != "literary":
        errors.append("literary execution requires task_type=literary")
    if not isinstance(order, dict):
        return errors + ["valid Literary Order Package is required"]
    if order.get("order_authority") != "VALIDATED_TEXT_ORDER_PACKAGE":
        errors.append("literary order authority is not validated")
    if order.get("owner_token") != "deepseek_harness":
        errors.append("literary order owner token mismatch")
    if order.get("max_targeted_repairs") != 2:
        errors.append("literary order must cap targeted repairs at exactly 2")
    try:
        if order.get("input_hash") != literary_input_hash(order):
            errors.append("literary order input hash mismatch")
        if order.get("order_hash") != literary_order_hash(order):
            errors.append("literary order hash mismatch")
    except StoryConstructionError as exc:
        errors.append(str(exc))
    forbidden_capabilities = set(order.get("forbidden_capabilities", []))
    required_forbidden = {
        "CREATE_T1",
        "CREATE_T2",
        "CREATE_C1",
        "MODIFY_AUTHORITY",
        "WRITE_PERSISTENT_STATE",
        "MODIFY_RUNTIME",
        "MODIFY_LUA",
        "MODIFY_GAME_PACKAGE",
    }
    missing = sorted(required_forbidden - forbidden_capabilities)
    if missing:
        errors.append(f"literary order lacks forbidden capabilities: {missing}")
    errors.extend(_validate_worker_targets(target_paths, LITERARY_RETURN_PREFIX))

    if return_bundle is not None:
        if not isinstance(return_bundle, dict):
            errors.append("literary return bundle must be an object")
        elif return_bundle.get("status") == "BLOCKED_NEEDS_CANON":
            if not return_bundle.get("missing_canon"):
                errors.append("BLOCKED_NEEDS_CANON must identify missing canon")
        else:
            required = {
                "semantic_draft",
                "literary_draft",
                "semantic_mapping",
                "source_matrix",
                "self_check",
                "issues",
                "version_usage",
                "return_hashes",
            }
            absent = sorted(required - set(return_bundle))
            if absent:
                errors.append(f"literary return bundle lacks fields: {absent}")
            if return_bundle.get("final_acceptance") == "PASS":
                errors.append("literary worker self-review cannot form final PASS")
    return errors


def visual_order_hash(order: dict[str, Any]) -> str:
    payload = {key: value for key, value in order.items() if key != "order_hash"}
    return canonical_sha256(payload)


def validate_visual_execution(
    packet: Any,
    order: Any,
    target_paths: Iterable[str],
) -> list[str]:
    errors = validate_task_packet_pairing(packet)
    if not isinstance(packet, dict) or packet.get("owner") != "grok":
        errors.append("visual execution requires owner=grok")
    if not isinstance(packet, dict) or packet.get("task_type") != "art":
        errors.append("visual execution requires task_type=art")
    if not isinstance(order, dict):
        return errors + ["validated Visual Order Package is required; raw art request rejected"]
    if order.get("order_authority") != "VALIDATED_VISUAL_ORDER_PACKAGE":
        errors.append("raw or unvalidated art request is not production authority")
    required_fields = {
        "semantic_composition_proof",
        "canon_refs",
        "dossier_refs",
        "must_objects",
        "forbidden_objects",
        "spatial_relations",
        "salience",
        "occlusion",
        "state_continuity",
        "reveal_refs",
        "accessibility_equivalent",
        "rights_provenance",
        "capability_declaration",
    }
    absent = sorted(required_fields - set(order))
    if absent:
        errors.append(f"visual order lacks fields: {absent}")
    fact_classes = set(order.get("proposed_fact_classes", []))
    forbidden = sorted(fact_classes & FORBIDDEN_VISUAL_FACT_CLASSES)
    if forbidden:
        errors.append(f"Grok cannot define authoritative facts: {forbidden}")
    try:
        if order.get("order_hash") != visual_order_hash(order):
            errors.append("visual order hash mismatch")
    except StoryConstructionError as exc:
        errors.append(str(exc))
    errors.extend(_validate_worker_targets(target_paths, VISUAL_RETURN_PREFIX))
    return errors


def validate_candidate_approval(
    approval: Any,
    expected: dict[str, str],
) -> list[str]:
    if not isinstance(approval, dict):
        return ["candidate approval must be an object"]
    errors: list[str] = []
    required = {
        "change_set_id",
        "base_commit",
        "base_tree",
        "base_canon_hash",
        "candidate_commit",
        "candidate_tree",
        "proposed_canon_hash",
        "merkle_root",
        "receipt_payload_hash",
    }
    for field in sorted(required):
        if approval.get(field) != expected.get(field):
            errors.append(f"candidate approval {field} mismatch")
    if approval.get("approval_status") != "APPROVED":
        errors.append("candidate approval status is not APPROVED")
    if approval.get("single_use") is not True:
        errors.append("candidate approval must be single-use")
    if approval.get("transferable") is not False:
        errors.append("candidate approval must be non-transferable")
    if approval.get("consumed") is not False:
        errors.append("candidate approval is already consumed")
    if approval.get("revoked") is not False:
        errors.append("candidate approval is revoked")
    return errors


def validate_canonical_manifest_binding(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["canonical manifest must be an object"]
    errors: list[str] = []
    if "manifest_sha256" in manifest or "self_sha256" in manifest:
        errors.append("canonical manifest self-hash binding is forbidden")
    serialized = json.dumps(manifest, ensure_ascii=False, sort_keys=True).lower()
    if "receipt" in serialized:
        errors.append("canonical manifest must not bind an installation receipt")
    return errors


def validate_pending_receipt_binding(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict):
        return ["installation receipt must be an object"]
    errors: list[str] = []
    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        return ["installation receipt payload must be an object"]
    if "payload_hash" in payload or "receipt_payload_hash" in payload:
        errors.append("receipt payload self-references its own hash")
    if receipt.get("payload_hash") != canonical_sha256(payload):
        errors.append("receipt payload hash mismatch")
    if payload.get("candidate_binding") != {
        "strategy": "EXACT_HEAD_AT_VALIDATION",
        "candidate_commit": None,
        "candidate_tree": None,
    }:
        errors.append("pending receipt fabricated candidate commit/tree")
    if payload.get("approval_status") != "PENDING_OWNER_HASH_APPROVAL":
        errors.append("pending receipt approval status drift")
    if receipt.get("owner_approval") is not None:
        errors.append("pending receipt fabricated owner approval")
    return errors


def validate_lifecycle_state(change_set: Any) -> list[str]:
    if not isinstance(change_set, dict):
        return ["Change Set must be an object"]
    version = change_set.get("schema_version")
    if version == "1.0.0":
        expected = {
            "lifecycle_stage": "CANDIDATE",
            "disposition": "CANDIDATE_NOT_ACTIVE",
            "approval_status": "PENDING_OWNER_HASH_APPROVAL",
        }
    elif version == "2.0.0":
        expected = {
            "lifecycle_stage": "APPROVED",
            "disposition": "ACTIVE",
            "approval_status": "PENDING_OWNER_ACTIVATION_HASH_APPROVAL",
            "release": "NOT_RELEASED",
        }
    else:
        return [f"unsupported Change Set state schema: {version!r}"]
    errors = [
        f"Change Set {field} is invalid for schema {version}"
        for field, value in expected.items()
        if change_set.get(field) != value
    ]
    if version == "2.0.0":
        activation = change_set.get("activation_state")
        if activation != {
            "tracked_target_state": "TRACKED_TARGET_STATE_ACTIVE",
            "authoritative_activation_effective": False,
            "required_external_proofs": [
                "ACTIVATION_SPECIFIC_OWNER_FULL_HASH_APPROVAL",
                "PASS_FIXED_ACTIVATION_CANDIDATE_ACCEPTED",
                "VALID_DETACHED_ACCEPTED_ACTIVATION_ENVELOPE_TAG",
                "FINAL_FAST_FORWARD_INTEGRATION",
            ],
        }:
            errors.append("Change Set active-state proof separation drift")
        if change_set.get("lifecycle_stage") == "RELEASED":
            errors.append("RELEASED cannot impersonate activation")
    return errors


def validate_implementation_approval_consumption(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["implementation approval consumption record must be an object"]
    expected: dict[str, Any] = {
        "schema_version": "1.0.0",
        "approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
        "change_set_id": CHANGE_SET_ID,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH,
        "candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
        "candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        "proposed_canon_hash": BASE_CANON_HASH,
        "implementation_merkle_root": PREVIOUS_GOVERNANCE_MERKLE_ROOT,
        "receipt_candidate_payload_hash": IMPLEMENTATION_RECEIPT_PAYLOAD_HASH,
        "approval": "OWNER_HASH_APPROVED_FOR_INDEPENDENT_ACCEPT",
        "single_use": True,
        "transferable": False,
        "revoked": False,
        "consumption_count": 1,
        "consumption_event": IMPLEMENTATION_ACCEPT_TASK_ID,
        "consumption_result": IMPLEMENTATION_ACCEPT_RESULT,
        "accepted_candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
        "accepted_candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        "accept_route_digest": IMPLEMENTATION_ACCEPT_ROUTE_DIGEST,
        "owner_approval_transport_sha256": (
            IMPLEMENTATION_OWNER_APPROVAL_TRANSPORT_SHA256
        ),
        "consumed": True,
    }
    return [
        f"implementation approval consumption {field} mismatch"
        for field, value in expected.items()
        if record.get(field) != value
    ]


def validate_final_receipt_binding(
    receipt: Any,
    *,
    expected_new_merkle_root: str,
    expected_consumption_sha256: str,
) -> list[str]:
    if not isinstance(receipt, dict):
        return ["final inner receipt must be an object"]
    payload = receipt.get("payload")
    if not isinstance(payload, dict):
        return ["final inner receipt payload must be an object"]
    errors: list[str] = []
    if receipt.get("schema_version") != "2.0.0":
        errors.append("final inner receipt schema version drift")
    if receipt.get("receipt_kind") != "TRACKED_INNER_ACTIVATION_RECEIPT":
        errors.append("final receipt is not the tracked inner receipt")
    if receipt.get("payload_hash") != canonical_sha256(payload):
        errors.append("final inner receipt payload hash mismatch")
    forbidden_payload_fields = {
        "payload_hash",
        "receipt_payload_hash",
        "activation_candidate_commit",
        "activation_candidate_tree",
        "activation_owner_approval",
        "activation_owner_approval_id",
        "activation_accept_task_id",
        "activation_accept_result",
        "activation_accept_route_digest",
        "outer_envelope_sha256",
        "tag_object_id",
    }
    present = sorted(forbidden_payload_fields & set(payload))
    if present:
        errors.append(f"final inner receipt contains forbidden self/external binding: {present}")
    expected: dict[str, Any] = {
        "schema_version": "2.0.0",
        "receipt_id": "RR-SC-GOV-INSTALL-RECEIPT-FINAL-001",
        "source_package_id": SOURCE_PACKAGE_ID,
        "source_zip_sha256": SOURCE_ZIP_SHA256,
        "source_manifest_file_sha256": SOURCE_MANIFEST_FILE_SHA256,
        "source_integrity_defect": SOURCE_INTEGRITY_DEFECT,
        "change_set_id": CHANGE_SET_ID,
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "base_canon_hash": BASE_CANON_HASH,
        "implementation_candidate_commit": IMPLEMENTATION_CANDIDATE_COMMIT,
        "implementation_candidate_tree": IMPLEMENTATION_CANDIDATE_TREE,
        "implementation_owner_approval_id": IMPLEMENTATION_OWNER_APPROVAL_ID,
        "implementation_accept_task_id": IMPLEMENTATION_ACCEPT_TASK_ID,
        "implementation_accept_result": IMPLEMENTATION_ACCEPT_RESULT,
        "implementation_accept_route_digest": IMPLEMENTATION_ACCEPT_ROUTE_DIGEST,
        "proposed_canon_hash": BASE_CANON_HASH,
        "previous_governance_merkle_root": PREVIOUS_GOVERNANCE_MERKLE_ROOT,
        "new_activation_merkle_root": expected_new_merkle_root,
        "approval_consumption_record_path": APPROVAL_CONSUMPTION_PATH.as_posix(),
        "approval_consumption_record_sha256": expected_consumption_sha256,
        "activation_binding": {
            "strategy": ACTIVATION_BINDING_STRATEGY,
            "authoritative_effect_requires_external_proof": True,
        },
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"final inner receipt {field} mismatch")
    return errors


def validate_merkle_transition(
    previous_manifest: Any,
    current_manifest: Any,
    transition: Any,
) -> list[str]:
    if not all(isinstance(value, dict) for value in (previous_manifest, current_manifest, transition)):
        return ["Merkle transition inputs must be objects"]
    errors: list[str] = []
    previous_records = previous_manifest.get("records", [])
    current_records = current_manifest.get("records", [])
    if not isinstance(previous_records, list) or not isinstance(current_records, list):
        return ["Merkle manifests must contain record arrays"]
    previous = {
        item.get("record_id"): item
        for item in previous_records
        if isinstance(item, dict)
    }
    current = {
        item.get("record_id"): item
        for item in current_records
        if isinstance(item, dict)
    }
    if len(previous_records) != 135 or len(current_records) != 135:
        errors.append("governance Merkle leaf count must remain exactly 135")
    if set(previous) != set(current):
        errors.append("governance Merkle record identity set drift")
    changed_ids = sorted(
        record_id
        for record_id in set(previous) & set(current)
        if previous[record_id].get("canonical_sha256")
        != current[record_id].get("canonical_sha256")
    )
    if changed_ids != list(ACTIVATION_CHANGED_LEAF_IDS):
        errors.append(f"unapproved Merkle semantic leaf transition: {changed_ids}")
    previous_root = previous_manifest.get("merkle", {}).get("root")
    current_root = current_manifest.get("merkle", {}).get("root")
    if previous_root != PREVIOUS_GOVERNANCE_MERKLE_ROOT:
        errors.append("previous governance Merkle root mismatch")
    if transition.get("leaf_count") != 135:
        errors.append("Merkle transition leaf_count drift")
    if transition.get("previous_root") != previous_root:
        errors.append("Merkle transition previous root mismatch")
    if transition.get("new_root") != current_root:
        errors.append("Merkle transition new root mismatch")
    expected_diff = [
        {
            "record_id": record_id,
            "old_canonical_sha256": previous[record_id]["canonical_sha256"],
            "new_canonical_sha256": current[record_id]["canonical_sha256"],
        }
        for record_id in ACTIVATION_CHANGED_LEAF_IDS
    ]
    if transition.get("changed_leaves") != expected_diff:
        errors.append("Merkle transition old/new leaf diff mismatch")
    forbidden_types = {
        "IMPLEMENTATION_APPROVAL_CONSUMPTION",
        "IMPLEMENTATION_ACCEPT",
        "FINAL_INNER_RECEIPT",
        "ACTIVATION_OWNER_APPROVAL",
        "ACTIVATION_ACCEPT",
        "ACTIVATION_OUTER_ENVELOPE",
    }
    leaked = sorted(
        item.get("record_id")
        for item in current_records
        if isinstance(item, dict)
        and (
            item.get("record_id") in forbidden_types
            or item.get("record_type") in forbidden_types
            or any(
                token in str(item.get("source_path", "")).lower()
                for token in ("approval", "receipt", "accept")
            )
        )
    )
    if leaked:
        errors.append(f"approval/receipt/ACCEPT entered governance Merkle: {leaked}")
    return errors


def validate_activation_owner_approval(
    approval: Any, expected: dict[str, Any]
) -> list[str]:
    if not isinstance(approval, dict):
        return ["activation Owner approval must be an object"]
    errors: list[str] = []
    for field, value in expected.items():
        if approval.get(field) != value:
            errors.append(f"activation Owner approval {field} mismatch")
    if approval.get("approval_id") == IMPLEMENTATION_OWNER_APPROVAL_ID:
        errors.append("implementation approval ID cannot serve as activation approval")
    if approval.get("approval_model") != "FULL_ACTIVATION_HASH_SET_REAPPROVAL_REQUIRED":
        errors.append("activation Owner approval model mismatch")
    if approval.get("approval_status") != "APPROVED":
        errors.append("activation Owner approval status is not APPROVED")
    if approval.get("single_use") is not True:
        errors.append("activation Owner approval must be single-use")
    if approval.get("transferable") is not False:
        errors.append("activation Owner approval must be non-transferable")
    if approval.get("consumed") is not False:
        errors.append("activation Owner approval is already consumed")
    if approval.get("revoked") is not False:
        errors.append("activation Owner approval is revoked")
    return errors


def validate_activation_closeout_envelope(
    envelope: Any, expected: dict[str, Any]
) -> list[str]:
    if not isinstance(envelope, dict):
        return ["activation closeout envelope must be an object"]
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return ["activation closeout envelope payload must be an object"]
    errors: list[str] = []
    if envelope.get("payload_hash") != canonical_sha256(payload):
        errors.append("activation closeout envelope payload hash mismatch")
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"activation closeout envelope {field} mismatch")
    if payload.get("binding_strategy") != ACTIVATION_BINDING_STRATEGY:
        errors.append("activation closeout envelope binding strategy mismatch")
    if payload.get("tag_target_commit") != payload.get("activation_candidate_commit"):
        errors.append("activation closeout envelope tag target commit mismatch")
    if payload.get("tag_target_tree") != payload.get("activation_candidate_tree"):
        errors.append("activation closeout envelope tag target tree mismatch")
    if payload.get("activation_accept_result") != "PASS_FIXED_ACTIVATION_CANDIDATE_ACCEPTED":
        errors.append("activation closeout envelope ACCEPT result mismatch")
    if payload.get("accepted_candidate_commit") != payload.get("activation_candidate_commit"):
        errors.append("activation ACCEPT candidate commit mismatch")
    if payload.get("accepted_candidate_tree") != payload.get("activation_candidate_tree"):
        errors.append("activation ACCEPT candidate tree mismatch")
    if payload.get("producer_id") == payload.get("verifier_id"):
        errors.append("builder self-accept is forbidden")
    if payload.get("verifier_worktree_state") != "CLEAN":
        errors.append("dirty verifier assumption is forbidden")
    if payload.get("activation_candidate_parent") != IMPLEMENTATION_CANDIDATE_COMMIT:
        errors.append("activation candidate lineage parent mismatch")
    if payload.get("lineage_commit_count") != 1:
        errors.append("activation candidate lineage must contain exactly one commit")
    if payload.get("integration_mode") != "FAST_FORWARD_ONLY":
        errors.append("activation integration must remain fast-forward-only")
    return errors


def authoritative_activation_status(
    *,
    tracked_target_state_active: bool,
    activation_approval: Any | None,
    expected_activation_approval: dict[str, Any],
    envelope: Any | None,
    expected_envelope: dict[str, Any],
    integration: Any | None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not tracked_target_state_active:
        errors.append("tracked target state is not ACTIVE")
    if activation_approval is None:
        errors.append("activation-specific Owner approval is missing")
    else:
        errors.extend(
            validate_activation_owner_approval(
                activation_approval, expected_activation_approval
            )
        )
    if envelope is None:
        errors.append("detached accepted activation envelope/tag is missing")
    else:
        errors.extend(validate_activation_closeout_envelope(envelope, expected_envelope))
    if not isinstance(integration, dict):
        errors.append("final fast-forward integration proof is missing")
    else:
        if integration.get("integrated") is not True:
            errors.append("activation candidate is not integrated")
        if integration.get("mode") != "FAST_FORWARD_ONLY":
            errors.append("activation integration proof is not fast-forward-only")
        expected_commit = expected_envelope.get("activation_candidate_commit")
        expected_tree = expected_envelope.get("activation_candidate_tree")
        if integration.get("commit") != expected_commit:
            errors.append("integrated activation commit mismatch")
        if integration.get("tree") != expected_tree:
            errors.append("integrated activation tree mismatch")
    return not errors, errors


def validate_m3_route_request(
    request: Any,
    expected_route_id: str,
    expected_mode: str,
) -> list[str]:
    if not isinstance(request, dict):
        return ["M3 route request must be an object"]
    errors: list[str] = []
    expected = {
        "route_id": expected_route_id,
        "mode": expected_mode,
        "milestone": "M3",
        "batch_id": "M3-B001",
        "capacity_bytes": 196608,
    }
    for field, value in expected.items():
        if request.get(field) != value:
            errors.append(f"wrong M3 route {field}")
    documents = request.get("documents")
    if not isinstance(documents, list):
        errors.append("M3 route documents must be an array")
    else:
        selected = {
            document.get("path")
            for document in documents
            if isinstance(document, dict)
        }
        forbidden = sorted(OLD_STORY_PREDECESSORS & selected)
        if forbidden:
            errors.append(f"old predecessor selected as authority: {forbidden}")
    return errors


def validate_region_design_complete(dossier: Any) -> list[str]:
    if not isinstance(dossier, dict):
        return ["Region Dossier must be an object"]
    errors: list[str] = []
    approvals = dossier.get("approvals", {})
    for required in ("T1", "T2", "T3_ENVELOPE", "C1_REVEAL_FAMILY"):
        if not isinstance(approvals, dict) or approvals.get(required) != "APPROVED":
            errors.append(f"Region Design Complete requires {required} approval")
    gate = dossier.get("design_complete_gate", {})
    required_gates = (
        "rules_exceptions_frozen",
        "timeline_verified",
        "npc_epistemic_verified",
        "routes_closed",
        "failure_covered",
        "retreat_covered",
        "remediation_covered",
        "tpk_covered",
        "reachability_verified",
        "style_frozen",
        "visual_anchors_frozen",
        "no_blocker",
    )
    for required in required_gates:
        if not isinstance(gate, dict) or gate.get(required) is not True:
            errors.append(f"Region Design Complete gate failed: {required}")
    return errors


def validate_region_acceptance(bundle: Any) -> list[str]:
    if not isinstance(bundle, dict):
        return ["Region Acceptance bundle must be an object"]
    errors: list[str] = []
    layers = bundle.get("validation_layers")
    for layer in ("V0", "V1", "V2", "V3", "V4", "V5", "V6"):
        if not isinstance(layers, dict) or layers.get(layer) != "PASS":
            errors.append(f"Region Acceptance requires {layer}=PASS")
    for defect in bundle.get("defects", []):
        if not isinstance(defect, dict):
            errors.append("Region Acceptance defect must be an object")
            continue
        if defect.get("status") == "OPEN" and defect.get("severity") in {
            "BLOCKER",
            "CRITICAL",
            "MAJOR",
        }:
            errors.append(
                f"open {defect.get('severity')} defect prevents Region Acceptance"
            )
    if errors and bundle.get("result") == "PASS":
        errors.append("Region Acceptance cannot claim PASS with failed gates")
    return errors


def validate_dab(bundle: Any, subject_class: str) -> list[str]:
    if not isinstance(bundle, dict):
        return ["DAB must be an object"]
    errors: list[str] = []
    mandatory_forensic = {"T1", "T2", "C1", "FAILURE_DISPUTE", "RC", "RELEASE"}
    if subject_class in mandatory_forensic and bundle.get("tier") != "FORENSIC":
        errors.append(f"{subject_class} requires a FORENSIC DAB")
    if bundle.get("private_chain_of_thought_recorded") is not False:
        errors.append("DAB must not record private chain-of-thought")
    return errors


def validate_acceptance_independence(bundle: Any) -> list[str]:
    if not isinstance(bundle, dict):
        return ["acceptance bundle must be an object"]
    if bundle.get("producer_id") == bundle.get("verifier_id"):
        return ["worker self-review cannot form final PASS"]
    if bundle.get("worker_self_review") == "PASS" and bundle.get("result") == "PASS":
        return ["worker self-review cannot form final PASS"]
    return []


def validate_runtime_projection(projection: Any) -> list[str]:
    if not isinstance(projection, dict):
        return ["runtime projection must be an object"]
    if projection.get("content_class") == "LITERARY_CANDIDATE" and projection.get(
        "owner_hash_approval"
    ) != "APPROVED":
        return ["unapproved literary candidate cannot enter runtime projection"]
    return []
