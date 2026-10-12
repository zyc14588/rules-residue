"""Self-contained pre-Lua contract checks.

These tests validate schema samples and snapshot/precondition relations. They do
not execute game Lua, mint authoritative events or certify a played task. Native
parser/compiler/HostCase admission is a separate required source-bound check.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tomllib
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1] / "platform-validation/task-prefix"
CALLBACKS = [
    "on_session_create", "on_session_restore", "on_session_start",
    "validate_command", "execute_command", "list_legal_actions", "project_view",
    "create_checkpoint", "restore_checkpoint", "resume_continuation",
    "on_safe_migration_boundary", "on_session_end", "cleanup",
]


def read_json(path: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON member: " + key)
            result[key] = value
        return result
    return json.loads((ROOT / path).read_text(encoding="utf-8"), object_pairs_hook=pairs)


def resolve_sample(sample):
    if "value" in sample:
        return copy.deepcopy(sample["value"])
    value = read_json("fixtures/" + sample["fixture"])
    for segment in sample["pointer"].split("/")[1:]:
        key = segment.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return copy.deepcopy(value)


def vector_value(vector):
    value = resolve_sample(vector["sample"])
    for mutation in vector["mutations"]:
        parent = value
        for key in mutation["path"][:-1]:
            parent = parent[key]
        key = mutation["path"][-1]
        if mutation["op"] == "set":
            parent[key] = copy.deepcopy(mutation["value"])
        elif mutation["op"] == "delete":
            del parent[key]
        else:
            raise ValueError("unknown vector mutation")
    return value


def validators():
    return {name: Draft202012Validator(read_json("schemas/" + name + ".schema.json"))
            for name in ("command", "state", "result", "view", "event")}


def canonical_payload_json(payload):
    """Encode the complete original request; array order and strings are exact."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def command_payload_from_event(primary, action):
    """Reconstruct the request fields independently from the typed response."""
    data = primary["data"]
    payload = {"action": action}
    if action in ("PUBLISH_TASK", "ACCEPT_TASK", "REFUSE_TASK", "WITHDRAW_TASK", "ADJUDICATE_TASK", "SETTLE_TASK"):
        payload["task_id"] = data["task_id"]
    elif action == "WATCH":
        payload["target"] = data["target"]
    elif action == "SUBMIT_OBSERVATION":
        payload.update({key: data[key] for key in ("task_id", "observation_event_id", "recipient", "description")})
    elif action == "WRITE_OWN_PAPER":
        payload.update({key: data[key] for key in ("paper_id", "source_event_id", "text")})
    elif action == "SHARE_SOURCE":
        payload.update({key: data[key] for key in ("source_event_id", "recipient_seat_ids", "record_kind", "text")})
    elif action == "HOST_PAUSE":
        payload = {}
    return payload


def expand_indexed_state(state):
    """Reconstruct logical fixture data; this neither emits nor executes events."""
    if state.get("representation") != "INDEXED_STATE_V1":
        return copy.deepcopy(state)
    rules = read_json("contract.json")["game_contract"]
    ledger = state["ledger"]
    history = []
    for event_id, record in sorted(state["events"].items(), key=lambda pair: pair[1]["sequence"]):
        kind, detail = next(iter(record["record"].items()))
        data = copy.deepcopy(detail)
        if kind == "SOURCE_SHARED":
            encoded = data.pop("recipient_order_json", "")
            try:
                order = json.loads(encoded)
            except (TypeError, ValueError):
                order = []
            data["recipient_seat_ids"] = order if isinstance(order, list) and all(isinstance(x, str) for x in order) else []
        for key in ("evidence_event_ids",):
            if key in data:
                data[key] = list(data[key])
        if kind in ("TASK_OFFERED", "TASK_PARTICIPATION", "REPORT_DELIVERED",
                    "NPC_ADJUDICATION", "PAPER_TRANSFER"):
            data["task_id"] = rules["task_id"]
        if kind == "TASK_OFFERED":
            data.update(issuer=rules["issuer"], target=rules["target"], terms=rules["visible_contract"])
        elif kind == "OBSERVATION":
            data.update(target=rules["target"], phenomenon="DISPLAY_RETURN")
        elif kind == "AMBIENT_WAVE":
            data.update(at_tick=2, pressure_delta=1)
        elif kind == "PAPER_TRANSFER":
            data.update(item_id="TEST_ONLY.tutorial.ordinary_record_sheet", quantity=1, issuer=rules["issuer"])
        if kind == "REPORT_DELIVERED":
            sources = [data["observation_event_id"]]
        elif kind == "NPC_ADJUDICATION":
            sources = data["evidence_event_ids"]
        elif kind == "PAPER_TRANSFER":
            matching = next((row for row in ledger["receipts"].values()
                             if row["transfer_event_id"] == event_id), None)
            sources = [] if matching is None else list(matching["source_event_ids"])
        elif kind in ("PAPER_WRITTEN", "SOURCE_SHARED"):
            sources = [data["source_event_id"]]
        else:
            sources = []
        start = record["execution_start_event_id"]
        binding = state["execution_bindings"].get(start) or {}
        actor = None if kind in ("AMBIENT_WAVE", "COMPONENT_PAUSED") else binding.get("opening_seat_id")
        history.append({"event_id": event_id, "payload": {
            "schema_version": state["schema_version"], "run_id": state["run_id"],
            "legitimate_loop_id": state["legitimate_loop_id"],
            "execution_start_event_id": None if event_id == start else start,
            "kind": kind, "tick": record["tick"], "actor_seat_id": actor,
            "audience": list(record["audience"]), "source_event_ids": sources, "data": data,
        }})
    events = {row["event_id"]: row["payload"] for row in history}
    npc = copy.deepcopy(ledger["npc"])
    npc["witnessed_event_ids"] = [key for key, event in events.items() if npc["id"] in event["audience"]]
    npc["received_report_event_ids"] = [key for key in npc["witnessed_event_ids"]
                                       if events[key]["kind"] == "REPORT_DELIVERED"]
    seats = []
    for seat_id, original in ledger["seats"].items():
        row = {key: copy.deepcopy(value) for key, value in original.items()
               if key not in ("submitted_claim_event_id", "issuer_adjudication_event_id", "settlement_receipt_id")}
        row["opening_seat_id"] = seat_id
        for note in row["private_notes"]:
            note["source_event_ids"] = list(note["source_event_ids"])
        row["observations"] = []
        for key, event in events.items():
            if seat_id not in event["audience"]:
                continue
            data = event["data"]
            if event["kind"] == "OBSERVATION":
                observation = {"kind": "DISPLAY_RETURN", "inspection_owner_seat_id": data["inspection_owner_seat_id"]}
            elif event["kind"] == "AMBIENT_WAVE":
                observation = {"kind": "AMBIENT_WIND", "inspection_owner_seat_id": None}
            elif event["kind"] == "SOURCE_SHARED" and seat_id in data["recipient_seat_ids"]:
                observation = {"kind": "SHARED_RECORD", "inspection_owner_seat_id": None}
            else:
                continue
            row["observations"].append({**observation, "source_event_id": key, "observer_seat_id": seat_id, "text": data["text"]})
        report = events.get(original["submitted_claim_event_id"])
        row["submitted_claim"] = None if report is None else {
            "delivered_event_id": original["submitted_claim_event_id"],
            "observation_event_id": report["data"].get("observation_event_id"),
            "description": report["data"].get("description"),
        }
        judgment = events.get(original["issuer_adjudication_event_id"])
        row["issuer_adjudication"] = {"status": "NONE", "reason": "NONE", "evidence_event_ids": []} if judgment is None else {
            "status": judgment["data"].get("status"), "reason": judgment["data"].get("reason"),
            "evidence_event_ids": judgment["data"].get("evidence_event_ids", []),
        }
        receipt_id = original["settlement_receipt_id"]
        canonical = ledger["receipts"].get(receipt_id)
        receipt = None if canonical is None else {
            **copy.deepcopy(canonical), "receipt_id": receipt_id, "source_event_ids": list(canonical["source_event_ids"]),
            "item_id": "TEST_ONLY.tutorial.ordinary_record_sheet", "quantity": 1,
            "issuer": rules["issuer"], "statement": "NPC_ACCEPTED_AND_TRANSFERRED",
        }
        row["entitlement"] = {"run_id": state["run_id"], "legitimate_loop_id": state["legitimate_loop_id"],
                              "task_definition_revision": state["task_definition_revision"],
                              "opening_seat_id": seat_id, "consumed": receipt_id is not None, "settlement_receipt": receipt}
        row["settlement_status"] = "SETTLED" if receipt_id is not None else "LOCAL_UNSETTLED"
        sheet = None if receipt is None else ledger["papers"].get(receipt["paper_id"])
        if sheet is None:
            row["paper"] = None
        else:
            written = events.get(sheet["write_event_id"])
            row["paper"] = {"paper_id": receipt["paper_id"], "item_id": "TEST_ONLY.tutorial.ordinary_record_sheet",
                            "holder_seat_id": sheet["holder_seat_id"], "write_event_id": sheet["write_event_id"],
                            "text": None if written is None else written["data"].get("text"),
                            "source_event_id": None if written is None else written["data"].get("source_event_id")}
        seats.append(row)
    result = {key: copy.deepcopy(value) for key, value in state.items()
              if key not in ("representation", "ledger", "events", "execution_bindings")}
    result["ledger"] = {"opening_seats": [{"seat_id": key, **value} for key, value in ledger["opening_seats"].items()],
                        "seats": seats, "npc": npc,
                        "paper_stock": sum(sheet["holder_seat_id"] is None for sheet in ledger["papers"].values())}
    result["history"] = history
    actions = {"TASK_OFFERED": "PUBLISH_TASK", "OBSERVATION": "WATCH", "REPORT_DELIVERED": "SUBMIT_OBSERVATION",
               "NPC_ADJUDICATION": "ADJUDICATE_TASK", "PAPER_TRANSFER": "SETTLE_TASK", "PAPER_WRITTEN": "WRITE_OWN_PAPER",
               "SOURCE_SHARED": "SHARE_SOURCE", "COMPONENT_PAUSED": "HOST_PAUSE"}
    result["action_receipts"] = []
    for start, binding in state["execution_bindings"].items():
        binding = {"callback": "on_session_end", "correlation_id": None, "opening_seat_id": None,
                   "payload_json": "{}", "payload_sha256": "sha256:" + hashlib.sha256(b"{}").hexdigest()} if binding is None else {
                       "callback": "command", **copy.deepcopy(binding)}
        related = [entry for entry in history if entry["event_id"] == start
                   or entry["payload"]["execution_start_event_id"] == start]
        principal = next((entry["payload"] for entry in related if entry["payload"]["kind"] != "AMBIENT_WAVE"), None)
        action = None if principal is None else actions.get(principal["kind"])
        if principal is not None and principal["kind"] == "TASK_PARTICIPATION":
            action = {"ACCEPTED": "ACCEPT_TASK", "DECLINED": "REFUSE_TASK", "WITHDRAWN": "WITHDRAW_TASK"}.get(principal["data"]["participation"])
        result["action_receipts"].append({"execution_start_event_id": start, **copy.deepcopy(binding), "action": action,
                                          "event_ids": [entry["event_id"] for entry in related], "tick_delta": int(action == "WATCH"),
                                          "result_status": "SETTLED" if action == "SETTLE_TASK" else "PAUSED" if action == "HOST_PAUSE" else "ACCEPTED"})
    return result


def state_relation_issues(state):
    """Check fixture joins, not event authenticity or executed game effects."""
    issues = []
    if state.get("representation") == "INDEXED_STATE_V1":
        sequences = [entry["sequence"] for entry in state["events"].values()]
        if sorted(sequences) != list(range(len(sequences))):
            issues.append("source sequence is not contiguous and unique")
        starts = {row["execution_start_event_id"] for row in state["events"].values()}
        if starts != set(state["execution_bindings"]):
            issues.append("execution binding/event group bijection")
        for start in starts:
            members = sorted((row["sequence"], event_id) for event_id, row in state["events"].items()
                             if row["execution_start_event_id"] == start)
            if not members or members[0][1] != start:
                issues.append("execution key is not its first actual returned event ID")
            if members and [sequence for sequence, _ in members] != list(
                    range(members[0][0], members[0][0] + len(members))):
                issues.append("same execution events must remain contiguous")
        for row in state["events"].values():
            detail = row["record"].get("SOURCE_SHARED")
            if detail is None:
                continue
            try:
                encoded = detail["recipient_order_json"]
                order = json.loads(encoded)
                if (not isinstance(order, list) or not all(isinstance(x, str) for x in order)
                        or len(order) != len(set(order)) or set(order) != set(detail["recipient_seat_ids"])
                        or canonical_payload_json(order) != encoded):
                    issues.append("ordered recipients differ from unique membership")
            except (KeyError, TypeError, ValueError):
                issues.append("ordered recipient encoding is missing or malformed")
        ledger = state["ledger"]
        receipt_references = [row["settlement_receipt_id"] for row in ledger["seats"].values()
                              if row["settlement_receipt_id"] is not None]
        if sorted(receipt_references) != sorted(ledger["receipts"]):
            issues.append("canonical receipt/reference bijection")
        for row in ledger["seats"].values():
            for field, kind in (("submitted_claim_event_id", "REPORT_DELIVERED"),
                                ("issuer_adjudication_event_id", "NPC_ADJUDICATION")):
                source = state["events"].get(row[field])
                if row[field] is not None and (source is None or kind not in source["record"]):
                    issues.append("wrong typed canonical source reference")
        for paper_id, sheet in ledger["papers"].items():
            if sheet["holder_seat_id"] is not None and not any(
                    receipt["paper_id"] == paper_id and receipt["recipient_seat_id"] == sheet["holder_seat_id"]
                    for receipt in ledger["receipts"].values()):
                issues.append("physical holder lacks matching canonical receipt")
            source = state["events"].get(sheet["write_event_id"])
            if sheet["write_event_id"] is not None and (source is None or "PAPER_WRITTEN" not in source["record"]):
                issues.append("paper write references wrong canonical event")
        state = expand_indexed_state(state)
    ledger = state["ledger"]
    bindings = ledger["opening_seats"]
    seats = ledger["seats"]
    seat_ids = [row["seat_id"] for row in bindings]
    entry_ids = [row["opening_seat_id"] for row in seats]
    if len(set(seat_ids)) != len(seat_ids) or sorted(seat_ids) != sorted(entry_ids):
        issues.append("immutable opening-seat/ledger bijection")
    history = state["history"]
    ids = [row["event_id"] for row in history]
    if len(set(ids)) != len(ids):
        issues.append("duplicate event id")
    events = {row["event_id"]: row["payload"] for row in history}
    indices = {row["event_id"]: i for i, row in enumerate(history)}
    npc = ledger["npc"]
    witnessed = set(npc["witnessed_event_ids"])
    received = set(npc["received_report_event_ids"])
    for event_id, payload in events.items():
        if (payload["run_id"], payload["legitimate_loop_id"]) != (
                state["run_id"], state["legitimate_loop_id"]):
            issues.append("event belongs to different run/loop")
        if not set(payload["audience"]) <= set(seat_ids + [npc["id"]]):
            issues.append("unknown event audience")
        for source in payload["source_event_ids"]:
            if source not in events or indices[source] >= indices[event_id]:
                issues.append("event source absent or future")
        if (npc["id"] in payload["audience"]) != (event_id in witnessed):
            issues.append("NPC witness index differs from actual audience")
        if payload["kind"] == "REPORT_DELIVERED":
            if event_id not in received or payload["data"]["recipient"] != npc["id"]:
                issues.append("report not actually delivered to issuer")
        if payload["kind"] == "SOURCE_SHARED":
            source = events.get(payload["data"]["source_event_id"])
            sender = payload["data"]["sender_seat_id"]
            if source is None or sender not in source["audience"]:
                issues.append("source share sender lacks source access")
            if not set(payload["data"]["recipient_seat_ids"]) <= set(payload["audience"]):
                issues.append("source share not delivered to declared recipient")
    if not witnessed <= set(ids) or not received <= set(ids):
        issues.append("NPC index references nonexistent events")
    held = [row["paper"] for row in seats if row["paper"] is not None]
    if ledger["paper_stock"] + len(held) != len(bindings):
        issues.append("stock/physical holder conservation")
    paper_ids = [paper["paper_id"] for paper in held]
    if len(set(paper_ids)) != len(paper_ids):
        issues.append("duplicate physical paper")
    receipt_ids = []
    for row in seats:
        seat = row["opening_seat_id"]
        entitlement = row["entitlement"]
        expected_key = (state["run_id"], state["legitimate_loop_id"],
                        state["task_definition_revision"], seat)
        if tuple(entitlement[key] for key in (
                "run_id", "legitimate_loop_id", "task_definition_revision", "opening_seat_id")) != expected_key:
            issues.append("entitlement does not bind current run/loop/revision/seat")
        accepted_id = row["accepted_event_id"]
        if accepted_id is not None:
            accepted = events.get(accepted_id)
            if (accepted is None or accepted["kind"] != "TASK_PARTICIPATION"
                    or accepted["data"]["opening_seat_id"] != seat
                    or accepted["data"]["participation"] != "ACCEPTED"):
                issues.append("accepted contract lacks own real participation source")
        inspection_id = row["own_inspection_event_id"]
        inspection = events.get(inspection_id)
        valid_inspection = (inspection is not None and inspection["kind"] == "OBSERVATION"
                            and inspection["actor_seat_id"] == seat
                            and inspection["data"]["inspection_owner_seat_id"] == seat
                            and seat in inspection["audience"] and npc["id"] in inspection["audience"]
                            and inspection_id in witnessed and accepted_id in indices
                            and indices[inspection_id] > indices[accepted_id])
        if inspection_id is not None and not valid_inspection:
            issues.append("personal post-accept co-observation source invalid")
        claim = row["submitted_claim"]
        valid_report = False
        if claim is not None:
            report = events.get(claim["delivered_event_id"])
            valid_report = (valid_inspection and claim["observation_event_id"] == inspection_id
                            and claim["description"] == inspection["data"]["text"]
                            and report is not None and report["kind"] == "REPORT_DELIVERED"
                            and report["actor_seat_id"] == seat
                            and report["data"]["opening_seat_id"] == seat
                            and report["data"]["observation_event_id"] == inspection_id
                            and report["data"]["description"] == claim["description"]
                            and claim["delivered_event_id"] in received)
            if not valid_report:
                issues.append("source-matching own report not delivered")
        if row["actual_fulfillment_internal"] and not (
                row["participation"] == "ACCEPTED" and valid_inspection and valid_report):
            issues.append("hidden fulfillment bit cannot create missing execution facts")
        judgment = row["issuer_adjudication"]
        if not set(judgment["evidence_event_ids"]) <= witnessed:
            issues.append("NPC judgment uses unwitnessed source")
        for observation in row["observations"]:
            source = events.get(observation["source_event_id"])
            if (observation["observer_seat_id"] != seat or source is None
                    or seat not in source["audience"]):
                issues.append("foreign-seat or nonexistent observation")
            if source is not None and observation["kind"] == "SHARED_RECORD" and (
                    source["kind"] != "SOURCE_SHARED"
                    or seat not in source["data"]["recipient_seat_ids"]):
                issues.append("shared material was not explicitly delivered")
        for note in row["private_notes"]:
            if note["author_seat_id"] != seat or any(
                    source not in events or seat not in events[source]["audience"]
                    for source in note["source_event_ids"]):
                issues.append("private note uses another seat or inaccessible source")
        receipt = entitlement["settlement_receipt"]
        paper = row["paper"]
        if entitlement["consumed"] != (receipt is not None and paper is not None):
            issues.append("consumed entitlement/paper/receipt atomic shape")
        if receipt is not None and paper is not None:
            receipt_ids.append(receipt["receipt_id"])
            if tuple(receipt[key] for key in (
                    "run_id", "legitimate_loop_id", "task_definition_revision", "opening_seat_id")) != expected_key:
                issues.append("receipt key mismatch")
            if receipt["recipient_seat_id"] != seat or paper["holder_seat_id"] != seat:
                issues.append("physical paper/receipt recipient mismatch")
            if receipt["paper_id"] != paper["paper_id"]:
                issues.append("receipt refers to another physical sheet")
            transfer = events.get(receipt["transfer_event_id"])
            if (transfer is None or transfer["kind"] != "PAPER_TRANSFER"
                    or transfer["data"]["paper_id"] != paper["paper_id"]
                    or transfer["data"]["recipient_seat_id"] != seat):
                issues.append("immutable receipt lacks transfer source")
            if any(source not in events for source in receipt["source_event_ids"]):
                issues.append("receipt has nonexistent evidence")
            if paper["text"] is not None:
                written = events.get(paper["write_event_id"])
                if (written is None or written["kind"] != "PAPER_WRITTEN"
                        or written["data"]["holder_seat_id"] != seat
                        or written["data"]["paper_id"] != paper["paper_id"]
                        or written["data"]["source_event_id"] != paper["source_event_id"]
                        or written["data"]["text"] != paper["text"]):
                    issues.append("paper text lacks explicit actual-holder write source")
    if len(set(receipt_ids)) != len(receipt_ids):
        issues.append("duplicate settlement receipt")
    waves = [i for i, row in enumerate(history) if row["payload"]["kind"] == "AMBIENT_WAVE"]
    if len(waves) != (1 if state["tick"] == 2 else 0):
        issues.append("tick2 wave must fire exactly once")
    for i, row in enumerate(history):
        payload = row["payload"]
        if payload["kind"] == "OBSERVATION" and payload["tick"] == 2:
            wave_start = None if not waves else history[waves[0]]["event_id"]
            if not waves or waves[0] >= i or wave_start != payload["execution_start_event_id"]:
                issues.append("tick2 pressure wave must precede B observation in same action")
    starts = [row["execution_start_event_id"] for row in state["action_receipts"]]
    if len(set(starts)) != len(starts):
        issues.append("duplicate action receipt")
    for receipt in state["action_receipts"]:
        start = receipt["execution_start_event_id"]
        related = [row["event_id"] for row in history
                   if row["event_id"] == start or row["payload"]["execution_start_event_id"] == start]
        if receipt["event_ids"] != related:
            issues.append("same-action receipt/event binding mismatch")
        action = receipt["action"]
        primary = next((events[key] for key in related if events[key]["kind"] != "AMBIENT_WAVE"), None)
        if primary is None or action is None:
            issues.append("execution lacks typed action response")
            continue
        if related[0] != start or events[start]["execution_start_event_id"] is not None:
            issues.append("first emission requires no not-yet-returned execution ID")
        expected_kinds = [primary["kind"]]
        if action == "WATCH" and primary["tick"] == 2:
            expected_kinds = ["AMBIENT_WAVE", "OBSERVATION"]
        if [events[key]["kind"] for key in related] != expected_kinds:
            issues.append("execution group does not match its single typed action")
        primary_seat = primary["actor_seat_id"]
        if action == "HOST_PAUSE":
            if receipt["callback"] != "on_session_end" or receipt["opening_seat_id"] is not None or receipt["correlation_id"] is not None:
                issues.append("lifecycle provenance differs from available callback input")
        else:
            if receipt["callback"] != "command" or receipt["opening_seat_id"] not in seat_ids or primary_seat != receipt["opening_seat_id"]:
                issues.append("execution lacks trusted current opening seat")
            if any(events[key]["actor_seat_id"] != receipt["opening_seat_id"] for key in related
                   if events[key]["kind"] not in ("AMBIENT_WAVE", "COMPONENT_PAUSED")):
                issues.append("execution actor differs from trusted binding")
        payload = command_payload_from_event(primary, action)
        actual_hash = "sha256:" + hashlib.sha256(canonical_payload_json(payload).encode()).hexdigest()
        if receipt["payload_sha256"] != actual_hash:
            issues.append("same-action request hash differs from typed response")
        # The independent original request survives checkpoint storage. A typed
        # response may not silently drop, sort, or rewrite any legal field.
        def unique_members(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError("duplicate request member")
                result[key] = value
            return result
        try:
            encoded = receipt["payload_json"]
            original = json.loads(encoded, object_pairs_hook=unique_members)
            if canonical_payload_json(original) != encoded:
                issues.append("original request encoding is not canonical")
            if action != "HOST_PAUSE" and not validators()["command"].is_valid(original):
                issues.append("original request violates command schema")
            if original != payload:
                issues.append("same-action original request differs from typed response")
            if "sha256:" + hashlib.sha256(encoded.encode()).hexdigest() != receipt["payload_sha256"]:
                issues.append("original request encoding hash mismatch")
        except (KeyError, TypeError, ValueError):
            issues.append("original request encoding is missing or malformed")
    emitted_starts = {row["event_id"] if row["payload"]["execution_start_event_id"] is None
                      else row["payload"]["execution_start_event_id"] for row in history}
    if set(starts) != emitted_starts:
        issues.append("history must retain same-action request/response bindings")
    return issues


def immutable_transition_issues(before, after):
    """Compare fixture snapshots; no command transaction is being run."""
    issues = []
    for key in ("run_id", "legitimate_loop_id", "task_definition_revision", "native_values"):
        if before[key] != after[key]:
            issues.append("immutable entitlement scope changed")
    if before["ledger"]["opening_seats"] != after["ledger"]["opening_seats"]:
        issues.append("opening seat/controller binding changed")
    if set(before["ledger"]["papers"]) != set(after["ledger"]["papers"]):
        issues.append("physical paper minted or removed")
    for receipt_id, receipt in before["ledger"]["receipts"].items():
        if after["ledger"]["receipts"].get(receipt_id) != receipt:
            issues.append("immutable settlement receipt changed or removed")
    for seat_id, row in before["ledger"]["seats"].items():
        if row["settlement_receipt_id"] is not None and after["ledger"]["seats"].get(seat_id, {}).get("settlement_receipt_id") != row["settlement_receipt_id"]:
            issues.append("consumed opening-seat entitlement reset or replaced")
    for event_id, event in before["events"].items():
        if after["events"].get(event_id) != event:
            issues.append("source history changed or removed")
    for start, binding in before["execution_bindings"].items():
        if after["execution_bindings"].get(start) != binding:
            issues.append("immutable execution binding changed or removed")
    return issues


def projection_relation_issues(view, state, trusted_seat):
    state = expand_indexed_state(state)
    issues = []
    if view["seat_id"] != trusted_seat:
        return ["foreign trusted-seat projection"]
    row = next((row for row in state["ledger"]["seats"]
                if row["opening_seat_id"] == trusted_seat), None)
    if row is None:
        return ["unknown trusted seat"]
    if view["own_notes"] != row["private_notes"] or any(
            note["author_seat_id"] != trusted_seat for note in view["own_notes"]):
        issues.append("other-seat private notes")
    if view["own_paper"] != row["paper"]:
        issues.append("foreign physical paper")
    events = {item["event_id"]: item["payload"] for item in state["history"]}
    for observation in view["observations"]:
        source = events.get(observation["source_event_id"])
        if (observation not in row["observations"] or source is None
                or trusted_seat not in source["audience"]):
            issues.append("observation not in actual caller audience")
    for share in view["received_shares"]:
        source = events.get(share["share_event_id"])
        if (source is None or source["kind"] != "SOURCE_SHARED"
                or trusted_seat not in source["data"]["recipient_seat_ids"]
                or source["data"]["source_event_id"] != share["source_event_id"]):
            issues.append("share not actually delivered to caller")
    if view["own_task"]["participation"] != row["participation"]:
        issues.append("foreign task participation")
    receipt = row["entitlement"]["settlement_receipt"]
    public = view["own_task"]["settlement_receipt"]
    if (receipt is None) != (public is None):
        issues.append("foreign settlement receipt")
    elif public is not None and any(receipt.get(key) != value for key, value in public.items()):
        issues.append("foreign settlement receipt")
    return issues


def declared_precondition_status(state, context, payload, command_validator, contract):
    """Read-only contract predicate. This is not a game action executor."""
    state = expand_indexed_state(state)
    supported = contract["game_contract"]["supported_actions"]
    if payload.get("action") not in supported:
        return "UNSUPPORTED_ACTION"
    if not command_validator.is_valid(payload):
        return "INVALID_PAYLOAD"
    binding = next((row for row in state["ledger"]["opening_seats"]
                    if row["seat_id"] == context["seat"]), None)
    if (binding is None or binding["controller_principal"] != context["principal"]
            or binding["authorized_character_id"] != context["authorized_character_id"]):
        return "UNAUTHORIZED_SEAT"
    if state["phase"] != "C01_TASK_PREFIX" or state["component_status"] != "ACTIVE":
        return "WRONG_PHASE"
    seat = context["seat"]
    row = next(item for item in state["ledger"]["seats"] if item["opening_seat_id"] == seat)
    events = {item["event_id"]: item["payload"] for item in state["history"]}
    action = payload["action"]
    if action == "WATCH":
        return "PREFIX_BOUNDARY" if state["tick"] >= 2 else "ALLOW"
    if action in ("PUBLISH_TASK", "ACCEPT_TASK", "REFUSE_TASK", "WITHDRAW_TASK"):
        return "ALLOW"
    if action == "SUBMIT_OBSERVATION":
        source = events.get(payload["observation_event_id"])
        if source is None:
            return "INVALID_SOURCE"
        indices = {item["event_id"]: index for index, item in enumerate(state["history"])}
        if (source["kind"] != "OBSERVATION" or source["actor_seat_id"] != seat
                or source["data"]["inspection_owner_seat_id"] != seat
                or source["run_id"] != state["run_id"]
                or source["legitimate_loop_id"] != state["legitimate_loop_id"]
                or payload["observation_event_id"] != row["own_inspection_event_id"]
                or row["participation"] != "ACCEPTED" or row["accepted_event_id"] not in indices
                or indices[payload["observation_event_id"]] <= indices[row["accepted_event_id"]]
                or "npc.lin-que" not in source["audience"]
                or source["data"]["text"] != payload["description"]):
            return "NEEDS_EVIDENCE"
        return "ALLOW"
    if action == "ADJUDICATE_TASK":
        return "ALLOW" if row["submitted_claim"] is not None else "NEEDS_EVIDENCE"
    if action == "SETTLE_TASK":
        if row["entitlement"]["consumed"]:
            return "RETURN_IMMUTABLE_RECEIPT"
        # Deliberately do not query actual_fulfillment_internal here: the NPC's
        # finite adjudication authorizes her transfer. The dice mistake branch
        # is outside this prefix and is not executed by these fixtures.
        if row["participation"] != "ACCEPTED" or row["issuer_adjudication"]["status"] not in (
                "ACCEPTED", "ACCEPTED_MISTAKEN"):
            return "NOT_ADJUDICATED"
        return "ALLOW" if state["ledger"]["paper_stock"] >= 1 else "NO_STOCK"
    if action == "WRITE_OWN_PAPER":
        paper = row["paper"]
        if (paper is None or paper["paper_id"] != payload["paper_id"]
                or paper["holder_seat_id"] != seat):
            return "NOT_PAPER_HOLDER"
        source = events.get(payload["source_event_id"])
        return "ALLOW" if source is not None and seat in source["audience"] else "INVALID_SOURCE"
    if action == "SHARE_SOURCE":
        source = events.get(payload["source_event_id"])
        if source is None or seat not in source["audience"]:
            return "INVALID_SOURCE"
        known = {item["seat_id"] for item in state["ledger"]["opening_seats"]}
        if not set(payload["recipient_seat_ids"]) <= known:
            return "INVALID_SOURCE"
        if payload["record_kind"] == "RAW_OBSERVATION" and (
                source["kind"] not in ("OBSERVATION", "AMBIENT_WAVE")
                or payload["text"] != source["data"]["text"]):
            return "INVALID_SOURCE"
        if payload["record_kind"] == "PAPER_TEXT" and (
                source["kind"] != "PAPER_WRITTEN" or source["data"]["holder_seat_id"] != seat
                or payload["text"] != source["data"]["text"]):
            return "INVALID_SOURCE"
        return "ALLOW"
    raise AssertionError("supported action has no contract predicate")


class NativeTaskPrefixContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = read_json("contract.json")
        cls.fixture = read_json("fixtures/task-prefix-cases.json")
        cls.callbacks = read_json("fixtures/native-callback-cases.json")
        cls.validators = validators()

    def test_native_manifest_identity_profile_and_least_capabilities(self):
        manifest = tomllib.loads((ROOT / "manifest.yaml").read_text())
        self.assertEqual(manifest["package_id"], "org.trpgplatform.rules-residue.validation/task-prefix")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["package_kind"], "game-system")
        self.assertEqual(manifest["lua_profile"], "platform-lua-5.5-p1")
        self.assertEqual(manifest["host_api"], {"major": 1, "min_minor": 0, "max_minor": 0})
        self.assertEqual(set(manifest["capabilities"]["required"]), {"host.state", "host.event"})
        self.assertEqual(self.contract["manifest"]["archive_path"], "package.toml")
        self.assertEqual(self.contract["entrypoint"]["path"], "lua/main.lua")
        self.assertEqual(self.contract["entrypoint"]["status"], "NOT_IMPLEMENTED")

    def test_self_contained_byte_bindings_and_schema_resources(self):
        for path, expected in self.contract["files"].items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)
        for name, validator in self.validators.items():
            with self.subTest(schema=name):
                validator.check_schema(validator.schema)
                self.assertEqual(validator.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        serialized = json.dumps(self.contract, ensure_ascii=False)
        self.assertNotIn(".codex/", serialized)
        self.assertNotIn("/home/", serialized)
        self.assertNotIn("/tmp/", serialized)

    def test_actual_hostcontract_slots_and_thirteen_callback_case_shapes(self):
        self.assertEqual(self.contract["standard_callbacks"], CALLBACKS)
        self.assertEqual(self.callbacks["standard_callbacks"], CALLBACKS)
        names = [name for case in self.callbacks["cases"] for name in case["callbacks"]]
        self.assertCountEqual(names, CALLBACKS)
        self.assertEqual(len(self.callbacks["cases"]), 12)
        self.assertFalse(self.contract["command_validation"]["host_contract_command_schema_slot"])
        self.assertNotIn("CommandSchema", self.contract["host_contract_index"])
        for case in self.callbacks["cases"]:
            host = case["host_case"]
            with self.subTest(case=case["name"]):
                self.assertEqual(set(host), {"Callback", "Input", "Expected", "Time", "Random"})
                self.assertGreaterEqual(host["Time"], 0)
                self.assertEqual(host["Random"], [])
                name = Path(case["expected_schema"]).name.split(".")[0]
                self.assertTrue(self.validators[name].is_valid(host["Expected"]))
                self.assertNotIn(host["Callback"], ("validate_command", "execute_command"))
                if host["Callback"] == "command":
                    self.assertEqual(set(host["Input"]), {"type", "seat_id", "correlation_id", "payload"})
                    self.assertTrue(self.validators["command"].is_valid(host["Input"]["payload"]))
                if host["Callback"] == "project_view":
                    self.assertEqual(set(host["Input"]), {"seat_id"})
                if host["Callback"] == "create_checkpoint":
                    self.assertEqual(host["Expected"], read_json("fixtures/initial-state.json"))
                if host["Callback"] == "restore_checkpoint":
                    self.assertTrue(self.validators["state"].is_valid(host["Input"]))

    def test_all_exact_schema_admission_vectors(self):
        self.assertGreater(len(self.fixture["schema_vectors"]), 60)
        for vector in self.fixture["schema_vectors"]:
            with self.subTest(vector=vector["id"]):
                value = vector_value(vector)
                actual = self.validators[vector["schema"]].is_valid(value)
                self.assertEqual(actual, vector["valid"], vector["id"])

    def test_all_snapshot_and_projection_relation_vectors(self):
        for vector in self.fixture["relation_vectors"]:
            with self.subTest(vector=vector["id"]):
                value = vector_value(vector)
                if vector["kind"] == "state":
                    issues = state_relation_issues(value)
                else:
                    issues = projection_relation_issues(value, resolve_sample(vector["state"]), vector["trusted_seat"])
                self.assertEqual(not issues, vector["valid"], str(issues))

    def test_declared_action_preconditions_are_read_only(self):
        for vector in self.fixture["action_vectors"]:
            with self.subTest(vector=vector["id"]):
                state = resolve_sample(vector["state"])
                before = copy.deepcopy(state)
                status = declared_precondition_status(state, vector["trusted_context"], vector["payload"],
                                                      self.validators["command"], self.contract)
                self.assertEqual(status, vector["expected"])
                self.assertEqual(state, before, "predicate must not execute an action")

    def test_exact_two_tick_trace_and_two_independent_entitlements(self):
        states = {key: expand_indexed_state(value) for key, value in self.fixture["states"].items()}
        first, second = states["after_watch_A"], states["after_watch_B"]
        self.assertEqual((first["tick"], first["pressure"]), (1, 0))
        self.assertEqual((second["tick"], second["pressure"]), (2, 1))
        self.assertEqual(second["fired_waves"], ["echo_arrival"])
        self.assertEqual([row["payload"]["kind"] for row in second["history"][-2:]],
                         ["AMBIENT_WAVE", "OBSERVATION"])
        final = states["final"]
        self.assertEqual(final["ledger"]["paper_stock"], 0)
        self.assertEqual(final["component_status"], "PAUSED")
        self.assertFalse(final["service_terminated"])
        self.assertFalse(final["opening_episode_closed"])
        self.assertFalse(final["campaign_terminal"])
        keys = []
        for row in final["ledger"]["seats"]:
            self.assertFalse(row["passenger_bound"])
            self.assertFalse(row["pending_repeat"])
            self.assertEqual(row["strain"], 0)
            self.assertTrue(row["entitlement"]["consumed"])
            keys.append(tuple(row["entitlement"][key] for key in self.contract["game_contract"]["entitlement_key"][:-1])
                        + (row["entitlement"]["opening_seat_id"],))
        self.assertEqual(len(set(keys)), 2)
        self.assertEqual(self.contract["game_contract"]["opening_seat_count"],
                         {"min": 2, "max": 6, "exercised_fixture_count": 2})

    def test_fulfillment_npc_judgment_and_physical_paper_remain_distinct(self):
        for row in expand_indexed_state(self.fixture["states"]["after_watch_B"])["ledger"]["seats"]:
            self.assertFalse(row["actual_fulfillment_internal"])
            self.assertEqual(row["issuer_adjudication"]["status"], "NONE")
            self.assertFalse(row["entitlement"]["consumed"])
            self.assertIsNone(row["paper"])
        state = expand_indexed_state(self.fixture["states"]["adjudicated_A"])
        state["ledger"]["seats"][0]["actual_fulfillment_internal"] = False
        context = {"principal": "fixture-principal-A", "seat": "opening-seat-A",
                   "authorized_character_id": "fixture-character-A"}
        self.assertEqual(declared_precondition_status(state, context,
                         {"action": "SETTLE_TASK", "task_id": "TASK.TEST.CLOCK_OBSERVATION.V1"},
                         self.validators["command"], self.contract), "ALLOW")
        self.assertIn("SOCIAL_INFLUENCE", self.contract["game_contract"]["outside_prefix"])
        self.assertEqual(expand_indexed_state(self.fixture["states"]["final"])["ledger"]["seats"][0]["paper"]["text"],
                         "显示牌变动后回到同一分钟。")

    def test_full_checkpoint_preserves_receipts_and_is_never_player_projection(self):
        checkpoint = copy.deepcopy(self.fixture["states"]["final"])
        restored = json.loads(json.dumps(checkpoint, ensure_ascii=False))
        self.assertTrue(self.validators["state"].is_valid(restored))
        self.assertFalse(state_relation_issues(restored))
        self.assertEqual(restored, checkpoint)
        self.assertFalse(self.validators["view"].is_valid(restored))
        for row in expand_indexed_state(restored)["ledger"]["seats"]:
            self.assertEqual(row["entitlement"]["settlement_receipt"],
                             next(item for item in expand_indexed_state(checkpoint)["ledger"]["seats"]
                                  if item["opening_seat_id"] == row["opening_seat_id"])["entitlement"]["settlement_receipt"])

    def test_exact_immutable_transition_vectors(self):
        for vector in self.fixture["transition_vectors"]:
            with self.subTest(vector=vector["id"]):
                before = resolve_sample(vector["before"])
                after = vector_value({"sample": vector["after"], "mutations": vector["mutations"]})
                self.assertEqual(not immutable_transition_issues(before, after), vector["valid"])

    def test_indexed_checkpoint_reconstructs_exact_emitted_payload_samples(self):
        reconstructed = [entry["payload"] for entry in expand_indexed_state(self.fixture["states"]["final"])["history"]]
        self.assertEqual(reconstructed, self.fixture["emitted_events"])

    def test_execution_provenance_uses_returned_event_ids_and_preserves_correlation(self):
        regression = self.fixture["provenance_regression"]
        self.assertEqual(len(set(regression["native_command_ids"])), 2)
        self.assertEqual(regression["native_callback_input"], self.callbacks["cases"][3]["host_case"]["Input"])
        self.assertEqual(set(regression["native_callback_input"]),
                         {"type", "seat_id", "correlation_id", "payload"})
        first = resolve_sample(regression["first_event_sample"])
        self.assertIsNone(first["execution_start_event_id"])
        self.assertNotIn("command_id", first)
        self.assertNotIn("event_id", first)
        self.assertTrue(self.validators["event"].is_valid(first))
        for state in self.fixture["states"].values():
            self.assertNotIn("command_bindings", state)
            for start in state["execution_bindings"]:
                self.assertIn(start, state["events"])
                self.assertEqual(state["events"][start]["execution_start_event_id"], start)
        # Same correlation may describe distinct groups; it is not a unique key.
        state = copy.deepcopy(self.fixture["states"]["accepted"])
        starts = list(state["execution_bindings"])
        state["execution_bindings"][starts[2]]["correlation_id"] = state["execution_bindings"][starts[1]]["correlation_id"]
        self.assertFalse(state_relation_issues(state))
        self.assertEqual(regression["native_replay"], "HOST_OWNED_BEFORE_LUA")
        self.assertEqual(regression["adopted_game_runtime"], "NOT_RUN")

    def test_execution_group_rejects_circular_or_mismatched_sources(self):
        state = copy.deepcopy(self.fixture["states"]["after_watch_B"])
        history = expand_indexed_state(state)["history"]
        wave, observation = history[-2:]
        self.assertIsNone(wave["payload"]["execution_start_event_id"])
        self.assertEqual(observation["payload"]["execution_start_event_id"], wave["event_id"])
        first = history[0]["event_id"]
        state["events"][wave["event_id"]]["execution_start_event_id"] = observation["event_id"]
        self.assertTrue(state_relation_issues(state))
        state = copy.deepcopy(self.fixture["states"]["accepted"])
        second = list(state["events"])[1]
        state["events"][second]["execution_start_event_id"] = first
        del state["execution_bindings"][second]
        self.assertIn("execution group does not match its single typed action", state_relation_issues(state))

    def test_ordered_recipient_requests_survive_indexed_checkpoint(self):
        regression = self.fixture["recipient_order_regression"]
        hashes = []
        for case in regression["cases"]:
            with self.subTest(case=case["id"]):
                state = resolve_sample(case["state"])
                payload = case["native_callback_input"]["payload"]
                start = case["execution_start_event_id"]
                stored = json.loads(json.dumps(state, ensure_ascii=False, sort_keys=True))
                self.assertTrue(self.validators["state"].is_valid(stored))
                self.assertFalse(state_relation_issues(stored))
                binding = stored["execution_bindings"][start]
                self.assertEqual(json.loads(binding["payload_json"]), payload)
                self.assertEqual(binding["payload_json"], canonical_payload_json(payload))
                hashes.append(binding["payload_sha256"])
                event = next(row["payload"] for row in expand_indexed_state(stored)["history"] if row["event_id"] == start)
                self.assertEqual(command_payload_from_event(event, "SHARE_SOURCE"), payload)
                self.assertEqual(set(event["audience"]), {"opening-seat-A", "opening-seat-B"})
                wrong = copy.deepcopy(stored)
                wrong["events"][start]["record"]["SOURCE_SHARED"]["recipient_order_json"] = canonical_payload_json(list(reversed(payload["recipient_seat_ids"])))
                self.assertTrue(state_relation_issues(wrong))
                wrong = copy.deepcopy(stored)
                changed = copy.deepcopy(payload)
                changed["recipient_seat_ids"].reverse()
                wrong["execution_bindings"][start]["payload_json"] = canonical_payload_json(changed)
                wrong["execution_bindings"][start]["payload_sha256"] = "sha256:" + hashlib.sha256(canonical_payload_json(changed).encode()).hexdigest()
                self.assertIn("same-action original request differs from typed response", state_relation_issues(wrong))
        self.assertEqual(len(set(hashes)), 2)

    def test_complete_request_codec_covers_every_supported_payload_shape(self):
        codec = self.fixture["payload_codec_vectors"]
        covered = set()
        for case in codec:
            payload = case["payload"]
            with self.subTest(case=case["id"]):
                self.assertTrue(self.validators["command"].is_valid(payload))
                encoded = canonical_payload_json(payload)
                # Native State stores a string, so object iteration cannot
                # supply recipient order or reinterpret escaped string bytes.
                stored = json.loads(json.dumps({"payload_json": encoded}, ensure_ascii=False, sort_keys=True))
                self.assertEqual(json.loads(stored["payload_json"]), payload)
                self.assertEqual(stored["payload_json"].encode(), encoded.encode())
                self.assertEqual("sha256:" + hashlib.sha256(encoded.encode()).hexdigest(), case["payload_sha256"])
                covered.add(payload["action"])
        self.assertEqual(covered, set(self.contract["game_contract"]["supported_actions"]))
        for shape in self.validators["command"].schema["oneOf"]:
            action = shape["properties"]["action"]["const"]
            optional = set(shape["properties"]) - set(shape["required"])
            for field in optional:
                samples = [case["payload"] for case in codec if case["payload"]["action"] == action]
                self.assertTrue(any(field in payload for payload in samples))
                self.assertTrue(any(field not in payload for payload in samples))

    def test_qualification_requires_real_native_proof_and_future_game_runtime(self):
        self.assertEqual(self.fixture["fixture_kind"], "CONTRACT_VECTORS_NOT_PLAYED_HISTORY")
        self.assertEqual(self.contract["qualification"]["native_parser_and_schema_proof"],
                         "EXTERNAL_SOURCE_BOUND_REQUIRED")
        for key, status in self.contract["qualification"].items():
            if key != "native_parser_and_schema_proof":
                self.assertEqual(status, "NOT_RUN")
        self.assertEqual(self.contract["capabilities"]["optional"], [])
        self.assertEqual(self.contract["host_contract_index"]["Namespaces"], {})
        self.assertEqual(self.contract["host_contract_index"]["Intents"], {})
        self.assertEqual(self.contract["host_contract_index"]["Named"], {})

    def test_native_construction_templates_are_strict_and_checkpoint_owned(self):
        initial = read_json("fixtures/initial-state.json")
        templates = initial["native_values"]
        self.assertEqual(templates, self.validators["state"].schema["properties"]["native_values"]["const"])
        self.assertEqual(templates["empty_array"], [])
        self.assertIsNone(templates["event"]["execution_start_event_id"])
        self.assertIsNone(templates["event"]["actor_seat_id"])
        self.assertEqual(templates["lifecycle_binding"], {
            "callback": "on_session_end", "correlation_id": None, "opening_seat_id": None,
            "payload_json": "{}", "payload_sha256": "sha256:" + hashlib.sha256(b"{}").hexdigest(),
        })
        final = self.fixture["states"]["final"]
        pause = next(event_id for event_id, row in final["events"].items() if "COMPONENT_PAUSED" in row["record"])
        self.assertEqual(final["execution_bindings"][pause], templates["lifecycle_binding"])
        logical = expand_indexed_state(final)
        receipt = next(row for row in logical["action_receipts"] if row["execution_start_event_id"] == pause)
        self.assertEqual((receipt["callback"], receipt["opening_seat_id"], receipt["correlation_id"], receipt["payload_json"]),
                         ("on_session_end", None, None, "{}"))
        for state in self.fixture["states"].values():
            self.assertEqual(state["native_values"], templates)
        restored = json.loads(json.dumps(initial, ensure_ascii=False))
        self.assertEqual(restored, initial)
        for mutation in ({}, {"empty_array": {}}, {**templates, "event": {"actor_seat_id": None}}):
            wrong = copy.deepcopy(initial)
            wrong["native_values"] = mutation
            self.assertFalse(self.validators["state"].is_valid(wrong))
        construction = self.contract["game_contract"]["state_representation"]["native_construction"]
        self.assertEqual(construction["state_path"], ["native_values"])
        self.assertIn("install.HostContract.State.Seed", construction["template_source"])
        self.assertIn("host.state.get", construction["consumption"])
        self.assertTrue(construction["room_configuration_status"].startswith("NOT_RUN"))
        changed = copy.deepcopy(initial)
        changed["native_values"]["empty_array"] = {}
        self.assertIn("immutable entitlement scope changed", immutable_transition_issues(initial, changed))

    def test_naturally_composed_two_seat_first_and_repeat_write_boundaries(self):
        regression = self.fixture["native_budget_regression"]
        self.assertEqual(regression["qualification"], "CONTRACT_VECTORS_NOT_PLAYED_HISTORY")
        self.assertEqual(regression["native_admission"], "EXTERNAL_SOURCE_BOUND_REQUIRED")
        self.assertEqual({case["id"] for case in regression["cases"]},
                         {"ORDINARY", "MAX_NUL", "MAX_EMOJI", "MAX_ESCAPING"})
        base = regression["base_state"]
        self.assertFalse(state_relation_issues(base))
        self.assertTrue(self.validators["state"].is_valid(base))
        self.assertTrue(all(paper["write_event_id"] is None for paper in base["ledger"]["papers"].values()))
        for case in regression["cases"]:
            before = base
            self.assertEqual([step["id"] for step in case["steps"]],
                             ["A_FIRST", "B_FIRST", "A_REPEAT", "B_REPEAT"])
            self.assertEqual(len({step["native_command_id"] for step in case["steps"]}), 4)
            for step in case["steps"]:
                with self.subTest(case=case["id"], step=step["id"]):
                    state, payload = step["state"], step["payload"]
                    self.assertEqual(len(payload["text"]), case["text_codepoints"])
                    self.assertEqual(len(payload["text"].encode()), case["text_utf8_bytes"])
                    self.assertEqual(case["text_codepoints"], 2048 if case["id"].startswith("MAX_") else 13)
                    for key, schema in (("payload", "command"), ("event", "event"), ("result", "result"), ("state", "state")):
                        self.assertTrue(self.validators[schema].is_valid(step[key]), key)
                    self.assertFalse(state_relation_issues(state))
                    self.assertFalse(immutable_transition_issues(before, state))
                    self.assertEqual(state["ledger"]["receipts"], base["ledger"]["receipts"])
                    self.assertEqual(set(state["ledger"]["papers"]), set(base["ledger"]["papers"]))
                    self.assertEqual(len(state["events"]), len(before["events"]) + 1)
                    self.assertEqual((state["tick"], state["pressure"]), (2, 1))
                    event_id = step["result"]["event_ids"][0]
                    binding = state["execution_bindings"][event_id]
                    self.assertEqual(binding["payload_json"], canonical_payload_json(payload))
                    self.assertEqual(json.loads(binding["payload_json"]), payload)
                    self.assertIsNone(step["event"]["execution_start_event_id"])
                    self.assertEqual(step["event"]["data"]["text"], payload["text"])
                    self.assertEqual(binding["opening_seat_id"], step["trusted_seat"])
                    for seat, view in step["views"].items():
                        self.assertTrue(self.validators["view"].is_valid(view))
                        self.assertFalse(projection_relation_issues(view, state, seat))
                        self.assertNotIn("native_values", view)
                    restored = json.loads(json.dumps(state, ensure_ascii=False))
                    self.assertEqual(restored, state)
                    self.assertFalse(state_relation_issues(restored))
                    too_long = copy.deepcopy(payload)
                    too_long["text"] = payload["text"] * 2049 if case["id"] == "ORDINARY" else payload["text"] + "x"
                    self.assertFalse(self.validators["command"].is_valid(too_long))
                    before = state


if __name__ == "__main__":
    unittest.main()
