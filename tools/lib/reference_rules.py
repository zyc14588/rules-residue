from __future__ import annotations

from typing import Any

SUCCESS_OUTCOMES = {"strong_success", "success", "success_with_cost"}


def classify(total: int, difficulty: int) -> str:
    if total >= difficulty + 3:
        return "strong_success"
    if total >= difficulty:
        return "success"
    if total >= difficulty - 2:
        return "success_with_cost"
    return "failure_with_consequence"


def plan_kind(action: dict[str, Any]) -> str:
    return "resource_spend" if action["action_type"] == "spend_insight" else "roll"


def expected_effect_types(
    action: dict[str, Any],
    rule_input: dict[str, Any],
    resolution_input: dict[str, Any],
) -> tuple[str, list[str]]:
    if resolution_input["kind"] == "resource_spend":
        mode = action.get("parameters", {}).get("mode")
        tail = "grant_reroll_token" if mode == "reroll" else "reveal_fact"
        return "resource_spent", ["append_event", "adjust_resource", tail]

    roll = resolution_input["roll_result"]
    outcome = classify(roll["total"], roll["difficulty"])
    effects = ["append_event"]
    if outcome in SUCCESS_OUTCOMES:
        action_type = action["action_type"]
        if action_type == "investigate":
            effects.append("reveal_fact")
        elif action_type == "influence":
            effects.append("set_status")
        elif action_type == "intervene":
            effects.append("set_flag")
        elif action_type == "assist":
            effects.append("set_status")
        elif action_type == "stabilize":
            effects.append("adjust_resource")
            if rule_input.get("clear_overloaded") is True:
                effects.append("clear_status")
        if outcome == "strong_success":
            effects.append("adjust_resource")
        elif outcome == "success_with_cost":
            effects.append("adjust_resource")
    else:
        if rule_input.get("critical_path") is True:
            effects.append("reveal_fact")
        effects.append("adjust_resource")
        if rule_input.get("failure_track_id") is not None:
            effects.append("advance_track")
    return outcome, effects
