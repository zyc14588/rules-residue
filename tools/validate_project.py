from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import csv
import json
import re
import shutil
import subprocess
from typing import Any

from tools.lib.common import (
    GAME_PACKAGE_ROOT,
    PROJECT_ROOT,
    compute_lock_document,
    find_duplicates,
    read_json,
)
from tools.lib.reference_rules import classify, expected_effect_types, plan_kind
from tools.lib.schema_subset import validate

REQUIRED_ROOT_FILES = [
    "README.md",
    "AGENTS.md",
    "VERSION",
    "LICENSE-PENDING.md",
    "governance/decisions.json",
    "governance/scope.json",
    "governance/release-gates.json",
    "governance/traceability.csv",
    "game-package/manifest.json",
    "game-package/package.lock.json",
    "docs/authority/12_HYBRID_DEVELOPMENT_WORKFLOW.md",
    "workflow/task-packet.schema.json",
    ".opencode/SCRIPT_TASK_PROMPT.md",
    ".grok/ART_TASK_PROMPT.md",
]

SCHEMA_MAP = {
    "manifest": "manifest.schema.json",
    "scenario": "scenario.schema.json",
    "module_manifest": "module-manifest.schema.json",
    "expected_path": "expected-path.schema.json",
    "action": "structured-action.schema.json",
    "roll_result": "roll-result.schema.json",
    "state": "game-state.schema.json",
    "memory": "memory-record.schema.json",
}

FORBIDDEN_IP_TERMS = [
    "call of cthulhu",
    "chaosium",
    "克苏鲁的呼唤",
    "dungeons & dragons",
    "pathfinder roleplaying game",
]

FORBIDDEN_LUA_PATTERNS = {
    r"\bio\s*\.": "filesystem API io.*",
    r"\bos\s*\.": "operating-system API os.*",
    r"\bdebug\s*\.": "debug library",
    r"\bmath\s*\.\s*random(?:seed)?\b": "script-side randomness",
    r"\bpackage\s*\.\s*loadlib\b": "dynamic library loading",
    r"\bdofile\s*\(": "dofile",
    r"\bloadfile\s*\(": "loadfile",
    r"\bloadstring\s*\(": "loadstring",
    r"\bcollectgarbage\s*\(": "runtime control",
    r"\brequire\s*\(\s*[\"'](?:socket|http|https|ffi|lfs|posix)": "external module",
}

ALLOWED_REQUIRE_MODULES = {
    "lib.contract",
    "lib.check",
    "lib.effects",
    "lib.visibility",
}


def _schema(name: str) -> dict[str, Any]:
    return read_json(GAME_PACKAGE_ROOT / "schemas" / SCHEMA_MAP[name])


def _extend_schema_errors(errors: list[str], label: str, instance: Any, schema_name: str) -> None:
    for issue in validate(instance, _schema(schema_name)):
        errors.append(f"{label}: {issue}")


def _check_json_files(errors: list[str]) -> None:
    for path in sorted(PROJECT_ROOT.rglob("*.json")):
        try:
            read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {path.relative_to(PROJECT_ROOT)}: {exc}")


def _check_manifest(errors: list[str]) -> dict[str, Any]:
    manifest = read_json(GAME_PACKAGE_ROOT / "manifest.json")
    _extend_schema_errors(errors, "manifest", manifest, "manifest")

    referenced: list[str] = []
    referenced.extend(manifest["entrypoints"].values())
    content = manifest["content"]
    referenced.extend(
        [
            content["ruleset"],
            content["action_catalog"],
            content["status_catalog"],
            content["character_templates"],
        ]
    )
    referenced.extend(content["locales"])
    referenced.extend(content["modules"])
    for relative in referenced:
        if not (GAME_PACKAGE_ROOT / relative).is_file():
            errors.append(f"manifest references missing file: {relative}")

    if manifest["release"]["public_release_blocked"] is not True:
        errors.append("public release must remain blocked during M0")
    if manifest["release"]["license"] != "LicenseRef-Pending-FirstParty":
        errors.append("M0 license marker changed without closing RR-O001")
    return manifest


def _check_governance(errors: list[str], manifest: dict[str, Any]) -> None:
    decisions = read_json(PROJECT_ROOT / "governance" / "decisions.json")
    entries = decisions.get("decisions", [])
    ids = [entry.get("id", "") for entry in entries]
    for duplicate in find_duplicates(ids):
        errors.append(f"duplicate decision id: {duplicate}")
    allowed_status = {"ACCEPTED", "PROVISIONAL", "OPEN", "REJECTED"}
    for entry in entries:
        decision_id = entry.get("id", "")
        if re.fullmatch(r"RR-[DPO][0-9]{3}", decision_id) is None:
            errors.append(f"invalid decision id: {decision_id!r}")
        if entry.get("status") not in allowed_status:
            errors.append(f"invalid status for {decision_id}: {entry.get('status')!r}")
    status_by_id = {entry["id"]: entry["status"] for entry in entries if "id" in entry}
    for required in ["RR-D001", "RR-D006", "RR-D007", "RR-D009", "RR-D014", "RR-D016", "RR-D018", "RR-D019", "RR-D020", "RR-D021", "RR-D022", "RR-D023"]:
        if status_by_id.get(required) != "ACCEPTED":
            errors.append(f"required accepted decision missing: {required}")
    for blocker in manifest["release"]["blockers"]:
        if status_by_id.get(blocker) != "OPEN":
            errors.append(f"manifest release blocker is not OPEN: {blocker}")

    scope = read_json(PROJECT_ROOT / "governance" / "scope.json")
    p0 = scope.get("p0", [])
    requirement_ids = [item.get("id", "") for item in p0]
    for duplicate in find_duplicates(requirement_ids):
        errors.append(f"duplicate P0 requirement id: {duplicate}")
    acceptance_ids = [acc for item in p0 for acc in item.get("acceptance", [])]
    for duplicate in find_duplicates(acceptance_ids):
        errors.append(f"duplicate acceptance id: {duplicate}")

    trace_path = PROJECT_ROOT / "governance" / "traceability.csv"
    with trace_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    traced_requirements = {row["Requirement"] for row in rows}
    missing = sorted(set(requirement_ids) - traced_requirements)
    if missing:
        errors.append(f"P0 requirements missing from traceability: {missing}")
    traced_acceptance: set[str] = set()
    for row in rows:
        traced_acceptance.update(item for item in row["Acceptance"].split(";") if item)
    missing_acceptance = sorted(set(acceptance_ids) - traced_acceptance)
    if missing_acceptance:
        errors.append(f"acceptance ids missing from traceability: {missing_acceptance}")

    gates = read_json(PROJECT_ROOT / "governance" / "release-gates.json")
    gate_ids = {gate["id"] for gate in gates.get("gates", [])}
    for profile, data in gates.get("profiles", {}).items():
        unknown = sorted(set(data.get("required", [])) - gate_ids)
        if unknown:
            errors.append(f"release profile {profile} references unknown gates: {unknown}")
    public = set(gates["profiles"]["public_release"]["required"])
    for required in ["GATE-REL-001", "GATE-REL-002"]:
        if required not in public:
            errors.append(f"public release profile missing gate: {required}")
    for profile in ["development", "integration", "public_release"]:
        if "GATE-WORKFLOW-001" not in set(gates["profiles"][profile]["required"]):
            errors.append(f"release profile {profile} missing workflow gate")


def _check_control_contract(errors: list[str]) -> None:
    actions = read_json(GAME_PACKAGE_ROOT / "rules" / "action_catalog.json")["actions"]
    influence = next((item for item in actions if item.get("id") == "influence"), None)
    if influence is None:
        errors.append("influence action is missing")
        return
    contract = influence.get("control_effect", {})
    if contract.get("can_substitute_next_action") is not True:
        errors.append("influence action does not preserve bounded action substitution")
    if contract.get("default_max_actions") != 1:
        errors.append("P0 influence control must default to exactly one substituted action")


def _check_locales(errors: list[str]) -> None:
    locale_paths = [GAME_PACKAGE_ROOT / "locales" / "zh-CN.json", GAME_PACKAGE_ROOT / "locales" / "en.json"]
    locales = [read_json(path)["strings"] for path in locale_paths]
    required_keys: set[str] = set()
    for entry in read_json(GAME_PACKAGE_ROOT / "rules" / "ruleset.json")["approaches"]:
        required_keys.add(entry["name_key"])
    for entry in read_json(GAME_PACKAGE_ROOT / "rules" / "ruleset.json")["resources"]:
        required_keys.add(entry["name_key"])
    for entry in read_json(GAME_PACKAGE_ROOT / "rules" / "action_catalog.json")["actions"]:
        required_keys.add(entry["name_key"])
    for entry in read_json(GAME_PACKAGE_ROOT / "rules" / "status_catalog.json")["statuses"]:
        required_keys.add(entry["name_key"])
    for entry in read_json(GAME_PACKAGE_ROOT / "rules" / "character_templates.json")["templates"]:
        required_keys.add(entry["name_key"])
        required_keys.add(entry["notes_key"])
    for path, strings in zip(locale_paths, locales):
        missing = sorted(required_keys - set(strings))
        if missing:
            errors.append(f"locale {path.name} missing keys: {missing}")


def _check_scenario_references(errors: list[str], scenario: dict[str, Any], label: str) -> None:
    scenes = scenario["scenes"]
    scene_ids = [scene["id"] for scene in scenes]
    for duplicate in find_duplicates(scene_ids):
        errors.append(f"{label}: duplicate scene id {duplicate}")
    scene_id_set = set(scene_ids)
    if scenario["metadata"]["entry_scene_id"] not in scene_id_set:
        errors.append(f"{label}: entry scene does not exist")
    minimum = scenario["metadata"]["recommended_players"]["minimum"]
    maximum = scenario["metadata"]["recommended_players"]["maximum"]
    if minimum > maximum:
        errors.append(f"{label}: recommended player minimum exceeds maximum")
    for scene in scenes:
        for target in scene["exits"]:
            if target not in scene_id_set:
                errors.append(f"{label}: scene {scene['id']} exits to missing scene {target}")
    clue_ids = [clue["id"] for clue in scenario["clues"]]
    for duplicate in find_duplicates(clue_ids):
        errors.append(f"{label}: duplicate clue id {duplicate}")
    for clue in scenario["clues"]:
        if clue["source_scene_id"] not in scene_id_set:
            errors.append(f"{label}: clue {clue['id']} references missing scene")
        if clue["critical"] is True and clue["failure_fallback"] is None:
            errors.append(f"{label}: critical clue {clue['id']} lacks failure fallback")
    threat_ids = [threat["id"] for threat in scenario["threats"]]
    for duplicate in find_duplicates(threat_ids):
        errors.append(f"{label}: duplicate threat id {duplicate}")
    if "keeper_truth" not in scenario["visibility"]["gm_only_fields"]:
        errors.append(f"{label}: keeper_truth is not declared gm_only")


def _check_roll_arithmetic(errors: list[str], roll: dict[str, Any], label: str) -> None:
    _extend_schema_errors(errors, label, roll, "roll_result")
    if sum(roll["faces"]) != roll["dice_total"]:
        errors.append(f"{label}: dice_total mismatch")
    if roll["dice_total"] + roll["modifier"] != roll["total"]:
        errors.append(f"{label}: total mismatch")


def _check_modules_and_vectors(errors: list[str]) -> None:
    golden_outcomes: set[str] = set()
    for module_name in ["tutorial", "golden"]:
        base = GAME_PACKAGE_ROOT / "modules" / module_name
        module_manifest = read_json(base / "manifest.json")
        scenario = read_json(base / "scenario.json")
        expected = read_json(base / "expected-path.json")
        _extend_schema_errors(errors, f"{module_name} module manifest", module_manifest, "module_manifest")
        _extend_schema_errors(errors, f"{module_name} scenario", scenario, "scenario")
        _extend_schema_errors(errors, f"{module_name} expected path", expected, "expected_path")
        if module_manifest["id"] != scenario["metadata"]["id"] or module_manifest["id"] != expected["module_id"]:
            errors.append(f"{module_name}: module/scenario/expected IDs differ")
        if module_manifest["classification"] != scenario["metadata"]["classification"]:
            errors.append(f"{module_name}: classification mismatch")
        if module_manifest["original_content"] is not True:
            errors.append(f"{module_name}: original_content must be true")
        _check_scenario_references(errors, scenario, module_name)

        vector_ids = [vector["id"] for vector in expected["vectors"]]
        for duplicate in find_duplicates(vector_ids):
            errors.append(f"{module_name}: duplicate vector id {duplicate}")
        for vector in expected["vectors"]:
            label = f"{module_name}/{vector['id']}"
            action = vector["action"]
            _extend_schema_errors(errors, f"{label} action", action, "action")
            expected_kind = plan_kind(action)
            if vector["expected"]["plan_kind"] != expected_kind:
                errors.append(f"{label}: plan kind mismatch")
            resolution_input = vector["resolution_input"]
            if resolution_input["kind"] == "roll":
                roll = resolution_input["roll_result"]
                _check_roll_arithmetic(errors, roll, f"{label} roll")
                if roll["request_id"] != action["action_id"] + ":roll":
                    errors.append(f"{label}: roll request_id mismatch")
            outcome, effect_types = expected_effect_types(action, vector["rule_input"], resolution_input)
            if vector["expected"]["outcome"] != outcome:
                errors.append(f"{label}: outcome mismatch; computed {outcome}")
            if vector["expected"]["effect_types"] != effect_types:
                errors.append(f"{label}: effect sequence mismatch; computed {effect_types}")
            if module_name == "golden" and resolution_input["kind"] == "roll":
                golden_outcomes.add(outcome)

    required_outcomes = {"strong_success", "success", "success_with_cost", "failure_with_consequence"}
    if golden_outcomes != required_outcomes:
        errors.append(f"golden vectors do not cover all four outcomes: {sorted(golden_outcomes)}")


def _check_fixtures(errors: list[str]) -> None:
    fixtures = GAME_PACKAGE_ROOT / "tests" / "fixtures"
    valid_action = read_json(fixtures / "valid_action.json")
    _extend_schema_errors(errors, "valid action fixture", valid_action, "action")
    invalid_action = read_json(fixtures / "invalid_action_direct_patch.json")
    if not validate(invalid_action, _schema("action")):
        errors.append("invalid action fixture unexpectedly passes action schema")
    _extend_schema_errors(errors, "sample state fixture", read_json(fixtures / "sample_state.json"), "state")
    _extend_schema_errors(errors, "sample memory fixture", read_json(fixtures / "sample_memory.json"), "memory")


def _check_lua(errors: list[str]) -> None:
    lua_files = sorted((GAME_PACKAGE_ROOT / "scripts").rglob("*.lua"))
    required = {"bootstrap.lua", "plan_action.lua", "resolve_action.lua", "project_state.lua"}
    found = {path.name for path in lua_files if path.parent == GAME_PACKAGE_ROOT / "scripts"}
    missing = sorted(required - found)
    if missing:
        errors.append(f"missing Lua entrypoints: {missing}")
    require_pattern = re.compile(r"require\s*\(\s*[\"']([^\"']+)[\"']\s*\)")
    for path in lua_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(PROJECT_ROOT)
        for pattern, description in FORBIDDEN_LUA_PATTERNS.items():
            if re.search(pattern, text, flags=re.IGNORECASE):
                errors.append(f"{rel}: forbidden Lua capability: {description}")
        for module in require_pattern.findall(text):
            if module not in ALLOWED_REQUIRE_MODULES:
                errors.append(f"{rel}: require of non-whitelisted module {module!r}")
        if re.search(r"ctx\s*\.\s*state(?:\s*\[[^]]+\]|\s*\.\s*[A-Za-z_][A-Za-z0-9_]*)?\s*=", text):
            errors.append(f"{rel}: direct ctx.state mutation is forbidden")
        if "return M" not in text:
            errors.append(f"{rel}: module does not return M")

    compiler = shutil.which("texluac") or shutil.which("luac")
    if compiler is not None:
        for path in lua_files:
            result = subprocess.run([compiler, "-p", str(path)], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                errors.append(f"{path.relative_to(PROJECT_ROOT)}: Lua syntax check failed: {result.stderr.strip()}")



def _check_hybrid_workflow(errors: list[str]) -> None:
    schema_path = PROJECT_ROOT / "workflow" / "task-packet.schema.json"
    schema = read_json(schema_path)
    examples = sorted((PROJECT_ROOT / "workflow" / "examples").glob("*.json"))
    if not examples:
        errors.append("hybrid workflow has no task packet examples")
        return
    seen_ids: list[str] = []
    for path in examples:
        packet = read_json(path)
        for issue in validate(packet, schema):
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: {issue}")
        task_id = packet.get("task_id", "")
        seen_ids.append(task_id)
        owner = packet.get("owner")
        task_type = packet.get("task_type")
        if owner == "opencode" and task_type != "script":
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: OpenCode task must be script")
        if owner == "grok" and task_type != "art":
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: Grok task must be art")
        if packet.get("status") != "PLANNED":
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: example task must remain PLANNED")
        if not packet.get("authority"):
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: task lacks authority sources")
        if not packet.get("acceptance"):
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: task lacks acceptance criteria")
    for duplicate in find_duplicates(seen_ids):
        errors.append(f"duplicate workflow example task id: {duplicate}")

def _check_originality(errors: list[str]) -> None:
    for path in sorted(GAME_PACKAGE_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".lua", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="strict").lower()
        for term in FORBIDDEN_IP_TERMS:
            if term in text:
                errors.append(f"{path.relative_to(PROJECT_ROOT)}: forbidden third-party IP marker {term!r}")
    binary_assets = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (GAME_PACKAGE_ROOT / "assets").rglob("*")
        if path.is_file() and path.name not in {"README.md", ".gitkeep"}
    ]
    if binary_assets:
        errors.append(f"M0 contains unapproved asset files: {binary_assets}")


def _check_lock(errors: list[str]) -> None:
    lock_path = GAME_PACKAGE_ROOT / "package.lock.json"
    actual = read_json(lock_path)
    expected = compute_lock_document()
    if actual != expected:
        errors.append("game-package/package.lock.json is stale; run python3 tools/update_lock.py")


def collect_errors() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_ROOT_FILES:
        if not (PROJECT_ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")
    if errors:
        return errors
    _check_json_files(errors)
    manifest = _check_manifest(errors)
    _check_governance(errors, manifest)
    _check_control_contract(errors)
    _check_locales(errors)
    _check_modules_and_vectors(errors)
    _check_fixtures(errors)
    _check_lua(errors)
    _check_hybrid_workflow(errors)
    _check_originality(errors)
    _check_lock(errors)
    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        print("VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALIDATION: PASS")
    print("- governance and traceability: PASS")
    print("- manifest and package references: PASS")
    print("- scenarios and golden vectors: PASS")
    print("- visibility/memory fixtures: PASS")
    print("- Lua static policy and available syntax check: PASS")
    print("- hybrid Codex/OpenCode/Grok workflow: PASS")
    print("- originality and release block: PASS")
    print("- package lock: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
