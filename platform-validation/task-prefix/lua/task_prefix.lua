-- Finite C01 observation task. Authoritative data lives only in Host State.
local M = {}
local TASK = "TASK.TEST.CLOCK_OBSERVATION.V1"
local NPC = "npc.lin-que"
local TARGET = "target.departure_board"
local ITEM = "TEST_ONLY.tutorial.ordinary_record_sheet"
local TEXT = "显示牌变动后回到同一分钟。"
local TERMS = "我想留下一份这块显示牌的现场记录。愿意的话，请你亲自看一次它怎样变动，再把你看到的经过告诉我；我会和你一起看。这里不收原因猜测，也不要求去站台。每个完成自己这份观察说明的人可领一张空白记录纸，每人一次。你可以拒绝或放弃；缺少共同观察时先补证。"

local function keys(value)
    local out = {}
    for k in pairs(value) do out[#out + 1] = k end
    table.sort(out)
    return out
end

local function quote(value)
    local short = {[8] = "\\b", [9] = "\\t", [10] = "\\n", [12] = "\\f", [13] = "\\r"}
    return '"' .. string.gsub(value, '[%z\1-\31\\"]', function(c)
        if c == '"' then return '\\"' end
        if c == '\\' then return '\\\\' end
        return short[string.byte(c)] or string.format("\\u%04x", string.byte(c))
    end) .. '"'
end

local encode
local function encode_array(value)
    local out = {}
    for i = 1, #value do out[i] = encode(value[i]) end
    return "[" .. table.concat(out, ",") .. "]"
end
encode = function(value)
    local kind = type(value)
    if kind == "string" then return quote(value) end
    if kind == "boolean" then return value and "true" or "false" end
    if kind == "number" then return tostring(value) end
    if kind == "nil" then return "null" end
    assert(kind == "table", "INVALID_PAYLOAD")
    if #value > 0 then return encode_array(value) end
    local out = {}
    for _, k in ipairs(keys(value)) do
        assert(type(k) == "string", "INVALID_PAYLOAD")
        out[#out + 1] = quote(k) .. ":" .. encode(value[k])
    end
    return "{" .. table.concat(out, ",") .. "}"
end

-- Also used by isolated native codec tests, never as a game callback.
function M.encode_payload(payload)
    local text = encode(payload)
    return text, "sha256:" .. string.sha256(text)
end

local function template(name)
    return host.state.get({"native_values", name})
end
local function array() return template("empty_array") end
local function state() return host.state.get(array()) end
local function put(value) host.state.put(array(), value) end
local function count(value)
    local n = 0
    for _ in pairs(value) do n = n + 1 end
    return n
end
local function membership(value)
    local out = {}
    for _, k in ipairs(value) do out[k] = true end
    return out
end
local function id(value)
    return type(value) == "string" and #value >= 1 and #value <= 128
        and string.match(value, "^[a-zA-Z0-9][a-zA-Z0-9_.-]*$") ~= nil
end
local function event_id(value)
    return type(value) == "string" and #value == 36 and string.match(value, "^evt%-[0-9a-f]+$") ~= nil
end
local function text(value)
    if type(value) ~= "string" then return false end
    local n = utf8.len(value)
    return n ~= nil and n >= 1 and n <= 2048
end
local function exact(value, fields)
    if type(value) ~= "table" or count(value) ~= #fields then return false end
    for _, k in ipairs(fields) do if value[k] == nil then return false end end
    return true
end
local task_actions = {PUBLISH_TASK = true, ACCEPT_TASK = true, REFUSE_TASK = true,
    WITHDRAW_TASK = true, ADJUDICATE_TASK = true, SETTLE_TASK = true}
local function payload_valid(p)
    if type(p) ~= "table" then return false end
    if task_actions[p.action] then return exact(p, {"action", "task_id"}) and p.task_id == TASK end
    if p.action == "WATCH" then return exact(p, {"action", "target"}) and p.target == TARGET end
    if p.action == "SUBMIT_OBSERVATION" then
        return exact(p, {"action", "task_id", "observation_event_id", "recipient", "description"})
            and p.task_id == TASK and event_id(p.observation_event_id) and p.recipient == NPC and text(p.description)
    end
    if p.action == "WRITE_OWN_PAPER" then
        return exact(p, {"action", "paper_id", "source_event_id", "text"})
            and id(p.paper_id) and event_id(p.source_event_id) and text(p.text)
    end
    if p.action == "SHARE_SOURCE" then
        if not exact(p, {"action", "source_event_id", "recipient_seat_ids", "record_kind", "text"})
            or not event_id(p.source_event_id) or not text(p.text)
            or (p.record_kind ~= "RAW_OBSERVATION" and p.record_kind ~= "PLAYER_CLAIM" and p.record_kind ~= "PAPER_TEXT")
            or type(p.recipient_seat_ids) ~= "table" or #p.recipient_seat_ids < 1 or #p.recipient_seat_ids > 6
            or count(p.recipient_seat_ids) ~= #p.recipient_seat_ids then return false end
        local seen = {}
        for _, v in ipairs(p.recipient_seat_ids) do
            if not id(v) or seen[v] then return false end
            seen[v] = true
        end
        return true
    end
    return false
end
local function source(s, source_id, seat, kind)
    if not source_id then return nil end
    if s.validating and not s.events[source_id] then
        s.events[source_id] = host.state.get({"events", source_id})
    end
    local e = s.events[source_id]
    if not e or not e.audience[seat] or (kind and not e.record[kind]) then return nil end
    if s.validating then
        local start = e.execution_start_event_id
        if not s.events[start] then s.events[start] = host.state.get({"events", start}) end
        if not s.execution_bindings[start] then
            s.execution_bindings[start] = host.state.get({"execution_bindings", start})
        end
    end
    local first = s.events[e.execution_start_event_id]
    local binding = s.execution_bindings[e.execution_start_event_id]
    if not first or first.sequence > e.sequence or first.execution_start_event_id ~= e.execution_start_event_id
        or not binding then return nil end
    if binding.callback ~= "on_session_end" and not s.ledger.opening_seats[binding.opening_seat_id] then return nil end
    if binding.payload_sha256 ~= "sha256:" .. string.sha256(binding.payload_json) then return nil end
    local d = e.record.OBSERVATION or e.record.REPORT_DELIVERED or e.record.NPC_ADJUDICATION
        or e.record.PAPER_TRANSFER or e.record.PAPER_WRITTEN or e.record.SOURCE_SHARED or e.record.TASK_PARTICIPATION
    local owner = d and (d.inspection_owner_seat_id or d.opening_seat_id or d.holder_seat_id or d.sender_seat_id)
    if owner and binding.opening_seat_id ~= owner then return nil end
    return e
end
local function receipt_valid(s, seat, receipt_id)
    local r = s.ledger.receipts[receipt_id]
    if not r or r.run_id ~= s.run_id or r.legitimate_loop_id ~= s.legitimate_loop_id
        or r.task_definition_revision ~= s.task_definition_revision or r.opening_seat_id ~= seat
        or r.recipient_seat_id ~= seat then return false end
    local paper = s.ledger.papers[r.paper_id]
    local e = source(s, r.transfer_event_id, seat, "PAPER_TRANSFER")
    if not paper or paper.holder_seat_id ~= seat or not e then return false end
    local d = e.record.PAPER_TRANSFER
    if d.opening_seat_id ~= seat or d.recipient_seat_id ~= seat or d.paper_id ~= r.paper_id then return false end
    local evidence = {}
    for k in pairs(r.source_event_ids) do
        local prior = source(s, k, NPC)
        if not prior or prior.sequence >= e.sequence then return false end
        for kind, detail in pairs(prior.record) do
            if kind ~= "OBSERVATION" and kind ~= "REPORT_DELIVERED" and kind ~= "NPC_ADJUDICATION" then return false end
            evidence[kind] = {id = k, event = prior, detail = detail}
        end
    end
    local watch, claim, judgment = evidence.OBSERVATION, evidence.REPORT_DELIVERED, evidence.NPC_ADJUDICATION
    if count(r.source_event_ids) ~= 3 or not watch or not claim or not judgment then return false end
    return watch.event.audience[seat] and watch.detail.inspection_owner_seat_id == seat
        and claim.detail.opening_seat_id == seat and claim.detail.observation_event_id == watch.id
        and claim.detail.recipient == NPC and claim.detail.description == watch.detail.text
        and judgment.detail.opening_seat_id == seat and judgment.detail.status == "ACCEPTED"
        and judgment.detail.evidence_event_ids[watch.id] and judgment.detail.evidence_event_ids[claim.id]
        and count(judgment.detail.evidence_event_ids) == 2
        and watch.event.sequence < claim.event.sequence and claim.event.sequence < judgment.event.sequence
end
local function roster_valid(s)
    local n = count(s.ledger.opening_seats)
    if n < 2 or n > 6 or count(s.ledger.seats) ~= n or count(s.ledger.papers) ~= n then return false end
    for seat, binding in pairs(s.ledger.opening_seats) do
        if not id(seat) or not id(binding.authorized_character_id) or not id(binding.controller_principal)
            or not s.ledger.seats[seat] then return false end
    end
    local consumed = 0
    for seat, row in pairs(s.ledger.seats) do
        if row.settlement_receipt_id and not receipt_valid(s, seat, row.settlement_receipt_id) then return false end
        if row.settlement_receipt_id then consumed = consumed + 1 end
        for _, note in ipairs(row.private_notes) do
            if note.author_seat_id ~= seat then return false end
            for source_id in pairs(note.source_event_ids) do if not source(s, source_id, seat) then return false end end
        end
    end
    if count(s.ledger.receipts) ~= consumed then return false end
    for paper_id, paper in pairs(s.ledger.papers) do
        if paper.holder_seat_id then
            local row = s.ledger.seats[paper.holder_seat_id]
            local r = row and s.ledger.receipts[row.settlement_receipt_id]
            if not r or r.paper_id ~= paper_id then return false end
        end
        if not s.validating and paper.write_event_id then
            local written = source(s, paper.write_event_id, paper.holder_seat_id, "PAPER_WRITTEN")
            if not written or written.record.PAPER_WRITTEN.paper_id ~= paper_id
                or written.record.PAPER_WRITTEN.holder_seat_id ~= paper.holder_seat_id then return false end
        end
    end
    return true
end
local function inspection(s, seat)
    local row = s.ledger.seats[seat]
    local e = source(s, row.own_inspection_event_id, seat, "OBSERVATION")
    local accepted = source(s, row.accepted_event_id, seat, "TASK_PARTICIPATION")
    return e and accepted and row.participation == "ACCEPTED" and e.audience[NPC]
        and e.record.OBSERVATION.inspection_owner_seat_id == seat
        and accepted.record.TASK_PARTICIPATION.opening_seat_id == seat
        and accepted.record.TASK_PARTICIPATION.participation == "ACCEPTED" and e.sequence > accepted.sequence and e or nil
end
local function report(s, seat)
    local row = s.ledger.seats[seat]
    local watch = inspection(s, seat)
    local e = source(s, row.submitted_claim_event_id, NPC, "REPORT_DELIVERED")
    local d = e and e.record.REPORT_DELIVERED
    return watch and d and e.audience[seat] and e.sequence > watch.sequence and d.opening_seat_id == seat
        and d.recipient == NPC and d.observation_event_id == row.own_inspection_event_id
        and d.description == watch.record.OBSERVATION.text and e or nil
end
local function precondition(s, command)
    if not exact(command, {"type", "seat_id", "correlation_id", "payload"})
        or command.type ~= "task-prefix" or not id(command.seat_id) or not id(command.correlation_id)
        or not payload_valid(command.payload) then return false end
    if not roster_valid(s) or not s.ledger.opening_seats[command.seat_id]
        or s.phase ~= "C01_TASK_PREFIX" or s.component_status ~= "ACTIVE" then return false end
    local p, seat = command.payload, command.seat_id
    local row = s.ledger.seats[seat]
    if p.action == "WATCH" then return s.tick < 2 end
    if p.action == "SUBMIT_OBSERVATION" then
        local e = inspection(s, seat)
        return e and p.observation_event_id == row.own_inspection_event_id and p.description == e.record.OBSERVATION.text
            and row.access_status == "ACCESSIBLE" and s.ledger.npc.location == row.location or false
    end
    if p.action == "SETTLE_TASK" then
        if row.settlement_receipt_id then return receipt_valid(s, seat, row.settlement_receipt_id) end
        local e = source(s, row.issuer_adjudication_event_id, NPC, "NPC_ADJUDICATION")
        if not s.task_offered or row.participation ~= "ACCEPTED" or row.access_status ~= "ACCESSIBLE"
            or s.ledger.npc.location ~= row.location or not e
            or e.record.NPC_ADJUDICATION.opening_seat_id ~= seat or e.record.NPC_ADJUDICATION.status ~= "ACCEPTED"
            or not report(s, seat) then return false end
        for _, paper in pairs(s.ledger.papers) do if not paper.holder_seat_id then return true end end
        return false
    end
    if p.action == "WRITE_OWN_PAPER" then
        local r = s.ledger.receipts[row.settlement_receipt_id]
        local paper = s.ledger.papers[p.paper_id]
        return r and r.paper_id == p.paper_id and paper and paper.holder_seat_id == seat
            and source(s, p.source_event_id, seat) ~= nil or false
    end
    if p.action == "SHARE_SOURCE" then
        local e = source(s, p.source_event_id, seat)
        if not e then return false end
        for _, recipient in ipairs(p.recipient_seat_ids) do if not s.ledger.opening_seats[recipient] then return false end end
        if p.record_kind == "RAW_OBSERVATION" then
            local d = e.record.OBSERVATION or e.record.AMBIENT_WAVE
            return d and d.text == p.text or false
        end
        if p.record_kind == "PAPER_TEXT" then
            local d = e.record.PAPER_WRITTEN
            return d and d.holder_seat_id == seat and d.text == p.text or false
        end
    end
    return true
end
function M.validate_command(command)
    if not exact(command, {"type", "seat_id", "correlation_id", "payload"})
        or not payload_valid(command.payload) then return false end
    -- Read only the current roster and evidence needed by this validation.
    -- The execution phase rechecks the complete authoritative snapshot.
    local s = {validating = true, ledger = host.state.get({"ledger"}), events = {}, execution_bindings = {}}
    for _, field in ipairs({"run_id", "legitimate_loop_id", "task_definition_revision", "phase", "component_status", "tick", "task_offered"}) do
        s[field] = host.state.get({field})
    end
    return precondition(s, command) == true
end

local function public_receipt(s, receipt_id)
    local r = s.ledger.receipts[receipt_id]
    return {receipt_id = receipt_id, transfer_event_id = r.transfer_event_id, opening_seat_id = r.opening_seat_id,
        paper_id = r.paper_id, item_id = ITEM, quantity = 1, issuer = NPC, recipient_seat_id = r.recipient_seat_id,
        statement = "NPC_ACCEPTED_AND_TRANSFERRED"}
end
local function all_audience(s)
    local out = keys(s.ledger.seats)
    out[#out + 1] = NPC
    return out
end
local function emitter(s, command)
    local first, event_ids = nil, array()
    local binding
    if command then
        local json, digest = M.encode_payload(command.payload)
        binding = {opening_seat_id = command.seat_id, correlation_id = command.correlation_id,
            payload_json = json, payload_sha256 = digest}
    else binding = template("lifecycle_binding") end
    local function emit(kind, actor, audience, sources, detail, compact)
        local e = template("event")
        e.schema_version, e.run_id, e.legitimate_loop_id = s.schema_version, s.run_id, s.legitimate_loop_id
        e.kind, e.tick, e.audience, e.source_event_ids, e.data = kind, s.tick, audience, sources, detail
        if actor then e.actor_seat_id = actor end
        if first then e.execution_start_event_id = first end
        local actual_id = host.event.emit("task_action", e)
        assert(event_id(actual_id) and not s.events[actual_id], "INVALID_SOURCE")
        if not first then first = actual_id; s.execution_bindings[first] = binding end
        s.events[actual_id] = {sequence = count(s.events), tick = s.tick, audience = membership(audience),
            execution_start_event_id = first, record = {[kind] = compact}}
        event_ids[#event_ids + 1] = actual_id
        return actual_id
    end
    return emit, event_ids
end

function M.execute_command(command)
    local s = state()
    assert(precondition(s, command), "COMMAND_VALIDATION_FAILED")
    local p, seat = command.payload, command.seat_id
    local row = s.ledger.seats[seat]
    local result = template("result")
    result.kind, result.action, result.status, result.reason = "ACTION_RESULT", p.action, "ACCEPTED", "NONE"
    result.tick, result.tick_delta, result.event_ids = s.tick, 0, array()
    if p.action == "SETTLE_TASK" and row.settlement_receipt_id then
        result.status, result.settlement_receipt = "SETTLED", public_receipt(s, row.settlement_receipt_id)
        return result
    end
    local emit, event_ids = emitter(s, command)
    local local_audience = {seat, NPC}
    if p.action == "PUBLISH_TASK" then
        s.task_offered = true
        emit("TASK_OFFERED", seat, all_audience(s), array(), {task_id = TASK, issuer = NPC, target = TARGET, terms = TERMS}, {})
    elseif p.action == "ACCEPT_TASK" or p.action == "REFUSE_TASK" or p.action == "WITHDRAW_TASK" then
        local participation = p.action == "ACCEPT_TASK" and "ACCEPTED" or p.action == "REFUSE_TASK" and "DECLINED" or "WITHDRAWN"
        local e = emit("TASK_PARTICIPATION", seat, local_audience, array(),
            {task_id = TASK, opening_seat_id = seat, participation = participation}, {opening_seat_id = seat, participation = participation})
        row.participation = participation
        if p.action == "ACCEPT_TASK" then if not row.accepted_event_id then row.accepted_event_id = e end
        else
            row.closure_reason = p.action == "REFUSE_TASK" and "VOLUNTARY_REFUSAL" or "VOLUNTARY_WITHDRAWAL"
            row.actual_fulfillment_internal = false
        end
    elseif p.action == "WATCH" then
        s.tick, result.tick_delta = s.tick + 1, 1
        if s.tick == 2 and #s.fired_waves == 0 then
            s.fired_waves[#s.fired_waves + 1], s.pressure = "echo_arrival", s.pressure + 1
            emit("AMBIENT_WAVE", nil, all_audience(s), array(),
                {wave_id = "echo_arrival", at_tick = 2, pressure_delta = 1, text = "候车厅里的风声明显增强。"},
                {wave_id = "echo_arrival", text = "候车厅里的风声明显增强。"})
        end
        local audience = {seat}
        if s.ledger.npc.location == row.location and row.access_status == "ACCESSIBLE" then audience[#audience + 1] = NPC end
        local e = emit("OBSERVATION", seat, audience, array(),
            {target = TARGET, inspection_owner_seat_id = seat, phenomenon = "DISPLAY_RETURN", text = TEXT},
            {inspection_owner_seat_id = seat, text = TEXT})
        if row.participation == "ACCEPTED" and row.accepted_event_id and #audience == 2 then row.own_inspection_event_id = e end
    elseif p.action == "SUBMIT_OBSERVATION" then
        row.submitted_claim_event_id = emit("REPORT_DELIVERED", seat, local_audience, {p.observation_event_id},
            {task_id = TASK, opening_seat_id = seat, observation_event_id = p.observation_event_id, recipient = NPC, description = p.description},
            {opening_seat_id = seat, observation_event_id = p.observation_event_id, recipient = NPC, description = p.description})
        row.actual_fulfillment_internal = report(s, seat) ~= nil
    elseif p.action == "ADJUDICATE_TASK" then
        local evidence, reason, status = array(), "MISSING_PERSONAL_INSPECTION", "NEEDS_EVIDENCE"
        local own = inspection(s, seat)
        if own then
            evidence[#evidence + 1] = row.own_inspection_event_id
            reason = "MISSING_SUBMISSION"
            if report(s, seat) and row.access_status == "ACCESSIBLE" and s.ledger.npc.location == row.location then
                evidence[#evidence + 1] = row.submitted_claim_event_id
                reason, status = "MATCHING_DELIVERED_OBSERVATION", "ACCEPTED"
            end
        elseif row.own_inspection_event_id then reason = "MISSING_SHARED_OBSERVATION" end
        row.issuer_adjudication_event_id = emit("NPC_ADJUDICATION", seat, local_audience, evidence,
            {task_id = TASK, opening_seat_id = seat, status = status, reason = reason, evidence_event_ids = evidence},
            {opening_seat_id = seat, status = status, reason = reason, evidence_event_ids = membership(evidence)})
        if status == "NEEDS_EVIDENCE" then result.status, result.reason = status, reason end
    elseif p.action == "SETTLE_TASK" then
        local paper_id
        for _, k in ipairs(keys(s.ledger.papers)) do if not s.ledger.papers[k].holder_seat_id then paper_id = k; break end end
        assert(paper_id, "NO_STOCK")
        local sources = {row.own_inspection_event_id, row.submitted_claim_event_id, row.issuer_adjudication_event_id}
        local e = emit("PAPER_TRANSFER", seat, local_audience, sources,
            {task_id = TASK, opening_seat_id = seat, paper_id = paper_id, item_id = ITEM, quantity = 1, recipient_seat_id = seat, issuer = NPC},
            {opening_seat_id = seat, paper_id = paper_id, recipient_seat_id = seat})
        local receipt_id = "receipt-" .. string.sub(e, 5)
        s.ledger.receipts[receipt_id] = {transfer_event_id = e, source_event_ids = membership(sources), run_id = s.run_id,
            legitimate_loop_id = s.legitimate_loop_id, task_definition_revision = s.task_definition_revision,
            opening_seat_id = seat, paper_id = paper_id, recipient_seat_id = seat}
        s.ledger.papers[paper_id].holder_seat_id, row.settlement_receipt_id = seat, receipt_id
        result.status, result.settlement_receipt = "SETTLED", public_receipt(s, receipt_id)
    elseif p.action == "WRITE_OWN_PAPER" then
        local detail = {paper_id = p.paper_id, holder_seat_id = seat, source_event_id = p.source_event_id, text = p.text}
        s.ledger.papers[p.paper_id].write_event_id = emit("PAPER_WRITTEN", seat, {seat}, {p.source_event_id}, detail, detail)
    elseif p.action == "SHARE_SOURCE" then
        local audience, seen = {seat}, {[seat] = true}
        for _, recipient in ipairs(p.recipient_seat_ids) do
            if not seen[recipient] then audience[#audience + 1] = recipient; seen[recipient] = true end
        end
        emit("SOURCE_SHARED", seat, audience, {p.source_event_id},
            {sender_seat_id = seat, source_event_id = p.source_event_id, recipient_seat_ids = p.recipient_seat_ids,
                record_kind = p.record_kind, text = p.text},
            {sender_seat_id = seat, source_event_id = p.source_event_id, recipient_seat_ids = membership(p.recipient_seat_ids),
                recipient_order_json = encode_array(p.recipient_seat_ids), record_kind = p.record_kind, text = p.text})
    end
    result.tick, result.event_ids = s.tick, event_ids
    put(s)
    return result
end

local function lifecycle(callback, status, reason)
    return {kind = "LIFECYCLE_RESULT", callback = callback, schema_version = 1, status = status, reason = reason or "NONE"}
end
local function empty(input) return type(input) == "table" and count(input) == 0 end
function M.on_session_create(input)
    assert(empty(input) and roster_valid(state()), "INVALID_SEED")
    return lifecycle("on_session_create", "READY")
end
function M.on_session_start(input)
    assert(empty(input) and roster_valid(state()), "INVALID_SEED")
    return lifecycle("on_session_start", "READY")
end
function M.create_checkpoint(input)
    assert(input == nil or empty(input), "INVALID_CHECKPOINT_INPUT")
    local s = state()
    assert(roster_valid(s), "INVALID_CHECKPOINT")
    return s
end
local function restore_input(input)
    local s = state()
    local function equal(a, b)
        if type(a) ~= type(b) then return false end
        if type(a) ~= "table" then return a == b end
        if count(a) ~= count(b) then return false end
        for k, v in pairs(a) do if not equal(v, b[k]) then return false end end
        return true
    end
    assert(type(input) == "table" and input.representation == "INDEXED_STATE_V1" and roster_valid(s)
        and equal(input, s), "INVALID_CHECKPOINT")
end
function M.restore_checkpoint(input)
    restore_input(input)
    return lifecycle("restore_checkpoint", "RESTORED")
end
function M.on_session_restore(input)
    if not empty(input) then restore_input(input) end
    assert(roster_valid(state()), "INVALID_CHECKPOINT")
    return lifecycle("on_session_restore", "RESTORED")
end
function M.resume_continuation(input)
    assert(empty(input), "INVALID_INPUT")
    return lifecycle("resume_continuation", "UNSUPPORTED", "CONTINUATION_NOT_SUPPORTED")
end
function M.on_safe_migration_boundary(input)
    assert(empty(input), "INVALID_INPUT")
    return lifecycle("on_safe_migration_boundary", "PAUSED")
end
function M.cleanup(input)
    assert(empty(input), "INVALID_INPUT")
    return lifecycle("cleanup", "CLEANED")
end
function M.on_session_end(input)
    assert(empty(input), "INVALID_INPUT")
    local s = state()
    assert(roster_valid(s), "INVALID_CHECKPOINT")
    if s.component_status ~= "PAUSED" then
        local emit = emitter(s, nil)
        local reason = s.tick == 2 and "PREFIX_BOUNDARY" or "HOST_PAUSE"
        emit("COMPONENT_PAUSED", nil, keys(s.ledger.seats), array(), {reason = reason}, {reason = reason})
        s.component_status = "PAUSED"
        put(s)
    end
    return lifecycle("on_session_end", "PAUSED")
end
local function trusted_view(input, s)
    assert(exact(input, {"seat_id"}) and s.ledger.opening_seats[input.seat_id] and roster_valid(s), "UNAUTHORIZED_SEAT")
    return input.seat_id, s.ledger.seats[input.seat_id]
end
function M.project_view(input)
    local s = state()
    local seat, row = trusted_view(input, s)
    local v = template("view")
    v.schema_version, v.seat_id, v.location, v.strain, v.component_status = 1, seat, row.location, row.strain, s.component_status
    if s.task_offered then v.published_task = {task_id = TASK, issuer = NPC, target = TARGET, terms = TERMS} end
    v.own_task = template("own_task")
    v.own_task.participation, v.own_task.npc_response, v.own_task.visible_reason = row.participation, "NONE", "NONE"
    v.own_task.settlement_status, v.own_task.access_status = row.settlement_receipt_id and "SETTLED" or "LOCAL_UNSETTLED", row.access_status
    if row.settlement_receipt_id then v.own_task.settlement_receipt = public_receipt(s, row.settlement_receipt_id) end
    local judgment = source(s, row.issuer_adjudication_event_id, seat, "NPC_ADJUDICATION")
    if judgment then
        v.own_task.npc_response = judgment.record.NPC_ADJUDICATION.status
        v.own_task.visible_reason = judgment.record.NPC_ADJUDICATION.reason
    end
    v.observations, v.own_notes, v.received_shares = array(), array(), array()
    for _, note in ipairs(row.private_notes) do
        local sources = keys(note.source_event_ids)
        if #sources == 0 then sources = array() end
        v.own_notes[#v.own_notes + 1] = {note_id = note.note_id, author_seat_id = seat,
            source_event_ids = sources, kind = "PLAYER_CLAIM", text = note.text}
    end
    local ordered = {}
    for k, e in pairs(s.events) do ordered[e.sequence + 1] = k end
    for _, k in ipairs(ordered) do
        local e = s.events[k]
        if e.audience[seat] then
            local d = e.record.OBSERVATION or e.record.AMBIENT_WAVE or e.record.SOURCE_SHARED
            if d and (not e.record.SOURCE_SHARED or d.recipient_seat_ids[seat]) then
                local observation = template("observation")
                observation.source_event_id, observation.observer_seat_id, observation.text = k, seat, d.text
                observation.kind = e.record.OBSERVATION and "DISPLAY_RETURN" or e.record.AMBIENT_WAVE and "AMBIENT_WIND" or "SHARED_RECORD"
                if e.record.OBSERVATION then observation.inspection_owner_seat_id = d.inspection_owner_seat_id end
                v.observations[#v.observations + 1] = observation
            end
            local share = e.record.SOURCE_SHARED
            if share and share.recipient_seat_ids[seat] then
                v.received_shares[#v.received_shares + 1] = {share_event_id = k, source_event_id = share.source_event_id,
                    sender_seat_id = share.sender_seat_id, record_kind = share.record_kind, text = share.text}
            end
        end
    end
    if row.settlement_receipt_id then
        local r = s.ledger.receipts[row.settlement_receipt_id]
        local sheet = s.ledger.papers[r.paper_id]
        if sheet.holder_seat_id == seat then
            local paper = template("paper")
            paper.paper_id, paper.item_id, paper.holder_seat_id = r.paper_id, ITEM, seat
            local written = s.events[sheet.write_event_id]
            if written then
                local d = written.record.PAPER_WRITTEN
                paper.write_event_id, paper.source_event_id, paper.text = sheet.write_event_id, d.source_event_id, d.text
            end
            v.own_paper = paper
        end
    end
    return v
end
function M.list_legal_actions(input)
    local s = state()
    local seat, row = trusted_view(input, s)
    local actions = array()
    local candidates = {{action = "PUBLISH_TASK", task_id = TASK}, {action = "WATCH", target = TARGET}}
    if s.task_offered then
        candidates = {{action = "ACCEPT_TASK", task_id = TASK}, {action = "REFUSE_TASK", task_id = TASK},
            {action = "WITHDRAW_TASK", task_id = TASK}, {action = "ADJUDICATE_TASK", task_id = TASK},
            {action = "SETTLE_TASK", task_id = TASK}, {action = "WATCH", target = TARGET}}
        if inspection(s, seat) then candidates[#candidates + 1] = {action = "SUBMIT_OBSERVATION", task_id = TASK,
            observation_event_id = row.own_inspection_event_id, recipient = NPC, description = TEXT} end
    end
    for _, p in ipairs(candidates) do
        if precondition(s, {type = "task-prefix", seat_id = seat, correlation_id = "legal-actions", payload = p}) then actions[#actions + 1] = p end
    end
    return {kind = "LEGAL_ACTIONS", actions = actions}
end
return M
