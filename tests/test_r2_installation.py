from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from tools import validate_m2_plan as plan

from tools.validate_r2_install import (
    DEFAULT_PACKAGE_ROOT,
    PROJECT_ROOT,
    validate_r2_install,
    _check_schemas_and_json,
    _check_runtime_diff,
    R2_AUTHORITY_SCHEMA_PATHS,
    UNREGISTERED_INTERFACE_ARTIFACTS,
    INTERFACE_COMPATIBILITY_ARTIFACTS,
    PUBLIC_BASELINE_CONTROL_ARTIFACTS,
)


class R2InterfaceAttachmentTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="r2-interface-attachment-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for relative in [*R2_AUTHORITY_SCHEMA_PATHS, *UNREGISTERED_INTERFACE_ARTIFACTS, *INTERFACE_COMPATIBILITY_ARTIFACTS, *PUBLIC_BASELINE_CONTROL_ARTIFACTS]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT_ROOT / relative, target)

    def errors(self):
        errors = []
        _check_schemas_and_json(self.root, errors)
        return errors

    def test_exact_attachment_uses_only_public_baseline_controls(self):
        batches = json.loads((self.root / ".codex/plans/m2-vertical-slice/batches.json").read_text())
        self.assertEqual([item["id"] for item in batches["batches"]],
                         [f"M2-B{number:03}" for number in range(1, 17)])
        self.assertEqual(self.errors(), [])

    def test_current_repository_uses_real_attachment_bytes(self):
        errors = []
        _check_schemas_and_json(PROJECT_ROOT, errors)
        self.assertEqual(errors, [])

    def test_absent_attachment_keeps_original_authority_set(self):
        for relative in UNREGISTERED_INTERFACE_ARTIFACTS:
            (self.root / relative).unlink()
        self.assertEqual(self.errors(), [])

    def test_each_artifact_requires_exact_regular_bytes(self):
        for relative in [*UNREGISTERED_INTERFACE_ARTIFACTS, *INTERFACE_COMPATIBILITY_ARTIFACTS, *PUBLIC_BASELINE_CONTROL_ARTIFACTS]:
            target = self.root / relative
            original = target.read_bytes()
            for kind in ("missing", "drift", "symlink"):
                with self.subTest(path=relative, kind=kind):
                    target.unlink()
                    if kind == "drift":
                        target.write_bytes(original + b" ")
                    elif kind == "symlink":
                        external = self.root / "same-bytes"
                        external.write_bytes(original)
                        target.symlink_to(external)
                    try:
                        self.assertTrue(any("R2_SCHEMA_ATTACHMENT" in error for error in self.errors()))
                    finally:
                        if target.exists() or target.is_symlink():
                            target.unlink()
                        target.write_bytes(original)

    def test_current_validator_sentinel_cannot_select_history(self):
        target = self.root / "tests/m2/probes/validate_r2_int_010_platform_identity_rebind.py"
        current = target.read_text()
        needle = "    archive = archive_observation if archive_observation is not None else validate_platform_archive()"
        self.assertIn(needle, current)
        target.write_text(current.replace(needle, '    raise RebindValidationError("PUBLIC_EXPORT_CURRENT_VALIDATOR_SENTINEL")\n' + needle, 1))
        self.assertTrue(any("artifact byte drift: tests/m2/probes/validate_r2_int_010_platform_identity_rebind.py" in error for error in self.errors()))

    def test_other_extra_schema_is_rejected(self):
        extra = self.root / "schemas/r2/other.schema.json"
        extra.write_text(json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema",
                                     "$id": "urn:test:other", "type": "object"}))
        self.assertTrue(any("authoritative schema set drift" in error for error in self.errors()))

    def test_same_count_authority_replacement_is_rejected(self):
        (self.root / "schemas/r2/region-v1.schema.json").rename(self.root / "schemas/r2/replacement.schema.json")
        self.assertTrue(any("authoritative schema set drift" in error for error in self.errors()))

    def test_unregistered_schema_still_receives_meta_validation(self):
        target = self.root / "schemas/r2/exemption-protocol-v1.schema.json"
        schema = json.loads(target.read_text())
        schema["type"] = "not-a-json-type"
        target.write_text(json.dumps(schema))
        errors = self.errors()
        self.assertTrue(any("R2_SCHEMA_ATTACHMENT" in error for error in errors))
        self.assertTrue(any("R2_SCHEMA_META" in error for error in errors))


class R2InstallationValidationTests(unittest.TestCase):
    def test_repository_native_r2_validation_passes(self) -> None:
        self.assertEqual(validate_r2_install(PROJECT_ROOT, DEFAULT_PACKAGE_ROOT), [])

    def test_all_role_route_requests_are_persisted(self) -> None:
        expected = {
            "r2-authority-install-plan-request.json": "PLAN",
            "r2-authority-install-implement-request.json": "IMPLEMENT",
            "r2-authority-install-accept-request.json": "ACCEPT",
            "r2-authority-install-repair-request.json": "REPAIR",
        }
        for name, mode in expected.items():
            request = json.loads((PROJECT_ROOT / ".codex/routes" / name).read_text(encoding="utf-8"))
            self.assertEqual(request["mode"], mode)
            self.assertEqual(request["milestone"], "M1")
            self.assertEqual(request["batch_id"], "M1-B002")


class R2InstallationNegativeProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="r2-install-negative-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        shutil.copytree(
            PROJECT_ROOT,
            self.root,
            ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
        )

    def errors(self) -> list[str]:
        return validate_r2_install(self.root, DEFAULT_PACKAGE_ROOT)

    def assert_rejected_with(self, marker: str) -> None:
        errors = self.errors()
        self.assertTrue(errors, "negative probe was unexpectedly accepted")
        self.assertTrue(
            any(marker in error for error in errors),
            f"expected marker {marker!r}; errors={errors}",
        )

    def test_deleted_decision_is_rejected(self) -> None:
        path = self.root / "governance/r2/decisions.r2.yaml"
        text = path.read_text(encoding="utf-8")
        start = text.index("- decision_id: R2-A01\n")
        end = text.index("- decision_id: R2-A02\n")
        path.write_text(text[:start] + text[end:], encoding="utf-8", newline="\n")
        self.assert_rejected_with("R2_DECISION_COUNT_191")

    def test_duplicate_decision_id_is_rejected(self) -> None:
        path = self.root / "governance/r2/decisions.r2.yaml"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("- decision_id: R2-A02", "- decision_id: R2-A01", 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_rejected_with("R2_DECISION_IDS_UNIQUE")

    def test_duplicate_section_id_is_rejected(self) -> None:
        path = self.root / "docs/authority/r2/00_R2_AUTHORITY_ENTRY.md"
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n<!-- SECTION-ID: R2-AUTH-ENTRY -->\n# duplicate probe\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assert_rejected_with("R2_SECTION_IDS_UNIQUE")

    def test_broken_json_schema_is_rejected(self) -> None:
        path = self.root / "schemas/r2/region-v1.schema.json"
        path.write_text("{\n", encoding="utf-8", newline="\n")
        self.assert_rejected_with("R2_SCHEMA")

    def test_deleted_traceability_item_is_rejected(self) -> None:
        path = self.root / "governance/r2/traceability-matrix.r2.yaml"
        text = path.read_text(encoding="utf-8")
        start = text.index("- decision_id: R2-A01\n")
        end = text.index("- decision_id: R2-A02\n")
        path.write_text(text[:start] + text[end:], encoding="utf-8", newline="\n")
        self.assert_rejected_with("R2_TRACEABILITY_191_OF_191")

    def test_truth_bible_runtime_leak_is_rejected(self) -> None:
        path = self.root / "game-package/manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["content"]["r2_truth_source"] = "authoring/story/01_TRUTH_BIBLE.md"
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assert_rejected_with("RUNTIME_BOUNDARY")

    def test_deleted_safety_stage_is_rejected(self) -> None:
        path = self.root / "governance/r2/content-safety-policy.r2.yaml"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("- build\n", "", 1), encoding="utf-8", newline="\n")
        self.assert_rejected_with("R2_CONTENT_SAFETY")

    def test_merged_canonical_section_deletion_and_word_change_are_rejected(self) -> None:
        path = self.root / "authoring/story/00_STORY_BIBLE.md"
        original = path.read_text(encoding="utf-8")
        probes = {
            "deleted line": ("- 世界通过规则勉强维持自身；\n", ""),
            "changed word": ("因果公平", "绝对公平"),
        }
        for label, (before, after) in probes.items():
            with self.subTest(label=label):
                self.assertIn(before, original)
                path.write_text(
                    original.replace(before, after, 1),
                    encoding="utf-8",
                    newline="\n",
                )
                self.assert_rejected_with("MERGE_INTO_EXISTING: canonical R2 section missing")

    def test_normalized_install_canonical_deletion_and_word_change_are_rejected(self) -> None:
        path = self.root / ".codex/prompts/r2/R2-AUTHORITY-INSTALL/IMPLEMENT.md"
        original = path.read_text(encoding="utf-8")
        probes = {
            "deleted line": ("- 未决数值。\n", ""),
            "changed word": ("只实现已冻结的R2权威安装批次", "任意修改R2权威安装批次"),
        }
        for label, (before, after) in probes.items():
            with self.subTest(label=label):
                self.assertIn(before, original)
                path.write_text(
                    original.replace(before, after, 1),
                    encoding="utf-8",
                    newline="\n",
                )
                self.assert_rejected_with("INSTALL_CANONICAL: normalized byte mismatch")


class R2RuntimeCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="r2-runtime-compatibility-")
        self.addCleanup(temporary.cleanup)
        self.temporary = Path(temporary.name)
        self.root = self.temporary / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "core.filemode", "true")
        self.git("config", "core.autocrlf", "false")
        self.write("baseline.txt", "pinned test baseline\n")
        self.write("legacy.lua", "return {}\n")
        self.write("game-package/manifest.json", "{}\n")
        self.write("dist/baseline.txt", "unchanged\n")
        self.write("TRPG_PLATFORM/baseline.txt", "unchanged\n")
        self.git("add", "--all")
        self.git(
            "-c", "user.name=R2 Runtime Test",
            "-c", "user.email=r2-runtime-test@example.invalid",
            "-c", "commit.gpgsign=false",
            "-c", "core.hooksPath=" + str(self.temporary / "no-hooks"),
            "commit", "-qm", "pinned runtime test baseline",
        )
        self.baseline = self.git("rev-parse", "HEAD").strip()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def write(self, relative: str, text: str = "return {}\n") -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def pair(self) -> tuple[str, str]:
        return (
            "platform-validation/task-prefix/lua/main.lua",
            "platform-validation/task-prefix/lua/task_prefix.lua",
        )

    def add_pair(self) -> None:
        for relative in self.pair():
            self.write(relative)
        self.git("add", "--", *self.pair())

    def reset(self) -> None:
        # This is exclusively the test's newly created temporary repository.
        self.git("reset", "--hard", self.baseline)

    def errors(self, pinned_source: str | None = None) -> list[str]:
        errors: list[str] = []
        # Only the baseline constant is injected. Diff, filesystem and path
        # handling execute against the real temporary Git repository.
        with patch("tools.validate_r2_install.PINNED_SOURCE_COMMIT", pinned_source or self.baseline):
            _check_runtime_diff(self.root, errors)
        return errors

    def assert_rejected(self, marker: str = "RUNTIME_UNCHANGED") -> None:
        errors = self.errors()
        self.assertTrue(any(marker in error for error in errors), errors)

    def test_unchanged_pinned_baseline_without_pair_is_allowed(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_nonruntime_document_change_without_pair_is_allowed(self) -> None:
        self.write("notes.txt", "installation-only change\n")
        self.git("add", "--", "notes.txt")
        self.assertEqual(self.errors(), [])

    def test_complete_regular_pair_is_allowed(self) -> None:
        self.add_pair()
        self.assertEqual(self.errors(), [])

    def test_complete_pair_content_is_not_frozen(self) -> None:
        self.add_pair()
        self.write(self.pair()[1], "return {compatible = true}\n")
        self.assertEqual(self.errors(), [])

    def test_each_incomplete_pair_is_rejected(self) -> None:
        for relative in self.pair():
            with self.subTest(path=relative):
                self.write(relative)
                self.git("add", "--", relative)
                self.assert_rejected("incomplete platform-validation Lua pair")
                self.reset()

    def test_removing_one_member_of_pair_is_rejected(self) -> None:
        for relative in self.pair():
            with self.subTest(path=relative):
                self.add_pair()
                (self.root / relative).unlink()
                self.git("add", "--all")
                self.assert_rejected("incomplete platform-validation Lua pair")
                self.reset()

    def test_extra_lua_paths_are_rejected(self) -> None:
        for relative in (
            "platform-validation/task-prefix/lua/extra.lua",
            "platform-validation/other.lua",
            "elsewhere/extra.lua",
        ):
            with self.subTest(path=relative):
                self.add_pair()
                self.write(relative)
                self.git("add", "--", relative)
                self.assert_rejected("forbidden source-to-candidate changes")
                self.reset()

    def test_legacy_runtime_destination_changes_are_rejected(self) -> None:
        for relative in (
            "game-package/manifest.json",
            "game-package/package.lock.json",
            "game-package/new-content.txt",
            "dist/baseline.txt",
            "TRPG_PLATFORM/baseline.txt",
        ):
            with self.subTest(path=relative):
                self.add_pair()
                self.write(relative, "changed\n")
                self.git("add", "--", relative)
                self.assert_rejected("forbidden source-to-candidate changes")
                self.reset()

    def test_legacy_lua_edit_or_deletion_is_rejected(self) -> None:
        for operation in ("edit", "delete"):
            with self.subTest(operation=operation):
                self.add_pair()
                if operation == "edit":
                    self.write("legacy.lua", "return {changed = true}\n")
                else:
                    (self.root / "legacy.lua").unlink()
                self.git("add", "--all")
                self.assert_rejected("forbidden source-to-candidate changes")
                self.reset()

    def test_legacy_lua_rename_is_rejected(self) -> None:
        self.add_pair()
        self.git("mv", "--", "legacy.lua", "retired.txt")
        self.assert_rejected("forbidden source-to-candidate changes")

    def test_symlinked_pair_leaves_are_rejected(self) -> None:
        external = self.temporary / "external.lua"
        external.write_text("return {}\n", encoding="utf-8")
        for relative in self.pair():
            for destination in (external, self.temporary / "missing.lua"):
                with self.subTest(path=relative, destination=destination.name):
                    self.add_pair()
                    target = self.root / relative
                    target.unlink()
                    target.symlink_to(destination)
                    self.git("add", "--", relative)
                    self.assert_rejected("regular non-executable file")
                    self.reset()

    def test_symlinked_pair_ancestors_are_rejected(self) -> None:
        for number, relative in enumerate((
            "platform-validation",
            "platform-validation/task-prefix",
            "platform-validation/task-prefix/lua",
        )):
            with self.subTest(ancestor=relative):
                self.add_pair()
                ancestor = self.root / relative
                external = self.temporary / f"external-directory-{number}"
                ancestor.rename(external)
                ancestor.symlink_to(external, target_is_directory=True)
                self.git("add", "--all")
                self.assert_rejected("non-symlink directory")
                self.reset()

    def test_each_execute_permission_on_pair_is_rejected(self) -> None:
        for relative in self.pair():
            for execute_bit in (0o100, 0o010, 0o001):
                with self.subTest(path=relative, execute_bit=execute_bit):
                    self.add_pair()
                    (self.root / relative).chmod(0o600 | execute_bit)
                    self.assert_rejected("regular non-executable file")
                    self.reset()

    def test_nonregular_pair_leaves_are_rejected(self) -> None:
        for relative in self.pair():
            for kind in ("directory", "fifo"):
                with self.subTest(path=relative, kind=kind):
                    self.add_pair()
                    target = self.root / relative
                    target.unlink()
                    if kind == "directory":
                        target.mkdir()
                    else:
                        os.mkfifo(target)
                    try:
                        self.assert_rejected()
                    finally:
                        if kind == "directory":
                            target.rmdir()
                        else:
                            target.unlink()
                        self.reset()

    def test_ambiguous_extra_paths_cannot_impersonate_pair(self) -> None:
        for relative in (
            "prefix\nplatform-validation/task-prefix/lua/main.lua",
            " platform-validation/task-prefix/lua/main.lua",
            "\tplatform-validation/task-prefix/lua/task_prefix.lua",
            "platform-validation/task-prefix/lua/main.lua ",
            "platform-validation/task-prefix/lua/main.lua\n",
            "platform-validation/task-prefix/lua/main.lua\nnot-lua.txt",
        ):
            with self.subTest(path=relative):
                self.add_pair()
                self.write(relative)
                self.git("add", "--", relative)
                self.assert_rejected("forbidden source-to-candidate changes")
                self.reset()

    def test_failed_pinned_source_comparison_is_rejected(self) -> None:
        self.add_pair()
        errors = self.errors("0" * 40)
        self.assertTrue(any("cannot diff pinned source" in error for error in errors), errors)



class R2NativeSourceTransitionTests(unittest.TestCase):
    """Real signed public objects; fault probes never mock Git or signatures."""
    real_root = Path(__file__).resolve().parents[1]

    def fixture(self) -> Path:
        proof = plan._native_consumer_revision(self.real_root)
        self.assertIsNotNone(proof)
        self.assertIsNotNone(proof["r2_revision"])
        temporary = tempfile.TemporaryDirectory(prefix="r2-native-source-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "repo"
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
                        str(self.real_root), str(root)], check=True, capture_output=True)
        self.git(root, "checkout", "--quiet", "--detach", proof["head"])
        return root

    def git(self, root: Path, *args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE,
                                       env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"})

    def commit(self, root: Path, paths: list[str], message: str) -> str:
        self.git(root, "add", "--", *paths)
        self.git(root, "-c", "user.name=R2 Source Test", "-c", "user.email=r2-source-test@example.invalid",
                 "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + str(root / ".git/no-hooks"),
                 "commit", "--quiet", "-m", message)
        return self.git(root, "rev-parse", "HEAD").decode().strip()

    def recreated(self, root: Path, tree: str, parent: str) -> str:
        return self.git(root, "-c", "user.name=R2 Source Test", "-c", "user.email=r2-source-test@example.invalid",
                        "-c", "commit.gpgsign=false", "commit-tree", tree, "-p", parent,
                        "-m", "Unsigned R2 source fault probe").decode().strip()

    def test_bound_transition_keeps_five_path_api_and_complete_preserved_inventory(self) -> None:
        root = self.fixture()
        proof = plan._native_consumer_revision(root)
        self.assertEqual(set(proof["expected"]), set(plan.NATIVE_CONSUMER_PATHS))
        self.assertEqual(set(proof["current_sha256"]), set(plan.NATIVE_CONSUMER_PATHS))
        self.assertEqual(set(proof["r2_revision"]["expected"]), set(plan.NATIVE_R2_PATHS[1:]))
        preserved = plan._native_preserved_entries(root)
        original = plan._native_tree_entries(root, plan.NATIVE_CONSUMER_BASE["commit"])
        self.assertEqual(preserved, {path: entry for path, entry in original.items()
                                   if path not in plan.NATIVE_CONSUMER_PATHS and path not in plan.SUFFIX_CONTROL_PATHS})
        self.assertTrue(set(plan.NATIVE_R2_PATHS[1:]).issubset(preserved))
        for relative in plan.NATIVE_R2_PATHS[1:]:
            old = self.git(root, "show", plan.NATIVE_R2_BASE["commit"] + ":" + relative)
            self.assertTrue(plan._current_pin_matches(root, relative, hashlib.sha256(old).hexdigest()))
        plan._native_receipt_candidate(root, proof["head"],
                                       {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in preserved})

    def test_pretransition_source_retains_original_reader_and_r2_bytes(self) -> None:
        root = self.fixture()
        self.git(root, "checkout", "--quiet", "--detach", plan.NATIVE_R2_BASE["commit"])
        proof = plan._native_consumer_revision(root)
        self.assertIsNone(proof["r2_revision"])
        self.assertEqual(set(proof["expected"]), set(plan.NATIVE_CONSUMER_PATHS))
        for relative in plan.NATIVE_R2_PATHS:
            self.assertEqual((root / relative).read_bytes(),
                             self.git(root, "show", plan.NATIVE_R2_BASE["commit"] + ":" + relative))

    def test_fixed_source_additions_keep_separate_complete_preservation(self) -> None:
        root = self.fixture()
        proof = plan._native_consumer_revision(root)
        fixed = plan._native_tree_entries(root, plan.NATIVE_R2_BASE["commit"])
        old = plan._native_tree_entries(root, plan.NATIVE_CONSUMER_BASE["commit"])
        self.assertEqual(proof["r2_revision"]["preserved_entries"],
                         {path: entry for path, entry in fixed.items() if path not in old})
        self.assertEqual(len(proof["r2_revision"]["preserved_entries"]), 11)

    def test_each_fixed_source_addition_rejects_bytes_execute_modes_missing_and_links(self) -> None:
        root = self.fixture()
        preserved = plan._native_consumer_revision(root)["r2_revision"]["preserved_entries"]
        for relative in preserved:
            path = root / relative; raw, mode = path.read_bytes(), path.stat().st_mode
            for fault in ("bytes", "execute", "missing", "symlink"):
                with self.subTest(path=relative, fault=fault):
                    try:
                        if fault == "bytes": path.write_bytes(raw + b"\n")
                        elif fault == "execute": path.chmod(mode | 0o111)
                        elif fault == "missing": path.unlink()
                        else:
                            path.unlink(); path.symlink_to("missing-public-source-fault-probe")
                        with self.assertRaises((ValueError, OSError)):
                            plan._native_consumer_revision(root)
                    finally:
                        if path.is_symlink(): path.unlink()
                        path.write_bytes(raw); path.chmod(mode)

    def test_each_fixed_source_addition_rejects_staged_execute_modes(self) -> None:
        root = self.fixture()
        preserved = plan._native_consumer_revision(root)["r2_revision"]["preserved_entries"]
        for relative in preserved:
            with self.subTest(path=relative):
                try:
                    self.git(root, "update-index", "--chmod=+x", "--", relative)
                    with self.assertRaisesRegex(ValueError, "staged or uncommitted change"):
                        plan._native_consumer_revision(root)
                finally:
                    self.git(root, "update-index", "--chmod=-x", "--", relative)

    def test_fixed_source_addition_touch_and_revert_is_rejected(self) -> None:
        root = self.fixture()
        relative = next(iter(plan._native_consumer_revision(root)["r2_revision"]["preserved_entries"]))
        path = root / relative; raw = path.read_bytes()
        for value, message in ((raw + b"\n", "touch"), (raw, "restore")):
            path.write_bytes(value)
            self.commit(root, [relative], "Fixed public source " + message + " fault probe")
        self.assertEqual(path.read_bytes(), raw)
        with self.assertRaisesRegex(ValueError, "preserved input history touched/reverted"):
            plan._native_consumer_revision(root)

    def test_malformed_r2_parent_tree_hash_or_artifact_set_is_rejected(self) -> None:
        root = self.fixture()
        faults = [lambda r: r.update(parent={"commit": "0" * 40, "tree": "0" * 40}),
                  lambda r: r.update(tree="0" * 40),
                  lambda r: r["artifacts"].update({plan.NATIVE_R2_PATHS[1]: "0" * 64}),
                  lambda r: r["artifacts"].pop(plan.NATIVE_R2_PATHS[2]),
                  lambda r: r["artifacts"].update({"tools/future-r2-reader.py": "0" * 64}),
                  lambda r: r.update(commit="future")]
        for fault in faults:
            revision = copy.deepcopy(plan.NATIVE_R2_REVISION)
            fault(revision)
            with self.subTest(revision=revision), patch.object(plan, "NATIVE_R2_REVISION", revision):
                with self.assertRaises(ValueError):
                    plan._native_consumer_revision(root)

    def test_missing_r2_binding_descriptor_is_rejected(self) -> None:
        root = self.fixture()
        with patch.object(plan, "NATIVE_R2_REVISION", None):
            with self.assertRaisesRegex(ValueError, "native R2 binding missing"):
                plan._native_consumer_revision(root)

    def test_implementation_without_its_binding_is_rejected(self) -> None:
        root = self.fixture()
        self.git(root, "checkout", "--quiet", "--detach", plan.NATIVE_R2_REVISION["commit"])
        with self.assertRaisesRegex(ValueError, "native R2 binding missing"):
            plan._native_consumer_revision(root)

    def test_recreated_unsigned_r2_implementation_and_wrong_parent_are_rejected(self) -> None:
        for wrong_parent in (False, True):
            root = self.fixture()
            revision = copy.deepcopy(plan.NATIVE_R2_REVISION)
            parent = (self.git(root, "rev-parse", plan.NATIVE_R2_BASE["commit"] + "^").decode().strip()
                      if wrong_parent else plan.NATIVE_R2_BASE["commit"])
            candidate = self.recreated(root, revision["tree"], parent)
            self.git(root, "checkout", "--quiet", "--detach", candidate)
            revision["commit"] = candidate
            diagnostic = "sole parent mismatch" if wrong_parent else "signature verification failed"
            with self.subTest(wrong_parent=wrong_parent), patch.object(plan, "NATIVE_R2_REVISION", revision):
                with self.assertRaisesRegex(ValueError, diagnostic):
                    plan._native_consumer_revision(root)

    def test_r2_implementation_with_an_extra_path_is_rejected(self) -> None:
        root = self.fixture()
        revision = copy.deepcopy(plan.NATIVE_R2_REVISION)
        self.git(root, "checkout", "--quiet", "--detach", revision["commit"])
        marker = root / "r2-extra-source-fault.txt"
        marker.write_text("Extra path fault probe\n", encoding="utf-8")
        self.git(root, "add", "--", marker.name)
        tree = self.git(root, "write-tree").decode().strip()
        candidate = self.recreated(root, tree, plan.NATIVE_R2_BASE["commit"])
        self.git(root, "checkout", "--quiet", "--detach", candidate)
        revision.update(commit=candidate, tree=tree)
        with patch.object(plan, "NATIVE_R2_REVISION", revision):
            with self.assertRaisesRegex(ValueError, "exact three-path boundary mismatch"):
                plan._native_consumer_revision(root)

    def test_unsigned_r2_binding_is_rejected(self) -> None:
        root = self.fixture()
        proof = plan._native_consumer_revision(root)
        tree = self.git(root, "rev-parse", proof["binding_commit"] + "^{tree}").decode().strip()
        candidate = self.recreated(root, tree, plan.NATIVE_R2_REVISION["commit"])
        self.git(root, "checkout", "--quiet", "--detach", candidate)
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            plan._native_consumer_revision(root)

    def test_r2_binding_requires_an_immediate_sole_parent(self) -> None:
        root = self.fixture()
        proof = plan._native_consumer_revision(root)
        implementation = plan.NATIVE_R2_REVISION
        intervening = self.recreated(root, implementation["tree"], implementation["commit"])
        tree = self.git(root, "rev-parse", proof["binding_commit"] + "^{tree}").decode().strip()
        candidate = self.recreated(root, tree, intervening)
        self.git(root, "checkout", "--quiet", "--detach", candidate)
        with self.assertRaisesRegex(ValueError, "native R2 binding sole parent mismatch"):
            plan._native_consumer_revision(root)

    def test_r2_binding_cannot_change_any_other_path(self) -> None:
        root = self.fixture()
        marker = root / "r2-extra-binding-fault.txt"
        marker.write_text("Extra binding path fault probe\n", encoding="utf-8")
        self.git(root, "add", "--", marker.name)
        tree = self.git(root, "write-tree").decode().strip()
        candidate = self.recreated(root, tree, plan.NATIVE_R2_REVISION["commit"])
        self.git(root, "checkout", "--quiet", "--detach", candidate)
        with self.assertRaisesRegex(ValueError, "native R2 binding changed other paths"):
            plan._native_consumer_revision(root)

    def test_unknown_branch_cannot_borrow_the_r2_source_descriptor(self) -> None:
        root = self.fixture()
        self.git(root, "checkout", "--quiet", "--detach", plan.NATIVE_R2_BASE["commit"])
        marker = root / "unknown-r2-source-fault.txt"
        marker.write_text("Unknown source fault probe\n", encoding="utf-8")
        self.commit(root, [marker.name], "Unknown public source transition fault probe")
        with self.assertRaisesRegex(ValueError, "unknown source transition"):
            plan._native_consumer_revision(root)

    def test_current_r2_bytes_execute_bits_missing_and_symlink_leaves_are_rejected(self) -> None:
        root = self.fixture()
        for relative in plan.NATIVE_R2_PATHS[1:]:
            path = root / relative
            raw, mode = path.read_bytes(), path.stat().st_mode
            for fault in ("bytes", "user-execute", "group-execute", "other-execute", "missing", "symlink"):
                with self.subTest(path=relative, fault=fault):
                    try:
                        if fault == "bytes": path.write_bytes(raw + b"\n")
                        elif fault == "missing": path.unlink()
                        elif fault == "symlink":
                            path.unlink(); path.symlink_to("missing-r2-fault-probe")
                        else: path.chmod(mode | {"user-execute": 0o100, "group-execute": 0o010, "other-execute": 0o001}[fault])
                        with self.assertRaises((ValueError, OSError)):
                            plan._native_consumer_revision(root)
                    finally:
                        if path.is_symlink(): path.unlink()
                        path.write_bytes(raw); path.chmod(mode)

    def test_staged_r2_execute_modes_are_rejected(self) -> None:
        root = self.fixture()
        for relative in plan.NATIVE_R2_PATHS[1:]:
            with self.subTest(path=relative):
                try:
                    self.git(root, "update-index", "--chmod=+x", "--", relative)
                    with self.assertRaisesRegex(ValueError, "staged or uncommitted change"):
                        plan._native_consumer_revision(root)
                finally:
                    self.git(root, "update-index", "--chmod=-x", "--", relative)

    def test_each_r2_file_touch_and_revert_is_rejected(self) -> None:
        for relative in plan.NATIVE_R2_PATHS[1:]:
            root = self.fixture()
            path = root / relative; raw = path.read_bytes()
            for value, message in ((raw + b"\n", "touch"), (raw, "restore")):
                path.write_bytes(value)
                self.commit(root, [relative], "R2 source " + message + " fault probe")
            self.assertEqual(path.read_bytes(), raw)
            with self.subTest(path=relative), self.assertRaisesRegex(ValueError, "code history touched/reverted"):
                plan._native_consumer_revision(root)

    def test_unknown_r2_pin_and_borrowed_historical_candidate_are_rejected(self) -> None:
        root = self.fixture()
        for relative in plan.NATIVE_R2_PATHS[1:]:
            with self.subTest(path=relative):
                self.assertFalse(plan._current_pin_matches(root, relative, "0" * 64))
                with self.assertRaisesRegex(ValueError, "unknown R2 preserved pin"):
                    plan._native_receipt_candidate(root, self.git(root, "rev-parse", "HEAD").decode().strip(),
                                                   {relative: "0" * 64})
        old_pins = {relative: hashlib.sha256(self.git(root, "show", plan.NATIVE_R2_BASE["commit"] + ":" + relative)).hexdigest()
                    for relative in plan.NATIVE_R2_PATHS[1:]}
        with self.assertRaises(subprocess.CalledProcessError):
            plan._native_receipt_candidate(root, plan.NATIVE_R2_BASE["commit"], old_pins)


if __name__ == "__main__":
    unittest.main()
