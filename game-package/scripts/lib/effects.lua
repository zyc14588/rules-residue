local contract = require("lib.contract")

local M = {}

local function make_effect(action, index, effect_type, reason, visibility, payload)
  contract.assert_action(action)
  contract.assert_integer(index, "effect index")
  contract.assert_string(effect_type, "effect type")
  contract.assert_string(reason, "effect reason")
  contract.assert_string(visibility, "effect visibility")
  contract.assert_table(payload, "effect payload")
  return {
    schema_version = "rules-residue.effect/0.1",
    effect_id = action.action_id .. ":effect:" .. tostring(index),
    type = effect_type,
    source_action_id = action.action_id,
    reason = reason,
    visibility = visibility,
    payload = payload,
  }
end

function M.append_event(action, index, outcome, payload)
  local event_payload = contract.deep_copy(payload or {})
  event_payload.outcome = outcome
  event_payload.actor_id = action.actor_id
  event_payload.action_type = action.action_type
  event_payload.target_id = action.target_id
  return make_effect(action, index, "append_event", "record authoritative action resolution", action.visibility, event_payload)
end

function M.adjust_resource(action, index, character_id, resource, amount, reason, visibility)
  return make_effect(action, index, "adjust_resource", reason, visibility or action.visibility, {
    character_id = character_id,
    resource = resource,
    amount = amount,
  })
end

function M.set_status(action, index, target_id, status_id, payload, reason, visibility)
  local value = contract.deep_copy(payload or {})
  local duration = value.duration or { kind = "scene" }
  value.duration = nil
  return make_effect(action, index, "set_status", reason, visibility or action.visibility, {
    target_id = target_id,
    status_id = status_id,
    value = value,
    duration = contract.deep_copy(duration),
  })
end

function M.clear_status(action, index, target_id, status_id, reason, visibility)
  return make_effect(action, index, "clear_status", reason, visibility or action.visibility, {
    target_id = target_id,
    status_id = status_id,
  })
end

function M.reveal_fact(action, index, fact_id, reason, visibility)
  return make_effect(action, index, "reveal_fact", reason, visibility or action.visibility, {
    fact_id = fact_id,
    audience = visibility or action.visibility,
  })
end

function M.advance_track(action, index, track_id, amount, reason, visibility)
  return make_effect(action, index, "advance_track", reason, visibility or action.visibility, {
    track_id = track_id,
    amount = amount,
  })
end

function M.set_flag(action, index, flag_id, value, reason, visibility)
  return make_effect(action, index, "set_flag", reason, visibility or action.visibility, {
    flag_id = flag_id,
    value = value,
  })
end

function M.grant_reroll_token(action, index, character_id, action_id, reason, visibility)
  return make_effect(action, index, "grant_reroll_token", reason, visibility or action.visibility, {
    character_id = character_id,
    bound_action_id = action_id,
    uses = 1,
  })
end

return M
