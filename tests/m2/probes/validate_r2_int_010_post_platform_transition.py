#!/usr/bin/env python3
"""Fail-closed validator for the additive R2-INT-010 evidence transition."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "R2-INT-010-EVIDENCE-TRANSITION-IMPLEMENT-001"
EVIDENCE_ID = "R2-INT-010-POST-PLATFORM-TRANSITION-T001"
TRANSITION_DIR = "reports/m2/probes/remediations/r2-int-010-post-platform-transition"
EVIDENCE_PATH_TEXT = f"{TRANSITION_DIR}/evidence.json"
EXECUTION_PATH_TEXT = f"{TRANSITION_DIR}/execution-records.json"
CROSS_VERDICT_PATH_TEXT = f"{TRANSITION_DIR}/cross-accept-verdict.json"
CROSS_MANIFEST_PATH_TEXT = f"{TRANSITION_DIR}/cross-accept-verdict.manifest.json"
MANIFEST_PATH_TEXT = f"{TRANSITION_DIR}/evidence-manifest.json"
VALIDATOR_PATH_TEXT = "tests/m2/probes/validate_r2_int_010_post_platform_transition.py"
TEST_PATH_TEXT = "tests/m2/probes/test_r2_int_010_post_platform_transition.py"

EVIDENCE_PATH = ROOT / EVIDENCE_PATH_TEXT
EXECUTION_PATH = ROOT / EXECUTION_PATH_TEXT
CROSS_VERDICT_PATH = ROOT / CROSS_VERDICT_PATH_TEXT
CROSS_MANIFEST_PATH = ROOT / CROSS_MANIFEST_PATH_TEXT
MANIFEST_PATH = ROOT / MANIFEST_PATH_TEXT

ARTIFACT_PATHS = [
    EVIDENCE_PATH_TEXT,
    EXECUTION_PATH_TEXT,
    CROSS_VERDICT_PATH_TEXT,
    CROSS_MANIFEST_PATH_TEXT,
    VALIDATOR_PATH_TEXT,
    TEST_PATH_TEXT,
]

RULES_COMMIT = "455cd5d66c683565a4aad7ef8d6523421d37db71"
RULES_TREE = "d74aae0baf791566a770ef1aaed2da7562f681d5"
PLATFORM_COMMIT = "1339c490bd8cae1e2a6e6607fc0f1db019faab64"
PLATFORM_TREE = "25d5645caf883a73f165db0179accbca48ddf526"
PLATFORM_ACCEPT_COMMIT = "65731845177d1657e9f192f3e7c56969ebe81bc5"
PLATFORM_ACCEPT_TREE = "3c176856c7ded8858e9771c94c9f06e1f1cb8da3"
CREATOR_SHA256 = "7e31836febd753ca32dc0b81d9f9d8fc7c15fee123730fc4998ca1ee30b7e3a2"
CROSS_VERDICT_SHA256 = "099aaa7244b4a443e31bcdb733bbef2728de11b5129382328b4274ffe2534185"
CROSS_SOURCE_MANIFEST_SHA256 = "04d3086860294a819da9f3155482c45877e2902a3e306157058bdd1eec1f0bf3"
CROSS_VERDICT_CANONICAL_SHA256 = "5ee8334cd181f19e3f3035f52ee4ef8ceddfeefaab786fe398e144e7874cf18e"
EVIDENCE_CANONICAL_SHA256 = "f337613cffb83f2538a29984a8d781baecc979c5a060b4a6fa5edc26ebebe2d2"
EXECUTION_CANONICAL_SHA256 = "f6efbbeb125462353a823b4cb18b632d6c42ce8a43187f8e48076066da60336c"
CROSS_MANIFEST_CANONICAL_SHA256 = "c75fd7762ef76d10df08faaf535a802f6a788a90d717041b2871f16b78c0f7d5"

OLD_COMMITS = [
    "02f261a326cc7bffead5e6a46017c352f822aa94",
    "c6a840b10db46dc475cd9af9e6a1a13f1e68abd4",
    "65a0a1671720345425e0368136793754567187cc",
]

HISTORICAL_HASHES = {
    "reports/m2/probes/probe-results.json": "154e7c0ddf8ce7b2243ad6c78d10ceb6cddf02c3aeb6592716dcc5ad8fc64218",
    "reports/m2/probes/external-gates.json": "a8951312cb9f23cf3f999a7258900603716ea6f0b4e7f684b8f6a53ed8f13a2d",
    "reports/m2/probes/evidence-manifest.json": "3a48da621e45980d9b2258513954e1f29480fd9e12a35dcd29c12b77015c8ca7",
    "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json": "287708242e1418a7e8a88d4918e049dafdb31ecd498819a5e5b6cd7ce40d81f9",
    "reports/m2/probes/remediations/r2-int-010-rem-001/execution-records.json": "9d3bc8c8e5681d14740fcccf525bcf42087dfe5e7e6287bf50852f43c17475c4",
    "reports/m2/probes/remediations/r2-int-010-rem-001/evidence-manifest.json": "eb5e811122efc10cdd1350b2c44031b9bdd58690482df2105ad35f0c62d1b03e",
    "reports/m2/probes/remediations/r2-int-010-rem-001/provenance-disposition.json": "09425d3f343d0a1141bd06558107b2f6daa4478d02bc4799c751c3ff0aaca36e",
    "reports/m2/probes/external/r2-int-010-platform-acceptance/platform-acceptance.json": "bba1b6f68f30143938c2e22b7bc4a0366549ca1f90a0b81af477f13bd142841e",
    "reports/m2/probes/external/r2-int-010-platform-acceptance/evidence-manifest.json": "bfa8cd4c45f9ea183883798f5e3e35bed36306a44972ee807ac1248f345e988e",
}

EXPECTED_TARGET_PAIR = [
    {"target": "A:rules-residue", "repository": "rules-residue", "commit": RULES_COMMIT, "tree": RULES_TREE},
    {"target": "B:TRPG_PLATFORM", "repository": "TRPG_PLATFORM", "commit": PLATFORM_COMMIT, "tree": PLATFORM_TREE},
]

EXPECTED_ACCEPTED_EVIDENCE = [
    ("XPAIR-R001", "db75643fc902660e88c24d683ae53b54919d2b6837b9c740aa81240bced2dcad", 0, "PASS"),
    ("XPAIR-R002", "0a342feba1207e4cbd325037af07db43a6557c02d6f0260b6dcda3ad318958c1", 0, "PASS"),
    ("XPAIR-R003", "ec55c6a28a1c81a4233ad89775168f2e110d58011d3ee09c650b7873e4a72252", 0, "PASS"),
    ("XPAIR-R005", "33de8ce08e45704c210eb75c70f67e58ff6a169428210e88fc2998e0a6c58b1f", 0, "PASS"),
    ("XPAIR-R006", "e8074783d7d0a1faa5780e8db5c3092d09efca50764d3222aadf5d0511293fb2", 0, "PASS"),
    ("XPAIR-R007", "0e5054f212ea6cc3ee945c8d1948fa98f4f31c85d285b816f020edf72e95c969", 0, "PASS"),
    ("XPAIR-R008", "54c69610e328cb1eb536c9cbe92b3f7fd4c3141c63caf15e2aa0dac8889e2edc", 0, "PASS"),
    ("XPAIR-R010", "ae8b84768255d42c29e3a3807f039c76d582aced46930573516a2c01e87c9bc8", 0, "PASS"),
    ("XPAIR-R011", "8e458edff8b39ad9b1ad7545353018ee303e2821575cf8dec749f9430a6e02c6", 0, "PASS"),
    ("XPAIR-R012", "35aa157b7c894681c06158b93fd1eff49410ef535cb41a8240350d5d7f122555", 0, "PASS"),
    ("XPAIR-R013", "06839ca6dd7121ec6c6bdbbd532404aa1356da07a09a0233b673b875229b194b", 0, "PASS"),
    ("XPAIR-R014", "2a0c6ba383118673eb5157a71b0fce1a3700ba603dccb9a18f262cc9fde59582", 0, "PASS"),
    ("XPAIR-R015", "3425f8bad8e1ec9e3604aead94ec93c0c70470b4a3ca3b9b24c61bd415fd6696", 0, "PASS"),
    ("XPAIR-R016", "2b229cb528fb2d691b0fe693f66cd1463ef6a12d9dcb6d72c29be622fbcdacda", 0, "PASS"),
    ("XPAIR-R017", "a7e678dfc4eee6b33bb44fa26317982d278452509490cec65151e9666ff84a95", 0, "PASS"),
    ("XPAIR-R019", "2b3ea24f88e3e8861fa283dc4f7880e905326c2346535e7adbe846288caa131c", 0, "PASS"),
    ("XPAIR-R020", "3857132fb0c61dc0caf2264d8d76b566c0666ad64acafe4bcdeef8e19aa0d2d4", 0, "PASS"),
    ("XPAIR-R021", "ef7833b8c79088c03b11d6dea8c2c80c58a51e0ea4d8c501bc7a0c48c28d6a53", 1, "PASS"),
    ("XPAIR-R022", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0, "PASS"),
    ("XPAIR-R023", "4a30d5cd98311355960b860569903997ed9dab4365618103f238d6be10aa2263", 0, "PASS"),
    ("XPAIR-R024", "83104cf64827b443697e5a3721465148f5de92c1b0a4cfa19bfad4ebfc2bd2b1", 0, "PASS"),
    ("XPAIR-R025", "5367a92ca1de6b534462d570af9bbdbfacfdd5ef88d7593d9877fad9935f560b", 0, "PASS"),
    ("XPAIR-R026", "4e3bbc90e2cceed51211dcae2237775fa7ac1fddb448ea80aad9dd4b1f6c4f8c", 0, "PASS"),
    ("XPAIR-R027", "4bee340f80d332293ff5b77b77ba14ebb2f6d7553ae7403b4fd0c1cea0c12c32", 0, "PASS"),
    ("XPAIR-R028", "9c02876644020e5c5d1983159324519ae96b06e5cabed26d728ebc694df9d386", 0, "PASS"),
    ("XPAIR-R029", "f48a955fba262d4eff80634e83e1098633599637dbe96cc4e2ac90dc8dc987e2", 0, "PASS"),
    ("XPAIR-R030", "ec55c6a28a1c81a4233ad89775168f2e110d58011d3ee09c650b7873e4a72252", 0, "PASS"),
    ("XPAIR-R031", "54c69610e328cb1eb536c9cbe92b3f7fd4c3141c63caf15e2aa0dac8889e2edc", 0, "PASS"),
    ("XPAIR-R032", "29886a9fdbe97ed98739dacee52d3b632136526bb834ed21adf89fd607ba54d3", 0, "PASS"),
]

EXPECTED_DIAGNOSTICS = [
    ("XPAIR-R004", "f718031b71a6eb82bab59b71d6f3fe40fc7744ce7bfb810d8499a7ac0b9e304c", 1, "FAIL"),
    ("XPAIR-R009", "76f53c01ab6792d2743534544111af503868e6ed61f30b5500974f7fe061e264", 1, "FAIL"),
    ("XPAIR-R018", "958a3c7f5cf56c9d5ace0acfb06bc5c196a33509a3ff48621da2be336098b423", 3, "FAIL"),
]

EXPECTED_PHASE_MAP = [
    ("SOURCE_DOUBLE_BUILD", ["XPAIR-R012", "XPAIR-R013", "XPAIR-R014"]),
    ("HOST_IMPORT_REPACK_REIMPORT", ["XPAIR-R015"]),
    ("CREATOR_REAL_EDIT", ["XPAIR-R016", "XPAIR-R019"]),
    ("CREATOR_REPEAT_DETERMINISM", ["XPAIR-R017", "XPAIR-R019"]),
    ("HOST_RELOAD_AFTER_CREATOR", ["XPAIR-R020"]),
    ("CREATOR_SCHEMA_INVALID_REJECTION", ["XPAIR-R021", "XPAIR-R022"]),
    ("HOST_TYPED_NEGATIVES", ["XPAIR-R023"]),
    ("RULES_SYMLINK_NEGATIVE", ["XPAIR-R024"]),
    ("PLATFORM_REGRESSION", ["XPAIR-R025"]),
    ("RULES_REGRESSION", ["XPAIR-R026", "XPAIR-R027", "XPAIR-R028"]),
    ("IDENTITY_ATTACKS", ["XPAIR-R029"]),
]


class TransitionValidationError(ValueError):
    """Raised when the transition evidence is incomplete, stale, or overclaims."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TransitionValidationError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_constant(value: str) -> None:
    raise TransitionValidationError(f"non-finite JSON constant is forbidden: {value}")


def load_json_text(text: str, context: str = "JSON evidence") -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise TransitionValidationError(f"cannot load {context}: {exc}") from exc
    require(isinstance(value, dict), f"{context} must be an object")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_text(path.read_text(encoding="utf-8"), str(path))
    except (OSError, UnicodeDecodeError) as exc:
        raise TransitionValidationError(f"cannot load JSON evidence {path}: {exc}") from exc


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_historical_artifacts() -> None:
    for path_text, digest in HISTORICAL_HASHES.items():
        path = ROOT / path_text
        require(path.is_file(), f"immutable historical artifact missing: {path_text}")
        require(sha256_path(path) == digest, f"immutable historical artifact changed: {path_text}")

    probe_results = load_json(ROOT / "reports/m2/probes/probe-results.json")
    probe = next((item for item in probe_results.get("probes", []) if item.get("probe_id") == "R2-INT-010"), None)
    require(isinstance(probe, dict), "R2-INT-010 predecessor is missing")
    require(probe.get("execution_status") == "FAIL", "R2-INT-010 predecessor FAIL was rewritten")

    platform = load_json(ROOT / "reports/m2/probes/external/r2-int-010-platform-acceptance/platform-acceptance.json")
    require(platform.get("record_role") == "ACCEPTED_PLATFORM_CAPABILITY_ANTECEDENT_ONLY", "platform antecedent role changed")
    require(platform.get("platform") == {
        "code_commit": PLATFORM_COMMIT,
        "code_tree": PLATFORM_TREE,
        "acceptance_authority_commit": PLATFORM_ACCEPT_COMMIT,
        "acceptance_authority_tree": PLATFORM_ACCEPT_TREE,
        "acceptance_status": "PASS",
        "creator_binary_sha256": CREATOR_SHA256,
    }, "platform independent acceptance identity changed")

    provenance = load_json(ROOT / "reports/m2/probes/remediations/r2-int-010-rem-001/provenance-disposition.json")
    require(
        [item.get("commit") for item in provenance.get("historical_antecedents", [])] == OLD_COMMITS,
        "old provisional commit lineage changed",
    )
    require(
        all(item.get("classification") == "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED" for item in provenance["historical_antecedents"]),
        "old provisional classification changed",
    )
    require(provenance.get("policy") == {
        "may_be_used_as_historical_antecedent": True,
        "may_be_used_as_execution_evidence": False,
        "may_satisfy_post_platform_adapter_gate": False,
        "may_transition_R2_INT_010": False,
    }, "old provisional evidence policy changed")


def validate_evidence(data: dict[str, Any]) -> None:
    require(canonical_sha256(data) == EVIDENCE_CANONICAL_SHA256, "transition evidence semantics changed")
    require(data.get("task_id") == TASK_ID and data.get("evidence_id") == EVIDENCE_ID, "transition evidence identity mismatch")
    require(data.get("nature") == "ADDITIVE_STATUS_TRANSITION_CANDIDATE", "transition nature changed")
    require(data.get("previous_status") == "FAIL", "previous_status was rewritten")
    require(data.get("new_status") == "RESOLVED_ADAPTER", "new_status was forged")
    require(data.get("classification") == "R2_COMPATIBILITY_ADAPTER", "transition classification changed")
    require(data.get("acceptance_state") == {
        "authoritative_r2_int_010": "FAIL",
        "transition_candidate": "IMPLEMENTED_NOT_ACCEPTED",
        "transition_acceptance": "NOT_RUN",
    }, "transition was falsely represented as accepted")
    require(data.get("route_binding") == {
        "route_id": "M2-B001-EXTERNAL-PROBE-UPDATE-001",
        "mode": "IMPLEMENT",
        "milestone": "M2",
        "batch_id": "M2-B001",
        "source_commit": RULES_COMMIT,
        "source_tree": RULES_TREE,
        "binding_digest": "33883e8cc5bd4d3ebf9efa0be52bd9f3cd3ea70a9a5af9f8a1eae6c6d9ec54a7",
        "freshness_status": "PASS",
    }, "transition route binding is stale or altered")
    require(data.get("exact_target_pair") == EXPECTED_TARGET_PAIR, "exact repository target pair changed")
    require(len({item["target"] for item in data["exact_target_pair"]}) == 2, "exact target pair duplicated")
    require(OLD_COMMITS[1] not in {item["commit"] for item in data["exact_target_pair"]}, "old c6 adapter identity substituted")
    require(data.get("creator_identity") == {
        "platform_commit": PLATFORM_COMMIT,
        "platform_tree": PLATFORM_TREE,
        "binary_version": "0.1.0-m1",
        "binary_sha256": CREATOR_SHA256,
    }, "Creator identity changed")
    require(data.get("creator_build") == {
        "source_verdict_evidence_id": "XPAIR-R011",
        "source_command": "bash /tmp/r2-int-010-exact-pair/build_creator.sh",
        "normalized_command": "bash <EXACT_PAIR_AUDIT_ROOT>/build_creator.sh",
        "identity_match": True,
    }, "Creator build command was not preserved from the verified verdict")

    previous = data.get("previous_evidence")
    require(isinstance(previous, list) and len(previous) == 4, "previous evidence chain is missing or duplicated")
    require(len({item["evidence_id"] for item in previous}) == 4, "previous evidence ID duplicated")
    require(previous[0] == {
        "evidence_id": "M2-B001-R2-INT-010",
        "record_role": "STATUS_PREDECESSOR",
        "path": "reports/m2/probes/probe-results.json",
        "sha256": HISTORICAL_HASHES["reports/m2/probes/probe-results.json"],
        "previous_status": "FAIL",
        "disposition": "IMMUTABLE_PREDECESSOR",
    }, "immutable FAIL predecessor changed")
    for item in previous[1:]:
        require(item.get("disposition") == "SUPERSEDED_PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED", "old provisional disposition changed")
        require(item.get("may_be_used_as_execution_evidence") is False, "old provisional evidence promoted to execution authority")
        require(item.get("sha256") == HISTORICAL_HASHES[item["path"]], f"old provisional hash changed: {item['path']}")

    expected_history = [
        {"commit": commit, "classification": "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED"}
        for commit in OLD_COMMITS
    ]
    require(data.get("historical_commits") == expected_history, "old provisional commit dispositions changed")
    require(data.get("execution_authority") == {
        "type": "VERIFIED_PERSISTED_EXACT_PAIR_ACCEPT_VERDICT",
        "artifact": CROSS_VERDICT_PATH_TEXT,
        "sha256": CROSS_VERDICT_SHA256,
        "accepted_evidence_count": 29,
        "old_provisional_used_as_execution_evidence": False,
        "host_creator_rerun_this_transition": False,
    }, "execution authority was changed or old evidence was substituted")

    phases = data.get("phase_results")
    require(isinstance(phases, list) and len(phases) == len(EXPECTED_PHASE_MAP), "phase projection is incomplete")
    phase_map = [(item.get("phase"), item.get("source_verdict_evidence_ids")) for item in phases]
    require(phase_map == EXPECTED_PHASE_MAP, "phase-to-exact-pair evidence mapping changed")
    require(len({item["phase"] for item in phases}) == len(phases), "duplicate phase result")
    for item in phases:
        require(item.get("execution_status") == "PASS", f"phase result changed: {item.get('phase')}")
        require(item.get("evidence_source") == "PERSISTED_EXACT_PAIR_ACCEPT_VERDICT", f"phase authority changed: {item.get('phase')}")

    require(data.get("non_claims") == {
        "formal_B002": {"execution_status": "NOT_RUN", "claimed": False},
        "formal_B009": {"execution_status": "NOT_RUN", "claimed": False},
        "aggregate_status": "NOT_CLAIMED",
    }, "formal or aggregate scope was promoted")
    require(data.get("readiness_projection") == {
        "M2-B002_READY": "NO",
        "M2-B002": "NOT_STARTED",
        "blocking_ids": ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"],
        "projection_only": True,
    }, "M2-B002 readiness was forged")

    antecedents = data.get("antecedents", {})
    require(antecedents.get("platform_independent_acceptance", {}).get("result") == "PASS", "platform acceptance antecedent missing")
    require(antecedents["platform_independent_acceptance"].get("acceptance_authority_commit") == PLATFORM_ACCEPT_COMMIT, "platform acceptance authority changed")
    require(antecedents.get("rules_adapter_independent_acceptance", {}).get("result") == "PASS", "rules adapter independent acceptance missing")
    require(antecedents["rules_adapter_independent_acceptance"].get("commit") == RULES_COMMIT, "rules adapter acceptance identity changed")
    require(antecedents.get("exact_pair_cross_repository_acceptance") == {
        "result": "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED",
        "source_verdict_sha256": CROSS_VERDICT_SHA256,
        "persisted_verdict_path": CROSS_VERDICT_PATH_TEXT,
        "accepted_evidence_count": 29,
    }, "exact-pair acceptance antecedent changed")


def validate_execution(data: dict[str, Any]) -> None:
    require(canonical_sha256(data) == EXECUTION_CANONICAL_SHA256, "transition execution-record semantics changed")
    require(data.get("evidence_set_id") == EVIDENCE_ID and data.get("task_id") == TASK_ID, "execution-record identity mismatch")
    require(data.get("previous_status") == "FAIL", "execution records rewrote previous_status")
    require(data.get("source_phase") == "VERIFIED_EXACT_PAIR_ACCEPT_VERDICT_PROJECTION", "execution source phase changed")
    require(data.get("execution_scope") == {
        "host_creator_rerun": False,
        "execution_authority": "PERSISTED_EXACT_PAIR_ACCEPT_VERDICT",
        "old_j_records_reused": False,
    }, "transition execution scope was misrepresented")
    records = data.get("records")
    require(isinstance(records, list) and len(records) == 14, "T-series verification records are incomplete")
    expected_ids = [f"T-R{number:03d}" for number in range(1, 15)]
    ids = [item.get("evidence_id") for item in records]
    require(ids == expected_ids and len(ids) == len(set(ids)), "T-series evidence IDs are missing, duplicated, or reordered")
    require(all(not item["evidence_id"].startswith("J-") for item in records), "old J-series record reused")
    require(all(item.get("exit_code") == 0 and item.get("verification_status") == "PASS" for item in records), "transition verification record failed or changed")
    require(records[8]["observed"] == {"accepted_evidence_count": 29, "unique_evidence_ids": 29, "verified_log_hashes": 29}, "29-evidence integrity record changed")
    require(records[9]["observed"].get("previous_status") == "FAIL", "previous FAIL execution record changed")
    require(records[10]["observed"].get("may_be_used_as_execution_evidence") is False, "old provisional execution authority forged")
    require(records[11]["observed"] == {"formal_B002": False, "execution_status": "NOT_RUN", "claimed": False}, "formal B002 promoted")
    require(records[12]["observed"] == {"formal_B009": False, "execution_status": "NOT_RUN", "claimed": False}, "formal B009 promoted")
    require(records[13]["observed"]["aggregate_status"] == "NOT_CLAIMED", "aggregate readiness promoted")


def validate_cross_verdict(data: dict[str, Any], check_raw_path: bool = False) -> None:
    if check_raw_path:
        require(sha256_path(CROSS_VERDICT_PATH) == CROSS_VERDICT_SHA256, "persisted exact-pair verdict bytes changed")
    require(canonical_sha256(data) == CROSS_VERDICT_CANONICAL_SHA256, "persisted exact-pair verdict semantics changed")
    require(data.get("result") == "PASS_EXACT_PAIR_CROSS_REPOSITORY_ACCEPTED", "exact-pair result changed")
    identity = data.get("identity", {})
    require(identity.get("rules_commit") == RULES_COMMIT and identity.get("rules_tree") == RULES_TREE, "exact-pair rules identity changed")
    require(identity.get("platform_commit") == PLATFORM_COMMIT and identity.get("platform_tree") == PLATFORM_TREE, "exact-pair platform identity changed")
    require(identity.get("creator_binary_sha256") == CREATOR_SHA256, "exact-pair Creator identity changed")
    require(identity.get("platform_acceptance_authority") == PLATFORM_ACCEPT_COMMIT, "platform acceptance authority changed")
    require(identity.get("platform_acceptance_authority_tree") == PLATFORM_ACCEPT_TREE, "platform acceptance authority tree changed")

    evidence = data.get("evidence")
    require(isinstance(evidence, list) and len(evidence) == 29, "one or more of 29 accepted evidence records is missing")
    observed = [(item.get("evidence_id"), item.get("log_sha256"), item.get("exit_code"), item.get("classification")) for item in evidence]
    require(observed == EXPECTED_ACCEPTED_EVIDENCE, "accepted evidence ID, hash, exit code, or classification changed")
    require(len({item[0] for item in observed}) == 29, "duplicate exact-pair evidence ID")
    diagnostics = data.get("audit_diagnostics")
    observed_diagnostics = [(item.get("evidence_id"), item.get("log_sha256"), item.get("exit_code"), item.get("classification")) for item in diagnostics]
    require(observed_diagnostics == EXPECTED_DIAGNOSTICS, "exact-pair diagnostic audit changed")

    governance = data.get("governance", {})
    require(governance.get("r2_int_010") == "FAIL", "source verdict falsely resolved authoritative R2-INT-010")
    require(governance.get("formal_b002") is False and governance.get("formal_b009") is False, "source verdict promoted formal B002/B009")
    require(governance.get("m2_b002_started") is False, "source verdict forged M2-B002 start")
    require(data.get("antecedents", {}).get("provisional_execution_evidence_used") is False, "old provisional evidence used by source verdict")
    require(all(data.get("binding_attacks", {}).get(key) is True for key in (
        "wrong_platform_identity_rejected",
        "wrong_rules_identity_rejected",
        "wrong_creator_identity_rejected",
        "missing_target_rejected",
        "old_c6_rules_identity_rejected",
        "old_65_evidence_identity_rejected",
        "old_provisional_identity_rejected",
    )), "source verdict binding attack coverage changed")
    creator_build = next(item for item in evidence if item["evidence_id"] == "XPAIR-R011")
    require(creator_build.get("command") == "bash /tmp/r2-int-010-exact-pair/build_creator.sh", "Creator build command changed")


def validate_cross_manifest(data: dict[str, Any]) -> None:
    require(canonical_sha256(data) == CROSS_MANIFEST_CANONICAL_SHA256, "cross-accept manifest semantics changed")
    require(data.get("evidence_set_id") == EVIDENCE_ID and data.get("task_id") == TASK_ID, "cross-accept manifest identity mismatch")
    require(data.get("artifact") == {
        "path": CROSS_VERDICT_PATH_TEXT,
        "sha256": CROSS_VERDICT_SHA256,
        "copy_policy": "BYTE_IDENTICAL_READ_ONLY_SOURCE_VERDICT_COPY",
        "source_path_label": "EXACT_PAIR_ACCEPT_VERDICT_SOURCE",
    }, "cross-accept artifact binding changed")
    source = data.get("source_manifest_verification", {})
    require(source.get("source_manifest_sha256") == CROSS_SOURCE_MANIFEST_SHA256, "source manifest hash changed")
    require(source.get("final_verdict_sha256") == CROSS_VERDICT_SHA256, "source verdict hash changed")
    require(source.get("accepted_evidence_count") == 29 and source.get("evidence_records_all_log_hash_verified") is True, "source evidence integrity claim changed")
    expected_ids = [item[0] for item in EXPECTED_ACCEPTED_EVIDENCE]
    require(data.get("accepted_evidence_ids") == expected_ids, "cross manifest accepted evidence coverage changed")
    require(len(data["accepted_evidence_ids"]) == len(set(data["accepted_evidence_ids"])), "cross manifest evidence ID duplicated")
    require(data.get("diagnostic_evidence_ids") == [item[0] for item in EXPECTED_DIAGNOSTICS], "cross manifest diagnostics changed")


def validate_manifest(data: dict[str, Any]) -> None:
    require(set(data) == {
        "schema_version",
        "evidence_set_id",
        "task_id",
        "artifacts",
        "immutable_historical_artifacts",
        "immutable_predecessor_commits",
        "source_exact_pair",
        "policies",
    }, "evidence manifest fields are missing or unknown")
    require(data.get("schema_version") == "rules-residue.m2.r2-int-010-post-platform-transition-manifest/1.0", "evidence manifest schema version changed")
    require(data.get("evidence_set_id") == EVIDENCE_ID and data.get("task_id") == TASK_ID, "evidence manifest identity mismatch")
    expected_artifacts = [{"path": path_text, "sha256": sha256_path(ROOT / path_text)} for path_text in ARTIFACT_PATHS]
    require(data.get("artifacts") == expected_artifacts, "new artifact missing, altered, reordered, or wrongly hashed")
    expected_historical = [{"path": path_text, "sha256": digest} for path_text, digest in HISTORICAL_HASHES.items()]
    require(data.get("immutable_historical_artifacts") == expected_historical, "immutable predecessor coverage or hash changed")
    expected_commits = [
        {"commit": commit, "classification": "PRE_PLATFORM_PROVISIONAL_NOT_ACCEPTED"}
        for commit in OLD_COMMITS
    ]
    require(data.get("immutable_predecessor_commits") == expected_commits, "immutable predecessor commit disposition changed")
    require(data.get("source_exact_pair") == {
        "source_verdict_sha256": CROSS_VERDICT_SHA256,
        "source_manifest_sha256": CROSS_SOURCE_MANIFEST_SHA256,
        "accepted_evidence_count": 29,
        "source_manifest_verified": True,
    }, "exact-pair source manifest binding changed")
    require(data.get("policies") == {
        "historical_mutation": "REJECT_ANY_CURRENT_BYTE_MISMATCH",
        "evidence_evolution": "ADDITIVE_ONLY",
        "old_provisional_execution_authority": False,
        "transition_acceptance": "NOT_RUN",
        "authoritative_r2_int_010": "FAIL",
        "schema_reuse": "NOT_USED_HARDCODED_PRE_PLATFORM_SCHEMA_LEFT_UNCHANGED",
    }, "transition evidence policy changed")
    validate_historical_artifacts()


def validate_transition(
    evidence_data: dict[str, Any] | None = None,
    execution_data: dict[str, Any] | None = None,
    cross_data: dict[str, Any] | None = None,
    cross_manifest_data: dict[str, Any] | None = None,
    manifest_data: dict[str, Any] | None = None,
) -> None:
    validate_historical_artifacts()
    evidence = evidence_data if evidence_data is not None else load_json(EVIDENCE_PATH)
    execution = execution_data if execution_data is not None else load_json(EXECUTION_PATH)
    cross = cross_data if cross_data is not None else load_json(CROSS_VERDICT_PATH)
    cross_manifest = cross_manifest_data if cross_manifest_data is not None else load_json(CROSS_MANIFEST_PATH)
    manifest = manifest_data if manifest_data is not None else load_json(MANIFEST_PATH)
    validate_evidence(evidence)
    validate_execution(execution)
    validate_cross_verdict(cross, check_raw_path=cross_data is None)
    validate_cross_manifest(cross_manifest)
    validate_manifest(manifest)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="validate the additive evidence transition candidate")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        require(args.validate, "select --validate")
        validate_transition()
        print(json.dumps({
            "task_id": TASK_ID,
            "previous_status": "FAIL",
            "proposed_new_status": "RESOLVED_ADAPTER",
            "validation_status": "PASS",
            "authoritative_r2_int_010": "FAIL",
            "transition_acceptance": "NOT_RUN",
            "formal_B002": False,
            "formal_B009": False,
            "aggregate_status": "NOT_CLAIMED",
        }, sort_keys=True))
        return 0
    except (TransitionValidationError, OSError, UnicodeError, ValueError) as exc:
        print(f"{TASK_ID} transition evidence validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
