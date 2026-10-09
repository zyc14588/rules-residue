import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_package import _quarantine_encode as build_package
from tools.lib.common import (
    GAME_PACKAGE_ROOT,
    NON_RUNTIME_MODULE_MARKER,
    compute_lock_document,
    read_json,
    runtime_files,
    write_json,
)
from tools.validate_project import validate_module_registry


class ModuleRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.game_package_root = Path(self._temporary_directory.name) / "game-package"
        shutil.copytree(GAME_PACKAGE_ROOT, self.game_package_root)
        self.manifest = read_json(self.game_package_root / "manifest.json")

    def _copy_third_module(self, name: str, unique_id: bool = True) -> str:
        source = self.game_package_root / "modules" / "tutorial"
        destination = self.game_package_root / "modules" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
        registry_path = f"modules/{name}/manifest.json"

        if unique_id:
            module_id = f"rr.scenario.{name}"
            module_manifest = read_json(destination / "manifest.json")
            module_manifest["id"] = module_id
            module_manifest["title"] = f"Registry test {name}"
            module_manifest["classification"] = "scenario"
            write_json(destination / "manifest.json", module_manifest)

            scenario = read_json(destination / "scenario.json")
            scenario["metadata"]["id"] = module_id
            scenario["metadata"]["classification"] = "scenario"
            write_json(destination / "scenario.json", scenario)

            expected = read_json(destination / "expected-path.json")
            expected["module_id"] = module_id
            write_json(destination / "expected-path.json", expected)

        return registry_path

    def test_registered_third_module_passes(self) -> None:
        registry_path = self._copy_third_module("third")
        self.manifest["content"]["modules"].append(registry_path)
        self.assertEqual(validate_module_registry(self.manifest, self.game_package_root), [])

    def test_registered_third_module_builds_with_all_runtime_artifacts(self) -> None:
        registry_path = self._copy_third_module("third-build")
        self.manifest["content"]["modules"].append(registry_path)
        write_json(self.game_package_root / "manifest.json", self.manifest)
        write_json(
            self.game_package_root / "package.lock.json",
            compute_lock_document(self.game_package_root),
        )
        self.assertEqual(validate_module_registry(self.manifest, self.game_package_root), [])

        output = Path(self._temporary_directory.name) / "third-build.trpgpkg"
        build_package(
            output,
            validate_first=True,
            game_package_root=self.game_package_root,
        )
        with zipfile.ZipFile(output) as archive:
            packaged_paths = set(archive.namelist())

        module_manifest = read_json(self.game_package_root / registry_path)
        module_root = Path(registry_path).parent
        self.assertIn(registry_path, packaged_paths)
        self.assertIn((module_root / module_manifest["scenario"]).as_posix(), packaged_paths)
        self.assertIn((module_root / module_manifest["expected_path"]).as_posix(), packaged_paths)

    def test_unregistered_module_is_rejected(self) -> None:
        registry_path = self._copy_third_module("unregistered")
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(
            any(
                error == f"unregistered executable Module manifest: {registry_path}"
                for error in errors
            ),
            errors,
        )

    def test_explicit_non_runtime_module_is_ignored_and_not_packaged(self) -> None:
        registry_path = self._copy_third_module("template")
        module_root = (self.game_package_root / registry_path).parent
        (module_root / NON_RUNTIME_MODULE_MARKER).write_text(
            "authoring template\n",
            encoding="utf-8",
        )

        self.assertEqual(validate_module_registry(self.manifest, self.game_package_root), [])
        runtime_paths = {
            path.relative_to(self.game_package_root).as_posix()
            for path in runtime_files(self.game_package_root)
        }
        self.assertFalse(any(path.startswith("modules/template/") for path in runtime_paths))

    def test_registered_missing_module_is_rejected(self) -> None:
        self.manifest["content"]["modules"].append("modules/missing/manifest.json")
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(any("registered Module does not exist" in error for error in errors), errors)

    def test_missing_registered_runtime_dependency_is_rejected(self) -> None:
        registry_path = self._copy_third_module("missing-expected")
        self.manifest["content"]["modules"].append(registry_path)
        expected_path = self.game_package_root / "modules/missing-expected/expected-path.json"
        expected_path.unlink()
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(any("expected path does not exist" in error for error in errors), errors)
        self.assertTrue(any("not in the package runtime set" in error for error in errors), errors)

    def test_hidden_module_paths_are_rejected_by_runtime_membership(self) -> None:
        for name in (".hidden-third", "foo/.hidden"):
            with self.subTest(name=name):
                registry_path = self._copy_third_module(name)
                self.manifest["content"]["modules"].append(registry_path)
                errors = validate_module_registry(self.manifest, self.game_package_root)
                self.assertTrue(
                    any(
                        "manifest: file is not in the package runtime set" in error
                        and registry_path in error
                        for error in errors
                    ),
                    errors,
                )
                self.manifest["content"]["modules"].remove(registry_path)

    def test_tests_backed_module_manifest_is_rejected(self) -> None:
        registry_path = self._copy_third_module("foo/tests")
        self.manifest["content"]["modules"].append(registry_path)
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(
            any("manifest: file is not in the package runtime set" in error for error in errors),
            errors,
        )

    def test_registered_non_runtime_marker_module_is_rejected(self) -> None:
        registry_path = self._copy_third_module("registered-template")
        module_root = (self.game_package_root / registry_path).parent
        (module_root / NON_RUNTIME_MODULE_MARKER).write_text(
            "authoring template\n",
            encoding="utf-8",
        )
        self.manifest["content"]["modules"].append(registry_path)
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(
            any("manifest: file is not in the package runtime set" in error for error in errors),
            errors,
        )

    def test_runtime_dependencies_in_tests_paths_are_rejected(self) -> None:
        for field in ("scenario", "expected_path"):
            with self.subTest(field=field):
                name = f"tests-reference-{field}"
                registry_path = self._copy_third_module(name)
                module_path = self.game_package_root / registry_path
                module_root = module_path.parent
                module_manifest = read_json(module_path)
                original_name = module_manifest[field]
                tests_path = module_root / "tests" / original_name
                tests_path.parent.mkdir()
                shutil.move(module_root / original_name, tests_path)
                module_manifest[field] = f"tests/{original_name}"
                write_json(module_path, module_manifest)
                self.manifest["content"]["modules"].append(registry_path)

                errors = validate_module_registry(self.manifest, self.game_package_root)
                label = "scenario reference" if field == "scenario" else "expected path reference"
                self.assertTrue(
                    any(
                        label in error and "file is not in the package runtime set" in error
                        for error in errors
                    ),
                    errors,
                )
                self.manifest["content"]["modules"].remove(registry_path)

    def test_registry_absolute_and_parent_escape_paths_are_rejected(self) -> None:
        for registry_path in ("/tmp/manifest.json", "../outside/manifest.json"):
            with self.subTest(registry_path=registry_path):
                self.manifest["content"]["modules"].append(registry_path)
                errors = validate_module_registry(self.manifest, self.game_package_root)
                self.assertTrue(any("path escapes its allowed root" in error for error in errors), errors)
                self.manifest["content"]["modules"].remove(registry_path)

    def test_module_directory_symlink_escape_is_rejected(self) -> None:
        outside_module = Path(self._temporary_directory.name) / "outside-module"
        shutil.copytree(self.game_package_root / "modules" / "tutorial", outside_module)
        link = self.game_package_root / "modules" / "safe-link"
        try:
            link.symlink_to(outside_module, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlink creation unavailable on this platform: {exc}")

        self.manifest["content"]["modules"].append("modules/safe-link/manifest.json")
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(any("path escapes its allowed root" in error for error in errors), errors)

    def test_invalid_runtime_registration_blocks_build_before_output(self) -> None:
        registry_path = self._copy_third_module(".hidden-build")
        self.manifest["content"]["modules"].append(registry_path)
        write_json(self.game_package_root / "manifest.json", self.manifest)
        write_json(
            self.game_package_root / "package.lock.json",
            compute_lock_document(self.game_package_root),
        )
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(any("not in the package runtime set" in error for error in errors), errors)

        output = Path(self._temporary_directory.name) / "must-not-build.trpgpkg"
        with self.assertRaisesRegex(RuntimeError, "not in the package runtime set"):
            build_package(
                output,
                validate_first=True,
                game_package_root=self.game_package_root,
            )
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(output.suffix + ".sha256").exists())

    def test_duplicate_module_id_is_rejected(self) -> None:
        registry_path = self._copy_third_module("duplicate-id", unique_id=False)
        self.manifest["content"]["modules"].append(registry_path)
        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertIn("duplicate Module ID: rr.tutorial.zero-platform", errors)

    def test_scenario_reference_cannot_escape_module(self) -> None:
        registry_path = self._copy_third_module("unsafe-reference")
        self.manifest["content"]["modules"].append(registry_path)
        module_path = self.game_package_root / registry_path
        module_manifest = read_json(module_path)
        module_manifest["scenario"] = "../tutorial/scenario.json"
        write_json(module_path, module_manifest)

        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(any("scenario reference: path escapes" in error for error in errors), errors)

    def test_invalid_scenario_schema_is_rejected(self) -> None:
        registry_path = self._copy_third_module("invalid-scenario")
        self.manifest["content"]["modules"].append(registry_path)
        scenario_path = self.game_package_root / "modules" / "invalid-scenario" / "scenario.json"
        scenario = read_json(scenario_path)
        del scenario["metadata"]["summary"]
        write_json(scenario_path, scenario)

        errors = validate_module_registry(self.manifest, self.game_package_root)
        self.assertTrue(any("scenario: $.metadata: missing required property 'summary'" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
