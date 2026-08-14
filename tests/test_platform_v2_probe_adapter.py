from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_package import build_package
from tools.build_platform_v2_probe import (
    MAX_PAYLOAD_BYTES,
    MAX_SCHEMA_BYTES,
    PROBE_SOURCE_ROOT,
    PROBE_SCOPE_LABEL,
    _load_json_bytes,
    _portable_collision_key,
    _validated_relative_path,
    build_source_fixture,
    derive_extension_namespace,
    derive_platform_package_id,
    load_adapter_inputs,
    source_project_files,
)
from tools.lib.common import (
    GAME_PACKAGE_ROOT,
    compute_lock_document,
    read_json,
    runtime_relative_paths,
)
from tools.lib.schema_subset import validate


def copy_game_package(directory: str) -> Path:
    root = Path(directory) / "game-package"
    shutil.copytree(GAME_PACKAGE_ROOT, root)
    return root


def copy_probe_source(directory: str) -> Path:
    root = Path(directory) / "r2-int-010-rem-001"
    shutil.copytree(PROBE_SOURCE_ROOT, root)
    return root


def fixture_file(root: Path, descriptor_path: object) -> Path:
    return root / Path(str(descriptor_path)).name


def write_json_file(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def rebind_schema_digest(root: Path, descriptor: dict[str, object]) -> None:
    schema_path = fixture_file(root, descriptor["schema_path"])
    adapter_path = root / "platform-v2-probe.json"
    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    adapter["extension_descriptor"]["schema_sha256"] = (
        "sha256:" + hashlib.sha256(schema_path.read_bytes()).hexdigest()
    )
    write_json_file(adapter_path, adapter)


class PlatformV2ProbeIdentityTests(unittest.TestCase):
    def test_generic_namespace_and_package_id_derivation(self) -> None:
        cases = [
            (
                "org.trpgplatform.rules-residue",
                "org.trpgplatform.rules-residue.probe",
                "org.trpgplatform/rules-residue",
            ),
            ("example.vendor/game", "example.vendor.game.probe", "example.vendor/game"),
            ("alpha.vendor.content", "alpha.vendor.content.probe", "alpha.vendor/content"),
            ("a.b", "a.b.probe", "a/b"),
            ("co.example/my-game", "co.example.my-game.probe", "co.example/my-game"),
        ]
        for stable_id, namespace, platform_id in cases:
            with self.subTest(stable_id=stable_id):
                self.assertEqual(derive_extension_namespace(stable_id), namespace)
                self.assertEqual(derive_platform_package_id(stable_id), platform_id)

    def test_namespace_boundary_accepts_128_bytes_and_rejects_129(self) -> None:
        maximum = "a." + "b" * 64 + "." + "c" * 55
        derived = derive_extension_namespace(maximum)
        self.assertEqual(len(derived.encode("ascii")), 128)

        overlong = "a." + "b" * 64 + "." + "c" * 56
        with self.assertRaisesRegex(ValueError, "outside the platform boundary"):
            derive_extension_namespace(overlong)

    def test_invalid_fold_reserved_shape_and_segment_count_are_rejected(self) -> None:
        invalid = [
            "Org.trpgplatform.rules-residue",
            "org.TRPGplatform.rules-residue",
            "org.trpgplatform.ruleſ-residue",
            "org..rules-residue",
            "org.trpgplatform/rules/residue",
            "org.trpgplatform.-rules",
            "trpg.platform/probe",
            "a.b.c.d.e.f.g.h",
            "a." + "b" * 65,
        ]
        for stable_id in invalid:
            with self.subTest(stable_id=stable_id):
                with self.assertRaises(ValueError):
                    derive_extension_namespace(stable_id)

        for stable_id in ["Org.example.game", "org.example/game/extra", "org.example."]:
            with self.subTest(platform_id=stable_id):
                with self.assertRaises(ValueError):
                    derive_platform_package_id(stable_id)

        for suffix in ["Probe", "bad_suffix", "x" * 65]:
            with self.subTest(suffix=suffix):
                with self.assertRaises(ValueError):
                    derive_extension_namespace("example.vendor/game", suffix)


class PlatformV2ProbeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = load_adapter_inputs()
        self.definition = self.inputs.definition
        self.descriptor = self.definition["extension_descriptor"]

    def test_descriptor_is_exact_generic_v2_contract_with_raw_schema_digest(self) -> None:
        self.assertEqual(
            set(self.descriptor),
            {
                "namespace",
                "required",
                "contract_version",
                "schema_path",
                "schema_sha256",
                "payload_path",
                "host_api_major",
                "host_api_min_minor",
                "host_api_max_minor",
            },
        )
        self.assertEqual(
            self.descriptor["namespace"],
            derive_extension_namespace(self.definition["source_package_id"]),
        )
        self.assertEqual(
            self.definition["platform_package_id"],
            derive_platform_package_id(self.definition["source_package_id"]),
        )
        self.assertTrue(self.descriptor["required"])
        self.assertEqual(self.descriptor["contract_version"], 1)
        self.assertEqual(
            self.descriptor["schema_sha256"],
            "sha256:" + hashlib.sha256(self.inputs.schema_bytes).hexdigest(),
        )
        prefix = f"extensions/{self.descriptor['namespace']}/"
        self.assertTrue(self.descriptor["schema_path"].startswith(prefix))
        self.assertTrue(self.descriptor["payload_path"].startswith(prefix))

    def test_local_schema_is_closed_draft202012_and_probe_is_explicitly_non_formal(self) -> None:
        schema = self.inputs.schema
        payload = self.inputs.payload
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["type"], "object")
        self.assertIs(schema["additionalProperties"], False)
        self.assertIn(PROBE_SCOPE_LABEL, schema["title"])
        self.assertEqual(self.definition["scope"]["formal_B002"], False)
        self.assertEqual(self.definition["scope"]["formal_B009"], False)
        self.assertEqual(payload["formal_B002"], False)
        self.assertEqual(payload["formal_B009"], False)
        self.assertEqual(
            set(payload),
            {"probe_id", "formal_B002", "formal_B009", "count", "enabled"},
        )
        serialized = json.dumps(payload, sort_keys=True).lower()
        for forbidden in ["equipment", "semantic_kind", "short_rule", "long_rule", "lua", "runtime"]:
            self.assertNotIn(forbidden, serialized)

    def test_local_schema_rejects_unknown_missing_wrong_and_formal_payloads(self) -> None:
        schema = self.inputs.schema
        valid = self.inputs.payload
        self.assertEqual(validate(valid, schema), [])
        cases = {
            "unknown": {**valid, "extra": True},
            "missing": {key: value for key, value in valid.items() if key != "count"},
            "boolean-is-not-count": {**valid, "count": True},
            "negative-count": {**valid, "count": -1},
            "formal-b002": {**valid, "formal_B002": True},
            "formal-b009": {**valid, "formal_B009": True},
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                self.assertTrue(validate(payload, schema))

    def test_tampered_schema_namespace_and_source_binding_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = copy_probe_source(directory)
            schema_path = fixture_file(root, self.descriptor["schema_path"])
            schema_path.write_bytes(schema_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "exact raw schema bytes"):
                load_adapter_inputs(root)

        with tempfile.TemporaryDirectory() as directory:
            root = copy_probe_source(directory)
            adapter_path = root / "platform-v2-probe.json"
            adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
            adapter["namespace_derivation"]["derived_namespace"] = "outside.vendor.probe"
            adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "deterministic derivation"):
                load_adapter_inputs(root)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "game-package"
            shutil.copytree(GAME_PACKAGE_ROOT, root)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["id"] = "outside.vendor.game"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stable legacy manifest ID"):
                load_adapter_inputs(game_package_root=root)

    def test_parent_and_leaf_symlink_escapes_fail_before_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outside = copy_probe_source(directory)
            root = Path(directory) / "fixture-link"
            root.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "real directory, not a symlink"):
                load_adapter_inputs(root)

        with tempfile.TemporaryDirectory() as directory:
            root = copy_probe_source(directory)
            payload_path = fixture_file(root, self.descriptor["payload_path"])
            outside = Path(directory) / "outside-payload.json"
            shutil.copyfile(payload_path, outside)
            payload_path.unlink()
            payload_path.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "contains a symbolic link"):
                load_adapter_inputs(root)

    def test_schema_and_payload_size_limits_run_before_read_or_parse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = copy_probe_source(directory)
            schema_path = fixture_file(root, self.descriptor["schema_path"])
            with schema_path.open("wb") as handle:
                handle.truncate(MAX_SCHEMA_BYTES + 1)
            with self.assertRaisesRegex(ValueError, f"exceeds {MAX_SCHEMA_BYTES} bytes before read"):
                load_adapter_inputs(root)

        with tempfile.TemporaryDirectory() as directory:
            root = copy_probe_source(directory)
            payload_path = fixture_file(root, self.descriptor["payload_path"])
            with payload_path.open("wb") as handle:
                handle.truncate(MAX_PAYLOAD_BYTES + 1)
            with self.assertRaisesRegex(ValueError, f"exceeds {MAX_PAYLOAD_BYTES} bytes before read"):
                load_adapter_inputs(root)

    def test_strict_json_rejects_depth_nonfinite_surrogate_and_unbounded_numbers(self) -> None:
        accepted_depth = b"[" * 64 + b"0" + b"]" * 64
        self.assertIsInstance(_load_json_bytes(accepted_depth, "depth-64"), list)
        cases = {
            "depth-65": b"[" * 65 + b"0" + b"]" * 65,
            "nan": b'{"value":NaN}',
            "infinity": b'{"value":Infinity}',
            "surrogate": b'{"value":"\\ud800"}',
            "number-token": b'{"value":' + b"1" * 129 + b"}",
            "exponent": b'{"value":1e309}',
        }
        for name, document in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    _load_json_bytes(document, name)
        self.assertEqual(str(_load_json_bytes(b'{"value":1e2}', "bounded")["value"]), "1E+2")

    def test_schema_refs_are_local_fragments_only(self) -> None:
        rejected = [
            ("$ref", "https://example.invalid/probe.schema.json"),
            ("$ref", "other.schema.json#/$defs/value"),
            ("$dynamicRef", "#value"),
            ("$recursiveRef", "#"),
        ]
        for keyword, reference in rejected:
            with self.subTest(keyword=keyword, reference=reference):
                with tempfile.TemporaryDirectory() as directory:
                    root = copy_probe_source(directory)
                    schema_path = fixture_file(root, self.descriptor["schema_path"])
                    schema = json.loads(schema_path.read_text(encoding="utf-8"))
                    schema["properties"]["count"][keyword] = reference
                    write_json_file(schema_path, schema)
                    rebind_schema_digest(root, self.descriptor)
                    with self.assertRaisesRegex(ValueError, "same-document fragment|forbids"):
                        load_adapter_inputs(root)

        with tempfile.TemporaryDirectory() as directory:
            root = copy_probe_source(directory)
            schema_path = fixture_file(root, self.descriptor["schema_path"])
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["properties"]["count"]["$ref"] = "#/$defs/local-count"
            schema["$defs"] = {"local-count": {"type": "integer"}}
            write_json_file(schema_path, schema)
            rebind_schema_digest(root, self.descriptor)
            self.assertEqual(load_adapter_inputs(root).payload["count"], 1)

    def test_portable_paths_and_descriptor_collisions_fail_closed(self) -> None:
        self.assertEqual(
            _validated_relative_path("extensions/a.b.c/\u00c9.json", "valid").as_posix(),
            "extensions/a.b.c/\u00c9.json",
        )
        invalid = [
            "/absolute/value.json",
            "//server/share/value.json",
            "C:/drive/value.json",
            "extensions\\a.b.c\\value.json",
            "extensions/a.b.c/value\x00.json",
            "extensions/a.b.c/value\x01.json",
            "extensions/a.b.c/e\u0301.json",
            "extensions/a.b.c/CON.json",
            "extensions/a.b.c/com1.txt",
            "extensions/a.b.c/value.",
            "extensions/a.b.c/value.json ",
            "extensions/a.b.c/value?.json",
            "a/" + "b" * 239,
        ]
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    _validated_relative_path(path, "negative")
        self.assertEqual(
            _portable_collision_key("extensions/a.b.c/Stra\u00dfe.json"),
            _portable_collision_key("extensions/a.b.c/STRASSE.json"),
        )

        with tempfile.TemporaryDirectory() as directory:
            root = copy_probe_source(directory)
            adapter_path = root / "platform-v2-probe.json"
            adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
            adapter["extension_descriptor"]["payload_path"] = adapter[
                "extension_descriptor"
            ]["schema_path"]
            write_json_file(adapter_path, adapter)
            with self.assertRaisesRegex(ValueError, "collide under portable comparison"):
                load_adapter_inputs(root)


class PlatformV2ProbeBuildBoundaryTests(unittest.TestCase):
    @staticmethod
    def _tree_bytes(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_source_project_and_lock_seed_are_distinct_from_final_archive(self) -> None:
        files, lock_bytes = source_project_files()
        inputs = load_adapter_inputs()
        descriptor = inputs.definition["extension_descriptor"]
        self.assertEqual(
            set(files),
            {
                "package.toml",
                "adapters/platform-v2-probe.json",
                descriptor["schema_path"],
                descriptor["payload_path"],
            },
        )
        manifest = files["package.toml"].decode("utf-8")
        self.assertIn("schema_version = 2\n", manifest)
        self.assertIn('package_id = "org.trpgplatform/rules-residue"\n', manifest)
        self.assertIn('package_kind = "library"\n', manifest)
        self.assertIn(
            f'namespace = "{descriptor["namespace"]}"\n',
            manifest,
        )
        self.assertIn(f'schema_sha256 = "{descriptor["schema_sha256"]}"\n', manifest)
        self.assertNotIn("entrypoint", manifest)
        self.assertNotIn("lua_profile", manifest)

        lock = json.loads(lock_bytes)
        self.assertEqual(lock["root"], inputs.definition["platform_package_id"])
        self.assertEqual(lock["packages"][0]["content_hash"], "sha256:" + "0" * 64)
        self.assertEqual(lock["packages"][0]["dependencies"], [])

    def test_source_fixture_build_is_byte_deterministic_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = build_source_fixture(root / "first")
            second = build_source_fixture(root / "second")
            self.assertEqual(first.source_tree_sha256, second.source_tree_sha256)
            self.assertEqual(self._tree_bytes(first.output_root), self._tree_bytes(second.output_root))
            with self.assertRaisesRegex(ValueError, "already exists"):
                build_source_fixture(first.output_root)

    def test_adapter_source_stays_out_of_legacy_lock_and_package_bytes(self) -> None:
        self.assertFalse(PROBE_SOURCE_ROOT.is_relative_to(GAME_PACKAGE_ROOT))
        self.assertEqual(
            {
                path.relative_to(PROBE_SOURCE_ROOT).as_posix()
                for path in PROBE_SOURCE_ROOT.iterdir()
                if path.is_file()
            },
            {
                "README.md",
                "platform-v2-probe.json",
                "minimal-capability-probe.schema.json",
                "minimal-capability-probe.json",
            },
        )
        source_only_paths = {
            "adapters/platform-v2-probe.json",
            "extensions/org.trpgplatform.rules-residue.probe/minimal-capability-probe.schema.json",
            "extensions/org.trpgplatform.rules-residue.probe/minimal-capability-probe.json",
        }
        runtime_paths = set(runtime_relative_paths())
        self.assertTrue(source_only_paths.isdisjoint(runtime_paths))
        self.assertNotIn("adapters/README.md", runtime_paths)
        lock = read_json(GAME_PACKAGE_ROOT / "package.lock.json")
        locked_paths = {entry["path"] for entry in lock["files"]}
        self.assertEqual(lock, compute_lock_document())
        self.assertEqual(
            lock["runtime_tree_sha256"],
            "9e8a6e1ec38c0743925c356fe30e20b2475f657f15a95f5ac7d28ecf1658d9b8",
        )
        self.assertTrue(source_only_paths.isdisjoint(locked_paths))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.trpgpkg"
            second = root / "second.trpgpkg"
            first_digest = build_package(first, validate_first=True)
            second_digest = build_package(second, validate_first=True)
            self.assertEqual(
                first_digest,
                "29ea1e0278e37d183d4c0ff396437088b4873c58c5e9a9c857093f6c552a6314",
            )
            self.assertEqual(first_digest, second_digest)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["schema_version"], "trpg.game-package.manifest/0.1-draft")
            self.assertNotIn("package.toml", names)
            self.assertTrue(source_only_paths.isdisjoint(names))


if __name__ == "__main__":
    unittest.main()
