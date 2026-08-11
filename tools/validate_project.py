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
from pathlib import PurePosixPath
from typing import Any

from tools.lib.common import (
    GAME_PACKAGE_ROOT,
    PROJECT_ROOT,
    compute_lock_document,
    find_duplicates,
    read_json,
    runtime_relative_paths,
)
from tools.lib.reference_rules import expected_effect_types, plan_kind
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
    "tools/validate_opencode_task.py",
]

REQUIRED_AUTHORING_FILES = [
    "authoring/README.md",
    "authoring/story/00_STORY_BIBLE.md",
    "authoring/story/01_TRUTH_BIBLE.md",
    "authoring/story/02_MAIN_MYSTERY_GRAPH.md",
    "authoring/story/03_RETURN_HOME_ARC.md",
    "authoring/story/04_REVEAL_POLICY.md",
    "authoring/world/README.md",
    "authoring/world/regions/_template/REGION.md",
    "authoring/world/rule-domains/_template/RULE_DOMAIN.md",
    "authoring/arcs/README.md",
    "authoring/arcs/_template/ARC.md",
    "authoring/modules/README.md",
    "authoring/modules/_template/MODULE.md",
    "authoring/characters/README.md",
    "authoring/characters/npcs/_template/NPC.md",
    "authoring/characters/factions/_template/FACTION.md",
    "authoring/characters/entities/_template/ENTITY.md",
    "authoring/mysteries/README.md",
    "authoring/mysteries/clues/_template/CLUE.md",
    "authoring/mysteries/hypotheses/_template/HYPOTHESIS.md",
    "authoring/mysteries/revelations/_template/REVELATION.md",
    "authoring/art/README.md",
    "authoring/art/briefs/README.md",
    "authoring/art/briefs/_template/ART_BRIEF.md",
    "authoring/art/references/README.md",
    "docs/operations/CONTENT_AUTHORING_PIPELINE.md",
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

ORIGINALITY_TEXT_ROOTS = (
    "authoring",
    "game-package",
)

UNAPPROVED_TOP_LEVEL_CONTENT_SOURCES = (
    "knowledge",
)

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


REQUIRED_MODULES = {
    "rr.tutorial.zero-platform": "tutorial",
    "rr.golden.fifth-record": "golden",
}


def _schema(name: str, game_package_root: Path = GAME_PACKAGE_ROOT) -> dict[str, Any]:
    return read_json(game_package_root / "schemas" / SCHEMA_MAP[name])


def _extend_schema_errors(
    errors: list[str],
    label: str,
    instance: Any,
    schema_name: str,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> bool:
    issues = validate(instance, _schema(schema_name, game_package_root))
    for issue in issues:
        errors.append(f"{label}: {issue}")
    return not issues


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


def _check_roll_arithmetic(
    errors: list[str],
    roll: dict[str, Any],
    label: str,
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> None:
    if not _extend_schema_errors(errors, label, roll, "roll_result", game_package_root):
        return
    if sum(roll["faces"]) != roll["dice_total"]:
        errors.append(f"{label}: dice_total mismatch")
    if roll["dice_total"] + roll["modifier"] != roll["total"]:
        errors.append(f"{label}: total mismatch")


def _resolve_relative_file(
    errors: list[str],
    raw_path: Any,
    label: str,
    base: Path,
    containment_root: Path,
) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"{label}: path must be a non-empty string")
        return None
    if "\\" in raw_path:
        errors.append(f"{label}: path must use POSIX separators")
        return None

    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{label}: path escapes its allowed root: {raw_path}")
        return None
    if relative.as_posix() != raw_path or any(part in {"", "."} for part in relative.parts):
        errors.append(f"{label}: path is not canonical: {raw_path}")
        return None

    candidate = base.joinpath(*relative.parts)
    try:
        resolved_candidate = candidate.resolve()
        resolved_root = containment_root.resolve()
    except OSError as exc:
        errors.append(f"{label}: cannot resolve path {raw_path}: {exc}")
        return None
    if not resolved_candidate.is_relative_to(resolved_root):
        errors.append(f"{label}: path escapes its allowed root: {raw_path}")
        return None
    return candidate


def _read_json_checked(errors: list[str], path: Path, label: str) -> Any | None:
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: cannot read JSON: {exc}")
        return None


def _require_runtime_membership(
    errors: list[str],
    path: Path,
    label: str,
    game_package_root: Path,
    runtime_paths: set[str],
) -> bool:
    try:
        relative = path.relative_to(game_package_root).as_posix()
    except ValueError:
        errors.append(f"{label}: path is outside the Game Package runtime root")
        return False
    if relative not in runtime_paths:
        errors.append(f"{label}: file is not in the package runtime set: {relative}")
        return False
    return True


def _check_expected_vectors(
    errors: list[str],
    expected: dict[str, Any],
    label: str,
    game_package_root: Path,
    golden_outcomes: set[str] | None = None,
) -> None:
    vectors = expected["vectors"]
    vector_ids = [vector["id"] for vector in vectors]
    for duplicate in find_duplicates(vector_ids):
        errors.append(f"{label}: duplicate vector id {duplicate}")

    for vector in vectors:
        vector_label = f"{label}/{vector['id']}"
        action = vector["action"]
        action_valid = _extend_schema_errors(
            errors,
            f"{vector_label} action",
            action,
            "action",
            game_package_root,
        )
        if not action_valid:
            continue

        try:
            expected_kind = plan_kind(action)
            if vector["expected"]["plan_kind"] != expected_kind:
                errors.append(f"{vector_label}: plan kind mismatch")
            resolution_input = vector["resolution_input"]
            if resolution_input.get("kind") == "roll":
                roll = resolution_input.get("roll_result")
                if not isinstance(roll, dict):
                    errors.append(f"{vector_label}: roll resolution lacks roll_result")
                    continue
                _check_roll_arithmetic(
                    errors,
                    roll,
                    f"{vector_label} roll",
                    game_package_root,
                )
                if roll.get("request_id") != action["action_id"] + ":roll":
                    errors.append(f"{vector_label}: roll request_id mismatch")
            outcome, effect_types = expected_effect_types(
                action,
                vector["rule_input"],
                resolution_input,
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{vector_label}: cannot evaluate vector semantics: {exc}")
            continue

        if vector["expected"]["outcome"] != outcome:
            errors.append(f"{vector_label}: outcome mismatch; computed {outcome}")
        if vector["expected"]["effect_types"] != effect_types:
            errors.append(f"{vector_label}: effect sequence mismatch; computed {effect_types}")
        if golden_outcomes is not None and resolution_input.get("kind") == "roll":
            golden_outcomes.add(outcome)


def validate_module_registry(
    manifest: dict[str, Any],
    game_package_root: Path = GAME_PACKAGE_ROOT,
) -> list[str]:
    """Validate every runtime Module declared by the package registry."""

    errors: list[str] = []
    content = manifest.get("content")
    registered = content.get("modules") if isinstance(content, dict) else None
    if not isinstance(registered, list):
        errors.append("module registry: manifest.content.modules must be an array")
        return errors

    registered_strings = [item for item in registered if isinstance(item, str)]
    for duplicate in find_duplicates(registered_strings):
        errors.append(f"module registry: duplicate registered path {duplicate}")

    runtime_paths = set(runtime_relative_paths(game_package_root))
    discovered = {
        relative
        for relative in runtime_paths
        if (
            len(PurePosixPath(relative).parts) >= 3
            and PurePosixPath(relative).parts[0] == "modules"
            and PurePosixPath(relative).name == "manifest.json"
        )
    }
    resolved_registrations: set[str] = set()
    module_ids: list[str] = []
    golden_outcomes: set[str] = set()

    for index, raw_path in enumerate(registered):
        registry_label = f"module registry[{index}]"
        manifest_path = _resolve_relative_file(
            errors,
            raw_path,
            registry_label,
            game_package_root,
            game_package_root,
        )
        if manifest_path is None:
            continue

        relative = manifest_path.relative_to(game_package_root).as_posix()
        resolved_registrations.add(relative)
        relative_parts = PurePosixPath(relative).parts
        if len(relative_parts) < 3 or relative_parts[0] != "modules" or relative_parts[-1] != "manifest.json":
            errors.append(f"{registry_label}: registered Module must be modules/**/manifest.json: {relative}")
            continue
        if not manifest_path.is_file():
            errors.append(f"{registry_label}: registered Module does not exist: {relative}")
            continue
        if not _require_runtime_membership(
            errors,
            manifest_path,
            f"{registry_label} manifest",
            game_package_root,
            runtime_paths,
        ):
            continue

        label = relative.removesuffix("/manifest.json")
        module_manifest = _read_json_checked(errors, manifest_path, f"{label} module manifest")
        if not isinstance(module_manifest, dict):
            continue
        _extend_schema_errors(
            errors,
            f"{label} module manifest",
            module_manifest,
            "module_manifest",
            game_package_root,
        )

        module_id = module_manifest.get("id")
        if isinstance(module_id, str):
            module_ids.append(module_id)
            required_classification = REQUIRED_MODULES.get(module_id)
            if (
                required_classification is not None
                and module_manifest.get("classification") != required_classification
            ):
                errors.append(
                    f"{label}: required Module {module_id} must be classified "
                    f"{required_classification}"
                )
        if module_manifest.get("original_content") is not True:
            errors.append(f"{label}: original_content must be true")

        module_root = manifest_path.parent
        scenario_path = _resolve_relative_file(
            errors,
            module_manifest.get("scenario"),
            f"{label} scenario reference",
            module_root,
            module_root,
        )
        expected_path = _resolve_relative_file(
            errors,
            module_manifest.get("expected_path"),
            f"{label} expected path reference",
            module_root,
            module_root,
        )

        scenario: dict[str, Any] | None = None
        scenario_valid = False
        if scenario_path is not None:
            scenario_is_runtime = _require_runtime_membership(
                errors,
                scenario_path,
                f"{label} scenario reference",
                game_package_root,
                runtime_paths,
            )
            if not scenario_path.is_file():
                errors.append(f"{label}: scenario does not exist: {module_manifest.get('scenario')}")
            elif scenario_is_runtime:
                loaded = _read_json_checked(errors, scenario_path, f"{label} scenario")
                if isinstance(loaded, dict):
                    scenario = loaded
                    scenario_valid = _extend_schema_errors(
                        errors,
                        f"{label} scenario",
                        scenario,
                        "scenario",
                        game_package_root,
                    )

        expected: dict[str, Any] | None = None
        expected_valid = False
        if expected_path is not None:
            expected_is_runtime = _require_runtime_membership(
                errors,
                expected_path,
                f"{label} expected path reference",
                game_package_root,
                runtime_paths,
            )
            if not expected_path.is_file():
                errors.append(f"{label}: expected path does not exist: {module_manifest.get('expected_path')}")
            elif expected_is_runtime:
                loaded = _read_json_checked(errors, expected_path, f"{label} expected path")
                if isinstance(loaded, dict):
                    expected = loaded
                    expected_valid = _extend_schema_errors(
                        errors,
                        f"{label} expected path",
                        expected,
                        "expected_path",
                        game_package_root,
                    )

        if scenario is not None:
            metadata = scenario.get("metadata")
            scenario_id = metadata.get("id") if isinstance(metadata, dict) else None
            scenario_classification = (
                metadata.get("classification") if isinstance(metadata, dict) else None
            )
            if module_id != scenario_id:
                errors.append(f"{label}: module/scenario IDs differ")
            if module_manifest.get("classification") != scenario_classification:
                errors.append(f"{label}: classification mismatch")
            if scenario_valid:
                _check_scenario_references(errors, scenario, label)
        if expected is not None and module_id != expected.get("module_id"):
            errors.append(f"{label}: module/expected IDs differ")
        if expected is not None and expected_valid:
            outcomes = golden_outcomes if module_id == "rr.golden.fifth-record" else None
            _check_expected_vectors(errors, expected, label, game_package_root, outcomes)

    for unregistered in sorted(discovered - resolved_registrations):
        errors.append(f"unregistered executable Module manifest: {unregistered}")
    for duplicate in find_duplicates(module_ids):
        errors.append(f"duplicate Module ID: {duplicate}")

    missing_required = sorted(set(REQUIRED_MODULES) - set(module_ids))
    if missing_required:
        errors.append(f"required Tutorial/Golden Module IDs missing: {missing_required}")

    required_outcomes = {"strong_success", "success", "success_with_cost", "failure_with_consequence"}
    if golden_outcomes != required_outcomes:
        errors.append(f"golden vectors do not cover all four outcomes: {sorted(golden_outcomes)}")
    return errors


def _check_modules_and_vectors(errors: list[str], manifest: dict[str, Any]) -> None:
    errors.extend(validate_module_registry(manifest))


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

    opencode_skills = PROJECT_ROOT / ".opencode" / "skills"
    if opencode_skills.exists():
        errors.append(
            "OpenCode authority boundary: .opencode/skills/ is not authorized by RR-D023; "
            "use only .opencode/SCRIPT_TASK_PROMPT.md with a valid script Task Packet"
        )

    prompt_path = PROJECT_ROOT / ".opencode" / "SCRIPT_TASK_PROMPT.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    required_markers = {
        "tools/validate_opencode_task.py": "Task Packet validator command",
        "BLOCKED_NO_VALID_TASK_PACKET": "required refusal status",
        'owner == "opencode"': "OpenCode owner precondition",
        'task_type == "script"': "script task-type precondition",
        "allowed_paths": "allowed-path precondition",
        "default-deny": "positive default-deny authority model",
    }
    for marker, description in required_markers.items():
        if marker not in prompt:
            errors.append(f"OpenCode executor prompt lacks {description}: {marker}")


def validate_originality(
    project_root: Path = PROJECT_ROOT,
    game_package_root: Path | None = None,
) -> list[str]:
    """Validate governed content roots and reject known ungoverned sources."""

    errors: list[str] = []
    if game_package_root is None:
        game_package_root = project_root / "game-package"

    for relative in UNAPPROVED_TOP_LEVEL_CONTENT_SOURCES:
        path = project_root / relative
        if path.exists() or path.is_symlink():
            errors.append(
                f"unapproved top-level content source directory: {relative}/; "
                "RR-D003 requires content sources to use governed authoring/ or approved "
                "game-package/ inputs"
            )

    text_roots = {
        "authoring": project_root / "authoring",
        "game-package": game_package_root,
    }
    for relative in ORIGINALITY_TEXT_ROOTS:
        root = text_roots[relative]
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".lua", ".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="strict").lower()
            for term in FORBIDDEN_IP_TERMS:
                if term in text:
                    errors.append(
                        f"{path.relative_to(project_root)}: "
                        f"forbidden third-party IP marker {term!r}"
                    )

    binary_assets = [
        path.relative_to(project_root).as_posix()
        for path in (game_package_root / "assets").rglob("*")
        if path.is_file() and path.name not in {"README.md", ".gitkeep"}
    ]
    if binary_assets:
        errors.append(f"M0 contains unapproved asset files: {binary_assets}")
    return errors


def _check_originality(errors: list[str]) -> None:
    errors.extend(validate_originality())


def _check_lock(errors: list[str]) -> None:
    lock_path = GAME_PACKAGE_ROOT / "package.lock.json"
    actual = read_json(lock_path)
    expected = compute_lock_document()
    if actual != expected:
        errors.append("game-package/package.lock.json is stale; run python3 tools/update_lock.py")


def collect_errors() -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_ROOT_FILES + REQUIRED_AUTHORING_FILES:
        if not (PROJECT_ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")
    if errors:
        return errors
    _check_json_files(errors)
    manifest = _check_manifest(errors)
    _check_governance(errors, manifest)
    _check_control_contract(errors)
    _check_locales(errors)
    _check_modules_and_vectors(errors, manifest)
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
    print("- authoring source structure: PASS")
    print("- manifest and package references: PASS")
    print("- registered Modules, scenarios, and golden vectors: PASS")
    print("- visibility/memory fixtures: PASS")
    print("- Lua static policy and available syntax check: PASS")
    print("- hybrid Codex/OpenCode/Grok workflow: PASS")
    print("- originality and release block: PASS")
    print("- package lock: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
