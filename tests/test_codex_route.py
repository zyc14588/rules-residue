from __future__ import annotations

import copy
import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.codex_route import (
    HARD_LIMIT,
    SOFT_LIMIT,
    RouteError,
    calculate_binding_digest,
    check_reading_map,
    generate_reading_map,
    write_reading_map,
)


R2_PACKAGE = Path(
    "/home/zyc14588/RULE_RESIDUAL_R2_AUTHORITY_AND_PROGRESSIVE_DELIVERY_v1.0.0"
)
R2_BASELINE = R2_PACKAGE / "00_BASELINE_AND_INTEGRATION" / "M1_BASELINE_BINDING.md"


class CodexRouteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="codex-route-test-")
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        self.document = self.root / "authority.md"
        self.document.write_text(
            "<!-- SECTION-ID: TEST-REQUIRED -->\n"
            "required content\n"
            "<!-- SECTION-ID: TEST-OPTIONAL -->\n"
            "optional content\n"
            "<!-- SECTION-ID: TEST-TAIL -->\n"
            "tail content\n",
            encoding="utf-8",
            newline="\n",
        )
        (self.root / ".gitignore").write_text(
            "/.codex/routes/generated/*.json\n",
            encoding="utf-8",
            newline="\n",
        )
        self.git("init", "-q")
        self.git("config", "user.name", "Codex Route Tests")
        self.git("config", "user.email", "codex-route@example.invalid")
        self.git("add", "authority.md", ".gitignore")
        self.git("commit", "-q", "-m", "baseline")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *arguments],
            capture_output=True,
            text=True,
            check=check,
        )

    def request(
        self,
        *,
        path: str = "authority.md",
        required: list[str] | None = None,
        optional: list[str] | None = None,
        capacity: int = 100_000,
    ) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "route_id": "TEST-CODEX-ROUTE",
            "mode": "IMPLEMENT",
            "milestone": "M1",
            "batch_id": "M1-B001",
            "capacity_bytes": capacity,
            "documents": [
                {
                    "path": path,
                    "required_sections": required
                    if required is not None
                    else ["TEST-REQUIRED"],
                    "optional_sections": optional if optional is not None else [],
                    "reason": "Exercise the exact routed Section contract.",
                }
            ],
            "forbidden_bulk_reads": ["docs/**", "authoring/**", "*"],
        }

    def generate(self, request: dict[str, object] | None = None) -> dict[str, object]:
        return generate_reading_map(request or self.request(), repo_root=self.root)

    def check_map(
        self,
        reading_map: dict[str, object],
        *,
        route_id: str = "TEST-CODEX-ROUTE",
        mode: str = "IMPLEMENT",
        milestone: str = "M1",
        batch_id: str = "M1-B001",
        allow_roots: tuple[Path, ...] = (),
    ) -> None:
        check_reading_map(
            reading_map,
            expected_route_id=route_id,
            expected_mode=mode,
            expected_milestone=milestone,
            expected_batch_id=batch_id,
            repo_root=self.root,
            allow_roots=allow_roots,
        )

    def assert_rejected(self, code: str, function, *args, **kwargs) -> RouteError:
        with self.assertRaises(RouteError) as raised:
            function(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception


class CodexRoutePositiveTests(CodexRouteTestCase):
    def test_valid_route_generate_and_check_passes(self) -> None:
        reading_map = self.generate()
        self.check_map(reading_map)
        self.assertEqual(reading_map["schema_version"], "1.0")
        self.assertEqual(reading_map["documents"][0]["sections"], ["TEST-REQUIRED"])
        self.assertRegex(reading_map["source_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(reading_map["source_tree"], r"^[0-9a-f]{40}$")

    def test_explicitly_approved_r2_package_external_root_passes(self) -> None:
        self.assertTrue(R2_BASELINE.is_file(), R2_BASELINE)
        request = self.request(
            path=str(R2_BASELINE),
            required=["R2-INTEGRATION-M1-BASELINE"],
        )
        reading_map = generate_reading_map(
            request,
            repo_root=self.root,
            allow_roots=(R2_PACKAGE,),
        )
        self.check_map(reading_map, allow_roots=(R2_PACKAGE,))
        self.assertEqual(reading_map["documents"][0]["path"], str(R2_BASELINE))

    def test_generated_reading_map_is_ignored_and_untracked(self) -> None:
        request_path = self.root / "request.json"
        request_path.write_text(json.dumps(self.request()), encoding="utf-8")
        output = self.root / ".codex" / "routes" / "generated" / "probe.json"
        write_reading_map(request_path, output, repo_root=self.root)
        self.assertTrue(output.is_file())
        tracked = self.git("ls-files", "--error-unmatch", output.relative_to(self.root).as_posix(), check=False)
        self.assertNotEqual(tracked.returncode, 0)
        status = self.git("status", "--short", "--", output.relative_to(self.root).as_posix())
        self.assertEqual(status.stdout, "")


class CodexRouteNegativeProbeTests(CodexRouteTestCase):
    """Negative probes run directly from `just codex-check`."""

    def test_stale_source_commit_is_rejected(self) -> None:
        reading_map = self.generate()
        reading_map["source_commit"] = "0" * 40
        self.assert_rejected("STALE_SOURCE_COMMIT", self.check_map, reading_map)

    def test_stale_source_tree_is_rejected(self) -> None:
        reading_map = self.generate()
        reading_map["source_tree"] = "0" * 40
        self.assert_rejected("STALE_SOURCE_TREE", self.check_map, reading_map)

    def test_changed_document_hash_is_rejected(self) -> None:
        reading_map = self.generate()
        self.document.write_text(
            self.document.read_text(encoding="utf-8") + "changed but uncommitted\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assert_rejected("STALE_DOCUMENT", self.check_map, reading_map)

    def test_requested_section_id_missing_is_rejected(self) -> None:
        request = self.request(required=["TEST-MISSING"])
        self.assert_rejected("MISSING_SECTION", self.generate, request)

    def test_duplicate_section_id_in_one_document_is_rejected(self) -> None:
        self.document.write_text(
            self.document.read_text(encoding="utf-8")
            + "<!-- SECTION-ID: TEST-REQUIRED -->\nrepeat\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assert_rejected("DUPLICATE_SECTION", self.generate)

    def test_duplicate_section_id_across_route_documents_is_rejected(self) -> None:
        second = self.root / "second.md"
        second.write_text(
            "<!-- SECTION-ID: TEST-REQUIRED -->\nrepeat\n"
            "<!-- SECTION-ID: SECOND-ONLY -->\nsecond\n",
            encoding="utf-8",
            newline="\n",
        )
        request = self.request()
        request["documents"].append(
            {
                "path": "second.md",
                "required_sections": ["SECOND-ONLY"],
                "optional_sections": [],
                "reason": "Expose a duplicate marker elsewhere in the routed set.",
            }
        )
        self.assert_rejected("DUPLICATE_SECTION", self.generate, request)

    def test_route_id_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            "ROUTE_ID_MISMATCH",
            self.check_map,
            self.generate(),
            route_id="OTHER-CODEX-ROUTE",
        )

    def test_mode_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            "MODE_MISMATCH",
            self.check_map,
            self.generate(),
            mode="ACCEPT",
        )

    def test_milestone_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            "MILESTONE_MISMATCH",
            self.check_map,
            self.generate(),
            milestone="M2",
        )

    def test_batch_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            "BATCH_MISMATCH",
            self.check_map,
            self.generate(),
            batch_id="M1-B002",
        )

    def test_binding_digest_tamper_is_rejected(self) -> None:
        reading_map = self.generate()
        reading_map["binding_digest"] = "0" * 64
        self.assert_rejected("BINDING_DIGEST_MISMATCH", self.check_map, reading_map)

    def test_more_than_70_percent_context_blocks_without_output(self) -> None:
        request = self.request(capacity=1)
        request_path = self.root / "request.json"
        output = self.root / "route.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        self.assert_rejected(
            "BLOCK_AND_REPLAN",
            write_reading_map,
            request_path,
            output,
            repo_root=self.root,
        )
        self.assertFalse(output.exists())

    def test_more_than_55_percent_context_removes_optional_section(self) -> None:
        full = self.generate(self.request(required=["TEST-REQUIRED"], optional=["TEST-OPTIONAL"]))
        total = full["context_budget"]["planned_bytes"]
        capacity = math.ceil(total / 0.60)
        request = self.request(
            required=["TEST-REQUIRED"],
            optional=["TEST-OPTIONAL"],
            capacity=capacity,
        )
        reading_map = self.generate(request)
        self.assertEqual(reading_map["context_budget"]["status"], "SOFT_REDUCED")
        self.assertLessEqual(reading_map["context_budget"]["ratio"], SOFT_LIMIT)
        self.assertEqual(reading_map["documents"][0]["sections"], ["TEST-REQUIRED"])
        required_bytes = len(
            "<!-- SECTION-ID: TEST-REQUIRED -->\nrequired content\n".encode("utf-8")
        )
        self.assertEqual(reading_map["context_budget"]["planned_bytes"], required_bytes)
        self.check_map(reading_map)

    def test_soft_limit_without_enough_optional_content_requires_replan(self) -> None:
        required_only = self.generate()
        required_bytes = required_only["context_budget"]["planned_bytes"]
        capacity = math.ceil(required_bytes / 0.60)
        self.assert_rejected(
            "SOFT_LIMIT_REPLAN",
            self.generate,
            self.request(capacity=capacity),
        )

    def test_wildcard_bulk_path_is_rejected(self) -> None:
        self.assert_rejected(
            "BULK_PATH_REJECTED",
            self.generate,
            self.request(path="docs/**"),
        )

    def test_directory_path_is_rejected(self) -> None:
        (self.root / "docs").mkdir()
        self.assert_rejected(
            "DIRECTORY_PATH_REJECTED",
            self.generate,
            self.request(path="docs"),
        )

    def test_unapproved_external_path_is_rejected(self) -> None:
        external = Path(self.temporary.name) / "external.md"
        external.write_text(
            "<!-- SECTION-ID: TEST-EXTERNAL -->\nexternal\n",
            encoding="utf-8",
        )
        self.assert_rejected(
            "UNAPPROVED_EXTERNAL_PATH",
            self.generate,
            self.request(path=str(external), required=["TEST-EXTERNAL"]),
        )

    def test_external_symlink_escape_is_rejected(self) -> None:
        external = Path(self.temporary.name) / "external.md"
        external.write_text(
            "<!-- SECTION-ID: TEST-EXTERNAL -->\nexternal\n",
            encoding="utf-8",
        )
        (self.root / "escape.md").symlink_to(external)
        self.assert_rejected(
            "PATH_ESCAPE_REJECTED",
            self.generate,
            self.request(path="escape.md", required=["TEST-EXTERNAL"]),
        )

    def test_external_map_check_requires_allow_root_again(self) -> None:
        self.assertTrue(R2_BASELINE.is_file(), R2_BASELINE)
        request = self.request(
            path=str(R2_BASELINE),
            required=["R2-INTEGRATION-M1-BASELINE"],
        )
        reading_map = generate_reading_map(
            request,
            repo_root=self.root,
            allow_roots=(R2_PACKAGE,),
        )
        self.assert_rejected("UNAPPROVED_EXTERNAL_PATH", self.check_map, reading_map)

    def test_head_change_rejects_old_route(self) -> None:
        reading_map = self.generate()
        (self.root / "new.txt").write_text("new commit\n", encoding="utf-8")
        self.git("add", "new.txt")
        self.git("commit", "-q", "-m", "advance head")
        self.assert_rejected("STALE_SOURCE_COMMIT", self.check_map, reading_map)

    def test_document_content_change_rejects_old_route(self) -> None:
        reading_map = self.generate()
        original = self.document.read_text(encoding="utf-8")
        self.document.write_text(
            original.replace("required content", "different content"),
            encoding="utf-8",
            newline="\n",
        )
        self.assert_rejected("STALE_DOCUMENT", self.check_map, reading_map)

    def test_unknown_reading_map_field_is_rejected(self) -> None:
        reading_map = self.generate()
        reading_map["unexpected"] = True
        self.assert_rejected("INVALID_STRUCTURE", self.check_map, reading_map)

    def test_missing_required_reading_map_field_is_rejected(self) -> None:
        reading_map = self.generate()
        del reading_map["documents"]
        self.assert_rejected("INVALID_STRUCTURE", self.check_map, reading_map)

    def test_bound_field_tamper_is_rejected_even_with_current_sources(self) -> None:
        reading_map = copy.deepcopy(self.generate())
        reading_map["forbidden_bulk_reads"].append("secrets/**")
        self.assert_rejected("BINDING_DIGEST_MISMATCH", self.check_map, reading_map)

    def test_binding_digest_uses_documented_canonical_json(self) -> None:
        reading_map = self.generate()
        changed_timestamp = copy.deepcopy(reading_map)
        changed_timestamp["generated_at"] = "2099-01-01T00:00:00Z"
        self.assertEqual(
            calculate_binding_digest(reading_map),
            calculate_binding_digest(changed_timestamp),
        )
        changed_route = copy.deepcopy(reading_map)
        changed_route["route_id"] = "OTHER-CODEX-ROUTE"
        self.assertNotEqual(
            calculate_binding_digest(reading_map),
            calculate_binding_digest(changed_route),
        )

    def test_relative_allow_root_is_rejected(self) -> None:
        request = self.request()
        self.assert_rejected(
            "INVALID_ALLOW_ROOT",
            generate_reading_map,
            request,
            repo_root=self.root,
            allow_roots=(Path("relative-root"),),
        )


if __name__ == "__main__":
    unittest.main()
