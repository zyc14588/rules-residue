from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_ROOT = PROJECT_ROOT / ".codex" / "plans" / "m2-vertical-slice"

REQUIRED_BATCH_FIELDS = {
    "id",
    "state",
    "objective",
    "dependencies",
    "authority_ids",
    "r2_decision_ids",
    "input_sections",
    "allowed_paths",
    "forbidden_paths",
    "codex_responsibilities",
    "opencode_responsibilities",
    "grok_responsibilities",
    "platform_probes",
    "schemas",
    "fixtures",
    "tests",
    "negative_tests",
    "acceptance_gates",
    "stop_conditions",
    "rollback_recovery",
    "expected_commit_boundary",
    "non_goals",
    "reading_map_request",
}

PROBE_RESULT_REQUIRED_FIELDS = [
    "probe_id",
    "r2_requirement",
    "classification",
    "target_system",
    "existing_capability",
    "probe_procedure",
    "commands_actions_actually_run",
    "evidence_paths",
    "observed_result",
    "expected_result",
    "execution_status",
    "root_cause",
    "adapter_feasibility",
    "platform_change_necessity",
    "downstream_blocked_batches",
]

PROBE_EXECUTION_STATUSES = [
    "PASS",
    "FAIL",
    "NOT_RUN",
    "BLOCKED_EXTERNAL",
    "BLOCKED_ENVIRONMENT",
]

BATCH_RESULTS = [
    "PASS",
    "FAIL",
    "BLOCKED_EXTERNAL",
    "BLOCKED_ENVIRONMENT",
    "BLOCKED_DESIGN_CONFLICT",
]

RECOVERY_EVIDENCE_PATH = (
    Path("reports")
    / "m2"
    / "probes"
    / "closeouts"
    / "m2-b001-recovery-closeout-001"
    / "evidence.json"
)
FROZEN_RECOVERY_PENDING = "FROZEN_WITH_RECOVERY_EVIDENCE_PENDING_LIFECYCLE_CLOSEOUT"
ACCEPTED_WITH_BLOCKERS = "ACCEPTED_WITH_DOWNSTREAM_BLOCKERS"
INVALID_MIXED_STATE = "INVALID_MIXED_STATE"
EXPECTED_RECOVERY_BLOCKERS = ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"]


def _read_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(PROJECT_ROOT)} is not valid JSON: {exc}")
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_projection_parity(errors: list[str]) -> None:
    projection_path = PLAN_ROOT / "ROUTED_INPUT_PROJECTIONS.md"
    try:
        text = projection_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read routed input projections: {exc}")
        return

    sources = {
        "R2-M2-REFERENCE-WORK-PACKAGES": PROJECT_ROOT
        / "docs"
        / "implementation"
        / "r2"
        / "M2_REFERENCE_WORK_PACKAGES.yaml",
        "R2-INSTALL-INTEGRATION-CONFLICT-EVIDENCE": PROJECT_ROOT
        / "governance"
        / "evidence"
        / "r2-authority-install"
        / "integration-conflicts.yaml",
    }
    marker_re = re.compile(
        r"^<!-- SECTION-ID: ([A-Z0-9]+(?:-[A-Z0-9]+)+) -->$", re.MULTILINE
    )
    matches = list(marker_re.finditer(text))
    found_ids = [match.group(1) for match in matches]
    if found_ids != list(sources):
        errors.append(
            "routed input projection Section IDs/order differ from the two frozen sources"
        )
        return

    for index, match in enumerate(matches):
        section_id = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start() : end]
        source_path = sources[section_id]
        digest = _sha256(source_path)
        if f"source SHA-256: `{digest}`" not in section:
            errors.append(f"{section_id} does not bind the current source SHA-256")
        fenced = re.search(r"```yaml\n(.*?)```", section, re.DOTALL)
        if fenced is None:
            errors.append(f"{section_id} lacks a YAML projection payload")
            continue
        payload = fenced.group(1).encode("utf-8")
        try:
            source = source_path.read_bytes()
        except OSError as exc:
            errors.append(f"cannot read projection source {source_path}: {exc}")
            continue
        if payload != source:
            errors.append(f"{section_id} is not byte-identical to {source_path.relative_to(PROJECT_ROOT)}")


def _check_dag(batches: dict[str, Any], errors: list[str]) -> None:
    graph = batches.get("dependency_graph")
    items = batches.get("batches")
    expected_ids = [f"M2-B{index:03d}" for index in range(1, 17)]
    if not isinstance(graph, dict) or list(graph) != expected_ids:
        errors.append("M2 dependency graph must contain ordered M2-B001--M2-B016")
        return
    if not isinstance(items, list) or [item.get("id") for item in items if isinstance(item, dict)] != expected_ids:
        errors.append("M2 batch registry must contain ordered M2-B001--M2-B016")
        return

    order = {batch_id: index for index, batch_id in enumerate(expected_ids)}
    for item in items:
        if not isinstance(item, dict):
            errors.append("M2 batch registry contains a non-object")
            continue
        missing = REQUIRED_BATCH_FIELDS - set(item)
        if missing:
            errors.append(f"{item.get('id')} lacks fields: {sorted(missing)}")
        batch_id = item.get("id")
        dependencies = item.get("dependencies")
        if dependencies != graph.get(batch_id):
            errors.append(f"{batch_id} dependencies differ from dependency_graph")
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if dependency not in order or order[dependency] >= order.get(batch_id, -1):
                    errors.append(f"{batch_id} has unknown, self, forward, or cyclic dependency {dependency}")
        for field in REQUIRED_BATCH_FIELDS - {"dependencies", "opencode_responsibilities", "grok_responsibilities"}:
            value = item.get(field)
            if value in (None, "", []):
                errors.append(f"{batch_id}.{field} must not be empty")

    frozen = [item.get("id") for item in items if item.get("state") == "FROZEN"]
    planned = [item.get("id") for item in items if item.get("state") == "PLANNED"]
    if frozen != ["M2-B001"] or planned != expected_ids[1:]:
        errors.append("only M2-B001 may be FROZEN; M2-B002--M2-B016 must remain PLANNED")
    if batches.get("implementation_state") != "NOT_STARTED":
        errors.append("M2 implementation_state must remain NOT_STARTED")


def _check_controls(controls: dict[str, Any], errors: list[str]) -> None:
    acceptance = controls.get("acceptance_matrix")
    expected_acceptance = [f"M2-ACC-{index:03d}" for index in range(1, 32)]
    if not isinstance(acceptance, list) or [item.get("id") for item in acceptance if isinstance(item, dict)] != expected_acceptance:
        errors.append("acceptance matrix must contain ordered M2-ACC-001--031")
    elif any(item.get("status") != "PLANNED_NOT_RUN" for item in acceptance):
        errors.append("all M2 acceptance entries must remain PLANNED_NOT_RUN in PLAN")

    gates = controls.get("external_gates")
    if not isinstance(gates, list) or not gates:
        errors.append("M2 external gates must be a non-empty array")
    elif any(item.get("status") != "NOT_RUN" for item in gates):
        errors.append("all M2 external gates must remain NOT_RUN in PLAN")

    deferred = controls.get("deferred_consumption")
    if not isinstance(deferred, list) or len(deferred) != 10:
        errors.append("M2 deferred consumption plan must contain exactly 10 entries")
    elif any(not item.get("plan") or not item.get("checkpoint") for item in deferred):
        errors.append("every deferred item must have an explicit plan and checkpoint")

    packets = controls.get("task_packet_plan")
    if not isinstance(packets, list) or len(packets) != 8:
        errors.append("M2 Task Packet plan must contain six OpenCode and two Grok packets")
    else:
        owned_paths: dict[str, str] = {}
        for packet in packets:
            owner = packet.get("owner")
            task_type = packet.get("task_type")
            if packet.get("status") != "PLANNED_NOT_ISSUED" or packet.get("self_approval") is not False:
                errors.append(f"{packet.get('packet_id')} must be unissued and forbid self-approval")
            if (owner, task_type) not in {("opencode", "script"), ("grok", "art")}:
                errors.append(f"{packet.get('packet_id')} has an invalid owner/task_type pair")
            for path in packet.get("allowed_paths", []):
                previous = owned_paths.get(path)
                if previous is not None:
                    errors.append(f"Task Packet path {path} is owned by both {previous} and {packet.get('packet_id')}")
                owned_paths[path] = packet.get("packet_id", "")

    review = controls.get("self_review")
    if not isinstance(review, dict):
        errors.append("M2 self_review must be an object")
    else:
        forbidden_true = {
            "r2_modified",
            "oversized_batch",
            "cycle",
            "lua_before_schema",
            "unknown_platform_used_before_probe",
            "deferred_defaulted",
            "unbound_implementation_package",
        }
        required_true = {
            "required_scope_covered",
            "seed_and_secret_gates_covered",
            "repeat_safety_covered",
            "all_31_acceptance_ids_mapped",
            "only_first_batch_frozen",
        }
        if any(review.get(key) is not False for key in forbidden_true):
            errors.append("M2 self-review reports a freeze-blocking defect")
        if any(review.get(key) is not True for key in required_true):
            errors.append("M2 self-review lacks a required positive assertion")


def _check_probe_contract(probes: dict[str, Any], errors: list[str]) -> None:
    rules = probes.get("rules")
    if not isinstance(rules, dict):
        errors.append("capability probe matrix rules must be an object")
        return
    if rules.get("not_run_is_pass") is not False:
        errors.append("capability probe matrix must explicitly forbid NOT_RUN as PASS")
    if rules.get("allowed_batch_results") != BATCH_RESULTS:
        errors.append("M2 batch results must preserve the repository five-state contract")
    if rules.get("allowed_probe_execution_statuses") != PROBE_EXECUTION_STATUSES:
        errors.append(
            "probe execution statuses must be PASS/FAIL/NOT_RUN/"
            "BLOCKED_EXTERNAL/BLOCKED_ENVIRONMENT"
        )
    if rules.get("probe_result_required_fields") != PROBE_RESULT_REQUIRED_FIELDS:
        errors.append("probe result contract does not preserve every required evidence field")


def _classify_lifecycle(
    milestone: dict[str, Any],
    recovery: dict[str, Any],
    errors: list[str],
) -> str:
    if recovery.get("evidence_id") != "M2-B001-RECOVERY-CLOSEOUT-001-E002":
        errors.append("recovery closeout evidence identity is missing or stale")
    if recovery.get("task_id") != "RULES-RESIDUE-M2-B001-RECOVERY-CLOSEOUT-IMPLEMENT-002":
        errors.append("recovery closeout task identity is missing or stale")
    if recovery.get("closeout_id") != "M2-B001-RECOVERY-CLOSEOUT-001" or recovery.get("attempt_number") != 2:
        errors.append("recovery closeout/attempt identity is missing or stale")
    if recovery.get("historical_projection") != {
        "R2-INT-010": "FAIL",
        "source_path": "reports/m2/probes/probe-results.json",
        "source_sha256": "154e7c0ddf8ce7b2243ad6c78d10ceb6cddf02c3aeb6592716dcc5ad8fc64218",
    }:
        errors.append("recovery closeout must preserve historical R2-INT-010=FAIL")
    if recovery.get("effective_projection", {}).get("R2-INT-010") != "RESOLVED_ADAPTER":
        errors.append("recovery closeout must project effective R2-INT-010=RESOLVED_ADAPTER")
    if recovery.get("non_claims") != {
        "formal_B002": False,
        "formal_B009": False,
        "aggregate_M2_pass": False,
        "aggregate_external_capability_pass": False,
    }:
        errors.append("recovery closeout overclaims formal or aggregate readiness")
    if recovery.get("readiness") != {
        "M2-B002": "NOT_STARTED",
        "M2-B002_READY": "NO",
        "blocking_ids": EXPECTED_RECOVERY_BLOCKERS,
    }:
        errors.append("recovery closeout downstream blockers or readiness changed")
    if recovery.get("candidate_binding") != {
        "strategy": "EXACT_HEAD_AT_VALIDATION",
        "execution_status": "NOT_RUN",
        "required_phase": "INDEPENDENT_ACCEPT",
        "must_bind_exact_commit_tree": True,
        "clean_worktree_required": True,
    }:
        errors.append("recovery closeout candidate binding is not pending exact-HEAD validation")

    active = milestone.get("active_plan")
    active_state = active.get("implementation_state") if isinstance(active, dict) else None
    lifecycle_pair = (milestone.get("state"), active_state)
    if lifecycle_pair == ("FROZEN", "NOT_STARTED"):
        if recovery.get("lifecycle") != {
            "candidate_state": FROZEN_RECOVERY_PENDING,
            "lifecycle_closeout_executed": False,
            "independent_acceptance": "NOT_RUN",
        }:
            errors.append("frozen recovery evidence falsely claims lifecycle closeout")
        return FROZEN_RECOVERY_PENDING
    if lifecycle_pair == ("ACCEPTED", "ACCEPTED"):
        return ACCEPTED_WITH_BLOCKERS

    errors.append(
        f"{INVALID_MIXED_STATE}: milestone state and active implementation state are {lifecycle_pair!r}"
    )
    return INVALID_MIXED_STATE


def collect_validation(project_root: Path = PROJECT_ROOT) -> tuple[list[str], str]:
    global PROJECT_ROOT, PLAN_ROOT
    original_root = PROJECT_ROOT
    original_plan_root = PLAN_ROOT
    PROJECT_ROOT = project_root.resolve()
    PLAN_ROOT = PROJECT_ROOT / ".codex" / "plans" / "m2-vertical-slice"
    errors: list[str] = []
    lifecycle_state = INVALID_MIXED_STATE
    try:
        batches = _read_json(PLAN_ROOT / "batches.json", errors)
        probes = _read_json(PLAN_ROOT / "capability-probes.json", errors)
        controls = _read_json(PLAN_ROOT / "controls.json", errors)
        milestone = _read_json(PROJECT_ROOT / ".codex" / "state" / "MILESTONE_PLAN.yaml", errors)
        route = _read_json(PROJECT_ROOT / ".codex" / "routes" / "m2-vertical-slice-plan-request.json", errors)
        recovery = _read_json(PROJECT_ROOT / RECOVERY_EVIDENCE_PATH, errors)

        if isinstance(batches, dict):
            _check_dag(batches, errors)
        if isinstance(probes, dict):
            _check_probe_contract(probes, errors)
            probe_items = probes.get("probes")
            expected = [f"R2-INT-{index:03d}" for index in range(1, 13)]
            if not isinstance(probe_items, list) or [item.get("id") for item in probe_items if isinstance(item, dict)] != expected:
                errors.append("capability probe matrix must contain ordered R2-INT-001--012")
            elif any(item.get("current_status") != "DEFERRED_WITH_NON_BLOCKING_PROOF" for item in probe_items):
                errors.append("R2 integration probe statuses must preserve installation classifications")
        if isinstance(controls, dict):
            _check_controls(controls, errors)
        if isinstance(milestone, dict):
            if (milestone.get("milestone"), milestone.get("batch_id")) != ("M2", "M2-B001"):
                errors.append("milestone machine source must remain M2 / M2-B001")
            active = milestone.get("active_plan")
            if not isinstance(active, dict):
                errors.append("active M2 plan must remain an object")
            if isinstance(recovery, dict):
                lifecycle_state = _classify_lifecycle(milestone, recovery, errors)
        if isinstance(route, dict):
            identity = (route.get("route_id"), route.get("mode"), route.get("milestone"), route.get("batch_id"))
            if identity != ("M2-VERTICAL-SLICE-PLAN", "PLAN", "M2", "M2-B001"):
                errors.append("M2 PLAN route request identity is invalid")
            for document in route.get("documents", []):
                path = document.get("path", "") if isinstance(document, dict) else ""
                if Path(path).is_absolute():
                    errors.append(f"persistent M2 route request contains an absolute path: {path}")

        _check_projection_parity(errors)
        required_markdown = [
            PLAN_ROOT / "M2_VERTICAL_SLICE_PLAN.md",
            PLAN_ROOT / "READING_MAP_REQUESTS.md",
        ]
        for path in required_markdown:
            if not path.is_file():
                errors.append(f"missing M2 plan artifact: {path.relative_to(PROJECT_ROOT)}")
    finally:
        PROJECT_ROOT = original_root
        PLAN_ROOT = original_plan_root
    return errors, lifecycle_state


def collect_errors(project_root: Path = PROJECT_ROOT) -> list[str]:
    return collect_validation(project_root)[0]


def classify_lifecycle(project_root: Path = PROJECT_ROOT) -> str:
    errors, lifecycle_state = collect_validation(project_root)
    if errors:
        return INVALID_MIXED_STATE
    return lifecycle_state


def main() -> int:
    errors, lifecycle_state = collect_validation()
    if errors:
        print("M2_PLAN_VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("M2_PLAN_VALIDATION: PASS")
    print("- 16 ordered acyclic batches; only M2-B001 frozen: PASS")
    print("- 12 integration probes and 31 acceptance gates: PASS")
    print("- Task Packet ownership, deferred checkpoints, and external NOT_RUN states: PASS")
    print("- routed machine-input projections match their repository sources byte-for-byte: PASS")
    print(f"- M2-B001 lifecycle state: {lifecycle_state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
