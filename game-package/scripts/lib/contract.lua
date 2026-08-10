local M = {}

local ACTION_TYPES = {
  investigate = true,
  influence = true,
  intervene = true,
  assist = true,
  stabilize = true,
  spend_insight = true,
}

local APPROACHES = {
  analyze = true,
  connect = true,
  intervene = true,
  endure = true,
}

local ACTOR_KINDS = {
  human_player = true,
  ai_player = true,
  human_gm = true,
  ai_gm = true,
  system = true,
}

function M.assert_table(value, name)
  if type(value) ~= "table" then
    error(name .. " must be a table")
  end
  return value
end

function M.assert_string(value, name)
  if type(value) ~= "string" or value == "" then
    error(name .. " must be a non-empty string")
  end
  return value
end

function M.assert_integer(value, name)
  if type(value) ~= "number" or value % 1 ~= 0 then
    error(name .. " must be an integer")
  end
  return value
end

function M.assert_boolean(value, name)
  if type(value) ~= "boolean" then
    error(name .. " must be a boolean")
  end
  return value
end

function M.assert_action(action)
  M.assert_table(action, "action")
  if action.schema_version ~= "rules-residue.structured-action/0.1" then
    error("unsupported action schema")
  end
  M.assert_string(action.action_id, "action.action_id")
  M.assert_string(action.idempotency_key, "action.idempotency_key")
  M.assert_string(action.actor_id, "action.actor_id")
  if not ACTOR_KINDS[action.actor_kind] then
    error("unsupported actor_kind")
  end
  if not ACTION_TYPES[action.action_type] then
    error("unsupported action_type")
  end
  M.assert_string(action.goal, "action.goal")
  if not APPROACHES[action.approach] then
    error("unsupported approach")
  end
  M.assert_table(action.parameters, "action.parameters")
  M.assert_string(action.visibility, "action.visibility")
  if action.direct_state_patch ~= nil then
    error("direct state patches are forbidden")
  end
  return action
end

function M.assert_rule_input(rule_input)
  M.assert_table(rule_input, "ctx.rule_input")
  return rule_input
end

function M.copy_array(input)
  local output = {}
  if input == nil then
    return output
  end
  for index, value in ipairs(input) do
    output[index] = value
  end
  return output
end

function M.deep_copy(value)
  if type(value) ~= "table" then
    return value
  end
  local output = {}
  for key, item in pairs(value) do
    output[M.deep_copy(key)] = M.deep_copy(item)
  end
  return output
end

function M.sorted_keys(input)
  local keys = {}
  for key, _ in pairs(input or {}) do
    keys[#keys + 1] = key
  end
  table.sort(keys, function(left, right)
    return tostring(left) < tostring(right)
  end)
  return keys
end

function M.value_or(value, fallback)
  if value == nil then
    return fallback
  end
  return value
end

return M
