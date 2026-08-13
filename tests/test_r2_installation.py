from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.validate_r2_install import (
    DEFAULT_PACKAGE_ROOT,
    PROJECT_ROOT,
    validate_r2_install,
)


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
