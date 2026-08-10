local contract = require("lib.contract")
local check = require("lib.check")
local effects = require("lib.effects")

local M = {}
local RULE_VERSION = "rules-residue.core@0.1.0-dev.1"

local function append(list, value)
  list[#list + 1] = value
end

local function next_index(list)
  return #list + 1
end

local function is_success(outcome)
  return outcome == "strong_success" or outcome == "success" or outcome == "success_with_cost"
end

local function resolve_resource_spend(ctx, action, resolution_input)
  if resolution_input.approved ~= true then
    error("resource spend was not approved by host")
  end
  if resolution_input.resource ~= "insight" or resolution_input.amount ~= 1 then
    error("unexpected resource spend approval")
  end

  local result_effects = {}
  append(result_effects, effects.append_event(action, next_index(result_effects), "resource_spent", {
    mode = action.parameters.mode,
  }))
  append(result_effects, effects.adjust_resource(
    action,
    next_index(result_effects),
    action.actor_id,
    "insight",
    -1,
    "spend insight",
    action.visibility
  ))

  local narration_facts = {}
  if action.parameters.mode == "reroll" then
    contract.assert_string(ctx.rule_input.reroll_for_action_id, "ctx.rule_input.reroll_for_action_id")
    append(result_effects, effects.grant_reroll_token(
      action,
      next_index(result_effects),
      action.actor_id,
      ctx.rule_input.reroll_for_action_id,
      "insight grants one bound reroll",
      action.visibility
    ))
    narration_facts[#narration_facts + 1] = "reroll_token_granted"
  elseif action.parameters.mode == "extra_information" then
    contract.assert_string(ctx.rule_input.extra_fact_id, "ctx.rule_input.extra_fact_id")
    append(result_effects, effects.reveal_fact(
      action,
      next_index(result_effects),
      ctx.rule_input.extra_fact_id,
      "insight reveals scenario-defined additional information",
      action.visibility
    ))
    narration_facts[#narration_facts + 1] = ctx.rule_input.extra_fact_id
  else
    error("unsupported insight mode")
  end

  return {
    schema_version = "rules-residue.resolution/0.1",
    resolution_id = action.action_id .. ":resolution",
    action_id = action.action_id,
    kind = "resource_spend",
    outcome = "resource_spent",
    rule_version = RULE_VERSION,
    roll_summary = nil,
    effects = result_effects,
    narration_facts = narration_facts,
  }
end

local function apply_success_effect(ctx, action, outcome, result_effects, narration_facts)
  if action.action_type == "investigate" then
    contract.assert_string(ctx.rule_input.success_fact_id, "ctx.rule_input.success_fact_id")
    append(result_effects, effects.reveal_fact(
      action,
      next_index(result_effects),
      ctx.rule_input.success_fact_id,
      "investigation produced an authoritative fact",
      action.visibility
    ))
    narration_facts[#narration_facts + 1] = ctx.rule_input.success_fact_id
  elseif action.action_type == "influence" then
    local status_id = ctx.rule_input.target_status or "intent_shifted"
    contract.assert_string(action.target_id, "action.target_id")
    local control_value = {
      goal = action.goal,
      outcome = outcome,
      control_scope = "intent",
      substitute_next_action = false,
      max_substituted_actions = 0,
      duration = { kind = "scene" },
    }
    if ctx.rule_input.substitute_next_action == true then
      contract.assert_table(ctx.rule_input.replacement_action, "ctx.rule_input.replacement_action")
      local maximum = ctx.rule_input.max_substituted_actions or 1
      contract.assert_integer(maximum, "ctx.rule_input.max_substituted_actions")
      if maximum ~= 1 then
        error("P0 bounded control may substitute exactly one action")
      end
      control_value.control_scope = "substitute_action"
      control_value.substitute_next_action = true
      control_value.max_substituted_actions = maximum
      control_value.replacement_action = contract.deep_copy(ctx.rule_input.replacement_action)
      control_value.duration = { kind = "next_action" }
    end
    append(result_effects, effects.set_status(
      action,
      next_index(result_effects),
      action.target_id,
      status_id,
      control_value,
      "successful influence changes target intent within declared bounded scope",
      action.visibility
    ))
    narration_facts[#narration_facts + 1] = status_id
  elseif action.action_type == "intervene" then
    contract.assert_string(ctx.rule_input.success_flag, "ctx.rule_input.success_flag")
    append(result_effects, effects.set_flag(
      action,
      next_index(result_effects),
      ctx.rule_input.success_flag,
      true,
      "successful intervention changes a scenario flag",
      action.visibility
    ))
    narration_facts[#narration_facts + 1] = ctx.rule_input.success_flag
  elseif action.action_type == "assist" then
    contract.assert_string(action.target_id, "action.target_id")
    append(result_effects, effects.set_status(
      action,
      next_index(result_effects),
      action.target_id,
      "focused",
      { granted_by = action.actor_id, bound_to = ctx.rule_input.assist_for_action_type },
      "successful assist grants one bounded advantage",
      action.visibility
    ))
    narration_facts[#narration_facts + 1] = "focused"
  elseif action.action_type == "stabilize" then
    local target_id = action.target_id or action.actor_id
    append(result_effects, effects.adjust_resource(
      action,
      next_index(result_effects),
      target_id,
      "strain",
      -1,
      "successful stabilization reduces strain",
      action.visibility
    ))
    if ctx.rule_input.clear_overloaded == true then
      append(result_effects, effects.clear_status(
        action,
        next_index(result_effects),
        target_id,
        "overloaded",
        "stabilization clears overloaded when host conditions are met",
        action.visibility
      ))
    end
    narration_facts[#narration_facts + 1] = "strain_reduced"
  else
    error("unsupported check action")
  end
end

function M.resolve_action(ctx, action, resolution_input)
  contract.assert_table(ctx, "ctx")
  contract.assert_action(action)
  contract.assert_rule_input(ctx.rule_input)
  contract.assert_table(resolution_input, "resolution_input")

  if resolution_input.kind == "resource_spend" then
    return resolve_resource_spend(ctx, action, resolution_input)
  end
  if resolution_input.kind ~= "roll" then
    error("unsupported resolution input kind")
  end

  contract.assert_table(ctx.actor, "ctx.actor")
  contract.assert_table(ctx.actor.approaches, "ctx.actor.approaches")
  contract.assert_table(ctx.actor.proficiencies, "ctx.actor.proficiencies")
  local approach = ctx.actor.approaches[action.approach] or 0
  local proficiency = ctx.actor.proficiencies[action.action_type] or 0
  local situational = ctx.rule_input.situational_modifier or 0
  local modifier = approach + proficiency + situational
  local difficulty = ctx.rule_input.difficulty

  local roll_result = check.validate_roll_result(
    resolution_input.roll_result,
    action.action_id .. ":roll",
    modifier,
    difficulty
  )
  local outcome = check.classify(roll_result.total, difficulty)
  local result_effects = {}
  local narration_facts = {}

  append(result_effects, effects.append_event(action, next_index(result_effects), outcome, {
    rng_event_id = roll_result.rng_event_id,
    total = roll_result.total,
    difficulty = difficulty,
    rule_version = RULE_VERSION,
  }))

  if is_success(outcome) then
    apply_success_effect(ctx, action, outcome, result_effects, narration_facts)
    if outcome == "strong_success" then
      append(result_effects, effects.adjust_resource(
        action,
        next_index(result_effects),
        action.actor_id,
        "insight",
        1,
        "strong success grants one insight subject to host cap",
        action.visibility
      ))
    elseif outcome == "success_with_cost" then
      append(result_effects, effects.adjust_resource(
        action,
        next_index(result_effects),
        action.actor_id,
        "strain",
        1,
        "success with cost increases strain",
        action.visibility
      ))
    end
  else
    if ctx.rule_input.critical_path == true then
      contract.assert_string(ctx.rule_input.failure_fact_id, "ctx.rule_input.failure_fact_id")
      append(result_effects, effects.reveal_fact(
        action,
        next_index(result_effects),
        ctx.rule_input.failure_fact_id,
        "critical-path failure reveals scenario-defined fallback information",
        action.visibility
      ))
      narration_facts[#narration_facts + 1] = ctx.rule_input.failure_fact_id
    end
    append(result_effects, effects.adjust_resource(
      action,
      next_index(result_effects),
      action.actor_id,
      "strain",
      1,
      "failure consequence increases strain",
      action.visibility
    ))
    if ctx.rule_input.failure_track_id ~= nil then
      append(result_effects, effects.advance_track(
        action,
        next_index(result_effects),
        ctx.rule_input.failure_track_id,
        1,
        "failure consequence advances a scenario threat",
        action.visibility
      ))
    end
  end

  return {
    schema_version = "rules-residue.resolution/0.1",
    resolution_id = action.action_id .. ":resolution",
    action_id = action.action_id,
    kind = "roll",
    outcome = outcome,
    rule_version = RULE_VERSION,
    roll_summary = {
      request_id = roll_result.request_id,
      faces = contract.copy_array(roll_result.faces),
      dice_total = roll_result.dice_total,
      modifier = roll_result.modifier,
      total = roll_result.total,
      difficulty = roll_result.difficulty,
      rng_event_id = roll_result.rng_event_id,
    },
    effects = result_effects,
    narration_facts = narration_facts,
  }
end

return M
