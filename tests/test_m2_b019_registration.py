"""Registered suffix regressions; all extension fixtures are synthetic.

No private Owner path, private18 prose or private Git objects are required.
Synthetic admission tests mock only the existing signing boundary and legacy
validator result; real Git blobs/trees/ancestry, six current projections,
receipts, source eligibility, native maps and argparse remain exercised.
The unmodified real-source CLI test separately covers the installed16/17/18
path. These unit fixtures do not constitute a real B019 registration or an
independent acceptance. A signed suffix CLI probe is an explicit later gate.
"""
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest import mock

from tools import validate_m2_plan as plan


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class RegisteredSuffixTests(unittest.TestCase):
    real_root = Path(__file__).resolve().parents[1]

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="rr-suffix-unit-owned-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repository"
        self.root.mkdir()
        self.git("init", "--quiet")
        self.signature_calls = []
        self.contracts = []
        self.entries = []
        self.receipts = {}
        self.preparations = []
        self.owner_raw = encoded({"purpose": "synthetic unit authority, never a real grant"})
        self.owner_path = ".codex/plans/m2-vertical-slice/fixture-owner.json"
        self.put(self.owner_path, self.owner_raw)
        self.signer_raw = encoded({"signer": {"public_key": "synthetic", "fingerprint": "synthetic"}})
        self.put(plan.SCHEMA_ACCEPTED_RECEIPT, self.signer_raw)
        self.put(plan.CONTENT_SAFETY_ACCEPTED_RECEIPT, b"{}\n")
        self.put(plan.CONTENT_SAFETY_CONTRACT, encoded({"current_consumers_sha256": {}, "original_schema_sha256": {}}))
        self.put("legacy/business.txt", b"real-current-unit-business\n")
        self.put("legacy/rebind.py", b"# synthetic legacy input; never imported\n")
        projection = {"next_allowed_action": plan.SCHEMA_ACCEPTED_ACTION,
                      "blocking_ids": plan.EXPECTED_RECOVERY_BLOCKERS, "formal_B002": False,
                      "M2-B002": "PLANNED", "M2-B002_implementation": "NOT_STARTED", "M2-B002_READY": "NO"}
        old_rows = [self.batch(f"M2-B{i:03d}", state="FROZEN" if i in (1, 17, 18) else "PLANNED") for i in range(1, 19)]
        for i, row in enumerate(old_rows, 1):
            row["dependencies"] = ([] if i == 1 else ["M2-B001", "M2-B017"] if i in (2, 18)
                                   else ["M2-B001"] if i == 17 else [f"M2-B{i-1:03d}"])
        historical = ["M2-B001", "M2-B017", "M2-B018"]
        self.base_controls = {
            plan.SUFFIX_JSON_PATHS[0]: encoded({"batches": old_rows, "dependency_graph": {r["id"]: r["dependencies"] for r in old_rows},
                                               "frozen_batches": historical, "accepted_batches": historical,
                                               "lifecycle_projection": projection, "implementation_state": "NOT_STARTED"}),
            plan.SUFFIX_JSON_PATHS[1]: encoded({"lifecycle_projection": projection, "self_review": {"r2_modified": False, "fixture_revision": 1}, "acceptance_matrix": [{"state": "PLANNED_NOT_RUN"} for _ in range(31)]}),
            plan.SUFFIX_JSON_PATHS[2]: encoded({"lifecycle_projection": projection, "probes": [{"current_status": "DEFERRED_WITH_NON_BLOCKING_PROOF"} for _ in range(12)]}),
            plan.SUFFIX_JSON_PATHS[3]: encoded({"milestone": "M2", "batch_id": "M2-B001", "active_plan": {
                "next_allowed_action": plan.SCHEMA_ACCEPTED_ACTION, "lifecycle_projection": projection,
                "accepted_batches": historical, "frozen_batches": [], "implementation_state": "ACCEPTED"}}),
            plan.SUFFIX_MARKDOWN_PATHS[0]: b"<!-- SECTION-ID: SYNTHETIC-LEGACY-PLAN -->\nOriginal unit history.\n",
            plan.SUFFIX_MARKDOWN_PATHS[1]: b"<!-- SECTION-ID: SYNTHETIC-LEGACY-ROUTES -->\nOriginal unit routes.\n",
        }
        for path, raw in self.base_controls.items():
            self.put(path, raw)
        self.base_source = self.commit("synthetic immutable18 input")
        stack = self.enterContext(ExitStack())
        pins = {
            "SUFFIX_BASE": self.base_source, "SUFFIX_OWNER_SHA256": sha(self.owner_raw),
            "SCHEMA_ACCEPTED_RECEIPT_SHA256": sha(self.signer_raw),
            "CONTENT_SAFETY_ACCEPTED_RECEIPT_SHA256": sha(b"{}\n"),
            "CONTENT_SAFETY_CONTRACT_SHA256": sha(encoded({"current_consumers_sha256": {}, "original_schema_sha256": {}})),
            "CONTENT_SAFETY_ACCEPTED_ARTIFACTS": {"legacy/business.txt": sha(b"real-current-unit-business\n")},
            "SCHEMA_PREPARATION_LEGACY_IMPLEMENTATION_SHA256": {}, "B018_LEGACY_EVIDENCE": {},
            "SCHEMA_PREPARATION_REBIND_TEST": "legacy/rebind.py",
            "SCHEMA_PREPARATION_REBIND_TEST_SHA256": sha(b"# synthetic legacy input; never imported\n"),
            "PROJECT_ROOT": self.root, "PLAN_ROOT": self.root / ".codex/plans/m2-vertical-slice",
        }
        for name, value in pins.items():
            stack.enter_context(mock.patch.object(plan, name, value))
        self.signature_mock = stack.enter_context(mock.patch.object(plan, "_verify_schema_accepted_signatures", side_effect=self.signature_boundary))
        self.legacy_mock = stack.enter_context(mock.patch.object(plan, "_legacy_collect_validation", side_effect=self.legacy_boundary))

    def git(self, *args, input=None):
        return subprocess.check_output(["git", "--no-optional-locks", *args], cwd=self.root, input=input,
                                       stderr=subprocess.PIPE, env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"})

    def put(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def commit(self, message, paths=None):
        self.git("add", "--", *(paths or ["."]))
        self.git("-c", "user.name=ControlledSyntheticFixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", message)
        return {"commit": self.git("rev-parse", "HEAD").decode().strip(), "tree": self.git("rev-parse", "HEAD^{tree}").decode().strip()}

    def signature_boundary(self, root, signer, commits):
        self.assertEqual(root, self.root)
        self.assertEqual(signer, json.loads(self.signer_raw)["signer"])
        self.signature_calls.extend(commits)

    def legacy_boundary(self, root):
        self.assertEqual(root, self.root)
        current = {path: plan._regular_bytes(root, path) for path in self.base_controls}
        business = plan._regular_bytes(root, "legacy/business.txt")
        if plan._SUFFIX_VIEW.get() is None and (current != self.base_controls
                                                or business != b"real-current-unit-business\n"):
            return ["synthetic-legacy-current-byte-drift"], plan.ACCEPTED_WITH_BLOCKERS
        for path, raw in self.base_controls.items():
            self.assertEqual(plan._regular_bytes(root, path), raw)
        self.assertEqual(plan._regular_bytes(root, "legacy/business.txt"), b"real-current-unit-business\n")
        return [], plan.ACCEPTED_WITH_BLOCKERS

    @staticmethod
    def batch(batch_id, state="FROZEN"):
        # Entirely generated fields; no B018 row or private source is copied.
        row = {field: ["synthetic-unit-boundary"] for field in plan.REQUIRED_BATCH_FIELDS}
        row.update(id=batch_id, state=state, objective="Synthetic bounded Host1.0 validation",
                   dependencies=["M2-B001", "M2-B018"], allowed_paths=["platform-validation/task-prefix/fixtures/unit.json"],
                   forbidden_paths=["game-package/**", ".codex/**"], opencode_responsibilities=[], grok_responsibilities=[],
                   reading_map_request={"route_id": batch_id + "-SYNTHETIC-IMPLEMENT", "mode": "IMPLEMENT", "milestone": "M2",
                                        "batch_id": batch_id, "request": ".codex/routes/synthetic-implement.json"},
                   rollback_recovery="Restore the prior immutable synthetic fixture candidate",
                   expected_commit_boundary="one synthetic candidate",
                   tests=["synthetic-positive-check"], negative_tests=["synthetic-negative-check"],
                   implementation_state="NOT_STARTED", ready="YES" if state == "FROZEN" else "NO", parallel_safe=False,
                   formal_B002=False, acceptance_scope="NATIVE_HOST1_PLATFORM_VALIDATION_PREFIX_ONLY",
                   candidate_binding={"strategy": "EXACT_HEAD_AT_VALIDATION", "clean_worktree_required": True,
                                      "implementation_source": "ROOT_RECEIVED_INDEPENDENT_FROZEN_PLAN_SUCCESSOR"})
        return row

    def add_contract(self, kind="HOST1_CONTRACT", state="FROZEN", mutate=None, row_mutation=None, request_mutation=None):
        batch_id = f"M2-B{19 + len(self.entries):03d}"
        slug = batch_id.lower()
        binding_path = f".codex/plans/m2-vertical-slice/{slug}-synthetic-source.json"
        binding = {"schema_version": "rules-residue.native-host-source-bindings/1.0", "game": self.base_source,
                   "host": {"commit": "1" * 40, "tree": "2" * 40, "api_version": "1.0"},
                   "host_file_hashes": {"internal/synthetic_host.go": "3" * 64}, "qualification": "STATIC_SOURCE_ONLY"}
        self.put(binding_path, encoded(binding))
        row = self.batch(batch_id, state)
        row["source_binding"] = {"game": self.base_source, "host": binding["host"], "path": binding_path, "sha256": sha(encoded(binding))}
        if kind == "HOST1_LUA":
            row["dependencies"].append(self.entries[-1]["id"])
            row["allowed_paths"] = ["platform-validation/task-prefix/lua/main.lua", "tests/test_native_task_prefix_unit_lua.py"]
        else:
            row["allowed_paths"] = [f"platform-validation/task-prefix/fixtures/{slug}.json", f"tests/test_native_task_prefix_unit_{slug}.py"]
        document = f".codex/plans/m2-vertical-slice/{slug}-synthetic.md"
        section = batch_id + "-SYNTHETIC-ENVELOPE"
        routes = {mode: {"path": f".codex/routes/{slug}-synthetic-{mode.lower()}.json"} for mode in ("PLAN", "IMPLEMENT", "ACCEPT", "REPAIR")}
        row["reading_map_request"] = {"route_id": batch_id + "-SYNTHETIC-IMPLEMENT", "mode": "IMPLEMENT", "milestone": "M2",
                                      "batch_id": batch_id, "request": routes["IMPLEMENT"]["path"]}
        if row_mutation:
            row_mutation(row)
        row["envelope_sha256"] = plan.envelope_digest(row)
        doc_raw = (f"<!-- SECTION-ID: {section} -->\n# Synthetic envelope\n```json\n" + json.dumps(row, indent=2) + "\n```\n").encode()
        self.put(document, doc_raw)
        prepared_paths = [binding_path, document]
        for mode, ref in routes.items():
            request = {"schema_version": "1.0", "route_id": batch_id + "-SYNTHETIC-" + mode, "mode": mode,
                       "milestone": "M2", "batch_id": batch_id, "capacity_bytes": 196608,
                       "documents": [{"path": document, "required_sections": [section], "optional_sections": [], "reason": "synthetic unit envelope"}],
                       "forbidden_bulk_reads": ["docs/**", "authoring/**", "*", "git_history_all", "prior_chat_transcripts"]}
            if request_mutation:
                request_mutation(mode, request)
            raw = encoded(request); self.put(ref["path"], raw); ref["sha256"] = sha(raw); prepared_paths.append(ref["path"])
        prerequisites = self.receipts[self.entries[-1]["id"]]["IMPLEMENT"]["artifacts"] if kind == "HOST1_LUA" else {}
        contract = {"schema_version": plan.SUFFIX_CONTRACT_SCHEMA, "scope": plan.SUFFIX_SCOPE, "kind": kind,
                    "previous_contract_sha256": self.entries[-1]["contract"]["sha256"] if self.entries else sha(self.base_controls[plan.SUFFIX_JSON_PATHS[0]]),
                    "owner_authority": {"path": self.owner_path, "sha256": sha(self.owner_raw)}, "batch": row,
                    "source_bindings": {"path": binding_path, "sha256": sha(encoded(binding))},
                    "inputs": {"legacy/business.txt": sha(b"real-current-unit-business\n")}, "prerequisite_artifacts": prerequisites,
                    "routes": routes, "document": {"path": document, "sha256": sha(doc_raw), "section_id": section},
                    "appendices": {path: f"\n<!-- SECTION-ID: {batch_id}-SYNTHETIC-{i} -->\nSynthetic bounded registration.\n" for i, path in enumerate(plan.SUFFIX_MARKDOWN_PATHS)},
                    "plan_checks": ["synthetic-schema-check", "synthetic-negative-check"]}
        if mutate:
            mutate(contract)
        path = f".codex/plans/m2-vertical-slice/{slug}-synthetic-contract.json"
        raw = encoded(contract); self.put(path, raw); prepared_paths.append(path)
        source = self.commit("synthetic immutable contract descriptor", prepared_paths)
        self.preparations.append(source)
        self.contracts.append(contract)
        self.entries.append({"id": batch_id, "contract": {"source": source, "path": path, "sha256": sha(raw)},
                             "plan_acceptance": None, "implementation_acceptance": None})
        self.write_controls()
        return batch_id

    def lifecycle(self):
        accepted = [entry["id"] for entry in self.entries if entry["implementation_acceptance"] is not None]
        pending = next((entry for entry in self.entries if entry["implementation_acceptance"] is None), None)
        row = next((contract["batch"] for contract in self.contracts if pending and contract["batch"]["id"] == pending["id"]), None)
        frozen = [row["id"]] if row and row["state"] == "FROZEN" else []
        has_plan = pending and pending["plan_acceptance"] is not None
        state = "ACCEPTED" if pending is None else "PLAN_PENDING" if not frozen else "FROZEN_ACCEPTED_PLAN" if has_plan else "FROZEN_PLAN_PENDING_ACCEPTANCE"
        action = plan.SCHEMA_ACCEPTED_ACTION if pending is None else "PLAN_" + pending["id"] if not frozen else ("IMPLEMENT_" if has_plan else "ACCEPT_PLAN_") + pending["id"]
        return {"state": state, "accepted_batches": accepted, "frozen_batches": frozen, "next_allowed_action": action,
                "formal_B002": False, "blocking_ids": plan.EXPECTED_RECOVERY_BLOCKERS, "runtime_status": "NOT_RUN", "aggregate_M2_pass": False}

    def write_controls(self):
        # Independent fixture serialization, not a call to the implementation's
        # transition helper. Keep all18 original row slices verbatim.
        state = self.lifecycle()
        data = {path: json.loads(raw) for path, raw in self.base_controls.items() if path in plan.SUFFIX_JSON_PATHS}
        registry = {"schema_version": plan.SUFFIX_SCHEMA, "scope": plan.SUFFIX_SCOPE, "entries": self.entries}
        batches = data[plan.SUFFIX_JSON_PATHS[0]]
        batches["registered_suffix"] = registry
        batches["batches"].extend(contract["batch"] for contract in self.contracts)
        batches["dependency_graph"].update({c["batch"]["id"]: c["batch"]["dependencies"] for c in self.contracts})
        batches["accepted_batches"] += state["accepted_batches"]
        for path, value in data.items():
            value["registered_suffix_projection"] = state
            target = value["active_plan"] if path == plan.SUFFIX_JSON_PATHS[3] else value
            target["lifecycle_projection"]["next_allowed_action"] = state["next_allowed_action"]
            if path == plan.SUFFIX_JSON_PATHS[3]:
                target["accepted_batches"] += state["accepted_batches"]
                target["frozen_batches"] = state["frozen_batches"]
                target["next_allowed_action"] = state["next_allowed_action"]
            self.put(path, encoded(value))
        self.assertEqual(plan._raw_batch_rows((self.root / plan.SUFFIX_JSON_PATHS[0]).read_bytes())[:18],
                         plan._raw_batch_rows(self.base_controls[plan.SUFFIX_JSON_PATHS[0]]))
        for path in plan.SUFFIX_MARKDOWN_PATHS:
            self.put(path, self.base_controls[path] + b"".join(c["appendices"][path].encode() for c in self.contracts))

    def receive(self, batch_id, phase, candidate, source, mutate=None):
        index = next(i for i, entry in enumerate(self.entries) if entry["id"] == batch_id)
        contract = self.contracts[index]
        row = contract["batch"]
        checks = contract["plan_checks"] if phase == "PLAN" else row["tests"] + row["negative_tests"]
        artifacts = {} if phase == "PLAN" else {path: sha((self.root / path).read_bytes()) for path in row["allowed_paths"]}
        receipt = {"schema_version": "rules-residue.m2.suffix-independent-receipt/1.0", "phase": phase, "batch_id": batch_id,
                   "scope": plan.SUFFIX_SCOPE, "decision": "PASS", "candidate": candidate, "source": source,
                   "contract_sha256": self.entries[index]["contract"]["sha256"], "envelope_sha256": row["envelope_sha256"],
                   "producer": "/root/synthetic_producer", "reviewer": "/root/synthetic_reviewer", "independent": True,
                   "required_checks": [{"command": command, "exit_code": 0} for command in checks], "unresolved_findings": 0,
                   "control_inputs": {path: sha(self.git("show", candidate["commit"] + ":" + path)) for path in plan.SUFFIX_CONTROL_PATHS},
                   "artifacts": artifacts, "root_reception": {"decision": "RECEIVED_EXACT_INDEPENDENT_PASS", "root": "/root", "candidate": candidate, "phase": phase}}
        if mutate:
            mutate(receipt)
        path = f".codex/plans/m2-vertical-slice/{batch_id.lower()}-synthetic-{phase.lower()}-receipt.json"
        raw = encoded(receipt); self.put(path, raw)
        proof_source = self.commit("synthetic immutable independent receipt", [path])
        ref = {"source": proof_source, "path": path, "sha256": sha(raw)}
        self.entries[index]["plan_acceptance" if phase == "PLAN" else "implementation_acceptance"] = ref
        self.receipts.setdefault(batch_id, {})[phase] = receipt
        self.write_controls()
        return self.commit("synthetic received phase successor", list(plan.SUFFIX_CONTROL_PATHS))

    def received_plan(self):
        batch_id = self.add_contract()
        candidate = self.commit("synthetic pending frozen PLAN", list(plan.SUFFIX_CONTROL_PATHS))
        received = self.receive(batch_id, "PLAN", candidate, self.preparations[0])
        return batch_id, received

    def accepted_contract(self):
        batch_id, frozen = self.received_plan()
        for path in self.contracts[0]["batch"]["allowed_paths"]:
            self.put(path, b"synthetic accepted native contract input\n")
        candidate = self.commit("synthetic bounded implementation", self.contracts[0]["batch"]["allowed_paths"])
        self.receive(batch_id, "IMPLEMENT", candidate, frozen)
        return batch_id

    def cli(self, *args):
        with mock.patch.object(sys, "argv", ["validate_m2_plan.py", *args]), redirect_stdout(io.StringIO()) as output:
            result = plan.main()
        return result, output.getvalue()

    def assert_rejected_before_legacy(self):
        calls = self.legacy_mock.call_count
        errors, state = plan.collect_validation(self.root)
        self.assertTrue(errors)
        self.assertEqual(state, plan.INVALID_MIXED_STATE)
        self.assertEqual(self.legacy_mock.call_count, calls, errors)
        self.assertIsNone(plan._SUFFIX_VIEW.get())
        self.assertEqual(self.cli("--batch", "M2-B019")[0], 1)

    def test_current_installed_legacy_cli_uses_no_suffix_private_inputs(self):
        result = subprocess.run([sys.executable, "-B", "tools/validate_m2_plan.py"], cwd=self.real_root,
                                capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        unknown = subprocess.run([sys.executable, "-B", "tools/validate_m2_plan.py", "--batch", "M2-B999"], cwd=self.real_root,
                                 capture_output=True, text=True)
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("registered suffix", unknown.stdout)

    def test_absent_registry_keeps_legacy_refusal_and_present_malformed_registry_cannot_project(self):
        self.add_contract()
        path = self.root / plan.SUFFIX_JSON_PATHS[0]
        value = json.loads(path.read_bytes())
        value.pop("registered_suffix")
        self.put(plan.SUFFIX_JSON_PATHS[0], encoded(value))
        # The undeclared extra row must reach the old refusing validator;
        # no authenticated historical projection may hide current bytes.
        self.assertIsNone(plan._load_registered_suffix(self.root))
        calls = self.legacy_mock.call_count
        self.assertEqual(plan.collect_validation(self.root),
                         (["synthetic-legacy-current-byte-drift"], plan.ACCEPTED_WITH_BLOCKERS))
        self.assertEqual(self.legacy_mock.call_count, calls + 1)
        self.assertIsNone(plan._SUFFIX_VIEW.get())
        for malformed in (None, {}, [], False, 0):
            with self.subTest(registry=malformed):
                value["registered_suffix"] = malformed
                self.put(plan.SUFFIX_JSON_PATHS[0], encoded(value))
                self.assert_rejected_before_legacy()

    def test_pending_PLAN_validates_actual_cli_and_native_map_but_cannot_implement(self):
        batch_id = self.add_contract()
        self.assertEqual(plan.collect_validation(self.root), ([], plan.ACCEPTED_WITH_BLOCKERS))
        self.assertEqual(self.cli("--batch", batch_id)[0], 0)
        proof = plan._load_registered_suffix(self.root)
        self.assertEqual(proof["lifecycle"]["next_allowed_action"], "ACCEPT_PLAN_" + batch_id)
        self.assertTrue(self.signature_calls)
        self.assertTrue(plan.registered_suffix_batch_errors(self.root, batch_id, self.preparations[0]["commit"]))
        self.assertEqual(self.cli("--implementation-source", self.preparations[0]["commit"])[0], 1)

    def assert_missing_registry_refused_by_installed_source(self, undeclared_row):
        temporary = tempfile.TemporaryDirectory(prefix="rr-unregistered-current-source-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "repository"
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(self.real_root), str(root)],
                       check=True, capture_output=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.real_root).decode().strip()
        subprocess.run(["git", "checkout", "--quiet", "--detach", head], cwd=root, check=True, capture_output=True)
        self.assertFalse((root / ".git/objects/info/alternates").exists())
        shutil.copy2(self.real_root / "tools/validate_m2_plan.py", root / "tools/validate_m2_plan.py")
        spec = importlib.util.spec_from_file_location("installed_current_source_negative", root / "tools/validate_m2_plan.py")
        installed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installed)
        self.assertEqual(installed.collect_validation(root)[0], [], "actual current-source positive prerequisite")
        path = root / installed.SUFFIX_JSON_PATHS[0]
        original = path.read_bytes()
        value = json.loads(original)
        original_rows = installed._raw_batch_rows(original)
        value["batches"].append(copy.deepcopy(undeclared_row))
        value["registered_suffix"] = {"scope": "test-only removed registration"}
        value.pop("registered_suffix")
        self.assertTrue(original_rows)
        self.assertEqual(original.count(original_rows[-1]), 1)
        end = original.index(original_rows[-1]) + len(original_rows[-1])
        appended = b",\n" + b"\n".join(b"    " + line for line in encoded(undeclared_row).rstrip(b"\n").splitlines())
        path.write_bytes(original[:end] + appended + original[end:])
        self.assertEqual(json.loads(path.read_bytes()), value)
        self.assertEqual(installed._raw_batch_rows(path.read_bytes())[:-1], original_rows)
        self.assertEqual(json.loads(installed._raw_batch_rows(path.read_bytes())[-1]), undeclared_row)
        with mock.patch.object(installed, "_b018_source_bytes", wraps=installed._b018_source_bytes) as history:
            with mock.patch.object(installed, "_b018_git", wraps=installed._b018_git) as git_reads:
                errors, state = installed.collect_validation(root)
        self.assertTrue(errors)
        if len(original_rows) == 18:
            self.assertEqual(errors, [
                "B018 accepted lifecycle evidence rejected: current accepted byte drift: " + installed.SUFFIX_JSON_PATHS[0],
                "registered suffix DAG rejected: unregistered suffix DAG",
            ])
            self.assertEqual(state, installed.ACCEPTED_WITH_BLOCKERS)
        # Older public16/17 inputs retain their own native refusal diagnostics.
        # They require neither private18 documents nor private Git objects.
        self.assertIsNone(installed._SUFFIX_VIEW.get())
        history.assert_not_called()
        self.assertFalse(any(call.args[1] == "show" for call in git_reads.call_args_list))
        cli = subprocess.run([sys.executable, "-B", "tools/validate_m2_plan.py"], cwd=root,
                             capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(cli.returncode, 1, cli.stdout + cli.stderr)
        self.assertIn("M2_PLAN_VALIDATION: FAIL", cli.stdout)
        for error in errors:
            self.assertIn(error, cli.stdout)

    def test_unregistered_missing_duplicate_skipped_and_reordered_tail_is_denied(self):
        self.add_contract()
        self.assert_missing_registry_refused_by_installed_source(self.contracts[0]["batch"])
        path = self.root / plan.SUFFIX_JSON_PATHS[0]
        original = path.read_bytes()
        for mutation in [lambda d: d["registered_suffix"].update(scope="ANYTHING"),
                         lambda d: d["registered_suffix"]["entries"].append(copy.deepcopy(d["registered_suffix"]["entries"][0])),
                         lambda d: d["registered_suffix"]["entries"][0].update(id="M2-B020"),
                         lambda d: d["batches"].reverse()]:
            with self.subTest(mutation=mutation):
                data = json.loads(original); mutation(data); path.write_bytes(encoded(data))
                try:
                    self.assert_rejected_before_legacy()
                finally:
                    path.write_bytes(original)

    def test_six_current_control_files_and_old_raw_rows_are_checked_before_view(self):
        self.add_contract()
        for relative in plan.SUFFIX_CONTROL_PATHS:
            path = self.root / relative; original = path.read_bytes()
            with self.subTest(path=relative):
                if relative in plan.SUFFIX_JSON_PATHS:
                    data = json.loads(original); data["unsigned_extra"] = True; path.write_bytes(encoded(data))
                else:
                    path.write_bytes(b"changed old history\n" + original)
                try:
                    self.assert_rejected_before_legacy()
                finally:
                    path.write_bytes(original)
        registry = self.root / plan.SUFFIX_JSON_PATHS[0]
        original = registry.read_bytes(); registry.write_bytes(original.replace(b'"id": "M2-B001"', b'"id" : "M2-B001"', 1))
        try:
            self.assert_rejected_before_legacy()
        finally:
            registry.write_bytes(original)

    def test_type_changed_current_controls_are_denied_before_historical_view(self):
        self.add_contract()
        cases = [(plan.SUFFIX_JSON_PATHS[1], ("self_review", "r2_modified"), value) for value in (0, 0.0)]
        cases += [(plan.SUFFIX_JSON_PATHS[1], ("self_review", "fixture_revision"), value) for value in (True, 1.0)]
        cases += [(path, ("registered_suffix_projection", key), value)
                  for path in plan.SUFFIX_JSON_PATHS for key in ("formal_B002", "aggregate_M2_pass") for value in (0, 0.0)]
        for relative, keys, value in cases:
            with self.subTest(path=relative, keys=keys, value=value, value_type=type(value).__name__):
                path = self.root / relative; original = path.read_bytes(); data = json.loads(original)
                data[keys[0]][keys[1]] = value; path.write_bytes(encoded(data))
                try:
                    self.assert_rejected_before_legacy()
                finally:
                    path.write_bytes(original)

    def test_typed_envelope_and_native_reading_map_object_are_required(self):
        # Bind loop values explicitly; each subcase has its own immutable fixture.
        mutations = [("clean-bool-" + repr(value), lambda row, value=value: row["candidate_binding"].update(clean_worktree_required=value))
                     for value in (1, 1.0)]
        for field in ("objective", "rollback_recovery", "expected_commit_boundary"):
            mutations += [(field + "-" + type(value).__name__, lambda row, field=field, value=value: row.update({field: value}))
                          for value in (1, True, ["wrong-shape"], {"value": "wrong-shape"})]
        for field in ("authority_ids", "r2_decision_ids", "input_sections", "codex_responsibilities", "platform_probes", "schemas", "fixtures",
                      "acceptance_gates", "stop_conditions", "non_goals", "opencode_responsibilities", "grok_responsibilities"):
            mutations += [(field + "-" + type(value).__name__, lambda row, field=field, value=value: row.update({field: value}))
                          for value in (1, True, "wrong-shape", {"value": "wrong-shape"}, [1], [True])]
        mutations += [("route-object-required", lambda row: row.update(reading_map_request=".codex/routes/synthetic-implement.json")),
                      ("route-id", lambda row: row["reading_map_request"].update(route_id="M2-B019-DIFFERENT-IMPLEMENT")),
                      ("route-mode", lambda row: row["reading_map_request"].update(mode="REPAIR")),
                      ("route-batch", lambda row: row["reading_map_request"].update(batch_id="M2-B999")),
                      ("route-path", lambda row: row["reading_map_request"].update(request=".codex/routes/unregistered.json")),
                      ("route-extra", lambda row: row["reading_map_request"].update(unsigned_extra=True)),
                      ("route-missing", lambda row: row["reading_map_request"].pop("request"))]
        for name, mutation in mutations:
            with self.subTest(name=name):
                child = type(self)("runTest")
                try:
                    child.setUp(); child.add_contract(row_mutation=mutation); child.assert_rejected_before_legacy()
                finally:
                    child.doCleanups()

    def test_unselected_native_phase_request_shape_is_checked_before_view(self):
        # REPAIR is only descriptor data here; no future REPAIR map is generated.
        for value in (True, 196608.0):
            with self.subTest(capacity=value, value_type=type(value).__name__):
                child = type(self)("runTest")
                try:
                    child.setUp()
                    child.add_contract(request_mutation=lambda mode, request: request.update(capacity_bytes=value) if mode == "REPAIR" else None)
                    child.assert_rejected_before_legacy()
                finally:
                    child.doCleanups()

    def test_unknown_kind_source_hash_route_and_ownership_are_denied(self):
        cases = [lambda c: c.update(kind="UNREGISTERED_KIND"), lambda c: c.update(scope="FORMAL_B002"),
                 lambda c: c["owner_authority"].update(sha256="0" * 64), lambda c: c["source_bindings"].update(sha256="0" * 64),
                 lambda c: c["routes"]["IMPLEMENT"].update(sha256="0" * 64), lambda c: c["batch"].update(allowed_paths=["tools/validate_m2_plan.py"])]
        for mutation in cases:
            with self.subTest(mutation=mutation):
                # Each subcase starts with a separate synthetic repository via
                # a separate TestCase instance, never the shared source repo.
                child = type(self)("runTest")
                try:
                    child.setUp(); child.add_contract(mutate=mutation); child.assert_rejected_before_legacy()
                finally:
                    child.doCleanups()

    def test_nonregular_path_traversal_duplicate_JSON_and_nonfinite_are_denied(self):
        self.add_contract(); ref = self.entries[0]["contract"]; path = self.root / ref["path"]; original = path.read_bytes()
        for kind in ("missing", "directory", "symlink", "duplicate", "nonfinite"):
            with self.subTest(kind=kind):
                if kind in {"missing", "directory", "symlink"}:
                    path.unlink()
                    if kind == "directory": path.mkdir()
                    if kind == "symlink": path.symlink_to(self.root / self.owner_path)
                elif kind == "duplicate": path.write_bytes(original.replace(b'{\n', b'{\n "scope": "duplicate",\n', 1))
                else: path.write_bytes(original.replace(b'{\n', b'{\n "invalid": NaN,\n', 1))
                try:
                    self.assert_rejected_before_legacy()
                finally:
                    if path.is_symlink() or path.is_file(): path.unlink()
                    elif path.is_dir(): path.rmdir()
                    path.write_bytes(original)
        for bad in ("../escape.json", "/tmp/escape.json", ".codex/../escape.json", ".codex//escape.json", "name*.json"):
            with self.subTest(path=bad), self.assertRaises(ValueError): plan._suffix_path(bad)

    def test_source_tree_and_current_signed_blob_mismatch_is_denied(self):
        self.add_contract()
        path = self.root / plan.SUFFIX_JSON_PATHS[0]; original = path.read_bytes()
        data = json.loads(original); data["registered_suffix"]["entries"][0]["contract"]["source"]["tree"] = "0" * 40
        path.write_bytes(encoded(data))
        try:
            self.assert_rejected_before_legacy()
        finally:
            path.write_bytes(original)
        doc = self.root / self.contracts[0]["document"]["path"]; doc.write_bytes(doc.read_bytes() + b"\n")
        self.assert_rejected_before_legacy()

    def test_independent_PLAN_source_successor_enables_only_exact_bounded_implementation(self):
        batch_id, received = self.received_plan()
        self.assertEqual(plan._load_registered_suffix(self.root)["lifecycle"]["next_allowed_action"], "IMPLEMENT_" + batch_id)
        self.assertTrue(plan.registered_suffix_batch_errors(self.root, batch_id, self.preparations[0]["commit"]))
        for path in self.contracts[0]["batch"]["allowed_paths"]: self.put(path, b"bounded synthetic implementation\n")
        self.commit("bounded synthetic candidate", self.contracts[0]["batch"]["allowed_paths"])
        self.assertEqual(plan.registered_suffix_batch_errors(self.root, batch_id, received["commit"]), [])
        self.assertEqual(self.cli("--batch", batch_id, "--implementation-source", received["commit"])[0], 0)
        self.put("outside.txt", b"unauthorized\n"); self.commit("outside synthetic scope", ["outside.txt"])
        self.assertTrue(plan.registered_suffix_batch_errors(self.root, batch_id, received["commit"]))

    def test_self_acceptance_FAIL_missing_checks_and_candidate_hash_mismatch_are_denied(self):
        cases = [lambda r: r.update(reviewer=r["producer"]), lambda r: r.update(decision="FAIL"),
                 lambda r: r.update(required_checks=[]), lambda r: r["candidate"].update(tree="0" * 40),
                 lambda r: r.update(unresolved_findings=1), lambda r: r["control_inputs"].update({plan.SUFFIX_JSON_PATHS[0]: "0" * 64})]
        for mutation in cases:
            with self.subTest(mutation=mutation):
                child = type(self)("runTest")
                try:
                    child.setUp(); batch_id = child.add_contract(); candidate = child.commit("pending synthetic PLAN", list(plan.SUFFIX_CONTROL_PATHS))
                    child.receive(batch_id, "PLAN", candidate, child.preparations[0], mutate=mutation); child.assert_rejected_before_legacy()
                finally:
                    child.doCleanups()

    def test_contiguous_future_registration_has_no19_ceiling_and_preserves_historical_freeze(self):
        self.accepted_contract()
        self.add_contract(kind="HOST1_LUA")
        self.add_contract(state="PLANNED")
        proof = plan._load_registered_suffix(self.root)
        self.assertEqual([entry["id"] for entry in proof["entries"]], ["M2-B019", "M2-B020", "M2-B021"])
        self.assertEqual(proof["lifecycle"]["accepted_batches"], ["M2-B019"])
        self.assertEqual(proof["lifecycle"]["frozen_batches"], ["M2-B020"])
        self.assertEqual(proof["current_batches"]["frozen_batches"], ["M2-B001", "M2-B017", "M2-B018"])
        self.assertEqual(self.cli("--batch", "M2-B020")[0], 0)
        self.assertEqual(self.cli("--batch", "M2-B022")[0], 1)

    def test_missing_lua_prerequisite_real_current_artifact_and_conflicting_writers_are_denied(self):
        self.accepted_contract(); self.add_contract(kind="HOST1_LUA")
        path = self.root / self.contracts[0]["batch"]["allowed_paths"][0]
        original = path.read_bytes(); path.write_bytes(b"changed accepted prerequisite\n")
        try:
            self.assert_rejected_before_legacy()
        finally:
            path.write_bytes(original)
        self.add_contract(state="FROZEN", row_mutation=lambda row: row.update(allowed_paths=self.contracts[0]["batch"]["allowed_paths"]))
        self.assert_rejected_before_legacy()

    def test_legacy_business_is_current_and_cannot_be_hidden_by_projection(self):
        self.add_contract()
        self.put("legacy/business.txt", b"tampered current business\n")
        self.assert_rejected_before_legacy()
        self.put("legacy/business.txt", b"real-current-unit-business\n")
        self.assertEqual(plan.collect_validation(self.root), ([], plan.ACCEPTED_WITH_BLOCKERS))
        self.assertIsNone(plan._SUFFIX_VIEW.get())

    def test_dag_unknown_forward_self_dependency_and_extra_active_freeze_are_denied(self):
        for dependency in ("M2-B002", "M2-B019", "M2-B020", "UNKNOWN"):
            child = type(self)("runTest")
            try:
                child.setUp()
                child.add_contract(row_mutation=lambda row: row.update(dependencies=[dependency])); child.assert_rejected_before_legacy()
            finally:
                child.doCleanups()


if __name__ == "__main__":
    unittest.main()
