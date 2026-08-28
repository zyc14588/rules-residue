"""Adversarial contract tests for the post-platform source-only adapter."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import builder, validator


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def copy_source(directory: str) -> Path:
    root = Path(directory) / "r2_int_010_post_platform"
    shutil.copytree(builder.SOURCE_ROOT, root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return root


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected object: {path}")
    return value


def rebind_schema_digest(root: Path) -> None:
    descriptor_path = root / builder.ADAPTER_SOURCE
    descriptor = load_json(descriptor_path)
    schema_bytes = (root / builder.SCHEMA_SOURCE).read_bytes()
    descriptor["extension_descriptor"]["schema_sha256"] = "sha256:" + hashlib.sha256(schema_bytes).hexdigest()  # type: ignore[index]
    write_json(descriptor_path, descriptor)


def output_snapshot(root: Path) -> tuple[dict[str, bytes], dict[str, int]]:
    byte_map: dict[str, bytes] = {}
    mode_map: dict[str, int] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode_map[relative] = stat.S_IMODE(path.stat().st_mode)
        if path.is_file():
            byte_map[relative] = path.read_bytes()
    return byte_map, mode_map


class PostPlatformIdentityTests(unittest.TestCase):
    def test_generic_identity_derivation_has_no_first_party_exception(self) -> None:
        cases = [
            ("org.trpgplatform.rules-residue", "org.trpgplatform.rules-residue.probe", "org.trpgplatform/rules-residue"),
            ("example.vendor/game", "example.vendor.game.probe", "example.vendor/game"),
            ("alpha.vendor.content", "alpha.vendor.content.probe", "alpha.vendor/content"),
            ("a.b", "a.b.probe", "a/b"),
            ("co.example/my-game", "co.example.my-game.probe", "co.example/my-game"),
        ]
        for stable_id, namespace, platform_id in cases:
            with self.subTest(stable_id=stable_id):
                self.assertEqual(builder.derive_extension_namespace(stable_id), namespace)
                self.assertEqual(builder.derive_platform_package_id(stable_id), platform_id)

    def test_invalid_and_reserved_identities_fail_closed(self) -> None:
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
                    builder.derive_extension_namespace(stable_id)

    def test_first_party_identity_receives_no_capability_or_scope_privilege(self) -> None:
        inputs = builder.load_adapter_inputs()
        self.assertEqual(inputs.definition["v2_manifest"]["capabilities"]["required"], [])
        self.assertFalse(inputs.metadata["scope"]["privileged_package_identity"])
        self.assertFalse(inputs.metadata["scope"]["official_game_special_case"])
        source_text = Path(builder.__file__).read_text(encoding="utf-8")
        self.assertNotIn("build_platform_v2_probe", source_text)
        self.assertNotIn("tests/fixtures/r2-int-010-rem-001", source_text)


class PostPlatformSourceConfinementTests(unittest.TestCase):
    def test_default_builder_reads_only_declared_files_below_new_source_root(self) -> None:
        original = builder._confined_file_bytes
        reads: list[tuple[Path, str]] = []

        def audited(root: Path, relative, label: str, maximum_bytes: int) -> bytes:
            reads.append((Path(root).resolve(), relative.as_posix()))
            return original(root, relative, label, maximum_bytes)

        with mock.patch.object(builder, "_confined_file_bytes", side_effect=audited):
            builder.source_project_files()
        self.assertEqual(
            [relative for _, relative in reads],
            [
                builder.METADATA_SOURCE.as_posix(),
                builder.ADAPTER_SOURCE.as_posix(),
                builder.SCHEMA_SOURCE.as_posix(),
                builder.PAYLOAD_SOURCE.as_posix(),
            ],
        )
        self.assertTrue(all(root == builder.SOURCE_ROOT.resolve() for root, _ in reads))

    def test_root_and_leaf_symlinks_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            actual = copy_source(directory)
            linked = Path(directory) / "linked-source"
            linked.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "real directory, not a symlink"):
                builder.load_adapter_inputs(linked)

        with tempfile.TemporaryDirectory() as directory:
            root = copy_source(directory)
            schema = root / builder.SCHEMA_SOURCE
            outside = Path(directory) / "outside.schema.json"
            shutil.copyfile(schema, outside)
            schema.unlink()
            schema.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "contains a symbolic link"):
                builder.load_adapter_inputs(root)

    def test_source_mapping_traversal_and_descriptor_absolute_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = copy_source(directory)
            descriptor_path = root / builder.ADAPTER_SOURCE
            descriptor = load_json(descriptor_path)
            descriptor["source_files"]["schema"] = "../outside.json"  # type: ignore[index]
            write_json(descriptor_path, descriptor)
            with self.assertRaisesRegex(ValueError, "parent segment|one local JSON"):
                builder.load_adapter_inputs(root)

        for attack in ("/absolute/schema.json", "extensions/x/../../schema.json"):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as directory:
                root = copy_source(directory)
                descriptor_path = root / builder.ADAPTER_SOURCE
                descriptor = load_json(descriptor_path)
                descriptor["extension_descriptor"]["schema_path"] = attack  # type: ignore[index]
                write_json(descriptor_path, descriptor)
                with self.assertRaises(ValueError):
                    builder.load_adapter_inputs(root)

    def test_normalization_and_casefold_collisions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "NFC-normalized"):
            builder._validated_relative_path("extensions/example/e\u0301.json", "decomposed")
        with self.assertRaisesRegex(ValueError, "collide under portable normalization"):
            builder._ensure_unique_portable_paths(
                ("extensions/example/Straße.json", "extensions/example/STRASSE.json")
            )

    def test_file_size_limits_apply_before_parse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = copy_source(directory)
            with (root / builder.SCHEMA_SOURCE).open("wb") as handle:
                handle.truncate(builder.MAX_SCHEMA_BYTES + 1)
            with self.assertRaisesRegex(ValueError, f"exceeds {builder.MAX_SCHEMA_BYTES} bytes before read"):
                builder.load_adapter_inputs(root)

    def test_strict_json_bounds_duplicate_keys_and_nonfinite_values(self) -> None:
        accepted_depth = b"[" * builder.MAX_JSON_DEPTH + b"0" + b"]" * builder.MAX_JSON_DEPTH
        self.assertIsInstance(builder._load_json_bytes(accepted_depth, "depth-boundary"), list)
        attacks = {
            "depth": b"[" * (builder.MAX_JSON_DEPTH + 1) + b"0" + b"]" * (builder.MAX_JSON_DEPTH + 1),
            "duplicate": b'{"value":1,"value":2}',
            "nan": b'{"value":NaN}',
            "surrogate": b'{"value":"\\ud800"}',
            "number": b'{"value":' + b"1" * (builder.MAX_JSON_NUMBER_BYTES + 1) + b"}",
            "nodes": json.dumps([0] * builder.MAX_JSON_NODES).encode("ascii"),
        }
        for name, data in attacks.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                builder._load_json_bytes(data, name)


class PostPlatformSchemaTests(unittest.TestCase):
    def test_raw_schema_digest_and_local_fragment_reference_are_enforced(self) -> None:
        inputs = builder.load_adapter_inputs()
        descriptor = inputs.definition["extension_descriptor"]
        self.assertEqual(
            descriptor["schema_sha256"],
            "sha256:" + hashlib.sha256(inputs.schema_bytes).hexdigest(),
        )
        self.assertEqual(inputs.schema["properties"]["count"]["$ref"], "#/$defs/bounded_count")
        self.assertEqual(builder.validate_payload(inputs.payload, inputs.schema), [])

        with tempfile.TemporaryDirectory() as directory:
            root = copy_source(directory)
            schema = root / builder.SCHEMA_SOURCE
            schema.write_bytes(schema.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "exact raw schema bytes"):
                builder.load_adapter_inputs(root)

    def test_remote_cross_file_and_dynamic_references_fail_closed(self) -> None:
        attacks = [
            ("$ref", "https://example.invalid/probe.schema.json"),
            ("$ref", "other.schema.json#/$defs/bounded_count"),
            ("$dynamicRef", "#/$defs/bounded_count"),
            ("$recursiveRef", "#"),
        ]
        for keyword, reference in attacks:
            with self.subTest(keyword=keyword), tempfile.TemporaryDirectory() as directory:
                root = copy_source(directory)
                schema_path = root / builder.SCHEMA_SOURCE
                schema = load_json(schema_path)
                schema["properties"]["count"] = {keyword: reference}  # type: ignore[index]
                write_json(schema_path, schema)
                rebind_schema_digest(root)
                with self.assertRaisesRegex(ValueError, "same-document|forbids|local bounded-count"):
                    builder.load_adapter_inputs(root)

    def test_unknown_missing_wrong_type_formal_and_count_bounds_fail_closed(self) -> None:
        inputs = builder.load_adapter_inputs()
        valid = inputs.payload
        attacks = {
            "unknown": {**valid, "extra": True},
            "missing": {key: value for key, value in valid.items() if key != "count"},
            "boolean-count": {**valid, "count": True},
            "negative-count": {**valid, "count": -1},
            "excess-count": {**valid, "count": 1000001},
            "formal-b002": {**valid, "formal_B002": True},
            "formal-b009": {**valid, "formal_B009": True},
            "wrong-enabled": {**valid, "enabled": 1},
        }
        for name, payload in attacks.items():
            with self.subTest(name=name):
                self.assertTrue(builder.validate_payload(payload, inputs.schema))
                with tempfile.TemporaryDirectory() as directory:
                    root = copy_source(directory)
                    write_json(root / builder.PAYLOAD_SOURCE, payload)
                    with self.assertRaisesRegex(ValueError, "does not match its local schema"):
                        builder.load_adapter_inputs(root)


class PostPlatformAcceptanceTests(unittest.TestCase):
    def test_checked_in_platform_antecedent_and_provenance_validate(self) -> None:
        result = validator.validate_adapter_candidate()
        self.assertEqual(result["validation"], "PASS")
        self.assertEqual(result["platform_acceptance"], "PASS")
        self.assertEqual(result["post_platform_adapter"], "IMPLEMENTED_NOT_ACCEPTED")
        self.assertEqual(result["independent_adapter_acceptance"], "NOT_RUN")
        self.assertEqual(result["cross_repository_acceptance"], "NOT_RUN")
        self.assertEqual(result["r2_int_010"], "FAIL")

    def test_absent_or_nonpass_platform_antecedent_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = copy_source(directory)
            metadata_path = root / builder.METADATA_SOURCE
            metadata = load_json(metadata_path)
            metadata["platform_acceptance"]["status"] = "NOT_RUN"  # type: ignore[index]
            write_json(metadata_path, metadata)
            with self.assertRaisesRegex(ValueError, "platform PASS antecedent"):
                builder.load_adapter_inputs(root)

        record = load_json(validator.PLATFORM_REPORT_ROOT / validator.PLATFORM_RECORD_NAME)
        record["platform"]["acceptance_status"] = "NOT_RUN"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "platform PASS identity"):
            validator.validate_adapter_candidate(platform_record_data=record)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unavailable"):
                validator.validate_adapter_candidate(platform_report_root=Path(directory))

    def test_provisional_commit_or_evidence_cannot_be_platform_acceptance(self) -> None:
        for provisional in validator.PROVISIONAL_COMMITS:
            with self.subTest(provisional=provisional):
                record = load_json(validator.PLATFORM_REPORT_ROOT / validator.PLATFORM_RECORD_NAME)
                record["platform"]["code_commit"] = provisional  # type: ignore[index]
                with self.assertRaisesRegex(ValueError, "platform PASS identity|provisional"):
                    validator.validate_adapter_candidate(platform_record_data=record)

        provenance = copy.deepcopy(validator.expected_provenance())
        provenance["policy"]["may_be_used_as_execution_evidence"] = True
        with self.assertRaisesRegex(ValueError, "provenance disposition"):
            validator.validate_adapter_candidate(provenance_data=provenance)

    def test_platform_record_digest_tamper_is_rejected(self) -> None:
        manifest = load_json(validator.PLATFORM_REPORT_ROOT / validator.PLATFORM_MANIFEST_NAME)
        manifest["artifact"]["sha256"] = "0" * 64  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "digest is stale"):
            validator.validate_adapter_candidate(platform_manifest_data=manifest)


class PostPlatformDeterminismAndIsolationTests(unittest.TestCase):
    def test_two_builds_have_identical_bytes_modes_manifest_schema_payload_and_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = builder.build_source_fixture(root / "first")
            second = builder.build_source_fixture(root / "second")
            first_bytes, first_modes = output_snapshot(first.output_root)
            second_bytes, second_modes = output_snapshot(second.output_root)
            self.assertEqual(first.source_tree_sha256, second.source_tree_sha256)
            self.assertEqual(first.candidate_identity_sha256, second.candidate_identity_sha256)
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(first_modes, second_modes)
            self.assertEqual(set(first_modes.values()), {0o644, 0o755})
            self.assertTrue(all(mode == 0o644 for path, mode in first_modes.items() if path in first_bytes))

            inputs = builder.load_adapter_inputs()
            descriptor = inputs.definition["extension_descriptor"]
            project = first.project_root
            self.assertEqual((project / "package.toml").read_bytes(), builder.render_platform_v2_manifest(inputs))
            self.assertEqual((project / descriptor["schema_path"]).read_bytes(), inputs.schema_bytes)
            self.assertEqual((project / descriptor["payload_path"]).read_bytes(), inputs.payload_bytes)
            self.assertEqual(first.source_lock.read_bytes(), second.source_lock.read_bytes())
            lock = json.loads(first.source_lock.read_text(encoding="utf-8"))
            self.assertEqual(lock["platform_acceptance"]["status"], "PASS")
            self.assertEqual(lock["governance"]["rules_adapter_acceptance"], "NOT_RUN")
            self.assertEqual(lock["governance"]["r2_int_010"], "FAIL")

    def test_builder_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            builder.build_source_fixture(output)
            with self.assertRaisesRegex(ValueError, "already exists"):
                builder.build_source_fixture(output)

    def test_tampered_old_source_and_deleted_old_evidence_do_not_change_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory)
            source = copy_source(directory)
            old_source = sandbox / "tests/fixtures/r2-int-010-rem-001"
            old_source.mkdir(parents=True)
            (old_source / "platform-v2-probe.json").write_text("old provisional bytes\n", encoding="utf-8")
            old_evidence = sandbox / "reports/m2/probes/remediations/r2-int-010-rem-001/evidence.json"
            old_evidence.parent.mkdir(parents=True)
            old_evidence.write_text("old provisional evidence\n", encoding="utf-8")

            first = builder.source_project_files(source)
            (old_source / "platform-v2-probe.json").write_text("tampered old source\n", encoding="utf-8")
            old_evidence.unlink()
            second = builder.source_project_files(source)
            self.assertEqual(first, second)

    def test_new_source_never_enters_legacy_lock_or_lua_runtime(self) -> None:
        lock_path = builder.REPOSITORY_ROOT / "game-package/package.lock.json"
        before = lock_path.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            result = builder.build_source_fixture(Path(directory) / "candidate")
            output_paths = set(result.project_files)
        after = lock_path.read_bytes()
        self.assertEqual(before, after)
        legacy_lock = json.loads(before)
        legacy_paths = {entry["path"] for entry in legacy_lock["files"]}
        self.assertTrue(output_paths.isdisjoint(legacy_paths))
        self.assertFalse(any(path.endswith(".lua") for path in output_paths))
        self.assertFalse(builder.SOURCE_ROOT.is_relative_to(builder.REPOSITORY_ROOT / "game-package"))


__all__ = [
    "PostPlatformIdentityTests",
    "PostPlatformSourceConfinementTests",
    "PostPlatformSchemaTests",
    "PostPlatformAcceptanceTests",
    "PostPlatformDeterminismAndIsolationTests",
]
