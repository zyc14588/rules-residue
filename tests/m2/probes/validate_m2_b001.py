#!/usr/bin/env python3
"""Fail-closed validator and executable reference probes for M2-B001."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SOURCE_COMMIT = "c595ac5257aff83bd69d96e3acd64cf3485dc8cb"
SOURCE_TREE = "877927e564ba781ca5f355a3ec3d5f7da7ce879f"
ROUTE_ID = "M2-B001-CAPABILITY-PROBES-IMPLEMENT"
ROUTE_DIGEST = "e2aacf21c69b34841d84aaae4945f7eab740e8410b50aa3bd3f0c5f9c7c71bad"

RESULT_PATH = ROOT / "reports/m2/probes/probe-results.json"
GATE_PATH = ROOT / "reports/m2/probes/external-gates.json"
MANIFEST_PATH = ROOT / "reports/m2/probes/evidence-manifest.json"
SAFETY_PATH = ROOT / "reports/m2/probes/safety-stage-evidence.json"
VECTOR_PATH = ROOT / "tests/m2/probes/fixtures/local-capability-vectors.json"
PROBE_RESULTS_SHA256 = "154e7c0ddf8ce7b2243ad6c78d10ceb6cddf02c3aeb6592716dcc5ad8fc64218"

EXTERNAL_PACKET_ASSIGNMENTS = {
    "workflow/queue/m2-b001-trpg-platform-probes.json": {
        "task_id": "RR-TASK-2001",
        "external_system": "TRPG_PLATFORM",
        "target": "B:TRPG_PLATFORM",
        "result_path": "reports/m2/probes/external/m2-b001-trpg-platform-result.json",
        "evidence_prefix": "reports/m2/probes/external/m2-b001-trpg-platform-evidence/",
    },
    "workflow/queue/m2-b001-creator-tool-probes.json": {
        "task_id": "RR-TASK-2002",
        "external_system": "Creator Tool",
        "target": "C:Creator Tool",
        "result_path": "reports/m2/probes/external/m2-b001-creator-tool-result.json",
        "evidence_prefix": "reports/m2/probes/external/m2-b001-creator-tool-evidence/",
    },
}

EXTERNAL_GATE_LAYOUT = [
    ("EXT-TRPG-SEATS", "B:TRPG_PLATFORM", ["R2-INT-001"], "BLOCKING_FOR_BATCH"),
    ("EXT-TRPG-DECEASED-VIEW", "B:TRPG_PLATFORM", ["R2-INT-002"], "BLOCKING_FOR_BATCH"),
    ("EXT-TRPG-INTENT-WARNINGS", "B:TRPG_PLATFORM", ["R2-INT-003", "R2-INT-004"], "BLOCKING_FOR_BATCH"),
    ("EXT-TRPG-PERSISTENCE", "B:TRPG_PLATFORM", ["R2-INT-005"], "BLOCKING_FOR_BATCH"),
    ("EXT-TRPG-LINEAGE-UNLOCK", "B:TRPG_PLATFORM", ["R2-INT-006"], "NON_BLOCKING_UNTIL_RELEASE"),
    ("EXT-TRPG-TERMINATION", "B:TRPG_PLATFORM", ["R2-INT-008"], "BLOCKING_FOR_BATCH"),
    ("EXT-TRPG-CONTEXT-ISOLATION", "B:TRPG_PLATFORM", ["R2-INT-009"], "BLOCKING_FOR_BATCH"),
    ("EXT-CREATOR-EXTENSIONS", "C:Creator Tool", ["R2-INT-006", "R2-INT-010"], "BLOCKING_FOR_BATCH"),
    ("EXT-RUNTIME-SAFETY", "B:TRPG_PLATFORM", ["R2-INT-010", "R2-INT-011", "R2-INT-012"], "BLOCKING_FOR_M2_ACCEPTANCE"),
    ("EXT-CREATOR-PACKAGE-ROUNDTRIP", "C:Creator Tool", ["R2-INT-001", "R2-INT-011"], "BLOCKING_FOR_M2_ACCEPTANCE"),
]

ALLOWED_STATUSES = {
    "PASS",
    "FAIL",
    "NOT_RUN",
    "BLOCKED_EXTERNAL",
    "BLOCKED_ENVIRONMENT",
}

FROZEN_REQUIREMENTS = {
    "R2-INT-001": "A standard package and host can declare, create, persist, reconnect, and authorize 2 through 6 player seats without a hard four-player ceiling.",
    "R2-INT-002": "After one death, the host provides a private tethered deceased projection and strict action whitelist while rejecting living chat and out-of-range actions.",
    "R2-INT-003": "A multi-step in-world action contract accepts exact terminal intent without a final popup and rejects discussion, hypotheses, and observation.",
    "R2-INT-004": "Platform safety/legal warnings stay distinct from puzzle signals while anomaly entry and campaign termination remain conspicuously warned in-world.",
    "R2-INT-005": "Long campaigns support stable-boundary saves, package/content version locks, reload without reroll, and multi-session replay.",
    "R2-INT-006": "A lineage/account true-ending unlock can be declared without inheriting answers, rules, costs, anchors, anomalies, or key-item state.",
    "R2-INT-007": "Six observation interfaces coexist with exactly one real M2_TEST_REGION and five interface-only fixtures.",
    "R2-INT-008": "A package emits an auditable campaign-termination event that freezes the causal chain, removes every action, and cannot be ordinarily rolled back.",
    "R2-INT-009": "Player memory claims, world evidence, Agent memory, and authority state are separate stores with explicit one-way projections.",
    "R2-INT-010": "Namespaced equipment-rule extensions survive manifest validation, host load, Creator import/edit/export, and runtime execution without a privileged format.",
    "R2-INT-011": "Every safety stage emits fresh evidence, including runtime generation, restore, migration/hot update, asset import, build, and independent acceptance.",
    "R2-INT-012": "Logical abnormality is deterministic rules, scopes, priorities, exceptions/collisions, and seeded answers rather than engine nondeterminism.",
}

CLASSIFICATIONS = {
    "R2-INT-001": "PLATFORM_CAPABILITY_PROBE",
    "R2-INT-002": "PLATFORM_CAPABILITY_PROBE",
    "R2-INT-003": "R2_COMPATIBILITY_ADAPTER",
    "R2-INT-004": "R2_COMPATIBILITY_ADAPTER",
    "R2-INT-005": "PLATFORM_CAPABILITY_PROBE",
    "R2-INT-006": "PLATFORM_CAPABILITY_PROBE",
    "R2-INT-007": "PACKAGE_DECLARABLE",
    "R2-INT-008": "PLATFORM_CAPABILITY_PROBE",
    "R2-INT-009": "PACKAGE_DECLARABLE",
    "R2-INT-010": "R2_COMPATIBILITY_ADAPTER",
    "R2-INT-011": "PLATFORM_CAPABILITY_PROBE",
    "R2-INT-012": "R2_COMPATIBILITY_ADAPTER",
}

BLOCKS = {
    "R2-INT-001": ["M2-B006", "M2-B015", "M2-B016"],
    "R2-INT-002": ["M2-B006", "M2-B015", "M2-B016"],
    "R2-INT-003": ["M2-B010", "M2-B012", "M2-B015"],
    "R2-INT-004": ["M2-B008", "M2-B010", "M2-B015"],
    "R2-INT-005": ["M2-B005", "M2-B015", "M2-B016"],
    "R2-INT-006": [],
    "R2-INT-007": ["M2-B011"],
    "R2-INT-008": ["M2-B012", "M2-B015", "M2-B016"],
    "R2-INT-009": ["M2-B003", "M2-B010", "M2-B015"],
    "R2-INT-010": ["M2-B002", "M2-B009", "M2-B015"],
    "R2-INT-011": [
        "M2-B001", "M2-B002", "M2-B003", "M2-B004", "M2-B005",
        "M2-B006", "M2-B007", "M2-B008", "M2-B009", "M2-B010",
        "M2-B011", "M2-B012", "M2-B013", "M2-B014", "M2-B015", "M2-B016",
    ],
    "R2-INT-012": ["M2-B002", "M2-B004", "M2-B008"],
}


def is_allowed_candidate_path(path: str) -> bool:
    if path.startswith((
        "docs/implementation/m2/probes/",
        "tests/m2/probes/",
        "reports/m2/probes/",
    )):
        return True
    if re.fullmatch(r"workflow/queue/m2-b001-[^/]+\.json", path):
        return True
    return re.fullmatch(r"\.codex/routes/m2-b001-[^/]+\.json", path) is not None


class ProbeValidationError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProbeValidationError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProbeValidationError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeValidationError(message)


def reference_intent(vector: dict[str, Any]) -> str:
    if (
        vector.get("prepared") is True
        and vector.get("authorized") is True
        and vector.get("intent_kind") == "commit_irreversible_world_action"
    ):
        return "ACCEPT_TERMINAL_WITHOUT_SECOND_POPUP"
    return "REJECT_NO_MUTATION"


def check_seats(vectors: dict[str, Any]) -> dict[str, Any]:
    seat = vectors["seat_matrix"]
    require(seat["player_counts"] == [2, 3, 4, 5, 6], "seat matrix does not cover 2 through 6")
    require(seat["hard_cap"] is None, "local seat declaration imposes a hard cap")
    require(seat["standard_path_required"] is True, "seat fixture allows a privileged path")
    require(set(seat["required_lifecycle"]) == {"declare", "create", "join", "save", "reload", "reconnect", "authorize"}, "seat lifecycle is incomplete")
    return {"probe_id": "R2-INT-001", "execution_status": "PASS", "counts": seat["player_counts"]}


def check_deceased(vectors: dict[str, Any]) -> dict[str, Any]:
    deceased = vectors["deceased_projection"]
    require(deceased["role_transition"] == "LIVING_TO_DECEASED", "deceased role transition changed")
    projection = deceased["projection"]
    require(projection == {"private_per_seat": True, "tether_required": True, "living_chat_visible": False}, "deceased projection privacy/tether changed")
    require(set(deceased["allowed_actions"]) == {"observe_tethered", "paid_trace"}, "deceased whitelist changed")
    require(set(deceased["rejected_actions"]) == {"living_chat", "out_of_tether", "unauthorized_intervention"}, "deceased rejection set changed")
    require(deceased["audit_every_decision"] is True, "deceased actions are not audited")
    return {"probe_id": "R2-INT-002", "execution_status": "PASS", "whitelist": deceased["allowed_actions"]}


def check_intent(vectors: dict[str, Any]) -> dict[str, Any]:
    cases = vectors["intent_adapter"]["vectors"]
    require(len(cases) >= 7, "intent corpus is incomplete")
    observed = {case["id"]: reference_intent(case) for case in cases}
    expected = {case["id"]: case["expected"] for case in cases}
    require(observed == expected, "intent corpus result differs from expected")
    require(
        sum(value == "ACCEPT_TERMINAL_WITHOUT_SECOND_POPUP" for value in observed.values()) == 1,
        "exactly one intent vector must commit",
    )
    return {"probe_id": "R2-INT-003", "execution_status": "PASS", "cases": observed}


def check_warnings(vectors: dict[str, Any]) -> dict[str, Any]:
    cases = {case["id"]: case for case in vectors["warning_adapter"]["vectors"]}
    require(cases["ordinary_hazard"]["conspicuous"] is False, "ordinary hazard became a mandatory hint")
    for identity in ("platform_safety", "logical_anomaly_entry", "campaign_termination"):
        require(cases[identity]["conspicuous"] is True, f"{identity} must be conspicuous")
    for case in cases.values():
        require(case["reveals_answer"] is False, "warning discloses a puzzle answer")
        require(case["accessible_equivalent"] is True, "warning lacks accessible equivalent")
    return {"probe_id": "R2-INT-004", "execution_status": "PASS", "cases": sorted(cases)}


def check_persistence(vectors: dict[str, Any]) -> dict[str, Any]:
    persistence = vectors["persistence_reference"]
    require(persistence["stable_boundary"] is True, "save boundary is not stable")
    require(set(persistence["binding_fields"]) == {"package_version", "content_version", "seed_answer_hash", "event_log_hash"}, "save/version binding is incomplete")
    require(persistence["reload_rerolls"] is False, "reload may reroll the answer")
    require(persistence["accelerated_event_counts"] == [0, 1000, 10000], "accelerated persistence volumes changed")
    return {"probe_id": "R2-INT-005", "execution_status": "PASS", "event_counts": persistence["accelerated_event_counts"]}


def check_lineage(vectors: dict[str, Any]) -> dict[str, Any]:
    lineage = vectors["lineage_unlock"]
    require(lineage["cross_campaign_fields"] == ["opaque_true_ending_unlock"], "lineage unlock crosses more than one opaque flag")
    require(set(lineage["forbidden_inheritance"]) == {"answers", "rules", "costs", "anchors", "anomalies", "key_item_state"}, "lineage negative inheritance matrix changed")
    require(lineage["production_value"] == "DEFERRED", "B001 guessed the production unlock value")
    return {"probe_id": "R2-INT-006", "execution_status": "PASS", "cross_campaign_fields": lineage["cross_campaign_fields"]}


def check_observations(vectors: dict[str, Any]) -> dict[str, Any]:
    interfaces = vectors["observation_interfaces"]
    ids = [item["interface_id"] for item in interfaces]
    real = [item for item in interfaces if item["implementation"] == "REAL_TEST_INTERFACE"]
    fixtures = [item for item in interfaces if item["implementation"] == "TEST_ONLY_FIXTURE"]
    require(len(interfaces) == 6 and len(set(ids)) == 6, "six unique observation interfaces are required")
    require(len(real) == 1 and real[0]["region_role"] == "M2_TEST_REGION", "exactly one test-region interface is required")
    require(len(fixtures) == 5 and all(item["region_role"] == "INTERFACE_ONLY" for item in fixtures), "five interface-only fixtures are required")
    require(all(item["release_eligible"] is False for item in interfaces), "B001 interface fixture cannot claim release eligibility")
    return {"probe_id": "R2-INT-007", "execution_status": "PASS", "interface_ids": ids}


def check_memory(vectors: dict[str, Any]) -> dict[str, Any]:
    memory = vectors["memory_separation"]
    required_stores = {"player_memory_claim", "world_evidence", "agent_memory", "authority_state"}
    require(set(memory["stores"]) == required_stores, "memory fixture must contain four distinct stores")
    promotions = {(item["from"], item["to"], item["requires"]) for item in memory["allowed_promotions"]}
    require(promotions == {("world_evidence", "authority_state", "explicit_validation")}, "authority promotion was widened")
    forbidden = {(item["from"], item["to"]) for item in memory["forbidden_promotions"]}
    require(("player_memory_claim", "authority_state") in forbidden, "player memory can reach authority")
    require(("agent_memory", "authority_state") in forbidden, "Agent memory can reach authority")
    require("unrelated_authority_truth" in memory["excluded_from_ordinary_ai"], "ordinary AI received unrelated authority truth")
    return {"probe_id": "R2-INT-009", "execution_status": "PASS", "stores": sorted(required_stores)}


def check_termination(vectors: dict[str, Any]) -> dict[str, Any]:
    termination = vectors["termination_reference"]
    require(termination["event_type"] == "CAMPAIGN_TERMINATED", "termination event type changed")
    require(termination["threshold_state"] == "ACCEPTED_IMMUTABLE", "termination threshold is reversible")
    require(termination["causal_chain_frozen"] is True, "termination does not freeze the causal chain")
    require(set(termination["post_threshold_action_classes"]) == {"world_action", "chat_action", "host_action", "ai_action", "rollback_action"}, "post-threshold revocation is incomplete")
    require(termination["expected_authorization"] == "REJECT_AND_AUDIT", "post-threshold action is not rejected/audited")
    return {"probe_id": "R2-INT-008", "execution_status": "PASS", "revoked": termination["post_threshold_action_classes"]}


def check_equipment(vectors: dict[str, Any]) -> dict[str, Any]:
    equipment = vectors["equipment_extension"]
    require(equipment["namespace"] == "org.trpgplatform.rules-residue/equipment-rule", "equipment extension namespace changed")
    require({item["semantic_kind"] for item in equipment["fixtures"]} == {"LONG_RULE", "SHORT_RULE"}, "long/short equipment fixtures are incomplete")
    require(equipment["unknown_field_policy"] == "REJECT", "equipment extension accepts unknown fields")
    require(equipment["privileged_official_format"] is False, "equipment extension uses a privileged format")
    return {"probe_id": "R2-INT-010", "execution_status": "PASS", "fixture_ids": [item["id"] for item in equipment["fixtures"]]}


def anomaly_effect(anomaly: dict[str, Any], seed: str, has_token: bool) -> str:
    variant = anomaly["seed_profiles"][seed]["variant"]
    applicable: list[dict[str, Any]] = []
    for rule in anomaly["rules"]:
        condition = rule["condition"]
        if condition == "always":
            applicable.append(rule)
        elif condition == "seed_variant_is_mirror" and variant == "mirror":
            applicable.append(rule)
        elif condition == "has_permit_token" and has_token:
            applicable.append(rule)
    require(applicable, "logical anomaly has no applicable rule")
    return max(applicable, key=lambda rule: (rule["priority"], rule["rule_id"]))["effect"]


def check_anomaly(vectors: dict[str, Any]) -> dict[str, Any]:
    anomaly = vectors["logical_anomaly"]
    for rule in anomaly["rules"]:
        for field in ("rule_id", "scope", "trigger", "condition", "effect", "priority", "exceptions", "conflicts"):
            require(field in rule, f"logical rule lacks {field}")
    observed: dict[str, str] = {}
    for case in anomaly["cases"]:
        first = anomaly_effect(anomaly, case["seed"], case["has_permit_token"])
        repeat = anomaly_effect(anomaly, case["seed"], case["has_permit_token"])
        restored = anomaly_effect(copy.deepcopy(anomaly), case["seed"], case["has_permit_token"])
        require(first == repeat == restored == case["expected_effect"], f"nondeterministic anomaly case {case['case_id']}")
        observed[case["case_id"]] = first
    require(observed["alpha-no-token"] != observed["beta-no-token"], "controlled seed difference is missing")
    for case_id in anomaly["no_death_solution_case_ids"]:
        require(observed[case_id] == "ALLOWED", f"no-death solution {case_id} is not allowed")
    return {"probe_id": "R2-INT-012", "execution_status": "PASS", "trace": observed}


def validate_safety_evidence(data: dict[str, Any], vectors: dict[str, Any]) -> None:
    require(data.get("schema_version") == "rules-residue.m2.safety-stage-evidence/1.0", "invalid safety evidence version")
    require(data.get("batch_id") == "M2-B001", "safety evidence batch mismatch")
    source_hash = sha256_path(VECTOR_PATH)
    records = data.get("records")
    require(isinstance(records, list) and records, "safety records are missing")
    run_ids: set[str] = set()
    for record in records:
        require(record.get("source_sha256") == source_hash, f"stale safety evidence for {record.get('stage_id')}")
        require(record.get("run_id") not in run_ids, "safety stage reused another stage's run id")
        run_ids.add(record["run_id"])
        require(record.get("execution_status") in ALLOWED_STATUSES | {"NOT_APPLICABLE"}, "invalid safety stage status")
        if record.get("execution_status") == "PASS":
            require(record.get("decision") == "ALLOW", "passing safety stage did not allow the benign object")
    negative = data.get("symbolic_negative_control")
    require(negative == vectors["safety"]["absolute_reject_vector"], "absolute-reject control was weakened")
    require(negative["decision"] == "REJECT_AND_REDESIGN", "absolute-reject control was not rejected")


def check_safety(vectors: dict[str, Any]) -> dict[str, Any]:
    data = load_json(SAFETY_PATH)
    validate_safety_evidence(data, vectors)
    statuses = {record["stage_id"]: record["execution_status"] for record in data["records"]}
    return {"probe_id": "R2-INT-011", "execution_status": "BLOCKED_EXTERNAL", "stages": statuses}


LOCAL_CHECKS = {
    "R2-INT-001": check_seats,
    "R2-INT-002": check_deceased,
    "R2-INT-003": check_intent,
    "R2-INT-004": check_warnings,
    "R2-INT-005": check_persistence,
    "R2-INT-006": check_lineage,
    "R2-INT-007": check_observations,
    "R2-INT-008": check_termination,
    "R2-INT-009": check_memory,
    "R2-INT-010": check_equipment,
    "R2-INT-011": check_safety,
    "R2-INT-012": check_anomaly,
}


def run_local_check(probe_id: str, vectors: dict[str, Any] | None = None) -> dict[str, Any]:
    require(probe_id in LOCAL_CHECKS, f"no local executable check for {probe_id}")
    return LOCAL_CHECKS[probe_id](vectors or load_json(VECTOR_PATH))


def validate_source_binding(binding: dict[str, Any]) -> None:
    require(binding == {
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "route_id": ROUTE_ID,
        "route_binding_digest": ROUTE_DIGEST,
    }, "probe source/route binding mismatch")


def validate_probe_results(data: dict[str, Any]) -> None:
    require(data.get("schema_version") == "rules-residue.m2.probe-results/1.0", "invalid probe-result version")
    require(data.get("batch_id") == "M2-B001", "probe-result batch mismatch")
    validate_source_binding(data.get("source_binding", {}))
    probes = data.get("probes")
    require(isinstance(probes, list) and len(probes) == 12, "exactly twelve probe results are required")
    require({probe.get("probe_id") for probe in probes} == set(FROZEN_REQUIREMENTS), "probe ID set is incomplete or duplicated")

    required_fields = {
        "probe_id", "r2_requirement", "classification", "target_system", "existing_capability",
        "probe_procedure", "commands_actions_actually_run", "evidence_paths", "observed_result",
        "expected_result", "execution_status", "root_cause", "adapter_feasibility",
        "platform_change_necessity", "downstream_blocked_batches", "target_results", "candidate_binding",
    }
    for probe in probes:
        probe_id = probe["probe_id"]
        require(set(probe) == required_fields, f"{probe_id} fields differ from the frozen result contract")
        require(probe["r2_requirement"] == FROZEN_REQUIREMENTS[probe_id], f"{probe_id} lowers or changes the R2 requirement")
        require(probe["classification"] == CLASSIFICATIONS[probe_id], f"{probe_id} classification changed")
        require(probe["execution_status"] in ALLOWED_STATUSES, f"{probe_id} has invalid execution status")
        expected_blocks = [] if probe["execution_status"] == "PASS" else BLOCKS[probe_id]
        require(probe["downstream_blocked_batches"] == expected_blocks, f"{probe_id} actual downstream blockers are inaccurate")
        require(probe["probe_procedure"] and probe["evidence_paths"], f"{probe_id} lacks procedure/evidence")
        for path_text in probe["evidence_paths"]:
            require((ROOT / path_text).exists(), f"{probe_id} evidence path does not exist: {path_text}")

        adapter = probe["adapter_feasibility"]
        require(adapter.get("preserves_r2") is True, f"{probe_id} adapter lowers R2")
        require(adapter.get("local_status") in ALLOWED_STATUSES, f"{probe_id} adapter status invalid")
        necessity = probe["platform_change_necessity"]
        require(necessity.get("state") in {"NOT_NEEDED", "CONDITIONAL_PROPOSAL", "PROPOSAL_REQUIRED"}, f"{probe_id} platform-change state invalid")
        require(necessity.get("approval_status") in {"NOT_REQUIRED", "NOT_APPROVED", "APPROVED_WITH_BOUND_EVIDENCE"}, f"{probe_id} approval state invalid")
        if necessity["state"] != "NOT_NEEDED":
            require(necessity["approval_status"] != "NOT_REQUIRED", f"{probe_id} proposal was treated as unnecessary approval")

        binding = probe["candidate_binding"]
        require(binding == {
            "strategy": "EXACT_HEAD_AT_VALIDATION",
            "required_source_commit": SOURCE_COMMIT,
            "required_source_tree": SOURCE_TREE,
            "route_binding_digest": ROUTE_DIGEST,
            "evidence_manifest": "reports/m2/probes/evidence-manifest.json",
            "must_be_clean": True,
        }, f"{probe_id} candidate binding is incomplete or stale")

        target_results = probe["target_results"]
        require(isinstance(target_results, list) and target_results, f"{probe_id} target results missing")
        target_names = [target["target"] for target in target_results]
        require(target_names == probe["target_system"], f"{probe_id} target order/identity mismatch")
        for target in target_results:
            require(target["execution_status"] in ALLOWED_STATUSES, f"{probe_id} target status invalid")
            require(target["evidence_paths"], f"{probe_id} target evidence missing")
        if probe["execution_status"] == "PASS":
            require(all(target["execution_status"] == "PASS" for target in target_results), f"{probe_id} maps an incomplete target to PASS")
            commands = probe["commands_actions_actually_run"]
            require(commands and all(command["exit_code"] == 0 for command in commands), f"{probe_id} PASS lacks successful command evidence")
            require(necessity["approval_status"] != "NOT_APPROVED", f"{probe_id} treats a proposal as approval")
        elif any(target["execution_status"] in {"BLOCKED_EXTERNAL", "BLOCKED_ENVIRONMENT"} for target in target_results):
            require(probe["execution_status"] in {"BLOCKED_EXTERNAL", "BLOCKED_ENVIRONMENT", "FAIL"}, f"{probe_id} hides a blocked target")

        for command in probe["commands_actions_actually_run"]:
            require(set(command) == {"command", "exit_code", "observed_output", "output_sha256", "evidence_path"}, f"{probe_id} command evidence fields invalid")
            require(re.fullmatch(r"[0-9a-f]{64}", command["output_sha256"]) is not None, f"{probe_id} command digest invalid")
            require((ROOT / command["evidence_path"]).exists(), f"{probe_id} command evidence path missing")


def repository_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ProbeValidationError(f"path escapes the repository: {path}") from exc


def frozen_probe_map() -> dict[str, dict[str, Any]]:
    require(sha256_path(RESULT_PATH) == PROBE_RESULTS_SHA256, "frozen probe results changed")
    results = load_json(RESULT_PATH).get("probes")
    require(isinstance(results, list), "frozen probe results are missing")
    mapping = {probe.get("probe_id"): probe for probe in results}
    require(len(mapping) == len(results) == 12, "frozen probe results are incomplete or duplicated")
    return mapping


def packet_assignment(packet: dict[str, Any], packet_path: Path | None = None) -> tuple[str, dict[str, str]]:
    by_task = {
        assignment["task_id"]: (path, assignment)
        for path, assignment in EXTERNAL_PACKET_ASSIGNMENTS.items()
    }
    expected = by_task.get(packet.get("task_id"))
    require(expected is not None, f"Task Packet {packet.get('task_id')} is not assigned to M2-B001 external probes")
    expected_path, assignment = expected
    if packet_path is not None:
        require(repository_relative(packet_path) == expected_path, "Task Packet path/identity mismatch")
    return expected_path, assignment


def assigned_probe_ids(target: str) -> list[str]:
    return [
        probe_id
        for probe_id, probe in frozen_probe_map().items()
        if target in [item.get("target") for item in probe.get("target_results", [])]
    ]


def validate_task_packet(packet: dict[str, Any], packet_path: Path | None = None) -> None:
    required = {
        "schema_version", "task_id", "status", "owner", "task_type", "objective", "authority",
        "inputs", "allowed_paths", "forbidden_paths", "open_decisions", "acceptance", "expected_outputs", "notes",
    }
    require(set(packet) == required, f"Task Packet {packet.get('task_id')} fields do not match task-packet/1.0")
    require(packet["schema_version"] == "rules-residue.task-packet/1.0", "Task Packet schema version mismatch")
    require(re.fullmatch(r"RR-TASK-[0-9]{4,}", packet["task_id"]) is not None, "Task Packet ID invalid")
    require(packet["status"] == "PLANNED", "external packet must remain PLANNED before a bound return")
    require(packet["owner"] == "codex" and packet["task_type"] == "acceptance", "external probe packet has wrong role")
    for name in ("authority", "allowed_paths", "forbidden_paths", "acceptance", "expected_outputs"):
        require(isinstance(packet[name], list) and packet[name], f"Task Packet {name} missing")
    require(SOURCE_COMMIT in packet["notes"] and SOURCE_TREE in packet["notes"], "Task Packet lacks frozen source binding")
    require("exact candidate_commit and candidate_tree" in packet["notes"], "Task Packet does not require exact candidate binding")
    require("proposal is not approval" in packet["notes"], "Task Packet could treat a proposal as approval")
    _, assignment = packet_assignment(packet, packet_path)
    expected_ids = assigned_probe_ids(assignment["target"])
    objective_ids = re.findall(r"R2-INT-[0-9]{3}", packet["objective"])
    require(objective_ids == expected_ids, "Task Packet objective does not exactly enumerate its assigned probes")
    require(assignment["external_system"] in packet["objective"], "Task Packet objective/system mismatch")
    require(packet["allowed_paths"] == [
        assignment["result_path"], assignment["evidence_prefix"] + "**"
    ], "Task Packet output/evidence paths differ from its frozen assignment")


def validate_external_gates(data: dict[str, Any]) -> None:
    require(data.get("schema_version") == "rules-residue.m2.external-gates/1.0", "invalid external-gate version")
    validate_source_binding(data.get("source_binding", {}))
    gates = data.get("gates")
    require(isinstance(gates, list) and len(gates) == 10, "ten frozen external gates are required")
    probe_map = frozen_probe_map()
    packet_for_target = {
        assignment["target"]: path
        for path, assignment in EXTERNAL_PACKET_ASSIGNMENTS.items()
    }
    expected_gates: list[dict[str, Any]] = []
    for gate_id, target, probe_ids, gate_class in EXTERNAL_GATE_LAYOUT:
        packet_text = packet_for_target[target]
        packet_path = ROOT / packet_text
        require(packet_path.is_file(), f"missing external packet {packet_text}")
        validate_task_packet(load_json(packet_path), packet_path)
        blocks = sorted({batch for probe_id in probe_ids for batch in probe_map[probe_id]["downstream_blocked_batches"]})
        expected_gates.append({
            "gate_id": gate_id,
            "target": target,
            "probe_ids": probe_ids,
            "gate_class": gate_class,
            "execution_status": "BLOCKED_EXTERNAL",
            "task_packet": packet_text,
            "task_packet_sha256": sha256_path(packet_path),
            "external_result": None,
            "approval_status": "NOT_APPROVED",
            "blocks": blocks,
        })
    require(gates == expected_gates, "external gates differ from the frozen ID/target/packet/probe/class/blocker mapping")
    required_pairs = {
        (probe_id, target)
        for probe_id, probe in probe_map.items()
        for target in probe["target_system"]
        if target in packet_for_target
    }
    covered_pairs = {
        (probe_id, gate["target"])
        for gate in gates
        for probe_id in gate["probe_ids"]
    }
    require(len(required_pairs) == 15, "frozen external target coverage no longer contains fifteen pairs")
    require(covered_pairs == required_pairs, "external gates do not cover every required probe/target pair exactly once")
    require(sum(len(gate["probe_ids"]) for gate in gates) == len(covered_pairs), "external gate coverage contains duplicate target pairs")


def validate_evidence_manifest(data: dict[str, Any]) -> None:
    require(data.get("schema_version") == "rules-residue.m2.evidence-manifest/1.0", "invalid evidence manifest version")
    validate_source_binding(data.get("source_binding", {}))
    artifacts = data.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, "evidence manifest has no artifacts")
    seen: set[str] = set()
    for artifact in artifacts:
        path_text = artifact.get("path")
        require(path_text not in seen, f"duplicate evidence artifact {path_text}")
        seen.add(path_text)
        path = ROOT / path_text
        require(path.is_file(), f"evidence artifact is absent: {path_text}")
        require(artifact.get("sha256") == sha256_path(path), f"evidence artifact hash mismatch: {path_text}")


def validate_external_evidence_path(path_text: Any, evidence_prefix: str) -> Path:
    require(isinstance(path_text, str) and path_text, "external evidence path is invalid")
    require("\\" not in path_text, f"external evidence path is not portable: {path_text}")
    relative = Path(path_text)
    require(not relative.is_absolute() and ".." not in relative.parts, f"external evidence path escapes the repository: {path_text}")
    require(path_text.startswith(evidence_prefix) and path_text != evidence_prefix, f"external evidence path is outside its Task Packet assignment: {path_text}")
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"external evidence file is absent or unsafe: {path_text}")
    require(repository_relative(path) == path_text, f"external evidence path resolves outside its assignment: {path_text}")
    try:
        tracked = git_output("ls-files", "--error-unmatch", "--", path_text)
    except subprocess.CalledProcessError as exc:
        raise ProbeValidationError(f"external evidence file is not tracked: {path_text}") from exc
    require(tracked == path_text, f"external evidence path does not resolve to one tracked file: {path_text}")
    return path


def validate_external_result(
    data: dict[str, Any], packet_path: Path, candidate_commit: str, candidate_tree: str,
    result_path: Path | None = None,
) -> None:
    required = {
        "schema_version", "task_id", "packet_sha256", "game_source_commit", "game_source_tree",
        "game_candidate_commit", "game_candidate_tree", "external_system", "probe_results", "commands",
        "evidence_paths", "evidence_artifacts",
    }
    require(set(data) == required, "external result is unbound or has unknown fields")
    packet = load_json(packet_path)
    validate_task_packet(packet, packet_path)
    _, assignment = packet_assignment(packet, packet_path)
    if result_path is not None:
        require(repository_relative(result_path) == assignment["result_path"], "external result file/path does not match its Task Packet")
        require(result_path.is_file() and not result_path.is_symlink(), "external result file is absent or unsafe")
        try:
            tracked_result = git_output("ls-files", "--error-unmatch", "--", assignment["result_path"])
        except subprocess.CalledProcessError as exc:
            raise ProbeValidationError("external result file is not tracked in the exact candidate") from exc
        require(tracked_result == assignment["result_path"], "external result path does not resolve to one tracked file")
    require(data["schema_version"] == "rules-residue.m2.external-probe-result/1.0", "external result version mismatch")
    require(data["task_id"] == packet["task_id"], "external result Task Packet mismatch")
    require(data["packet_sha256"] == sha256_path(packet_path), "external result packet binding is stale")
    require(data["game_source_commit"] == SOURCE_COMMIT and data["game_source_tree"] == SOURCE_TREE, "external result source binding is stale")
    require(data["game_candidate_commit"] == candidate_commit and data["game_candidate_tree"] == candidate_tree, "external result candidate binding is stale")
    system = data.get("external_system")
    require(isinstance(system, dict), "external system identity missing")
    require(set(system) == {"name", "repository_commit", "repository_tree", "tracked_worktree_clean", "identity_command_ids"}, "external system identity incomplete")
    require(system["name"] == assignment["external_system"], "external result packet/system mismatch")
    require(system["tracked_worktree_clean"] is True, "external result came from a dirty tracked worktree")
    require(re.fullmatch(r"[0-9a-f]{40}", system["repository_commit"]) is not None and system["repository_commit"] != "0" * 40, "external commit missing")
    require(re.fullmatch(r"[0-9a-f]{40}", system["repository_tree"]) is not None and system["repository_tree"] != "0" * 40, "external tree missing")
    require(system["repository_commit"] != system["repository_tree"], "external commit/tree identity is not credible")
    probe_results = data.get("probe_results")
    expected_probe_ids = assigned_probe_ids(assignment["target"])
    require(isinstance(probe_results, list) and len(probe_results) == len(expected_probe_ids), "external result has incomplete assigned-probe coverage")
    actual_probe_ids = [result.get("probe_id") for result in probe_results if isinstance(result, dict)]
    require(actual_probe_ids == expected_probe_ids and len(set(actual_probe_ids)) == len(actual_probe_ids), "external assigned probes are missing, duplicated, or reordered")
    probe_map = frozen_probe_map()
    for result in probe_results:
        probe_id = result["probe_id"]
        require(set(result) == {"probe_id", "target", "execution_status", "observed_result", "procedure_results"}, f"external result fields invalid for {probe_id}")
        require(result["target"] == assignment["target"], f"external result target mismatch for {probe_id}")
        procedures = result["procedure_results"]
        expected_procedures = probe_map[probe_id]["probe_procedure"]
        require(isinstance(procedures, list) and len(procedures) == len(expected_procedures), f"external procedure coverage incomplete for {probe_id}")
        actual_procedures = [procedure.get("procedure") for procedure in procedures if isinstance(procedure, dict)]
        require(actual_procedures == expected_procedures and len(set(actual_procedures)) == len(actual_procedures), f"external procedures are missing, duplicated, or reordered for {probe_id}")

    allowed_external_statuses = {"PASS", "FAIL", "BLOCKED_EXTERNAL", "BLOCKED_ENVIRONMENT"}
    commands = data.get("commands")
    require(isinstance(commands, list) and len(commands) >= 4, "external result lacks identity and execution commands")
    command_by_id: dict[str, dict[str, Any]] = {}
    for command in commands:
        require(isinstance(command, dict) and set(command) == {"command_id", "command", "exit_code", "output_sha256", "evidence_path"}, "external command evidence incomplete")
        command_id = command["command_id"]
        require(isinstance(command_id, str) and re.fullmatch(r"[A-Z][A-Z0-9_-]{2,63}", command_id) is not None, "external command ID invalid")
        require(command_id not in command_by_id, f"duplicate external command ID: {command_id}")
        command_by_id[command_id] = command
        require(isinstance(command["command"], str) and command["command"].strip() not in {"", "true", ":", "/bin/true"}, f"external command {command_id} is not meaningful")
        require(isinstance(command["exit_code"], int) and not isinstance(command["exit_code"], bool) and 0 <= command["exit_code"] <= 255, f"external command {command_id} exit code invalid")
        require(re.fullmatch(r"[0-9a-f]{64}", command["output_sha256"]) is not None and command["output_sha256"] != "0" * 64, f"external command {command_id} digest invalid")

    evidence_paths = data.get("evidence_paths")
    artifacts = data.get("evidence_artifacts")
    require(isinstance(evidence_paths, list) and len(evidence_paths) >= 4 and len(evidence_paths) == len(set(evidence_paths)), "external evidence paths are missing or duplicated")
    require(isinstance(artifacts, list) and len(artifacts) == len(evidence_paths), "external evidence artifact coverage is incomplete")
    artifact_hashes: dict[str, str] = {}
    artifact_paths: dict[str, Path] = {}
    for artifact in artifacts:
        require(isinstance(artifact, dict) and set(artifact) == {"path", "sha256"}, "external evidence artifact fields invalid")
        path_text = artifact["path"]
        require(path_text not in artifact_hashes, f"duplicate external evidence artifact: {path_text}")
        require(re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is not None and artifact["sha256"] != "0" * 64, f"external evidence artifact digest invalid: {path_text}")
        path = validate_external_evidence_path(path_text, assignment["evidence_prefix"])
        actual_hash = sha256_path(path)
        require(artifact["sha256"] == actual_hash, f"external evidence artifact hash is unverifiable: {path_text}")
        artifact_hashes[path_text] = actual_hash
        artifact_paths[path_text] = path
    require(set(evidence_paths) == set(artifact_hashes), "external evidence_paths and evidence_artifacts differ")

    for command_id, command in command_by_id.items():
        require(command["evidence_path"] in artifact_hashes, f"external command {command_id} evidence is not declared")
        require(command["output_sha256"] == artifact_hashes[command["evidence_path"]], f"external command {command_id} output digest does not match its evidence file")

    identity_ids = system["identity_command_ids"]
    require(isinstance(identity_ids, dict) and set(identity_ids) == {"repository_commit", "repository_tree", "tracked_worktree_clean"}, "external identity command mapping incomplete")
    require(len(set(identity_ids.values())) == 3, "external identity commands must be distinct")
    identity_contract = {
        "repository_commit": ("git rev-parse HEAD", system["repository_commit"]),
        "repository_tree": ("git rev-parse HEAD^{tree}", system["repository_tree"]),
        "tracked_worktree_clean": ("git status --short", ""),
    }
    for identity_field, (expected_command, expected_output) in identity_contract.items():
        command_id = identity_ids[identity_field]
        require(command_id in command_by_id, f"external identity evidence missing for {identity_field}")
        command = command_by_id[command_id]
        require(command["command"] == expected_command and command["exit_code"] == 0, f"external identity command invalid for {identity_field}")
        output = artifact_paths[command["evidence_path"]].read_text(encoding="utf-8").strip()
        require(output == expected_output, f"external identity output does not bind {identity_field}")

    referenced_command_ids = set(identity_ids.values())
    referenced_evidence_paths = {command_by_id[command_id]["evidence_path"] for command_id in identity_ids.values()}
    identity_command_ids = set(identity_ids.values())
    for result in probe_results:
        probe_id = result["probe_id"]
        require(result["execution_status"] in allowed_external_statuses, f"external result status invalid for {probe_id}")
        require(isinstance(result["observed_result"], str) and result["observed_result"].strip(), f"external observed result missing for {probe_id}")
        procedures = result["procedure_results"]
        procedure_statuses: list[str] = []
        for procedure in procedures:
            require(set(procedure) == {"procedure", "execution_status", "command_ids", "evidence_paths"}, f"external procedure fields invalid for {probe_id}")
            status = procedure["execution_status"]
            require(status in allowed_external_statuses, f"external procedure status invalid for {probe_id}")
            procedure_statuses.append(status)
            procedure_command_ids = procedure["command_ids"]
            procedure_evidence = procedure["evidence_paths"]
            require(isinstance(procedure_command_ids, list) and len(procedure_command_ids) == len(set(procedure_command_ids)), f"external procedure command references duplicated for {probe_id}")
            require(isinstance(procedure_evidence, list) and procedure_evidence and len(procedure_evidence) == len(set(procedure_evidence)), f"external procedure evidence missing or duplicated for {probe_id}")
            require(all(command_id in command_by_id for command_id in procedure_command_ids), f"external procedure references an unknown command for {probe_id}")
            require(all(path in artifact_hashes for path in procedure_evidence), f"external procedure references undeclared evidence for {probe_id}")
            if status in {"PASS", "FAIL"}:
                require(procedure_command_ids and not identity_command_ids.intersection(procedure_command_ids), f"executed external procedure lacks its own command for {probe_id}")
            if status == "PASS":
                require(all(command_by_id[command_id]["exit_code"] == 0 for command_id in procedure_command_ids), f"passing external procedure contains a failing command for {probe_id}")
            referenced_command_ids.update(procedure_command_ids)
            referenced_evidence_paths.update(procedure_evidence)
        if result["execution_status"] == "PASS":
            require(all(status == "PASS" for status in procedure_statuses), f"external PASS lacks complete successful procedure evidence for {probe_id}")
        elif result["execution_status"] == "FAIL":
            require("FAIL" in procedure_statuses, f"external FAIL lacks a failed procedure for {probe_id}")
        else:
            require(result["execution_status"] in procedure_statuses and "FAIL" not in procedure_statuses, f"external blocked status is not supported by its procedures for {probe_id}")

    require(referenced_command_ids == set(command_by_id), "external result contains an unbound command record")
    referenced_evidence_paths.update(command["evidence_path"] for command in commands)
    require(referenced_evidence_paths == set(artifact_hashes), "external result contains unbound or unused evidence")


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return completed.stdout.strip()


def validate_candidate(candidate_commit: str, candidate_tree: str, manifest: dict[str, Any]) -> None:
    resolved_commit = git_output("rev-parse", candidate_commit)
    require(re.fullmatch(r"[0-9a-f]{40}", resolved_commit) is not None, "candidate commit cannot be resolved")
    require(git_output("rev-parse", "HEAD") == resolved_commit, "validator is not at the exact candidate commit")
    resolved_tree = git_output("rev-parse", f"{resolved_commit}^{{tree}}")
    require(resolved_tree == candidate_tree, "candidate tree argument mismatch")
    require(git_output("rev-parse", "HEAD^{tree}") == candidate_tree, "checkout tree differs from candidate tree")
    require(git_output("status", "--short") == "", "candidate worktree is not clean")
    subprocess.run(["git", "merge-base", "--is-ancestor", SOURCE_COMMIT, resolved_commit], cwd=ROOT, check=True)
    require(git_output("rev-parse", f"{SOURCE_COMMIT}^{{tree}}") == SOURCE_TREE, "frozen source tree mismatch")
    parent_line = git_output("rev-list", "--parents", "-n", "1", resolved_commit).split()
    require(parent_line == [resolved_commit, SOURCE_COMMIT], "candidate must be exactly one B001 commit atop the frozen source")
    changed = set(git_output("diff", "--name-only", SOURCE_COMMIT, resolved_commit).splitlines())
    require(changed and all(is_allowed_candidate_path(path) for path in changed), "candidate changed a path outside the frozen B001 envelope")
    manifest_paths = {artifact["path"] for artifact in manifest["artifacts"]}
    require(changed == manifest_paths | {"reports/m2/probes/evidence-manifest.json"}, "candidate contains unmanifested or missing B001 artifacts")
    for artifact in manifest["artifacts"]:
        subprocess.run(
            ["git", "cat-file", "-e", f"{resolved_commit}:{artifact['path']}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def validate_all(candidate_commit: str | None = None, candidate_tree: str | None = None) -> None:
    vectors = load_json(VECTOR_PATH)
    for probe_id in LOCAL_CHECKS:
        run_local_check(probe_id, vectors)
    results = load_json(RESULT_PATH)
    validate_probe_results(results)
    validate_external_gates(load_json(GATE_PATH))
    manifest = load_json(MANIFEST_PATH)
    validate_evidence_manifest(manifest)
    validate_safety_evidence(load_json(SAFETY_PATH), vectors)
    if candidate_commit is not None or candidate_tree is not None:
        require(candidate_commit is not None and candidate_tree is not None, "candidate commit and tree are required together")
        validate_candidate(candidate_commit, candidate_tree, manifest)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--local-check", choices=sorted(LOCAL_CHECKS))
    parser.add_argument("--candidate")
    parser.add_argument("--candidate-tree")
    parser.add_argument("--external-result", type=Path)
    parser.add_argument("--packet", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        output: dict[str, Any]
        if args.local_check:
            output = run_local_check(args.local_check)
        elif args.all:
            validate_all(args.candidate, args.candidate_tree)
            output = {
                "batch_id": "M2-B001",
                "execution_status": "PASS",
                "candidate": args.candidate or "DEFERRED_TO_EXACT_HEAD_VALIDATION",
                "route_binding_digest": ROUTE_DIGEST,
            }
        else:
            raise ProbeValidationError("select --all or --local-check")
        if args.external_result or args.packet:
            require(args.external_result is not None and args.packet is not None, "external result and packet are required together")
            require(args.candidate is not None and args.candidate_tree is not None, "bound external validation requires exact candidate")
            validate_external_result(
                load_json(args.external_result), args.packet, args.candidate, args.candidate_tree,
                args.external_result,
            )
            output["external_result"] = "VALID"
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
        return 0
    except (ProbeValidationError, subprocess.CalledProcessError) as exc:
        print(f"M2-B001 probe validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
