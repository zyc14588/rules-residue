local contract = require("lib.contract")

local M = {}
local RULE_VERSION = "rules-residue.core@0.1.0-dev.1"

local CHECK_ACTIONS = {
  investigate = true,
  influence = true,
  intervene = true,
  assist = true,
  stabilize = true,
}

local function get_modifier(ctx, action)
  contract.assert_table(ctx.actor, "ctx.actor")
  contract.assert_table(ctx.actor.approaches, "ctx.actor.approaches")
  contract.assert_table(ctx.actor.proficiencies, "ctx.actor.proficiencies")
  local approach = ctx.actor.approaches[action.approach] or 0
  local proficiency = ctx.actor.proficiencies[action.action_type] or 0
  local situational = ctx.rule_input.situational_modifier or 0
  contract.assert_integer(approach, "approach value")
  contract.assert_integer(proficiency, "proficiency value")
  contract.assert_integer(situational, "situational modifier")
  return approach + proficiency + situational
end

function M.plan_action(ctx, action)
  contract.assert_table(ctx, "ctx")
  contract.assert_action(action)
  contract.assert_rule_input(ctx.rule_input)

  if action.action_type == "spend_insight" then
    local mode = action.parameters.mode
    if mode ~= "reroll" and mode ~= "extra_information" then
      error("spend_insight requires reroll or extra_information mode")
    end
    return {
      schema_version = "rules-residue.plan-result/0.1",
      action_id = action.action_id,
      kind = "resource_spend",
      rule_version = RULE_VERSION,
      roll_request = nil,
      resource_request = {
        character_id = action.actor_id,
        resource = "insight",
        amount = 1,
        mode = mode,
      },
    }
  end

  if not CHECK_ACTIONS[action.action_type] then
    error("action is not supported by the check planner")
  end

  local difficulty = ctx.rule_input.difficulty
  contract.assert_integer(difficulty, "ctx.rule_input.difficulty")
  if difficulty ~= 7 and difficulty ~= 9 and difficulty ~= 11 and difficulty ~= 13 then
    error("unsupported difficulty")
  end

  local modifier = get_modifier(ctx, action)
  return {
    schema_version = "rules-residue.plan-result/0.1",
    action_id = action.action_id,
    kind = "roll",
    rule_version = RULE_VERSION,
    roll_request = {
      schema_version = "rules-residue.roll-request/0.1",
      request_id = action.action_id .. ":roll",
      action_id = action.action_id,
      dice = { count = 2, sides = 6 },
      modifier = modifier,
      difficulty = difficulty,
      source = "host_authoritative",
    },
    resource_request = nil,
  }
end

return M
