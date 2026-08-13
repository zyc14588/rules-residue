#!/usr/bin/env python3
"""Adversarial tests for the M2-B001 probe evidence contract."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("m2_b001_validator", HERE / "validate_m2_b001.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class M2B001ProbeTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((validator.ROOT / relative).read_text(encoding="utf-8"))

    def assert_rejected(self, function, *args):
        with self.assertRaises(validator.ProbeValidationError):
            function(*args)

    def test_all_twelve_local_reference_checks_execute(self):
        vectors = self.load("tests/m2/probes/fixtures/local-capability-vectors.json")
        self.assertEqual(set(validator.LOCAL_CHECKS), set(validator.FROZEN_REQUIREMENTS))
        for probe_id in sorted(validator.LOCAL_CHECKS):
            result = validator.run_local_check(probe_id, vectors)
            self.assertEqual(result["probe_id"], probe_id)
            self.assertIn(result["execution_status"], validator.ALLOWED_STATUSES)

    def test_current_probe_results_validate(self):
        validator.validate_probe_results(self.load("reports/m2/probes/probe-results.json"))

    def test_not_run_target_cannot_be_reported_as_pass(self):
        results = self.load("reports/m2/probes/probe-results.json")
        probe = next(item for item in results["probes"] if item["probe_id"] == "R2-INT-007")
        probe["target_results"][0]["execution_status"] = "NOT_RUN"
        self.assert_rejected(validator.validate_probe_results, results)

    def test_adapter_cannot_lower_r2(self):
        results = self.load("reports/m2/probes/probe-results.json")
        probe = next(item for item in results["probes"] if item["probe_id"] == "R2-INT-003")
        probe["adapter_feasibility"]["preserves_r2"] = False
        self.assert_rejected(validator.validate_probe_results, results)

    def test_requirement_text_cannot_be_narrowed(self):
        results = self.load("reports/m2/probes/probe-results.json")
        results["probes"][0]["r2_requirement"] = "Only four seats are required."
        self.assert_rejected(validator.validate_probe_results, results)

    def test_platform_proposal_is_not_approval(self):
        results = self.load("reports/m2/probes/probe-results.json")
        probe = next(item for item in results["probes"] if item["probe_id"] == "R2-INT-001")
        probe["execution_status"] = "PASS"
        for target in probe["target_results"]:
            target["execution_status"] = "PASS"
        for command in probe["commands_actions_actually_run"]:
            command["exit_code"] = 0
        self.assertEqual(probe["platform_change_necessity"]["approval_status"], "NOT_APPROVED")
        self.assert_rejected(validator.validate_probe_results, results)

    def test_safety_evidence_rejects_stale_source_hash(self):
        evidence = self.load("reports/m2/probes/safety-stage-evidence.json")
        evidence["records"][0]["source_sha256"] = "0" * 64
        vectors = self.load("tests/m2/probes/fixtures/local-capability-vectors.json")
        self.assert_rejected(validator.validate_safety_evidence, evidence, vectors)

    def fabricated_external_result(self):
        packet_path = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        return {
            "schema_version": "rules-residue.m2.external-probe-result/1.0",
            "task_id": "RR-TASK-2001",
            "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
            "game_source_commit": validator.SOURCE_COMMIT,
            "game_source_tree": validator.SOURCE_TREE,
            "game_candidate_commit": "c" * 40,
            "game_candidate_tree": "d" * 40,
            "external_system": {
                "name": "TRPG_PLATFORM",
                "repository_commit": "a" * 40,
                "repository_tree": "b" * 40,
                "tracked_worktree_clean": True,
            },
            "probe_results": [
                {"probe_id": "R2-INT-001", "execution_status": "PASS", "observed_result": "fabricated"},
                {"probe_id": "R2-INT-001", "execution_status": "PASS", "observed_result": "duplicated fabricated"},
            ],
            "commands": [
                {"command": "true", "exit_code": 0, "output_sha256": "0" * 64}
            ],
            "evidence_paths": ["/definitely/nonexistent/evidence.json"],
        }

    def valid_external_result(self):
        packet_path = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        packet = self.load("workflow/queue/m2-b001-trpg-platform-probes.json")
        _, assignment = validator.packet_assignment(packet, packet_path)
        prefix = assignment["evidence_prefix"]
        paths = [prefix + name for name in ("commit.txt", "tree.txt", "status.txt", "probe.txt")]
        commands = [
            {"command_id": "IDENTITY_COMMIT", "command": "git rev-parse HEAD", "exit_code": 0, "output_sha256": "e" * 64, "evidence_path": paths[0]},
            {"command_id": "IDENTITY_TREE", "command": "git rev-parse HEAD^{tree}", "exit_code": 0, "output_sha256": "e" * 64, "evidence_path": paths[1]},
            {"command_id": "IDENTITY_CLEAN", "command": "git status --short", "exit_code": 0, "output_sha256": "e" * 64, "evidence_path": paths[2]},
            {"command_id": "PROBE_EXECUTION", "command": "external-probe --exact-candidate", "exit_code": 1, "output_sha256": "e" * 64, "evidence_path": paths[3]},
        ]
        probe_map = validator.frozen_probe_map()
        probe_results = []
        for probe_id in validator.assigned_probe_ids(assignment["target"]):
            probe_results.append({
                "probe_id": probe_id,
                "target": assignment["target"],
                "execution_status": "BLOCKED_EXTERNAL",
                "observed_result": "External capability remains unavailable.",
                "procedure_results": [
                    {
                        "procedure": procedure,
                        "execution_status": "BLOCKED_EXTERNAL",
                        "command_ids": ["PROBE_EXECUTION"],
                        "evidence_paths": [paths[3]],
                    }
                    for procedure in probe_map[probe_id]["probe_procedure"]
                ],
            })
        return {
            "schema_version": "rules-residue.m2.external-probe-result/1.0",
            "task_id": packet["task_id"],
            "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
            "game_source_commit": validator.SOURCE_COMMIT,
            "game_source_tree": validator.SOURCE_TREE,
            "game_candidate_commit": "c" * 40,
            "game_candidate_tree": "d" * 40,
            "external_system": {
                "name": assignment["external_system"],
                "repository_commit": "a" * 40,
                "repository_tree": "b" * 40,
                "tracked_worktree_clean": True,
                "identity_command_ids": {
                    "repository_commit": "IDENTITY_COMMIT",
                    "repository_tree": "IDENTITY_TREE",
                    "tracked_worktree_clean": "IDENTITY_CLEAN",
                },
            },
            "probe_results": probe_results,
            "commands": commands,
            "evidence_paths": paths,
            "evidence_artifacts": [{"path": path, "sha256": "e" * 64} for path in paths],
        }

    def test_duplicate_fabricated_pass_is_rejected(self):
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(
            validator.validate_external_result,
            self.fabricated_external_result(),
            packet,
            "c" * 40,
            "d" * 40,
        )

    def test_external_result_schema_rejects_original_fabrication(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("optional jsonschema package is unavailable")
        schema = self.load("docs/implementation/m2/probes/external-result-v1.schema.json")
        jsonschema.Draft202012Validator(schema).validate(self.valid_external_result())
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(self.fabricated_external_result())

    def test_external_schema_freezes_packet_system_and_probe_sets(self):
        schema = self.load("docs/implementation/m2/probes/external-result-v1.schema.json")
        branches = schema["allOf"][0]["oneOf"]
        observed = {
            branch["properties"]["task_id"]["const"]: {
                "packet_sha256": branch["properties"]["packet_sha256"]["const"],
                "system": branch["properties"]["external_system"]["properties"]["name"]["const"],
                "probe_ids": set(branch["properties"]["probe_results"]["items"]["properties"]["probe_id"]["enum"]),
            }
            for branch in branches
        }
        for packet_text, assignment in validator.EXTERNAL_PACKET_ASSIGNMENTS.items():
            packet_path = validator.ROOT / packet_text
            expected_ids = set(validator.assigned_probe_ids(assignment["target"]))
            self.assertEqual(observed[assignment["task_id"]], {
                "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
                "system": assignment["external_system"],
                "probe_ids": expected_ids,
            })
        self.assertEqual(schema["$defs"]["sha256"]["not"]["const"], "0" * 64)

    def test_unbound_external_result_is_rejected(self):
        result = self.valid_external_result()
        del result["external_system"]["repository_tree"]
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_stale_external_candidate_is_rejected(self):
        result = self.valid_external_result()
        result["game_candidate_commit"] = "f" * 40
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_stale_task_packet_binding_is_rejected(self):
        result = self.valid_external_result()
        result["packet_sha256"] = "0" * 64
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_external_packet_system_mismatch_is_rejected(self):
        result = self.valid_external_result()
        result["external_system"]["name"] = "Creator Tool"
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_duplicate_assigned_probe_coverage_is_rejected(self):
        result = self.valid_external_result()
        duplicate = copy.deepcopy(result["probe_results"][0])
        result["probe_results"] = [copy.deepcopy(duplicate) for _ in result["probe_results"]]
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_incomplete_assigned_probe_coverage_is_rejected(self):
        result = self.valid_external_result()
        result["probe_results"].pop()
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_incomplete_external_procedure_coverage_is_rejected(self):
        result = self.valid_external_result()
        result["probe_results"][0]["procedure_results"].pop()
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_nonexistent_external_evidence_is_rejected(self):
        result = self.valid_external_result()
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_unverifiable_external_hash_is_rejected(self):
        result = self.valid_external_result()
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        with mock.patch.object(validator, "validate_external_evidence_path", return_value=Path(__file__)):
            self.assert_rejected(validator.validate_external_result, result, packet, "c" * 40, "d" * 40)

    def test_fully_bound_external_blocked_result_validates(self):
        result = self.valid_external_result()
        packet = validator.ROOT / "workflow/queue/m2-b001-trpg-platform-probes.json"
        contents = {
            "commit.txt": ("a" * 40 + "\n").encode(),
            "tree.txt": ("b" * 40 + "\n").encode(),
            "status.txt": b"",
            "probe.txt": b"external capability unavailable\n",
        }
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            temporary = Path(directory)
            resolved = {}
            for path_text in result["evidence_paths"]:
                name = Path(path_text).name
                path = temporary / name
                path.write_bytes(contents[name])
                resolved[path_text] = path
            for command in result["commands"]:
                command["output_sha256"] = hashlib.sha256(resolved[command["evidence_path"]].read_bytes()).hexdigest()
            for artifact in result["evidence_artifacts"]:
                artifact["sha256"] = hashlib.sha256(resolved[artifact["path"]].read_bytes()).hexdigest()
            with mock.patch.object(
                validator,
                "validate_external_evidence_path",
                side_effect=lambda path_text, _prefix: resolved[path_text],
            ):
                validator.validate_external_result(result, packet, "c" * 40, "d" * 40)

    def test_portable_task_packets_match_repository_contract(self):
        for relative in (
            "workflow/queue/m2-b001-trpg-platform-probes.json",
            "workflow/queue/m2-b001-creator-tool-probes.json",
        ):
            validator.validate_task_packet(self.load(relative))

    def test_external_gates_remain_blocked_without_bound_results(self):
        gates = self.load("reports/m2/probes/external-gates.json")
        validator.validate_external_gates(gates)
        self.assertTrue(all(item["external_result"] is None for item in gates["gates"]))
        self.assertTrue(all(item["execution_status"] == "BLOCKED_EXTERNAL" for item in gates["gates"]))

    def test_external_gates_cover_all_fifteen_frozen_target_pairs(self):
        gates = self.load("reports/m2/probes/external-gates.json")
        covered = {
            (probe_id, gate["target"])
            for gate in gates["gates"]
            for probe_id in gate["probe_ids"]
        }
        required_targets = {item["target"] for item in validator.EXTERNAL_PACKET_ASSIGNMENTS.values()}
        required = {
            (probe_id, target)
            for probe_id, probe in validator.frozen_probe_map().items()
            for target in probe["target_system"]
            if target in required_targets
        }
        self.assertEqual(len(required), 15)
        self.assertEqual(covered, required)
        self.assertIn(("R2-INT-006", "C:Creator Tool"), covered)
        self.assertIn(("R2-INT-010", "B:TRPG_PLATFORM"), covered)
        self.assertIn(("R2-INT-012", "B:TRPG_PLATFORM"), covered)

    def test_tampered_gate_coverage_is_rejected(self):
        gates = self.load("reports/m2/probes/external-gates.json")
        for gate in gates["gates"]:
            gate["probe_ids"] = ["R2-INT-001"]
            gate["blocks"] = []
            gate["gate_class"] = "NON_BLOCKING_UNTIL_RELEASE"
        self.assert_rejected(validator.validate_external_gates, gates)

    def test_gate_target_packet_and_blockers_are_exact(self):
        for field, replacement in (
            ("target", "C:Creator Tool"),
            ("task_packet", "workflow/queue/m2-b001-creator-tool-probes.json"),
            ("gate_class", "NON_BLOCKING_UNTIL_RELEASE"),
            ("blocks", []),
        ):
            with self.subTest(field=field):
                gates = self.load("reports/m2/probes/external-gates.json")
                gates["gates"][0][field] = replacement
                self.assert_rejected(validator.validate_external_gates, gates)

    def test_candidate_scope_is_default_deny(self):
        self.assertTrue(validator.is_allowed_candidate_path("reports/m2/probes/probe-results.json"))
        self.assertTrue(validator.is_allowed_candidate_path("workflow/queue/m2-b001-platform.json"))
        self.assertFalse(validator.is_allowed_candidate_path("game-package/lua/main.lua"))
        self.assertFalse(validator.is_allowed_candidate_path("workflow/queue/unrelated.json"))


if __name__ == "__main__":
    unittest.main()
