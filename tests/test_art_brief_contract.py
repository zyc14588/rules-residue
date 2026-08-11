import re
import unittest

from tools.lib.common import PROJECT_ROOT


class ArtBriefContractTests(unittest.TestCase):
    def setUp(self) -> None:
        briefs_root = PROJECT_ROOT / "authoring" / "art" / "briefs"
        self.readme = (briefs_root / "README.md").read_text(encoding="utf-8")
        self.template = (briefs_root / "_template" / "ART_BRIEF.md").read_text(
            encoding="utf-8"
        )

    def test_readme_required_fields_equal_template_top_level_fields(self) -> None:
        match = re.search(
            r"<!-- art-brief-required-fields:start -->(.*?)"
            r"<!-- art-brief-required-fields:end -->",
            self.readme,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "README required-field contract block is missing")
        assert match is not None
        declared = set(re.findall(r"`([a-z][a-z0-9_]*)`", match.group(1)))
        templated = set(
            re.findall(r"^([a-z][a-z0-9_]*):", self.template, flags=re.MULTILINE)
        )
        self.assertEqual(declared, templated)

    def test_originality_contract_is_explicit(self) -> None:
        for requirement in (
            "必须为本项目原创内容",
            "不得直接复制任何第三方作品",
            "不得仿制受保护角色、Logo、界面或具体作品资产",
            "非复制性的风格或事实参考",
            "provenance 政策记录",
        ):
            self.assertIn(requirement, self.template)

    def test_provenance_contract_uses_project_standard_and_required_fields(self) -> None:
        self.assertIn("standard: docs/operations/ART_PROVENANCE.md", self.template)
        self.assertIn("provenance_required: true", self.template)
        for field in (
            "tool",
            "model_or_version",
            "generation_method",
            "prompt_summary",
            "source_or_reference_summary",
            "human_edits",
            "final_file_hash",
            "rights_status",
            "review_status",
        ):
            self.assertRegex(
                self.template,
                re.compile(rf"^    {field}:", flags=re.MULTILINE),
            )
            self.assertIn(f"`{field}`", self.readme)


if __name__ == "__main__":
    unittest.main()
