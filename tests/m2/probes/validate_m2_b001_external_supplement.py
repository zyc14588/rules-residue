#!/usr/bin/env python3
"""Fail-closed validator for additive M2-B001 external evidence supplements."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BASE_SPEC = importlib.util.spec_from_file_location(
    "m2_b001_historical_validator",
    Path(__file__).with_name("validate_m2_b001.py"),
)
assert BASE_SPEC and BASE_SPEC.loader
base = importlib.util.module_from_spec(BASE_SPEC)
sys.modules[BASE_SPEC.name] = base
BASE_SPEC.loader.exec_module(base)

ProbeValidationError = base.ProbeValidationError

ACCEPTED_B001_COMMIT = "fdc1f4c9d8bc565888f33b44684cd6ccbe80c127"
ACCEPTED_B001_TREE = "f37e15cdd65e0a39eebcddb21f56a2c58ae6939e"
SUPPLEMENT_ID = "M2-B001-EXT-001"
SUPPLEMENT_ROUTE_ID = "M2-B001-EXTERNAL-PROBE-UPDATE-001"
SUPPLEMENT_ROUTE_DIGEST = "12fc07fa8a582c335c87a909795146f41625e182da81ff3383b5a31311a9cb05"
SUPPLEMENT_ROUTE_REQUEST_SHA256 = "5424875d6abfcc15f58ad0a4c00c8eb8fa5d459c950dbd80f54048eae7bf05de"
SUPPLEMENT_CREATED_AT = "2026-08-13T08:54:30Z"
SUPPLEMENT_ROUTE_CHECKED_AT = "2026-08-13T08:39:23Z"

CAPTURE_SOURCE_WORKTREE = "/tmp/rules-residue-b001-external-update"
PLATFORM_REPOSITORY = "/home/zyc14588/TRPG_PLATFORM"
PLATFORM_BRANCH = "m1/b002-lua-runtime"
PLATFORM_COMMIT = "02dd02447ed07fe6248108365847dccf4023ca00"
PLATFORM_TREE = "dc15acda453948fc78afdc259fea3e543f9e001c"

SUPPLEMENT_PATH_TEXT = "reports/m2/probes/external/m2-b001-ext-001/supplement.json"
COMMAND_PATH_TEXT = "reports/m2/probes/external/m2-b001-ext-001/platform-command-evidence.json"
MANIFEST_PATH_TEXT = "reports/m2/probes/external/m2-b001-ext-001/evidence-manifest.json"
INDEX_PATH_TEXT = "reports/m2/probes/external-evidence-index.json"
SCHEMA_PATH_TEXT = "docs/implementation/m2/probes/external-evidence-supplement-v1.schema.json"
ROUTE_REQUEST_PATH_TEXT = ".codex/routes/m2-b001-external-probe-update-request.json"
VALIDATOR_PATH_TEXT = "tests/m2/probes/validate_m2_b001_external_supplement.py"
TEST_PATH_TEXT = "tests/m2/probes/test_m2_b001_external_supplement.py"

SUPPLEMENT_PATH = ROOT / SUPPLEMENT_PATH_TEXT
COMMAND_PATH = ROOT / COMMAND_PATH_TEXT
MANIFEST_PATH = ROOT / MANIFEST_PATH_TEXT
INDEX_PATH = ROOT / INDEX_PATH_TEXT
SCHEMA_PATH = ROOT / SCHEMA_PATH_TEXT
ROUTE_REQUEST_PATH = ROOT / ROUTE_REQUEST_PATH_TEXT

HISTORICAL_HASHES = {
    "reports/m2/probes/evidence-manifest.json": "3a48da621e45980d9b2258513954e1f29480fd9e12a35dcd29c12b77015c8ca7",
    "docs/implementation/m2/probes/README.md": "8faa32e6c3871a5fc9446dc40da8ecc895a4f02e5e4a87d9d9e1cbf8666fe11b",
    "docs/implementation/m2/probes/probe-result-v1.schema.json": "2dca0b73a39f544e71d4d440b3d153a75e5c438f91853e7bf82bf21442bb8b75",
    "docs/implementation/m2/probes/external-result-v1.schema.json": "eef21de64c4fa44266a008acf567e101b5d117f8fea0e6a2ffd482a4a917b5b6",
    "tests/m2/probes/fixtures/local-capability-vectors.json": "6a7832c8193825abda5dfac4124d590731aa023be07297ba73aa89eb3504a96d",
    "tests/m2/probes/fixtures/platform-manifest-seat.toml": "8ff8807969994b77fa412abcb2aae6be57b7c906dff011776617fd833c10688d",
    "tests/m2/probes/fixtures/platform-manifest-extension.toml": "b2e8d719582830ad7930ece3e9ddc2266500811fb253eb774638ac8c8c4a1054",
    "tests/m2/probes/validate_m2_b001.py": "f60683c845acda5666014c3c5d0df5148d6c28445ec6734aa9a696a43bad44f2",
    "tests/m2/probes/test_m2_b001_probes.py": "7d5c452d92e5cb48e4701575fa384d95a8f3d8caca9e49b1b847f72918c22894",
    "workflow/queue/m2-b001-trpg-platform-probes.json": "7d21cb8f5a68f9911fa8b70c00561c7df46904b615f4151281701f53a070aaf1",
    "workflow/queue/m2-b001-creator-tool-probes.json": "e1beb6ed3413ae9b711f760b0a8cf0d6deb5e13fd92d928e20a9a92fb40f6af9",
    "reports/m2/probes/acceptance-evidence.json": "4eeee63b1dd9e4b70581a70fc2dc355790dfd4147488540741d1f4062dab25da",
    "reports/m2/probes/probe-results.json": "154e7c0ddf8ce7b2243ad6c78d10ceb6cddf02c3aeb6592716dcc5ad8fc64218",
    "reports/m2/probes/external-gates.json": "a8951312cb9f23cf3f999a7258900603716ea6f0b4e7f684b8f6a53ed8f13a2d",
    "reports/m2/probes/platform-inventory.json": "cc73c579c18a4db47bf678c57d20906718180e6df51f7643f628c65a7cb7e2bf",
    "reports/m2/probes/safety-stage-evidence.json": "a701f619aa9c8515ca9567dd6d74663b9ce7ea651a54f2ff01dc78101e24b5ea",
}

SUPPLEMENT_ARTIFACT_PATHS = {
    ROUTE_REQUEST_PATH_TEXT,
    SCHEMA_PATH_TEXT,
    INDEX_PATH_TEXT,
    COMMAND_PATH_TEXT,
    SUPPLEMENT_PATH_TEXT,
    VALIDATOR_PATH_TEXT,
    TEST_PATH_TEXT,
}

SUPPLEMENT_STATUS = {
    "R2-INT-001": "FAIL",
    "R2-INT-002": "BLOCKED_EXTERNAL",
    "R2-INT-003": "BLOCKED_EXTERNAL",
    "R2-INT-004": "BLOCKED_EXTERNAL",
    "R2-INT-005": "BLOCKED_EXTERNAL",
    "R2-INT-006": "BLOCKED_EXTERNAL",
    "R2-INT-007": "PASS",
    "R2-INT-008": "BLOCKED_EXTERNAL",
    "R2-INT-009": "BLOCKED_EXTERNAL",
    "R2-INT-010": "FAIL",
    "R2-INT-011": "BLOCKED_EXTERNAL",
    "R2-INT-012": "BLOCKED_EXTERNAL",
}

SUPPLEMENT_EXECUTION = {
    probe_id: (
        "RETAINED_NO_RETEST" if probe_id in {"R2-INT-001", "R2-INT-007"}
        else "ANALYZED_NO_RECLASSIFICATION" if probe_id == "R2-INT-010"
        else "EXECUTED"
    )
    for probe_id in SUPPLEMENT_STATUS
}

SUPPLEMENT_TARGET_STATUS = {
    "R2-INT-001": ["PASS", "FAIL", "BLOCKED_EXTERNAL"],
    "R2-INT-002": ["PASS", "BLOCKED_EXTERNAL"],
    "R2-INT-003": ["PASS", "BLOCKED_EXTERNAL"],
    "R2-INT-004": ["PASS", "BLOCKED_EXTERNAL"],
    "R2-INT-005": ["PASS", "BLOCKED_EXTERNAL", "BLOCKED_EXTERNAL"],
    "R2-INT-006": ["PASS", "BLOCKED_EXTERNAL", "BLOCKED_EXTERNAL"],
    "R2-INT-007": ["PASS"],
    "R2-INT-008": ["PASS", "BLOCKED_EXTERNAL"],
    "R2-INT-009": ["PASS", "BLOCKED_EXTERNAL"],
    "R2-INT-010": ["PASS", "FAIL", "BLOCKED_EXTERNAL"],
    "R2-INT-011": ["PASS", "BLOCKED_EXTERNAL", "BLOCKED_EXTERNAL"],
    "R2-INT-012": ["PASS", "BLOCKED_EXTERNAL"],
}

SUPPLEMENT_COMMAND_ASSIGNMENTS = {
    "R2-INT-001": [],
    "R2-INT-002": ["PLATFORMD_HEALTH", "PLATFORMD_HELP", "CAPABILITY_SCAN_GENERAL", "CAPABILITY_SCAN_HOST_SURFACES"],
    "R2-INT-003": ["PLATFORMD_HEALTH", "PLATFORMD_HELP", "CAPABILITY_SCAN_HOST_SURFACES"],
    "R2-INT-004": ["PLATFORMD_HEALTH", "PLATFORMD_HELP", "CREATOR_SHELL_TEST", "CAPABILITY_SCAN_HOST_SURFACES"],
    "R2-INT-005": ["LUA_CANDIDATE_EVIDENCE", "RECONSTRUCTION_FOCUSED", "PLATFORMD_HEALTH", "CAPABILITY_SCAN_GENERAL"],
    "R2-INT-006": ["PLATFORMD_HEALTH", "CREATOR_SHELL_TEST", "CAPABILITY_SCAN_GENERAL"],
    "R2-INT-007": [],
    "R2-INT-008": ["PLATFORMD_HEALTH", "PLATFORMD_HELP", "CAPABILITY_SCAN_GENERAL", "CAPABILITY_SCAN_HOST_SURFACES"],
    "R2-INT-009": ["PLATFORMD_HEALTH", "PLATFORMD_HELP", "CAPABILITY_SCAN_HOST_SURFACES"],
    "R2-INT-010": ["EQUIPMENT_EXTENSION_REJECTION", "CREATOR_SHELL_TEST", "PLATFORM_SOURCE_HASHES"],
    "R2-INT-011": ["PLATFORMD_HEALTH", "WORKERD_HEALTH", "CREATOR_SHELL_TEST", "CAPABILITY_SCAN_GENERAL", "CAPABILITY_SCAN_HOST_SURFACES"],
    "R2-INT-012": ["LUA_CANDIDATE_EVIDENCE", "RECONSTRUCTION_FOCUSED", "PLATFORM_COMPONENT_SUITES", "PLATFORMD_HEALTH", "PLATFORMD_HELP", "PLATFORM_SOURCE_HASHES"],
}

GATE_LAYOUT = base.EXTERNAL_GATE_LAYOUT
GATE_STATUS = {
    gate_id: ("FAIL" if gate_id == "EXT-RUNTIME-SAFETY" else "BLOCKED_EXTERNAL")
    for gate_id, _target, _probe_ids, _gate_class in GATE_LAYOUT
}

COMMAND_IDS = [
    "ROUTE_FRESHNESS",
    "PLATFORM_PRE_STATUS", "PLATFORM_PRE_BRANCH", "PLATFORM_PRE_COMMIT", "PLATFORM_PRE_TREE",
    "PLATFORM_CODEX_CHECK", "LUA_CANDIDATE_EVIDENCE", "PLATFORMD_HEALTH", "PLATFORMD_HELP",
    "WORKERD_HEALTH", "CREATOR_SHELL_TEST", "EQUIPMENT_EXTENSION_REJECTION",
    "PLATFORM_COMPONENT_SUITES", "CAPABILITY_SCAN_GENERAL", "CAPABILITY_SCAN_HOST_SURFACES",
    "PLATFORM_SOURCE_HASHES", "RECONSTRUCTION_FOCUSED",
    "PLATFORM_POST_STATUS", "PLATFORM_POST_BRANCH", "PLATFORM_POST_COMMIT", "PLATFORM_POST_TREE",
]

COMMAND_TEXT = {
    "ROUTE_FRESHNESS": "python3 tools/codex_route.py check --map .codex/routes/generated/m2-b001-external-probe-update-001.json --route-id M2-B001-EXTERNAL-PROBE-UPDATE-001 --mode IMPLEMENT --milestone M2 --batch-id M2-B001",
    "PLATFORM_PRE_STATUS": "git status --porcelain=v1 --untracked-files=no",
    "PLATFORM_PRE_BRANCH": "git branch --show-current",
    "PLATFORM_PRE_COMMIT": "git rev-parse HEAD",
    "PLATFORM_PRE_TREE": "git rev-parse HEAD^{tree}",
    "PLATFORM_CODEX_CHECK": "go run ./cmd/projectctl codex check",
    "LUA_CANDIDATE_EVIDENCE": f"go run ./cmd/lua-runner evidence --candidate-sha {PLATFORM_COMMIT}",
    "PLATFORMD_HEALTH": "go run ./cmd/platformd health",
    "PLATFORMD_HELP": "go run ./cmd/platformd help",
    "WORKERD_HEALTH": "go run ./cmd/workerd health",
    "CREATOR_SHELL_TEST": "./node_modules/.bin/vitest run --configLoader runner src/App.test.tsx",
    "EQUIPMENT_EXTENSION_REJECTION": f"go run ./cmd/creator-cli package validate --manifest {CAPTURE_SOURCE_WORKTREE}/tests/m2/probes/fixtures/platform-manifest-extension.toml --lock internal/package/testdata/package.lock.json",
    "PLATFORM_COMPONENT_SUITES": "go test -count=1 ./internal/package/... ./cmd/creator-cli/... ./internal/luaruntime/... ./cmd/lua-runner/...",
    "CAPABILITY_SCAN_GENERAL": "rg -n -i '(seat|max[_-]?players|player[_-]?count|reconnect|deceased|spectator|campaign[_-]?termination|lineage|true[_-]?ending|safety[_-]?filter|hot[_-]?update)' apps cmd internal schemas",
    "CAPABILITY_SCAN_HOST_SURFACES": "rg -n -i '(participant|deceased|projection|action[_-]?lifecycle|warning[_-]?channel|campaign|termination|memory[_-]?claim|authoritative[_-]?state|safety[_-]?(filter|stage)|seed[_-]?manifest|event[_-]?log|typed[_-]?effect)' cmd/platformd cmd/workerd internal/baselinecli apps/creator-studio",
    "PLATFORM_SOURCE_HASHES": "sha256sum cmd/platformd/main.go cmd/workerd/main.go internal/baselinecli/baselinecli.go apps/creator-studio/frontend/src/App.tsx apps/creator-studio/frontend/src/App.test.tsx internal/luaruntime/ipc/protocol.go internal/luaruntime/vm/reconstruct.go schemas/package/manifest-v1.schema.json cmd/creator-cli/package.go",
    "RECONSTRUCTION_FOCUSED": "go test -count=1 -run 'TestCheckpointReconstructionRestoresObservableStateAndIsIndependent|TestAuthoritativeAndCheckpointInputsIndependentlyAffectRecovery|TestReconstructionRejectsEveryCompatibilityMutation' -v ./internal/luaruntime/vm",
    "PLATFORM_POST_STATUS": "git status --porcelain=v1 --untracked-files=no",
    "PLATFORM_POST_BRANCH": "git branch --show-current",
    "PLATFORM_POST_COMMIT": "git rev-parse HEAD",
    "PLATFORM_POST_TREE": "git rev-parse HEAD^{tree}",
}

SOURCE_HASHES = {
    "cmd/platformd/main.go": "1321cbdd185d1a1b9fd94579d3703602d02f6bff01285fedf5dce588140f0b80",
    "cmd/workerd/main.go": "8c3e7e20441525ac3438c612ce121da6e6b1e48d55f058a1867b6f2783df25df",
    "internal/baselinecli/baselinecli.go": "9c8f352393326d3f0aa06da05304c78ec401d9534c37708a6b9c47caddc682f1",
    "apps/creator-studio/frontend/src/App.tsx": "4f63cecbf537afe3fb1dc0ca7b65d983ced02058debad57846166eee35d0e1e5",
    "apps/creator-studio/frontend/src/App.test.tsx": "d7d537101a31ab2cdf57a9fd6a064368e67e1da53d20dc0cdf8fd6079c3881c2",
    "internal/luaruntime/ipc/protocol.go": "e4cef99e88ab8dd83d242724e334b93dffaf634752e6d6cbbcb817a40117e3c5",
    "internal/luaruntime/vm/reconstruct.go": "598d85c38b7a45ac6a68060dc3a44d76d3604b2e9902df564c1af54886fe43e3",
    "schemas/package/manifest-v1.schema.json": "3137440a9e382893affb11d45987ae09c0e0e0dfa6755bba13f09b0be35710af",
    "cmd/creator-cli/package.go": "f98333c32d44f604cfa11018d7a484a4fd2ddfbf9c4edeab40c39bbfb521372f",
}

CAPABILITY_OBSERVATIONS = {
    "participant_lifecycle": "UNAVAILABLE_OR_UNEXECUTABLE",
    "deceased_private_projection": "UNAVAILABLE_OR_UNEXECUTABLE",
    "action_lifecycle": "UNAVAILABLE_OR_UNEXECUTABLE",
    "warning_channel_separation": "UNAVAILABLE_OR_UNEXECUTABLE",
    "campaign_persistence": "VM_CHECKPOINT_SUBCAPABILITY_ONLY",
    "campaign_termination": "UNAVAILABLE_OR_UNEXECUTABLE",
    "memory_authority_projection": "UNAVAILABLE_OR_UNEXECUTABLE",
    "runtime_safety_stages": "UNAVAILABLE_OR_UNEXECUTABLE",
    "creator_round_trip": "SHELL_ONLY_NO_CONTROLS",
    "namespaced_manifest_extension": "REJECTED",
    "logical_anomaly_host_integration": "VM_CHECKPOINT_SUBCAPABILITY_ONLY_NO_HOST_RULE_SEED_EVENT_OR_TYPED_EFFECT_PATH",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    return base.load_json(path)


def sha256_path(path: Path) -> str:
    return base.sha256_path(path)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_allowed_supplement_path(path: str) -> bool:
    return base.is_allowed_candidate_path(path)


def validate_route_request() -> None:
    require(sha256_path(ROUTE_REQUEST_PATH) == SUPPLEMENT_ROUTE_REQUEST_SHA256, "route request changed after route generation")
    request = load_json(ROUTE_REQUEST_PATH)
    require(request.get("route_id") == SUPPLEMENT_ROUTE_ID, "route request ID mismatch")
    require(request.get("mode") == "IMPLEMENT", "route request mode mismatch")
    require(request.get("milestone") == "M2" and request.get("batch_id") == "M2-B001", "route request milestone/batch mismatch")
    require(isinstance(request.get("documents"), list) and request["documents"], "route request has no authority documents")


def validate_command_evidence(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(set(data) == {"schema_version", "supplement_id", "captured_at", "external_system", "commands", "source_artifacts", "capability_observations"}, "command evidence fields are incomplete or unknown")
    require(data["schema_version"] == "rules-residue.m2.external-command-evidence/1.0", "command evidence version mismatch")
    require(data["supplement_id"] == SUPPLEMENT_ID, "command evidence supplement mismatch")
    require(data["captured_at"] == SUPPLEMENT_CREATED_AT, "command evidence timestamp is stale or altered")
    require(data["external_system"] == {
        "name": "TRPG_PLATFORM",
        "repository": PLATFORM_REPOSITORY,
        "branch": PLATFORM_BRANCH,
        "commit": PLATFORM_COMMIT,
        "tree": PLATFORM_TREE,
    }, "external command provenance is wrong or incomplete")

    commands = data.get("commands")
    require(isinstance(commands, list) and [item.get("command_id") for item in commands if isinstance(item, dict)] == COMMAND_IDS, "command evidence is missing, duplicated, or reordered")
    command_by_id: dict[str, dict[str, Any]] = {}
    for command in commands:
        require(set(command) == {"command_id", "command", "workdir", "exit_code", "observed_output", "output_sha256"}, f"command evidence fields invalid for {command.get('command_id')}")
        command_id = command["command_id"]
        require(command_id not in command_by_id, f"duplicate command evidence: {command_id}")
        command_by_id[command_id] = command
        require(command["command"] == COMMAND_TEXT[command_id], f"command text changed for {command_id}")
        expected_workdir = CAPTURE_SOURCE_WORKTREE if command_id == "ROUTE_FRESHNESS" else PLATFORM_REPOSITORY
        if command_id == "CREATOR_SHELL_TEST":
            expected_workdir += "/apps/creator-studio/frontend"
        require(command["workdir"] == expected_workdir, f"wrong command repository for {command_id}")
        require(isinstance(command["exit_code"], int) and not isinstance(command["exit_code"], bool), f"invalid exit code for {command_id}")
        expected_exit = 1 if command_id in {"EQUIPMENT_EXTENSION_REJECTION", "CAPABILITY_SCAN_GENERAL", "CAPABILITY_SCAN_HOST_SURFACES"} else 0
        require(command["exit_code"] == expected_exit, f"unexpected exit code for {command_id}")
        require(isinstance(command["observed_output"], str), f"missing exact output for {command_id}")
        require(command["output_sha256"] == sha256_text(command["observed_output"]), f"raw output hash mismatch for {command_id}")

    identity_outputs = {
        "PLATFORM_PRE_STATUS": "",
        "PLATFORM_PRE_BRANCH": PLATFORM_BRANCH + "\n",
        "PLATFORM_PRE_COMMIT": PLATFORM_COMMIT + "\n",
        "PLATFORM_PRE_TREE": PLATFORM_TREE + "\n",
        "PLATFORM_POST_STATUS": "",
        "PLATFORM_POST_BRANCH": PLATFORM_BRANCH + "\n",
        "PLATFORM_POST_COMMIT": PLATFORM_COMMIT + "\n",
        "PLATFORM_POST_TREE": PLATFORM_TREE + "\n",
    }
    for command_id, output in identity_outputs.items():
        require(command_by_id[command_id]["observed_output"] == output, f"platform identity mismatch at {command_id}")
    require(command_by_id["ROUTE_FRESHNESS"]["observed_output"] == "CHECK: PASS\nCODEX_ROUTE_FRESH=PASS\n", "route freshness is not PASS")
    require(PLATFORM_COMMIT in command_by_id["PLATFORM_CODEX_CHECK"]["observed_output"] and "[PASS]" in command_by_id["PLATFORM_CODEX_CHECK"]["observed_output"], "platform route check is not candidate-bound PASS")
    lua_result = json.loads(command_by_id["LUA_CANDIDATE_EVIDENCE"]["observed_output"])
    require(lua_result.get("candidate_sha") == PLATFORM_COMMIT and lua_result.get("result") == "PASS", "Lua evidence is stale or failed")
    require([item.get("test_id") for item in lua_result.get("tests", [])] == ["TEST-LUA-001", "TEST-LUA-002"], "Lua evidence test coverage changed")
    require(all(item.get("exit_code") == 0 and item.get("result") == "PASS" for item in lua_result["tests"]), "Lua evidence contains a failed test")
    require(json.loads(command_by_id["PLATFORMD_HEALTH"]["observed_output"]) == {"component": "platformd", "status": "ok", "milestone": "M0", "playable": False}, "platformd capability surface changed")
    require(json.loads(command_by_id["WORKERD_HEALTH"]["observed_output"]) == {"component": "workerd", "status": "ok", "milestone": "M0", "playable": False}, "workerd capability surface changed")
    require("manifest contains unknown fields" in command_by_id["EQUIPMENT_EXTENSION_REJECTION"]["observed_output"], "equipment extension rejection evidence is missing")
    require(all(field in command_by_id["EQUIPMENT_EXTENSION_REJECTION"]["observed_output"] for field in [
        "rules_residue.equipment_rule",
        "rules_residue.equipment_rule.schema_version",
        "rules_residue.equipment_rule.semantic_kind",
    ]), "equipment rejection lost a required field")
    require(command_by_id["CAPABILITY_SCAN_GENERAL"]["observed_output"] == "" and command_by_id["CAPABILITY_SCAN_HOST_SURFACES"]["observed_output"] == "", "bounded capability scan output changed")
    require("TestCheckpointReconstructionRestoresObservableStateAndIsIndependent" in command_by_id["RECONSTRUCTION_FOCUSED"]["observed_output"] and "PASS\n" in command_by_id["RECONSTRUCTION_FOCUSED"]["observed_output"], "focused reconstruction evidence is incomplete")

    sources = data.get("source_artifacts")
    require(isinstance(sources, list) and sources == [{"path": path, "sha256": digest} for path, digest in SOURCE_HASHES.items()], "platform source hash evidence is missing, duplicated, or altered")
    source_output = "".join(f"{digest}  {path}\n" for path, digest in SOURCE_HASHES.items())
    require(command_by_id["PLATFORM_SOURCE_HASHES"]["observed_output"] == source_output, "platform source hash output does not bind its artifacts")
    require(data.get("capability_observations") == CAPABILITY_OBSERVATIONS, "capability observations were widened or altered")
    return command_by_id


def historical_probe_snapshot(probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_status": probe["execution_status"],
        "evidence_paths": probe["evidence_paths"],
        "target_results": probe["target_results"],
        "downstream_blocked_batches": probe["downstream_blocked_batches"],
    }


def require_local_evidence_paths(paths: Any, context: str) -> None:
    require(isinstance(paths, list) and paths and len(paths) == len(set(paths)), f"{context} evidence paths are missing or duplicated")
    for path_text in paths:
        require(isinstance(path_text, str) and not Path(path_text).is_absolute() and ".." not in Path(path_text).parts, f"{context} evidence path is unsafe")
        require((ROOT / path_text).is_file(), f"{context} evidence path does not exist: {path_text}")


def validate_probe_transitions(transitions: Any, command_by_id: dict[str, dict[str, Any]]) -> None:
    require(isinstance(transitions, list) and [item.get("probe_id") for item in transitions if isinstance(item, dict)] == list(SUPPLEMENT_STATUS), "probe transitions are missing, duplicated, or reordered")
    historical = base.frozen_probe_map()
    for transition in transitions:
        probe_id = transition["probe_id"]
        require(set(transition) == {"probe_id", "probe_execution", "previous", "new", "transition_reason", "command_ids"}, f"transition fields invalid for {probe_id}")
        require(transition["probe_execution"] == SUPPLEMENT_EXECUTION[probe_id], f"probe execution mode changed for {probe_id}")
        previous = historical_probe_snapshot(historical[probe_id])
        require(transition["previous"] == previous, f"historical probe evidence was not preserved for {probe_id}")
        new = transition["new"]
        require(set(new) == {"execution_status", "evidence_paths", "target_results", "downstream_blocked_batches"}, f"new probe snapshot fields invalid for {probe_id}")
        require(new["execution_status"] == SUPPLEMENT_STATUS[probe_id], f"truthful status changed for {probe_id}")
        require(new["downstream_blocked_batches"] == historical[probe_id]["downstream_blocked_batches"], f"downstream blockers changed for {probe_id}")
        expected_paths = list(previous["evidence_paths"])
        if transition["probe_execution"] != "RETAINED_NO_RETEST":
            expected_paths.append(COMMAND_PATH_TEXT)
        require(new["evidence_paths"] == expected_paths, f"new evidence append is incomplete or altered for {probe_id}")
        require_local_evidence_paths(new["evidence_paths"], probe_id)
        targets = new.get("target_results")
        require(isinstance(targets, list) and [item.get("target") for item in targets if isinstance(item, dict)] == historical[probe_id]["target_system"], f"target pair is missing, duplicated, or altered for {probe_id}")
        require([item.get("execution_status") for item in targets] == SUPPLEMENT_TARGET_STATUS[probe_id], f"target status mapping is false for {probe_id}")
        for index, target in enumerate(targets):
            require(set(target) == {"target", "execution_status", "evidence_paths"}, f"target evidence fields invalid for {probe_id}")
            if target["target"] == "A:rules-residue" or transition["probe_execution"] == "RETAINED_NO_RETEST" or target["target"].startswith("D:"):
                expected_target_paths = previous["target_results"][index]["evidence_paths"]
            else:
                expected_target_paths = [COMMAND_PATH_TEXT]
            require(target["evidence_paths"] == expected_target_paths, f"target provenance is incomplete or altered for {probe_id}/{target['target']}")
            require_local_evidence_paths(target["evidence_paths"], f"{probe_id}/{target['target']}")
        require(transition["command_ids"] == SUPPLEMENT_COMMAND_ASSIGNMENTS[probe_id], f"command evidence mapping changed for {probe_id}")
        require(all(command_id in command_by_id for command_id in transition["command_ids"]), f"unknown command evidence for {probe_id}")
        require(isinstance(transition["transition_reason"], str) and transition["transition_reason"].strip(), f"transition reason missing for {probe_id}")
        if transition["probe_execution"] == "RETAINED_NO_RETEST":
            require(new == previous, f"retained probe {probe_id} was silently reclassified")
    require("M2-B002" not in historical["R2-INT-001"]["downstream_blocked_batches"], "R2-INT-001 was incorrectly made a B002 blocker")


def old_gate_snapshot(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_status": gate["execution_status"],
        "evidence_paths": ["reports/m2/probes/external-gates.json", gate["task_packet"]],
        "blocks": gate["blocks"],
    }


def current_gate_evidence(gate_id: str, task_packet: str) -> list[str]:
    if gate_id == "EXT-TRPG-SEATS":
        return ["reports/m2/probes/external-gates.json", task_packet]
    if gate_id in {"EXT-TRPG-PERSISTENCE", "EXT-CREATOR-PACKAGE-ROUNDTRIP"}:
        return [COMMAND_PATH_TEXT, task_packet]
    return [COMMAND_PATH_TEXT]


def validate_gate_updates(transitions: Any, current: Any) -> None:
    expected_ids = [item[0] for item in GATE_LAYOUT]
    require(isinstance(transitions, list) and [item.get("gate_id") for item in transitions if isinstance(item, dict)] == expected_ids, "external gate transitions are missing, duplicated, or reordered")
    require(isinstance(current, list) and [item.get("gate_id") for item in current if isinstance(item, dict)] == expected_ids, "current external gates are missing, duplicated, or reordered")
    old_gates = load_json(base.GATE_PATH)["gates"]
    old_by_id = {gate["gate_id"]: gate for gate in old_gates}
    current_by_id = {gate["gate_id"]: gate for gate in current}
    for gate_id, target, probe_ids, gate_class in GATE_LAYOUT:
        old = old_by_id[gate_id]
        transition = next(item for item in transitions if item["gate_id"] == gate_id)
        require(set(transition) == {"gate_id", "target", "probe_ids", "previous", "new", "transition_reason"}, f"external gate transition fields invalid for {gate_id}")
        require(transition["target"] == target and transition["probe_ids"] == probe_ids, f"external gate mapping changed for {gate_id}")
        require(transition["previous"] == old_gate_snapshot(old), f"historical external gate evidence changed for {gate_id}")
        gate = current_by_id[gate_id]
        require(set(gate) == {"gate_id", "target", "probe_ids", "gate_class", "execution_status", "evidence_paths", "blocks", "downstream_readiness"}, f"current external gate fields invalid for {gate_id}")
        require(gate["target"] == target and gate["probe_ids"] == probe_ids and gate["gate_class"] == gate_class, f"current gate target/probe/class mapping changed for {gate_id}")
        require(gate["execution_status"] == GATE_STATUS[gate_id], f"current external gate status is false for {gate_id}")
        require(gate["blocks"] == old["blocks"], f"current external gate blockers changed for {gate_id}")
        require(gate["evidence_paths"] == current_gate_evidence(gate_id, old["task_packet"]), f"current external gate evidence is incomplete for {gate_id}")
        require_local_evidence_paths(gate["evidence_paths"], gate_id)
        expected_readiness = "BLOCKED_BY_FAIL" if gate["execution_status"] == "FAIL" else "BLOCKED_EXTERNAL"
        require(gate["downstream_readiness"] == expected_readiness, f"current external gate readiness is false for {gate_id}")
        require(transition["new"] == {
            "execution_status": gate["execution_status"],
            "evidence_paths": gate["evidence_paths"],
            "blocks": gate["blocks"],
        }, f"external gate transition/current view disagree for {gate_id}")
        require(isinstance(transition["transition_reason"], str) and transition["transition_reason"].strip(), f"external gate transition reason missing for {gate_id}")
    required_pairs = {
        (probe_id, target)
        for probe_id, probe in base.frozen_probe_map().items()
        for target in probe["target_system"]
        if target in {"B:TRPG_PLATFORM", "C:Creator Tool"}
    }
    covered_pairs = {(probe_id, gate["target"]) for gate in current for probe_id in gate["probe_ids"]}
    require(len(required_pairs) == 15 and covered_pairs == required_pairs, "current external gates do not cover the exact fifteen target pairs")
    require(sum(len(gate["probe_ids"]) for gate in current) == 15, "current external gates contain a duplicate target pair")


def validate_downstream_readiness(readiness: Any) -> None:
    expected: list[dict[str, Any]] = []
    for number in range(1, 17):
        batch_id = f"M2-B{number:03d}"
        if batch_id == "M2-B001":
            expected.append({"batch_id": batch_id, "readiness": "ACCEPTED_BASE_UNCHANGED", "blocking_probe_ids": []})
            continue
        blockers = [
            probe_id for probe_id in SUPPLEMENT_STATUS
            if batch_id in base.BLOCKS[probe_id] and SUPPLEMENT_STATUS[probe_id] != "PASS"
        ]
        state = "BLOCKED_BY_FAIL" if any(SUPPLEMENT_STATUS[probe_id] == "FAIL" for probe_id in blockers) else "BLOCKED_EXTERNAL"
        expected.append({"batch_id": batch_id, "readiness": state, "blocking_probe_ids": blockers})
    require(readiness == expected, "downstream readiness does not follow the current probe transitions")


def validate_int_010(data: Any) -> None:
    require(isinstance(data, dict) and set(data) == {
        "probe_id", "execution_status", "remediation_class", "root_cause", "lost_fields", "loss_point",
        "adapter_feasibility", "platform_change_necessity", "creator_evidence", "required_repositories",
        "blocks_b002", "downstream_blocked_batches",
    }, "R2-INT-010 remediation fields are incomplete or unknown")
    require(data["probe_id"] == "R2-INT-010" and data["execution_status"] == "FAIL", "R2-INT-010 historical FAIL was reclassified")
    allowed = {"RULES_PACKAGE_ADAPTER", "CREATOR_CHANGE_REQUIRED", "PLATFORM_CHANGE_REQUIRED", "MULTI_REPO_CHANGE_REQUIRED", "BLOCKED_EXTERNAL"}
    require(isinstance(data["remediation_class"], str) and data["remediation_class"] in allowed and data["remediation_class"] == "MULTI_REPO_CHANGE_REQUIRED", "R2-INT-010 must select exactly the supported multi-repository remediation class")
    require(data["lost_fields"] == ["rules_residue.equipment_rule", "rules_residue.equipment_rule.schema_version", "rules_residue.equipment_rule.semantic_kind"], "R2-INT-010 lost-field evidence changed")
    require(data["loss_point"] == "STRICT_MANIFEST_DECODE_BEFORE_HOST_LOAD", "R2-INT-010 loss point changed")
    require(isinstance(data["root_cause"], str) and "reject" in data["root_cause"].lower() and "Creator" in data["root_cause"], "R2-INT-010 root cause is incomplete")
    require(data["adapter_feasibility"] == {
        "rules_package_adapter_possible": True,
        "adapter_alone_sufficient": False,
        "required_precondition": "A generic, third-party-compatible platform extension container/registry that preserves namespaced data through validation, Host load, and Creator round-trip.",
        "privileged_format_allowed": False,
    }, "R2-INT-010 adapter feasibility was widened")
    require(data["platform_change_necessity"] == "REQUIRED", "R2-INT-010 platform-change necessity changed")
    creator = data["creator_evidence"]
    require(creator.get("execution_status") == "BLOCKED_EXTERNAL" and creator.get("command_ids") == ["CREATOR_SHELL_TEST", "EQUIPMENT_EXTENSION_REJECTION"] and isinstance(creator.get("observed_result"), str) and creator["observed_result"].strip(), "R2-INT-010 Creator evidence is incomplete")
    repositories = data["required_repositories"]
    require(isinstance(repositories, list) and [item.get("repository") for item in repositories if isinstance(item, dict)] == [PLATFORM_REPOSITORY, "/home/zyc14588/rules-residue"], "R2-INT-010 required repository set changed")
    require(all(set(item) == {"repository", "minimum_change"} and isinstance(item["minimum_change"], str) and item["minimum_change"].strip() for item in repositories), "R2-INT-010 minimum changes are incomplete")
    require(data["blocks_b002"] is True and data["downstream_blocked_batches"] == base.BLOCKS["R2-INT-010"], "R2-INT-010 B002/downstream blocker mapping changed")


def validate_int_012(data: Any) -> None:
    require(isinstance(data, dict) and set(data) == {
        "probe_id", "execution_status", "platform_subcapability", "required_dimension_results",
        "all_required_dimensions_pass", "pass_claimed", "determination",
    }, "R2-INT-012 determination fields are incomplete or unknown")
    require(data["probe_id"] == "R2-INT-012" and data["execution_status"] == "BLOCKED_EXTERNAL", "R2-INT-012 was forged to PASS")
    subcapability = data["platform_subcapability"]
    require(subcapability.get("execution_status") == "PASS", "R2-INT-012 deterministic VM subcapability result changed")
    require(subcapability.get("command_ids") == ["LUA_CANDIDATE_EVIDENCE", "RECONSTRUCTION_FOCUSED"], "R2-INT-012 subcapability provenance changed")
    require(isinstance(subcapability.get("capability"), str) and isinstance(subcapability.get("limitation"), str) and all(subcapability.get(key, "").strip() for key in ("capability", "limitation")), "R2-INT-012 subcapability boundaries are incomplete")
    dimensions = [
        ("scope", "NOT_RUN"), ("trigger", "NOT_RUN"), ("condition", "NOT_RUN"),
        ("priority", "NOT_RUN"), ("conflict", "NOT_RUN"), ("exception", "NOT_RUN"),
        ("seed", "BLOCKED_EXTERNAL"), ("same_seed_state_action_same_result", "BLOCKED_EXTERNAL"),
        ("reload_does_not_redraw_answers", "BLOCKED_EXTERNAL"),
    ]
    results = data.get("required_dimension_results")
    require(isinstance(results, list) and [(item.get("dimension"), item.get("execution_status")) for item in results if isinstance(item, dict)] == dimensions, "R2-INT-012 required dimensions are missing, duplicated, reordered, or forged")
    require(all(set(item) == {"dimension", "execution_status", "reason"} and isinstance(item["reason"], str) and item["reason"].strip() for item in results), "R2-INT-012 dimension reason is missing")
    require(data["all_required_dimensions_pass"] is False and data["pass_claimed"] is False, "R2-INT-012 full capability PASS was forged")
    require(isinstance(data["determination"], str) and data["determination"].strip(), "R2-INT-012 determination is missing")


def validate_index(data: dict[str, Any]) -> None:
    require(set(data) == {"schema_version", "batch_id", "formal_batch", "evidence_chain", "latest_external_evidence", "resolution_rule", "formal_batch_reopened", "b002_started", "independent_acceptance_required"}, "external evidence index fields are incomplete or unknown")
    require(data["schema_version"] == "rules-residue.m2.external-evidence-index/1.0" and data["batch_id"] == "M2-B001", "external evidence index identity changed")
    require(data["formal_batch"] == {
        "status": "ACCEPTED_UNCHANGED",
        "commit": ACCEPTED_B001_COMMIT,
        "tree": ACCEPTED_B001_TREE,
        "result_path": "reports/m2/probes/probe-results.json",
        "result_sha256": HISTORICAL_HASHES["reports/m2/probes/probe-results.json"],
    }, "external evidence index reopens or alters accepted B001")
    require(data["evidence_chain"] == [
        {"ordinal": 0, "evidence_id": "M2-B001", "nature": "FORMAL_BATCH_EVIDENCE", "path": "reports/m2/probes/probe-results.json", "application": "BASE"},
        {"ordinal": 1, "evidence_id": SUPPLEMENT_ID, "nature": "EXTERNAL_EVIDENCE_SUPPLEMENT", "path": SUPPLEMENT_PATH_TEXT, "application": "APPEND_PROBE_TRANSITIONS_AND_UPDATE_EXTERNAL_GATES"},
    ], "external evidence application chain is missing, duplicated, or reordered")
    require(data["latest_external_evidence"] == {"evidence_id": SUPPLEMENT_ID, "nature": "EXTERNAL_EVIDENCE_SUPPLEMENT", "path": SUPPLEMENT_PATH_TEXT}, "supplement is not discoverable as latest external evidence")
    require("append probe_result_transitions" in data["resolution_rule"] and "current_external_gates" in data["resolution_rule"], "external evidence resolution rule is incomplete")
    require(data["formal_batch_reopened"] is False and data["b002_started"] is False and data["independent_acceptance_required"] is True, "supplement changed batch lifecycle state")


def validate_historical_hashes() -> None:
    for path_text, expected_hash in HISTORICAL_HASHES.items():
        path = ROOT / path_text
        require(path.is_file() and sha256_path(path) == expected_hash, f"historical B001 artifact changed: {path_text}")


def validate_manifest(data: dict[str, Any]) -> None:
    require(set(data) == {"schema_version", "supplement_id", "parent_binding", "candidate_binding_strategy", "artifacts", "immutable_historical_artifacts", "protected_scope_proof"}, "supplement manifest fields are incomplete or unknown")
    require(data["schema_version"] == "rules-residue.m2.external-evidence-manifest/1.0" and data["supplement_id"] == SUPPLEMENT_ID, "supplement manifest identity changed")
    require(data["parent_binding"] == {"commit": ACCEPTED_B001_COMMIT, "tree": ACCEPTED_B001_TREE}, "supplement manifest parent binding changed")
    require(data["candidate_binding_strategy"] == "EXACT_HEAD_AT_VALIDATION", "supplement candidate binding strategy changed")
    artifacts = data.get("artifacts")
    require(isinstance(artifacts, list) and [item.get("path") for item in artifacts if isinstance(item, dict)] == sorted(SUPPLEMENT_ARTIFACT_PATHS), "supplement manifest coverage is incomplete, duplicated, or reordered")
    for artifact in artifacts:
        require(set(artifact) == {"path", "sha256"}, f"supplement artifact fields invalid: {artifact.get('path')}")
        path = ROOT / artifact["path"]
        require(path.is_file() and artifact["sha256"] == sha256_path(path), f"supplement artifact hash mismatch: {artifact['path']}")
    immutable = data.get("immutable_historical_artifacts")
    expected_immutable = [{"path": path, "sha256": digest} for path, digest in sorted(HISTORICAL_HASHES.items())]
    require(immutable == expected_immutable, "immutable historical artifact coverage or hashes changed")
    proof = data.get("protected_scope_proof")
    require(proof == {
        "comparison_parent": ACCEPTED_B001_COMMIT,
        "allowed_path_families": ["docs/implementation/m2/probes/**", "tests/m2/probes/**", "workflow/queue/m2-b001-*.json", "reports/m2/probes/**", ".codex/routes/m2-b001-*.json"],
        "forbidden_path_families": [".codex/state/MILESTONE_PLAN.yaml", ".codex/plans/**", ".codex/controls/**", "docs/authority/r2/**", "governance/r2/**", "game-package/**", "schemas/r2/**", "authoring/**", "content/**", "art/**", "TRPG_PLATFORM/**"],
        "game_package_runtime_changed": False,
        "lock_updated": False,
    }, "supplement protected-scope proof changed")
    validate_historical_hashes()


def validate_supplement(
    data: dict[str, Any] | None = None,
    command_data: dict[str, Any] | None = None,
    index_data: dict[str, Any] | None = None,
    manifest_data: dict[str, Any] | None = None,
) -> None:
    validate_historical_hashes()
    validate_route_request()
    data = data or load_json(SUPPLEMENT_PATH)
    command_data = command_data or load_json(COMMAND_PATH)
    index_data = index_data or load_json(INDEX_PATH)
    manifest_data = manifest_data or load_json(MANIFEST_PATH)
    require(set(data) == {
        "schema_version", "supplement_id", "nature", "batch_id", "created_at", "accepted_b001_binding",
        "route_binding", "external_binding", "command_evidence", "probe_result_transitions",
        "external_gate_transitions", "current_external_gates", "downstream_readiness",
        "int_010_remediation", "int_012_determination", "candidate_binding", "overall_status",
    }, "supplement fields are incomplete or unknown")
    require(data["schema_version"] == "rules-residue.m2.external-evidence-supplement/1.0" and data["supplement_id"] == SUPPLEMENT_ID and data["nature"] == "EXTERNAL_EVIDENCE_SUPPLEMENT" and data["batch_id"] == "M2-B001", "supplement identity changed")
    require(data["created_at"] == SUPPLEMENT_CREATED_AT, "supplement timestamp is stale or altered")
    require(data["accepted_b001_binding"] == {
        "accepted_commit": ACCEPTED_B001_COMMIT,
        "accepted_tree": ACCEPTED_B001_TREE,
        "historical_result_path": "reports/m2/probes/probe-results.json",
        "historical_result_sha256": HISTORICAL_HASHES["reports/m2/probes/probe-results.json"],
        "historical_manifest_path": "reports/m2/probes/evidence-manifest.json",
        "historical_manifest_sha256": HISTORICAL_HASHES["reports/m2/probes/evidence-manifest.json"],
    }, "accepted B001 provenance is wrong, incomplete, or stale")
    require(data["route_binding"] == {
        "request_path": ROUTE_REQUEST_PATH_TEXT,
        "route_id": SUPPLEMENT_ROUTE_ID,
        "mode": "IMPLEMENT",
        "milestone": "M2",
        "batch_id": "M2-B001",
        "source_commit": ACCEPTED_B001_COMMIT,
        "source_tree": ACCEPTED_B001_TREE,
        "binding_digest": SUPPLEMENT_ROUTE_DIGEST,
        "context_status": "OK",
        "context_ratio": 0.4256642659505208,
        "freshness_status": "PASS",
        "checked_at": SUPPLEMENT_ROUTE_CHECKED_AT,
        "command_id": "ROUTE_FRESHNESS",
    }, "route provenance is wrong, incomplete, or stale")
    expected_identity_ids = {
        "before": ["PLATFORM_PRE_STATUS", "PLATFORM_PRE_BRANCH", "PLATFORM_PRE_COMMIT", "PLATFORM_PRE_TREE"],
        "after": ["PLATFORM_POST_STATUS", "PLATFORM_POST_BRANCH", "PLATFORM_POST_COMMIT", "PLATFORM_POST_TREE"],
    }
    require(data["external_binding"] == {
        "name": "TRPG_PLATFORM",
        "repository": PLATFORM_REPOSITORY,
        "branch": PLATFORM_BRANCH,
        "commit": PLATFORM_COMMIT,
        "tree": PLATFORM_TREE,
        "tracked_worktree_clean_before": True,
        "tracked_worktree_clean_after": True,
        "identity_command_ids": expected_identity_ids,
    }, "external platform provenance is wrong, incomplete, or stale")
    require(data["command_evidence"] == COMMAND_PATH_TEXT, "supplement command evidence path changed")
    command_by_id = validate_command_evidence(command_data)
    validate_probe_transitions(data["probe_result_transitions"], command_by_id)
    validate_gate_updates(data["external_gate_transitions"], data["current_external_gates"])
    validate_downstream_readiness(data["downstream_readiness"])
    validate_int_010(data["int_010_remediation"])
    validate_int_012(data["int_012_determination"])
    require(data["candidate_binding"] == {
        "strategy": "EXACT_HEAD_AT_VALIDATION",
        "required_parent_commit": ACCEPTED_B001_COMMIT,
        "required_parent_tree": ACCEPTED_B001_TREE,
        "evidence_manifest": MANIFEST_PATH_TEXT,
        "must_be_clean": True,
    }, "supplement candidate binding is incomplete or stale")
    require(data["overall_status"] == "BLOCKED_EXTERNAL", "supplement overall status was forged")
    validate_index(index_data)
    validate_manifest(manifest_data)


def git_output(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout.strip()


def validate_supplement_candidate(candidate_commit: str, candidate_tree: str, manifest: dict[str, Any]) -> None:
    resolved_commit = git_output("rev-parse", candidate_commit)
    require(re.fullmatch(r"[0-9a-f]{40}", resolved_commit) is not None, "supplement candidate commit cannot be resolved")
    require(git_output("rev-parse", "HEAD") == resolved_commit, "validator is not at the exact supplement candidate")
    resolved_tree = git_output("rev-parse", f"{resolved_commit}^{{tree}}")
    require(resolved_tree == candidate_tree and git_output("rev-parse", "HEAD^{tree}") == candidate_tree, "supplement candidate tree argument/checkout mismatch")
    require(git_output("status", "--short") == "", "supplement candidate worktree is not clean")
    require(git_output("rev-parse", f"{ACCEPTED_B001_COMMIT}^{{tree}}") == ACCEPTED_B001_TREE, "accepted B001 parent tree mismatch")
    parent_line = git_output("rev-list", "--parents", "-n", "1", resolved_commit).split()
    require(parent_line == [resolved_commit, ACCEPTED_B001_COMMIT], "supplement candidate must be exactly one commit atop accepted B001")
    changed = set(git_output("diff", "--name-only", ACCEPTED_B001_COMMIT, resolved_commit).splitlines())
    require(changed and all(is_allowed_supplement_path(path) for path in changed), "supplement candidate changed a path outside the frozen B001 envelope")
    manifest_paths = {artifact["path"] for artifact in manifest["artifacts"]}
    require(changed == manifest_paths | {MANIFEST_PATH_TEXT}, "supplement candidate contains an unmanifested or missing artifact")
    require(manifest_paths == SUPPLEMENT_ARTIFACT_PATHS, "supplement candidate manifest coverage is incomplete")
    require(changed.isdisjoint(HISTORICAL_HASHES), "supplement candidate overwrote historical B001 evidence")
    for path_text in changed:
        subprocess.run(["git", "cat-file", "-e", f"{resolved_commit}:{path_text}"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    validate_historical_hashes()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplement", action="store_true")
    parser.add_argument("--candidate")
    parser.add_argument("--candidate-tree")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        require(args.supplement, "select the distinct --supplement validation mode")
        validate_supplement()
        if args.candidate is not None or args.candidate_tree is not None:
            require(args.candidate is not None and args.candidate_tree is not None, "supplement candidate commit and tree are required together")
            validate_supplement_candidate(args.candidate, args.candidate_tree, load_json(MANIFEST_PATH))
        print(json.dumps({
            "supplement_id": SUPPLEMENT_ID,
            "validation_status": "PASS",
            "evidence_status": "BLOCKED_EXTERNAL",
            "candidate": args.candidate or "DEFERRED_TO_EXACT_HEAD_VALIDATION",
            "route_binding_digest": SUPPLEMENT_ROUTE_DIGEST,
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (ProbeValidationError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"M2-B001 external supplement validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
