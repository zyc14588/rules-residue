from __future__ import annotations

import json
import shutil
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.validate_r2_install import (
    DEFAULT_PACKAGE_ROOT,
    PROJECT_ROOT,
    validate_r2_install,
    _check_schemas_and_json,
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


if __name__ == "__main__":
    unittest.main()
