import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.lib.common import PROJECT_ROOT, read_json, write_json
from tools.validate_opencode_task import (
    REFUSAL_STATUS,
    validate_opencode_task_packet,
)
from tools.validate_project import validate_originality


class OriginalityRecoveryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.project_root = Path(self._temporary_directory.name) / "project"
        self.game_package_root = self.project_root / "game-package"
        (self.project_root / "authoring").mkdir(parents=True)
        self.game_package_root.mkdir(parents=True)

    def _validate(self) -> list[str]:
        return validate_originality(self.project_root, self.game_package_root)

    def test_knowledge_source_fails_until_removed(self) -> None:
        self.assertEqual(self._validate(), [])

        knowledge = self.project_root / "knowledge"
        knowledge.mkdir()
        (knowledge / "external-case-notes.md").write_text(
            "unapproved external research material\n",
            encoding="utf-8",
        )
        errors = self._validate()
        self.assertTrue(
            any("unapproved top-level content source directory: knowledge/" in error for error in errors),
            errors,
        )

        shutil.rmtree(knowledge)
        self.assertEqual(self._validate(), [])

    def test_authoring_and_game_package_are_both_scanned(self) -> None:
        for relative in ("authoring", "game-package"):
            with self.subTest(relative=relative):
                candidate = self.project_root / relative / "unapproved.txt"
                candidate.write_text("Chaosium\n", encoding="utf-8")
                errors = self._validate()
                self.assertTrue(
                    any(error.startswith(f"{relative}/unapproved.txt:") for error in errors),
                    errors,
                )
                candidate.unlink()
                self.assertEqual(self._validate(), [])


class OpenCodeTaskPacketRecoveryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = read_json(PROJECT_ROOT / "workflow/examples/task-0001.json")

    def assert_refused(self, errors: list[str], reason: str) -> None:
        self.assertTrue(errors, "expected OpenCode Task Packet gate to refuse")
        self.assertTrue(all(error.startswith(REFUSAL_STATUS) for error in errors), errors)
        self.assertTrue(any(reason in error for error in errors), errors)

    def test_valid_script_packet_and_allowed_target_pass(self) -> None:
        self.assertEqual(
            validate_opencode_task_packet(
                self.packet,
                ["game-package/scripts/plan_action.lua"],
            ),
            [],
        )

    def test_cli_reports_pass_for_script_and_refuses_default_deny_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            packet_path = Path(directory) / "packet.json"
            write_json(packet_path, self.packet)
            command = [
                sys.executable,
                "tools/validate_opencode_task.py",
                "--packet",
                str(packet_path),
                "--target",
                "game-package/scripts/plan_action.lua",
            ]
            accepted = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            self.assertEqual(accepted.stdout.strip(), "OPENCODE_TASK_PACKET: PASS")

            refused_packet = copy.deepcopy(self.packet)
            refused_packet["allowed_paths"] = ["README.md"]
            write_json(packet_path, refused_packet)
            refused_command = command[:-1] + ["README.md"]
            refused = subprocess.run(
                refused_command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
            self.assertIn(REFUSAL_STATUS, refused.stdout)
            self.assertNotIn("OPENCODE_TASK_PACKET: PASS", refused.stdout)

    def test_recursive_lua_glob_allows_direct_and_nested_scripts(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["allowed_paths"] = ["game-package/scripts/**/*.lua"]
        self.assertEqual(
            validate_opencode_task_packet(
                packet,
                [
                    "game-package/scripts/plan_action.lua",
                    "game-package/scripts/lib/check.lua",
                ],
            ),
            [],
        )

    def test_single_star_glob_does_not_authorize_nested_scripts(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["allowed_paths"] = ["game-package/scripts/*.lua"]

        self.assertEqual(
            validate_opencode_task_packet(
                packet,
                ["game-package/scripts/plan_action.lua"],
            ),
            [],
        )
        errors = validate_opencode_task_packet(
            packet,
            ["game-package/scripts/lib/check.lua"],
        )
        self.assert_refused(errors, "outside allowed_paths")

    def test_authorized_fixture_target_passes(self) -> None:
        self.assertEqual(
            validate_opencode_task_packet(
                self.packet,
                ["game-package/tests/fixtures/valid_action.json"],
            ),
            [],
        )

    def test_missing_task_packet_is_refused(self) -> None:
        errors = validate_opencode_task_packet(
            None,
            ["game-package/scripts/plan_action.lua"],
        )
        self.assert_refused(errors, "no Task Packet")

    def test_non_opencode_owner_is_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["owner"] = "codex"
        errors = validate_opencode_task_packet(
            packet,
            ["game-package/scripts/plan_action.lua"],
        )
        self.assert_refused(errors, 'owner must equal "opencode"')

    def test_non_script_task_is_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["task_type"] = "spec"
        errors = validate_opencode_task_packet(
            packet,
            ["game-package/scripts/plan_action.lua"],
        )
        self.assert_refused(errors, 'task_type must equal "script"')

    def test_literary_task_and_authoring_target_remain_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["task_type"] = "literary"
        packet["allowed_paths"] = ["authoring/story/draft.md"]
        errors = validate_opencode_task_packet(packet, ["authoring/story/draft.md"])
        self.assert_refused(errors, 'task_type must equal "script"')
        self.assertTrue(any("forbidden" in error or "positive authority" in error for error in errors), errors)

    def test_target_outside_allowed_paths_is_refused(self) -> None:
        errors = validate_opencode_task_packet(
            self.packet,
            ["tests/test_hybrid_workflow.py"],
        )
        self.assert_refused(errors, "outside the OpenCode positive authority")

    def test_authority_path_is_refused_even_if_packet_lists_it(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["allowed_paths"].append("authoring/**")
        errors = validate_opencode_task_packet(packet, ["authoring/story/01_TRUTH_BIBLE.md"])
        self.assert_refused(errors, "forbidden by RR-D023")

    def test_allowed_paths_are_default_deny(self) -> None:
        refused_paths = (
            "TRPG_PLATFORM/server.go",
            "tools/validate_project.py",
            "README.md",
            "docs/foo.md",
            "authoring/story/foo.md",
            "governance/decisions.json",
            "game-package/manifest.json",
            "game-package/schemas/foo.json",
        )
        for refused_path in refused_paths:
            with self.subTest(refused_path=refused_path):
                packet = copy.deepcopy(self.packet)
                packet["allowed_paths"] = [refused_path]
                errors = validate_opencode_task_packet(
                    packet,
                    ["game-package/scripts/plan_action.lua"],
                )
                self.assert_refused(errors, "allowed_paths[0]")
                self.assertTrue(
                    any("outside the OpenCode positive authority" in error for error in errors),
                    errors,
                )

    def test_absolute_and_parent_escape_allowed_paths_are_refused(self) -> None:
        for refused_path in ("/tmp/escape.lua", "../escape.lua", "C:/escape.lua"):
            with self.subTest(refused_path=refused_path):
                packet = copy.deepcopy(self.packet)
                packet["allowed_paths"] = [refused_path]
                errors = validate_opencode_task_packet(
                    packet,
                    ["game-package/scripts/plan_action.lua"],
                )
                self.assert_refused(errors, "escapes the project root")

    def test_absolute_and_parent_escape_targets_are_refused(self) -> None:
        for refused_path in ("/tmp/escape.lua", "../escape.lua", "C:/escape.lua"):
            with self.subTest(refused_path=refused_path):
                errors = validate_opencode_task_packet(self.packet, [refused_path])
                self.assert_refused(errors, "escapes the project root")

    def test_prefix_spoofing_is_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["allowed_paths"] = ["game-package/scripts-evil/**"]
        errors = validate_opencode_task_packet(
            packet,
            ["game-package/scripts-evil/file.lua"],
        )
        self.assert_refused(errors, "outside the OpenCode positive authority")

    def test_script_non_lua_target_is_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["allowed_paths"] = ["game-package/scripts/**"]
        errors = validate_opencode_task_packet(
            packet,
            ["game-package/scripts/README.md"],
        )
        self.assert_refused(errors, "not an authorized Lua/fixture file")

    def test_directory_authorization_is_normalized_and_stays_in_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory) / "project"
            (project_root / "game-package/scripts/scoped").mkdir(parents=True)
            (project_root / "game-package/tests/fixtures").mkdir(parents=True)
            packet = copy.deepcopy(self.packet)
            packet["allowed_paths"] = ["game-package/scripts/scoped/"]
            self.assertEqual(
                validate_opencode_task_packet(
                    packet,
                    ["game-package/scripts/scoped/new.lua"],
                    project_root=project_root,
                ),
                [],
            )

    def test_symlink_escape_is_refused_for_directory_and_actual_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            project_root = temporary_root / "project"
            scripts_root = project_root / "game-package/scripts"
            scripts_root.mkdir(parents=True)
            (project_root / "game-package/tests/fixtures").mkdir(parents=True)
            outside = temporary_root / "outside"
            outside.mkdir()
            escape_link = scripts_root / "escape"
            try:
                escape_link.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation unavailable on this platform: {exc}")

            directory_packet = copy.deepcopy(self.packet)
            directory_packet["allowed_paths"] = ["game-package/scripts/escape/"]
            directory_errors = validate_opencode_task_packet(
                directory_packet,
                ["game-package/scripts/escape/payload.lua"],
                project_root=project_root,
            )
            self.assert_refused(directory_errors, "escapes its OpenCode authority root")

            target_packet = copy.deepcopy(self.packet)
            target_packet["allowed_paths"] = ["game-package/scripts/**"]
            target_errors = validate_opencode_task_packet(
                target_packet,
                ["game-package/scripts/escape/payload.lua"],
                project_root=project_root,
            )
            self.assert_refused(target_errors, "via path resolution")

    def test_executor_prompt_requires_machine_gate_and_refusal(self) -> None:
        prompt = (PROJECT_ROOT / ".opencode/SCRIPT_TASK_PROMPT.md").read_text(encoding="utf-8")
        for marker in (
            "tools/validate_opencode_task.py",
            'owner == "opencode"',
            'task_type == "script"',
            "allowed_paths",
            "BLOCKED_NO_VALID_TASK_PACKET",
            "default-deny",
        ):
            self.assertIn(marker, prompt)


if __name__ == "__main__":
    unittest.main()
