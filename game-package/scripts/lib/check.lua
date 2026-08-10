local contract = require("lib.contract")

local M = {}

function M.classify(total, difficulty)
  contract.assert_integer(total, "total")
  contract.assert_integer(difficulty, "difficulty")
  if total >= difficulty + 3 then
    return "strong_success"
  end
  if total >= difficulty then
    return "success"
  end
  if total >= difficulty - 2 then
    return "success_with_cost"
  end
  return "failure_with_consequence"
end

function M.validate_roll_result(roll_result, expected_request_id, expected_modifier, expected_difficulty)
  contract.assert_table(roll_result, "roll_result")
  if roll_result.schema_version ~= "rules-residue.roll-result/0.1" then
    error("unsupported roll result schema")
  end
  if roll_result.request_id ~= expected_request_id then
    error("roll result request_id mismatch")
  end
  contract.assert_table(roll_result.faces, "roll_result.faces")
  if #roll_result.faces ~= 2 then
    error("roll result must contain exactly two faces")
  end
  local dice_total = 0
  for _, face in ipairs(roll_result.faces) do
    contract.assert_integer(face, "roll face")
    if face < 1 or face > 6 then
      error("roll face outside d6 range")
    end
    dice_total = dice_total + face
  end
  if roll_result.dice_total ~= dice_total then
    error("dice_total mismatch")
  end
  if roll_result.modifier ~= expected_modifier then
    error("roll modifier mismatch")
  end
  if roll_result.difficulty ~= expected_difficulty then
    error("roll difficulty mismatch")
  end
  if roll_result.total ~= dice_total + expected_modifier then
    error("roll total mismatch")
  end
  contract.assert_string(roll_result.rng_event_id, "roll_result.rng_event_id")
  return roll_result
end

return M
