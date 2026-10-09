import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_package import _quarantine_encode as build_package
from tools.lib.common import GAME_PACKAGE_ROOT, PROJECT_ROOT, compute_lock_document, read_json


class PackageTests(unittest.TestCase):
    def test_lock_matches_runtime_tree(self) -> None:
        self.assertEqual(read_json(GAME_PACKAGE_ROOT / "package.lock.json"), compute_lock_document())

    def test_deterministic_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.trpgpkg"
            second = Path(directory) / "second.trpgpkg"
            digest_a = build_package(first, validate_first=False)
            digest_b = build_package(second, validate_first=False)
            self.assertEqual(digest_a, digest_b)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_authoring_tree_is_not_a_runtime_input(self) -> None:
        self.assertTrue((PROJECT_ROOT / "authoring").is_dir())
        locked_paths = {
            entry["path"] for entry in read_json(GAME_PACKAGE_ROOT / "package.lock.json")["files"]
        }
        self.assertFalse(any(path == "authoring" or path.startswith("authoring/") for path in locked_paths))

    def test_registered_modules_enter_package_but_authoring_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "content-boundary.trpgpkg"
            build_package(output, validate_first=True)
            with zipfile.ZipFile(output) as archive:
                packaged_paths = set(archive.namelist())

        manifest = read_json(GAME_PACKAGE_ROOT / "manifest.json")
        for module_registry_path in manifest["content"]["modules"]:
            self.assertIn(module_registry_path, packaged_paths)
            module_manifest = read_json(GAME_PACKAGE_ROOT / module_registry_path)
            module_root = Path(module_registry_path).parent
            self.assertIn((module_root / module_manifest["scenario"]).as_posix(), packaged_paths)
            self.assertIn((module_root / module_manifest["expected_path"]).as_posix(), packaged_paths)
        self.assertFalse(
            any(path == "authoring" or path.startswith("authoring/") for path in packaged_paths)
        )


if __name__ == "__main__":
    unittest.main()
