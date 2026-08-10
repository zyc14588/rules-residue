local contract = require("lib.contract")
local visibility = require("lib.visibility")

local M = {}

function M.project_state(ctx, state, audience)
  contract.assert_table(ctx, "ctx")
  contract.assert_table(state, "state")
  contract.assert_table(audience, "audience")
  contract.assert_string(audience.id, "audience.id")
  contract.assert_table(state.authority, "state.authority")

  local facts = {}
  if state.world_truth ~= nil then
    facts = state.world_truth.facts or {}
  end

  return {
    schema_version = "rules-residue.participant-projection/0.1",
    audience_id = audience.id,
    source_state_revision = state.revision,
    phase = state.phase,
    scene_id = state.scene_id,
    visible_facts = visibility.project_facts(facts, audience, state.authority),
    visible_characters = visibility.project_characters(state.characters, audience, state.authority),
    visible_tracks = visibility.project_tracks(state.tracks),
    authority = {
      gm_mode = state.authority.gm_mode,
      gm_participant_id = state.authority.gm_participant_id,
      locked = state.authority.locked,
    },
  }
end

return M
