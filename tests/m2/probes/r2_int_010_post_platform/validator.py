#!/usr/bin/env python3
"""Fail-closed validator for the post-platform adapter candidate and antecedents."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import builder  # type: ignore[no-redef]
else:
    from . import builder


ROOT = builder.REPOSITORY_ROOT
PLATFORM_REPORT_ROOT = ROOT / "reports/m2/probes/external/r2-int-010-platform-acceptance"
PLATFORM_RECORD_NAME = PurePosixPath("platform-acceptance.json")
PLATFORM_MANIFEST_NAME = PurePosixPath("evidence-manifest.json")
PROVENANCE_PATH = ROOT / "reports/m2/probes/remediations/r2-int-010-rem-001/provenance-disposition.json"

RULES_SOURCE_COMMIT = "65a0a1671720345425e0368136793754567187cc"
RULES_SOURCE_TREE = "4f438d0aca3daea8bb66959560f9642d8f62810a"
ROUTE_ID = "M2-B001-EXTERNAL-PROBE-UPDATE-001"
ROUTE_DIGEST = "a7a37c8e3384d71e1b6a6759e421fb37f0560ebfbd6742d63664e37977691cb7"

PROVISIONAL_COMMITS = (
    "02f261a326cc7bffead5e6a46017c352f822aa94",
    "c6a840b10db46dc475cd9af9e6a1a13f1e68abd4",
    "65a0a1671720345425e0368136793754567187cc",
)
PROVISIONAL_CLASSIFICATION = "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load_confined_json(
    root: Path,
    relative: PurePosixPath,
    label: str,
    maximum_bytes: int = 1 << 20,
) -> tuple[dict[str, Any], bytes]:
    real_root = builder._validated_real_directory(root, f"{label} root")
    value, data = builder._load_json_file(real_root, relative, label, maximum_bytes)
    _require(isinstance(value, dict), f"{label} must be an object")
    return value, data


def _load_provenance(path: Path) -> dict[str, Any]:
    path = Path(path)
    value, _ = _load_confined_json(path.parent, PurePosixPath(path.name), "provenance disposition")
    return value


def expected_platform_object() -> dict[str, Any]:
    return {
        "code_commit": builder.PLATFORM_CODE_COMMIT,
        "code_tree": builder.PLATFORM_CODE_TREE,
        "acceptance_authority_commit": builder.PLATFORM_AUTHORITY_COMMIT,
        "acceptance_authority_tree": builder.PLATFORM_AUTHORITY_TREE,
        "acceptance_status": "PASS",
        "creator_binary_sha256": builder.CREATOR_BINARY_SHA256,
    }


def validate_platform_record(data: dict[str, Any], metadata: dict[str, Any]) -> None:
    builder._require_exact_keys(
        data,
        {
            "schema_version", "record_id", "task_id", "record_role", "platform",
            "adapter_state", "forbidden_claims", "registration",
        },
        "platform acceptance record",
    )
    _require(
        data["schema_version"] == "rules-residue.m2.platform-acceptance-antecedent/1.0",
        "platform acceptance record schema changed",
    )
    _require(data["record_id"] == builder.ACCEPTANCE_BINDING_ID, "platform record ID mismatch")
    _require(data["task_id"] == builder.TASK_ID, "platform record task mismatch")
    _require(
        data["record_role"] == "ACCEPTED_PLATFORM_CAPABILITY_ANTECEDENT_ONLY",
        "platform record role overclaims adapter acceptance",
    )
    platform = data["platform"]
    _require(platform == expected_platform_object(), "platform PASS identity is absent or mismatched")
    _require(platform["code_commit"] not in PROVISIONAL_COMMITS, "provisional rules commit used as platform acceptance")
    metadata_acceptance = metadata["platform_acceptance"]
    expected_metadata = {
        "binding_id": builder.ACCEPTANCE_BINDING_ID,
        "status": platform["acceptance_status"],
        "platform_code_commit": platform["code_commit"],
        "platform_code_tree": platform["code_tree"],
        "acceptance_authority_commit": platform["acceptance_authority_commit"],
        "acceptance_authority_tree": platform["acceptance_authority_tree"],
        "creator_binary_sha256": platform["creator_binary_sha256"],
    }
    _require(metadata_acceptance == expected_metadata, "source metadata is not exactly bound to platform PASS")
    _require(
        data["adapter_state"] == {
            "post_platform_adapter": "IMPLEMENTED_NOT_ACCEPTED",
            "independent_adapter_acceptance": "NOT_RUN",
            "cross_repository_acceptance": "NOT_RUN",
            "r2_int_010": "FAIL",
            "m2_b002_started": False,
        },
        "platform record forged a downstream transition",
    )
    _require(
        data["forbidden_claims"] == [
            "RESOLVED_ADAPTER",
            "M2-B001_ACCEPTED",
            "M2-B002_READY",
            "FORMAL_B002_PASS",
            "FORMAL_B009_PASS",
            "R2-INT-010_PASS",
        ],
        "platform record forbidden-claim guard changed",
    )
    _require(
        data["registration"] == {
            "rules_source_commit": RULES_SOURCE_COMMIT,
            "rules_source_tree": RULES_SOURCE_TREE,
            "route_id": ROUTE_ID,
            "mode": "IMPLEMENT",
            "milestone": "M2",
            "batch_id": "M2-B001",
            "binding_digest": ROUTE_DIGEST,
        },
        "platform record route/source registration is stale",
    )


def validate_platform_manifest(data: dict[str, Any], record_bytes: bytes) -> None:
    builder._require_exact_keys(
        data,
        {"schema_version", "evidence_set_id", "task_id", "artifact", "registered_claim", "downstream_non_claims"},
        "platform acceptance evidence manifest",
    )
    _require(
        data["schema_version"] == "rules-residue.m2.platform-acceptance-manifest/1.0",
        "platform manifest schema changed",
    )
    _require(data["evidence_set_id"] == builder.ACCEPTANCE_BINDING_ID, "platform manifest ID mismatch")
    _require(data["task_id"] == builder.TASK_ID, "platform manifest task mismatch")
    _require(
        data["artifact"] == {
            "path": "reports/m2/probes/external/r2-int-010-platform-acceptance/platform-acceptance.json",
            "sha256": hashlib.sha256(record_bytes).hexdigest(),
        },
        "platform acceptance record digest is stale",
    )
    _require(
        data["registered_claim"] == "PLATFORM_CAPABILITY_ACCEPTANCE_PASS_ONLY",
        "platform manifest overclaims its registered evidence",
    )
    _require(
        data["downstream_non_claims"] == {
            "rules_adapter_acceptance": "NOT_RUN",
            "cross_repository_acceptance": "NOT_RUN",
            "r2_int_010": "FAIL",
        },
        "platform manifest forged a downstream claim",
    )


def expected_provenance() -> dict[str, Any]:
    labels = ("initial_adapter", "adapter_fix", "old_evidence")
    return {
        "schema_version": "rules-residue.m2.provisional-provenance-disposition/1.0",
        "record_id": "R2-INT-010-REM-001-PROVENANCE-DISPOSITION-001",
        "task_id": builder.TASK_ID,
        "historical_antecedents": [
            {
                "label": label,
                "commit": commit,
                "classification": PROVISIONAL_CLASSIFICATION,
            }
            for label, commit in zip(labels, PROVISIONAL_COMMITS, strict=True)
        ],
        "policy": {
            "may_be_used_as_historical_antecedent": True,
            "may_be_used_as_execution_evidence": False,
            "may_satisfy_post_platform_adapter_gate": False,
            "may_transition_R2_INT_010": False,
        },
        "historical_artifact_paths": [
            "tests/fixtures/r2-int-010-rem-001/**",
            "tools/build_platform_v2_probe.py",
            "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json",
            "reports/m2/probes/remediations/r2-int-010-rem-001/evidence-manifest.json",
            "reports/m2/probes/remediations/r2-int-010-rem-001/execution-records.json",
        ],
        "old_provisional_files_modified": False,
        "current_gate": {
            "platform_acceptance": "PASS",
            "rules_adapter_acceptance": "NOT_RUN",
            "cross_repository_acceptance": "NOT_RUN",
            "r2_int_010": "FAIL",
        },
    }


def validate_provenance(data: dict[str, Any]) -> None:
    _require(data == expected_provenance(), "provisional provenance disposition is incomplete or altered")
    commits = [item["commit"] for item in data["historical_antecedents"]]
    _require(commits == list(PROVISIONAL_COMMITS), "provisional commit order or identity changed")
    _require(len(commits) == len(set(commits)), "provisional commit was duplicated")


def validate_adapter_candidate(
    source_root: Path = builder.SOURCE_ROOT,
    platform_report_root: Path = PLATFORM_REPORT_ROOT,
    provenance_path: Path = PROVENANCE_PATH,
    *,
    platform_record_data: dict[str, Any] | None = None,
    platform_manifest_data: dict[str, Any] | None = None,
    provenance_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inputs = builder.load_adapter_inputs(source_root)
    loaded_record, record_bytes = _load_confined_json(
        platform_report_root, PLATFORM_RECORD_NAME, "platform acceptance record"
    )
    loaded_manifest, _ = _load_confined_json(
        platform_report_root, PLATFORM_MANIFEST_NAME, "platform acceptance manifest"
    )
    record = platform_record_data if platform_record_data is not None else loaded_record
    manifest = platform_manifest_data if platform_manifest_data is not None else loaded_manifest
    provenance = provenance_data if provenance_data is not None else _load_provenance(provenance_path)
    validate_platform_record(record, inputs.metadata)
    validate_platform_manifest(manifest, record_bytes)
    validate_provenance(provenance)
    _, lock_bytes, source_tree, candidate_identity = builder.source_project_files(source_root)
    return {
        "task_id": builder.TASK_ID,
        "validation": "PASS",
        "platform_acceptance": "PASS",
        "post_platform_adapter": "IMPLEMENTED_NOT_ACCEPTED",
        "independent_adapter_acceptance": "NOT_RUN",
        "cross_repository_acceptance": "NOT_RUN",
        "r2_int_010": "FAIL",
        "source_tree_sha256": source_tree,
        "source_exact_lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "candidate_identity_sha256": candidate_identity,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the post-platform R2-INT-010 source candidate")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--source-root", type=Path, default=builder.SOURCE_ROOT)
    args = parser.parse_args(argv)
    if not args.validate:
        print("post-platform adapter validation failed: select --validate", file=sys.stderr)
        return 1
    try:
        result = validate_adapter_candidate(source_root=args.source_root)
    except (OSError, ValueError) as error:
        print(f"post-platform adapter validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
