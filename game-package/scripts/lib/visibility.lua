local contract = require("lib.contract")

local M = {}

local function split_once(value, delimiter)
  local start_index, end_index = string.find(value, delimiter, 1, true)
  if start_index == nil then
    return value, nil
  end
  return string.sub(value, 1, start_index - 1), string.sub(value, end_index + 1)
end

function M.can_view(label, audience, authority)
  if label == "public" then
    return true
  end
  if label == "gm_only" then
    if audience == nil or authority == nil then
      return false
    end
    local gm_kind = audience.kind == "human_gm" or audience.kind == "ai_gm"
    return gm_kind and audience.id == authority.gm_participant_id
  end

  local scope, identifier = split_once(label or "", ":")
  if identifier == nil or audience == nil then
    return false
  end
  if scope == "participant" then
    return audience.id == identifier
  end
  if scope == "team" then
    return audience.team_id == identifier
  end
  if scope == "agent" then
    return audience.agent_id == identifier
  end
  return false
end

function M.project_facts(facts, audience, authority)
  local visible = {}
  for _, fact in ipairs(facts or {}) do
    if M.can_view(fact.visibility, audience, authority) then
      visible[#visible + 1] = contract.deep_copy(fact)
    end
  end
  return visible
end

function M.project_characters(characters, audience, authority)
  local visible = {}
  for _, character in ipairs(characters or {}) do
    local label = character.visibility or "public"
    if M.can_view(label, audience, authority) then
      local projected = contract.deep_copy(character)
      if character.controller ~= audience.id and not M.can_view("gm_only", audience, authority) then
        projected.private_notes = nil
      end
      visible[#visible + 1] = projected
    end
  end
  return visible
end

function M.project_tracks(tracks)
  local visible = {}
  for _, key in ipairs(contract.sorted_keys(tracks or {})) do
    visible[key] = tracks[key]
  end
  return visible
end

return M
