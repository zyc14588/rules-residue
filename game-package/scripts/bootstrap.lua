local contract = require("lib.contract")

local M = {}

function M.bootstrap(ctx)
  contract.assert_table(ctx, "ctx")
  contract.assert_string(ctx.campaign_id, "ctx.campaign_id")
  contract.assert_string(ctx.package_version, "ctx.package_version")
  contract.assert_table(ctx.authority, "ctx.authority")
  contract.assert_string(ctx.authority.gm_participant_id, "ctx.authority.gm_participant_id")
  if ctx.authority.gm_mode ~= "human" and ctx.authority.gm_mode ~= "ai" then
    error("ctx.authority.gm_mode must be human or ai")
  end
  if ctx.authority.locked ~= true then
    error("campaign authority must be locked at bootstrap")
  end
  contract.assert_table(ctx.scenario, "ctx.scenario")
  contract.assert_table(ctx.scenario.metadata, "ctx.scenario.metadata")
  contract.assert_table(ctx.scenario.keeper_truth, "ctx.scenario.keeper_truth")

  local facts = {}
  for _, fact in ipairs(ctx.scenario.keeper_truth.immutable_facts or {}) do
    facts[#facts + 1] = contract.deep_copy(fact)
  end
  for _, clue in ipairs(ctx.scenario.clues or {}) do
    facts[#facts + 1] = {
      id = clue.fact_id,
      text = clue.text,
      visibility = "gm_only",
      source_clue_id = clue.id,
      revealed = false,
    }
    if clue.failure_fallback ~= nil then
      facts[#facts + 1] = {
        id = clue.failure_fallback.fact_id,
        text = clue.failure_fallback.text,
        visibility = "gm_only",
        source_clue_id = clue.id,
        revealed = false,
        partial = true,
      }
    end
  end

  local tracks = {}
  for _, threat in ipairs(ctx.scenario.threats or {}) do
    tracks[threat.id] = threat.initial
  end

  local state = {
    schema_version = "rules-residue.game-state/0.1",
    campaign_id = ctx.campaign_id,
    package_id = "org.trpgplatform.rules-residue",
    package_version = ctx.package_version,
    revision = 0,
    authority = contract.deep_copy(ctx.authority),
    phase = "setup",
    scene_id = ctx.scenario.metadata.entry_scene_id,
    participants = contract.deep_copy(ctx.participants or {}),
    characters = contract.deep_copy(ctx.characters or {}),
    world_truth = {
      scenario_id = ctx.scenario.metadata.id,
      facts = facts,
    },
    public_facts = {},
    tracks = tracks,
    flags = {},
    event_index = 0,
  }

  return {
    schema_version = "rules-residue.bootstrap-result/0.1",
    state = state,
    initial_event = {
      type = "campaign_initialized",
      package_id = state.package_id,
      package_version = state.package_version,
      scenario_id = ctx.scenario.metadata.id,
      gm_mode = state.authority.gm_mode,
    },
  }
end

return M
