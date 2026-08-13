from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.codex_route import (  # noqa: E402
    HARD_LIMIT,
    SOFT_LIMIT,
    RouteError,
    generate_reading_map,
    validate_request,
)
from tools.lib.schema_subset import validate as validate_schema_instance  # noqa: E402

try:  # Full YAML parsing is used when available; the fallback still fails closed structurally.
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - exercised only on deliberately minimal hosts.
    yaml = None

try:
    from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
    from jsonschema.exceptions import SchemaError  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - structural checks below remain active.
    Draft202012Validator = None
    SchemaError = Exception


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_ROOT = Path(
    "/home/zyc14588/RULE_RESIDUAL_R2_AUTHORITY_AND_PROGRESSIVE_DELIVERY_v1.0.0"
)
PINNED_SOURCE_COMMIT = "e8e536fe5c96c389736ffcf8d4855fa146a2b9c2"
EXPECTED_GROUP_COUNTS = {
    "R2-A": 10,
    "R2-B": 14,
    "R2-C": 16,
    "R2-D": 18,
    "R2-E": 20,
    "R2-F": 21,
    "R2-G": 22,
    "R2-H": 22,
    "R2-I": 24,
    "R2-J": 24,
}
EXPECTED_DISPOSITIONS = {
    "INSTALL_CANONICAL": 108,
    "MERGE_INTO_EXISTING": 9,
    "REFERENCE_ONLY": 0,
    "PACKAGE_PROVENANCE_ONLY": 5,
    "DUPLICATE_OF_CANONICAL": 2,
    "NOT_APPLICABLE_FIRST_RELEASE": 0,
    "UNCLASSIFIED": 0,
}
NORMALIZED_INSTALL_CANONICAL = {
    ".codex/prompts/r2/M2-VERTICAL-SLICE/ACCEPT.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/ACCEPT.md",
        "drop_one_final_blank_line",
        1,
    ),
    ".codex/prompts/r2/M2-VERTICAL-SLICE/IMPLEMENT.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/IMPLEMENT.md",
        "drop_one_final_blank_line",
        1,
    ),
    ".codex/prompts/r2/M2-VERTICAL-SLICE/PLAN.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/PLAN.md",
        "drop_one_final_blank_line",
        1,
    ),
    ".codex/prompts/r2/M2-VERTICAL-SLICE/REPAIR.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/M2-VERTICAL-SLICE/REPAIR.md",
        "drop_one_final_blank_line",
        1,
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/ACCEPT.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/ACCEPT.md",
        "drop_one_final_blank_line",
        1,
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/IMPLEMENT.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/IMPLEMENT.md",
        "drop_one_final_blank_line",
        1,
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/PLAN.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/PLAN.md",
        "drop_one_final_blank_line",
        1,
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/REPAIR.md": (
        "03_CODEX_PROGRESSIVE_DISCLOSURE/R2-AUTHORITY-INSTALL/REPAIR.md",
        "drop_one_final_blank_line",
        1,
    ),
    "docs/authority/r2/00_R2_AUTHORITY_ENTRY.md": (
        "01_REPO_OVERLAY/docs/authority/r2/00_R2_AUTHORITY_ENTRY.md",
        "strip_eol_ascii_spaces",
        6,
    ),
    "docs/operations/r2/R2_PROGRESSIVE_DISCLOSURE_PROTOCOL.md": (
        "01_REPO_OVERLAY/docs/operations/R2_PROGRESSIVE_DISCLOSURE_PROTOCOL.md",
        "strip_eol_ascii_spaces",
        2,
    ),
}
NORMALIZED_INSTALL_HASHES = {
    ".codex/prompts/r2/M2-VERTICAL-SLICE/ACCEPT.md": (
        "af44e25a13e2e549a87d4f875853342f1796cd3ed635961f9ec1f5ec117852a4",
        "f0431da7bbfe57cdd513df15f8362c9fb36a6b36d435e5b4e36baa3568e195d9",
    ),
    ".codex/prompts/r2/M2-VERTICAL-SLICE/IMPLEMENT.md": (
        "b4ec0633ff6408e675175d0bb7109b5cf831c277d16de50d8ec7debcb6e58167",
        "a21deb9b0b8a08f85f53ad0d783cc2014416a37b26a228137ece17d70d751a98",
    ),
    ".codex/prompts/r2/M2-VERTICAL-SLICE/PLAN.md": (
        "0e7c9291a39a046a3647dc468f8071aded1886069ea56bae91e133932c3b1c59",
        "fef9dafcdfb755f36aadc2619ab7684b74155a63e0a0191ce6cb5010c183a8a5",
    ),
    ".codex/prompts/r2/M2-VERTICAL-SLICE/REPAIR.md": (
        "96d4ecfc5f5de9b1aee6254d1fb02b03970410f948af46a83aca99d42d4a4485",
        "713f515e54a874e231956c8a5260e1c942c1e2a9fa19a4d9419037bcfb388db3",
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/ACCEPT.md": (
        "4255c6dab164d3455a0c96240fb4f1bd51b9a8c4289616cd09d62dcc5dd9fa6d",
        "a9d5ddfbdefcc2df928c2fe1e8d78e0fd511ce040ecbf73283da341323ddc227",
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/IMPLEMENT.md": (
        "b637b4c6dc86e50f91d2f3368faaf2f2997fb3ef5eb6c63d8712a8987b16a78f",
        "69f0a0554d05906a8d37477846895605d3085a7b9ea646278805b68aa3a802e0",
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/PLAN.md": (
        "4a422f911705f3847c393278d14bf0a7862ad911b118114e5bb58fb409406ddd",
        "f8f88bc610894b7535cd090b6464f9b2dda71e6f472f504816b35a1fb11f8b93",
    ),
    ".codex/prompts/r2/R2-AUTHORITY-INSTALL/REPAIR.md": (
        "652a5e325c12d5c3f9f826705bcc854bcddfa7cc564cf2705f57656a3a3fbb9e",
        "472c418daddedcdeda8d338e0e30d99057a91fae7bf9797e370b3db50a64c6af",
    ),
    "docs/authority/r2/00_R2_AUTHORITY_ENTRY.md": (
        "761f766a891ff62fafe4808d7592ff565089876a27a00c6f7e455c7e68d254df",
        "f5e2a033d09724e616c03019e22b02e62b64aa152f2f276c25a3cd334db32db2",
    ),
    "docs/operations/r2/R2_PROGRESSIVE_DISCLOSURE_PROTOCOL.md": (
        "d9cd2c568fb766c2894c7a6ce97710cae7bea291908f576ad6b5ca89c89bdda3",
        "5c15dfde8ee11feb0f70e9f51b86f44bd9f359f6b04065e6bba0b35b8e92c258",
    ),
}
EXPECTED_SAFETY_STAGES = {
    "knowledge_import",
    "design_input",
    "template",
    "prompt",
    "model_output",
    "human_edit",
    "semantic_conversion",
    "lua_runtime_data",
    "art_audio",
    "region_acceptance",
    "cross_region_validation",
    "build",
    "release_candidate",
    "runtime_generation",
    "hot_update",
    "migration",
    "old_save_load",
    "independent_acceptance",
}
EXPECTED_MINOR_PROHIBITIONS = {
    "sexual assault of minors",
    "sexual exploitation of minors",
    "sexual coercion of minors",
    "sexual grooming of minors",
    "sexual trafficking of minors",
    "sexual slavery of minors",
    "sexualization of minors",
}
SECTION_PATTERN = re.compile(r"<!--\s*SECTION-ID:\s*([A-Z0-9]+(?:-[A-Z0-9]+)+)\s*-->")
DECISION_PATTERN = re.compile(r"^R2-([A-J])([0-9]{2})$")
DISPOSITION_ROW_PATTERN = re.compile(r"  - \[([^,]+), ([A-Z_]+), ([^]]+)\]$")


def _read_text(path: Path, errors: list[str], label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{label}: cannot read {path}: {exc}")
        return ""


def _read_json(path: Path, errors: list[str], label: str) -> Any:
    text = _read_text(path, errors, label)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: invalid JSON {path}: {exc}")
        return None


def _normalize_merged_markdown(text: str) -> str:
    """Canonicalize only end-of-line ASCII spaces in merged Markdown."""

    return "\n".join(line.rstrip(" ") for line in text.splitlines())


def _canonicalize_explicit_install(
    source: bytes,
    kind: str,
    expected_removed_bytes: int,
) -> bytes:
    """Apply one frozen, whitespace-only transform to an explicit canonical path."""

    if kind == "drop_one_final_blank_line":
        if not source.endswith(b"\n\n") or source.endswith(b"\n\n\n"):
            raise ValueError("source does not contain exactly one final blank line")
        normalized = source[:-1]
    elif kind == "strip_eol_ascii_spaces":
        normalized = b"\n".join(line.rstrip(b" ") for line in source.split(b"\n"))
    else:  # Defensive default: a new normalization kind requires validator code review.
        raise ValueError(f"unknown normalization kind {kind}")
    removed = len(source) - len(normalized)
    if removed != expected_removed_bytes:
        raise ValueError(f"expected to remove {expected_removed_bytes} bytes, removed {removed}")
    return normalized


def _validate_yaml_fallback(text: str, label: str) -> None:
    """Validate the plain YAML subset used by the frozen package without dependencies."""

    square = 0
    curly = 0
    for number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise ValueError(f"line {number} contains a tab")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if (len(raw) - len(raw.lstrip(" "))) % 2:
            raise ValueError(f"line {number} has non-canonical indentation")
        content = raw.lstrip(" ")
        if not content.startswith("-") and ":" not in content:
            raise ValueError(f"line {number} is neither a mapping nor sequence item")
        square += content.count("[") - content.count("]")
        curly += content.count("{") - content.count("}")
        if square < 0 or curly < 0:
            raise ValueError(f"line {number} closes an unopened flow collection")
    if square or curly:
        raise ValueError("unclosed flow collection")


def _check_yaml_files(root: Path, errors: list[str]) -> None:
    roots = [
        root / "governance" / "r2",
        root / "governance" / "evidence" / "r2-authority-install",
        root / "docs" / "implementation" / "r2",
        root / ".opencode" / "r2",
        root / ".grok" / "r2",
        root / "docs" / "operations" / "agents" / "r2",
    ]
    paths = sorted({path for base in roots if base.exists() for path in base.rglob("*.yaml")})
    if len(paths) < 15:
        errors.append(f"YAML_PARSE: expected at least 15 installed YAML files, found {len(paths)}")
    for path in paths:
        text = _read_text(path, errors, "YAML_PARSE")
        if not text:
            continue
        try:
            if yaml is not None:
                loaded = yaml.safe_load(text)
                if loaded is None:
                    raise ValueError("document is empty")
            else:
                _validate_yaml_fallback(text, path.as_posix())
        except Exception as exc:  # PyYAML exposes several parser exception types.
            errors.append(f"YAML_PARSE: invalid YAML {path.relative_to(root)}: {exc}")


def _parse_disposition(root: Path, errors: list[str]) -> list[tuple[str, str, str]]:
    path = root / ".codex" / "plans" / "r2-authority-install" / "package-disposition.yaml"
    text = _read_text(path, errors, "PACKAGE_DISPOSITION")
    rows: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        match = DISPOSITION_ROW_PATTERN.fullmatch(line)
        if match:
            rows.append(tuple(part.strip() for part in match.groups()))
    counts = Counter(kind for _, kind, _ in rows)
    for kind, expected in EXPECTED_DISPOSITIONS.items():
        if counts.get(kind, 0) != expected:
            errors.append(
                f"PACKAGE_DISPOSITION: {kind} expected {expected}, found {counts.get(kind, 0)}"
            )
    if len(rows) != 124:
        errors.append(f"PACKAGE_DISPOSITION: expected 124 classified files, found {len(rows)}")
    if len({source for source, _, _ in rows}) != len(rows):
        errors.append("PACKAGE_DISPOSITION: a package source is classified more than once")
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _check_package_integrity(package_root: Path, errors: list[str]) -> None:
    required = [
        "PACKAGE_MANIFEST.yaml",
        "SHA256SUMS",
        "INTEGRITY_REPORT.json",
        "00_BASELINE_AND_INTEGRATION",
        "01_REPO_OVERLAY",
        "02_M2_IMPLEMENTATION_INPUT",
        "03_CODEX_PROGRESSIVE_DISCLOSURE",
        "04_OTHER_PLATFORM_PROGRESSIVE_DISCLOSURE",
        "05_INDEPENDENT_ACCEPTANCE_PACKET",
        "06_USAGE",
    ]
    for relative in required:
        if not (package_root / relative).exists():
            errors.append(f"PACKAGE_INTEGRITY: missing {relative}")
    sums_path = package_root / "SHA256SUMS"
    text = _read_text(sums_path, errors, "PACKAGE_INTEGRITY")
    entries: list[tuple[str, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            errors.append(f"PACKAGE_INTEGRITY: malformed SHA256SUMS line {number}")
            continue
        expected, relative = match.groups()
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            errors.append(f"PACKAGE_INTEGRITY: unsafe checksum path {relative}")
            continue
        entries.append((expected, relative))
        target = package_root.joinpath(*pure.parts)
        if not target.is_file():
            errors.append(f"PACKAGE_INTEGRITY: checksum target missing {relative}")
        elif _sha256(target) != expected:
            errors.append(f"PACKAGE_INTEGRITY: checksum mismatch {relative}")
    if len(entries) != 123:
        errors.append(f"PACKAGE_INTEGRITY: expected 123 checksum entries, found {len(entries)}")
    file_count = sum(1 for path in package_root.rglob("*") if path.is_file())
    if file_count != 124:
        errors.append(f"PACKAGE_INTEGRITY: expected 124 files, found {file_count}")
    expected_wrappers = {
        "PACKAGE_MANIFEST.yaml": "a5adb9fad5439926e0c8d46f23f3e3e107812bdd9ce13097acea04b8cc0a7ba1",
        "SHA256SUMS": "2d65a2ea9fefffc4f8e785fe2e55a0bdc83b7a54559afbb51162daedc0ab8e72",
    }
    for relative, expected in expected_wrappers.items():
        path = package_root / relative
        if path.is_file() and _sha256(path) != expected:
            errors.append(f"PACKAGE_INTEGRITY: pinned wrapper hash mismatch {relative}")


def _check_installed_bytes(
    root: Path,
    package_root: Path,
    rows: Iterable[tuple[str, str, str]],
    errors: list[str],
) -> None:
    normalized_seen: set[str] = set()
    for source, disposition, target in rows:
        source_path = package_root / source
        target_path = root / target
        if disposition == "INSTALL_CANONICAL":
            if not target_path.is_file():
                errors.append(f"INSTALL_CANONICAL: target missing {target}")
            elif not source_path.is_file():
                errors.append(f"INSTALL_CANONICAL: package source missing {source}")
            elif target in NORMALIZED_INSTALL_CANONICAL:
                expected_source, kind, removed_bytes = NORMALIZED_INSTALL_CANONICAL[target]
                normalized_seen.add(target)
                if source != expected_source:
                    errors.append(
                        f"INSTALL_CANONICAL: normalization source mismatch {source} -> {target}"
                    )
                    continue
                try:
                    expected_target = _canonicalize_explicit_install(
                        source_path.read_bytes(), kind, removed_bytes
                    )
                except ValueError as exc:
                    errors.append(f"INSTALL_CANONICAL: invalid frozen normalization {target}: {exc}")
                    continue
                if expected_target != target_path.read_bytes():
                    errors.append(
                        f"INSTALL_CANONICAL: normalized byte mismatch {source} -> {target}"
                    )
            elif source_path.read_bytes() != target_path.read_bytes():
                errors.append(f"INSTALL_CANONICAL: byte mismatch {source} -> {target}")
        elif disposition == "MERGE_INTO_EXISTING" and source.endswith(".md"):
            if not target_path.is_file() or not source_path.is_file():
                errors.append(f"MERGE_INTO_EXISTING: source or target missing {source} -> {target}")
            elif _normalize_merged_markdown(
                source_path.read_text(encoding="utf-8")
            ) not in _normalize_merged_markdown(target_path.read_text(encoding="utf-8")):
                errors.append(f"MERGE_INTO_EXISTING: canonical R2 section missing {source} -> {target}")
    missing_normalizations = set(NORMALIZED_INSTALL_CANONICAL) - normalized_seen
    if missing_normalizations:
        errors.append(
            "INSTALL_CANONICAL: explicit normalization paths absent from disposition: "
            + ", ".join(sorted(missing_normalizations))
        )
    duplicate_pairs = [
        (
            package_root / "01_REPO_OVERLAY/schemas/r2/reading-map-v1.schema.json",
            root / ".codex/schemas/reading-map-v1.schema.json",
        ),
        (
            package_root / "05_INDEPENDENT_ACCEPTANCE_PACKET/acceptance-result-v1.schema.json",
            root / "schemas/r2/acceptance-result-v1.schema.json",
        ),
    ]
    for source, target in duplicate_pairs:
        if not source.is_file() or not target.is_file() or source.read_bytes() != target.read_bytes():
            errors.append(f"DUPLICATE_OF_CANONICAL: binding mismatch {source.name} -> {target}")


def _check_normalization_record(root: Path, package_root: Path, errors: list[str]) -> None:
    record_path = (
        root
        / "governance/evidence/r2-authority-install/canonical-normalizations.yaml"
    )
    text = _read_text(record_path, errors, "R2_CANONICAL_NORMALIZATION")
    for token in [
        "semantic_change: false",
        "install_canonical_total: 108",
        "byte_exact_install_canonical: 98",
        "normalized_install_canonical: 10",
    ]:
        if token not in text:
            errors.append(f"R2_CANONICAL_NORMALIZATION: missing {token}")
    pattern = re.compile(
        r"^  - source: (\S+)\n"
        r"    target: (\S+)\n"
        r"    diff_type: (\S+)\n"
        r"    source_sha256: ([0-9a-f]{64})\n"
        r"    target_sha256: ([0-9a-f]{64})\n"
        r"    removed_ascii_bytes: ([0-9]+)$",
        re.MULTILINE,
    )
    rows = pattern.findall(text)
    targets = [row[1] for row in rows]
    if len(rows) != 10 or len(set(targets)) != 10:
        errors.append("R2_CANONICAL_NORMALIZATION: expected 10 unique normalization rows")
        return
    if set(targets) != set(NORMALIZED_INSTALL_CANONICAL):
        errors.append("R2_CANONICAL_NORMALIZATION: explicit target set mismatch")
        return
    for source, target, kind, source_hash, target_hash, removed in rows:
        expected_source, expected_kind, expected_removed = NORMALIZED_INSTALL_CANONICAL[target]
        expected_source_hash, expected_target_hash = NORMALIZED_INSTALL_HASHES[target]
        expected = (
            expected_source,
            expected_kind,
            str(expected_removed),
            expected_source_hash,
            expected_target_hash,
        )
        actual = (source, kind, removed, source_hash, target_hash)
        if actual != expected:
            errors.append(f"R2_CANONICAL_NORMALIZATION: frozen record mismatch {target}")
            continue
        source_path = package_root / source
        target_path = root / target
        if not source_path.is_file() or _sha256(source_path) != source_hash:
            errors.append(f"R2_CANONICAL_NORMALIZATION: source hash mismatch {source}")
        if not target_path.is_file() or _sha256(target_path) != target_hash:
            errors.append(f"R2_CANONICAL_NORMALIZATION: target hash mismatch {target}")


def _expected_decision_ids() -> set[str]:
    return {
        f"{group}{number:02d}"
        for group, count in EXPECTED_GROUP_COUNTS.items()
        for number in range(1, count + 1)
    }


def _field_values(text: str, field: str) -> list[str]:
    return re.findall(rf"^  {re.escape(field)}:\s*(.*?)\s*$", text, re.MULTILINE)


def _check_decisions_and_traceability(root: Path, errors: list[str]) -> set[str]:
    decisions_path = root / "governance/r2/decisions.r2.yaml"
    decisions_text = _read_text(decisions_path, errors, "R2_DECISIONS")
    ids = re.findall(r"^- decision_id:\s*(R2-[A-J][0-9]{2})\s*$", decisions_text, re.MULTILINE)
    expected = _expected_decision_ids()
    if len(ids) != 191:
        errors.append(f"R2_DECISION_COUNT_191: expected 191, found {len(ids)}")
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"R2_DECISION_IDS_UNIQUE: duplicates {duplicates}")
    if set(ids) != expected:
        errors.append(
            f"R2_DECISION_RANGE: missing={sorted(expected - set(ids))} extra={sorted(set(ids) - expected)}"
        )
    groups = _field_values(decisions_text, "group")
    if Counter(groups) != Counter(EXPECTED_GROUP_COUNTS):
        errors.append(f"R2_GROUP_COUNTS_EXACT: found {dict(Counter(groups))}")
    statuses = _field_values(decisions_text, "status")
    if len(statuses) != 191 or any(not item.startswith("FROZEN") for item in statuses):
        errors.append("R2_DECISIONS: every decision must retain a FROZEN status")
    options = _field_values(decisions_text, "option")
    if len(options) != 191 or any(not item.strip() for item in options):
        errors.append("R2_DECISIONS: every decision must retain a non-empty option")
    if not re.search(r"^decision_count:\s*191\s*$", decisions_text, re.MULTILINE):
        errors.append("R2_DECISIONS: registry decision_count is not 191")

    index_text = _read_text(root / "docs/authority/r2/R2_DECISION_INDEX.md", errors, "R2_INDEX")
    indexed = set(re.findall(r"\bR2-[A-J][0-9]{2}\b", index_text))
    if indexed != expected:
        errors.append(
            f"R2_DECISION_INDEX: missing={sorted(expected - indexed)} extra={sorted(indexed - expected)}"
        )

    trace_path = root / "governance/r2/traceability-matrix.r2.yaml"
    trace_text = _read_text(trace_path, errors, "R2_TRACEABILITY")
    traced = re.findall(r"^- decision_id:\s*(R2-[A-J][0-9]{2})\s*$", trace_text, re.MULTILINE)
    if len(traced) != 191 or len(set(traced)) != 191 or set(traced) != expected:
        errors.append("R2_TRACEABILITY_191_OF_191: traceability IDs do not exactly match decisions")
    authority_docs = re.findall(r"^  authority_document:\s*(\S.*?)\s*$", trace_text, re.MULTILINE)
    if len(authority_docs) != 191:
        errors.append(f"R2_TRACEABILITY: expected 191 authority documents, found {len(authority_docs)}")
    for relative in sorted(set(authority_docs)):
        if not (root / relative).is_file():
            errors.append(f"R2_TRACEABILITY: missing authority document {relative}")
    schema_refs = re.findall(r"^  - (schemas/r2/\S+\.schema\.json)\s*$", trace_text, re.MULTILINE)
    schema_compatibility_map = {
        "schemas/r2/reading-map-v1.schema.json": ".codex/schemas/reading-map-v1.schema.json"
    }
    for relative in sorted(set(schema_refs)):
        resolved = schema_compatibility_map.get(relative, relative)
        if not (root / resolved).is_file():
            errors.append(f"R2_TRACEABILITY: missing schema {relative} (mapped to {resolved})")
    acceptance_ids = re.findall(r"^  acceptance_id:\s*(\S+)\s*$", trace_text, re.MULTILINE)
    if len(acceptance_ids) != 191 or len(set(acceptance_ids)) != 191:
        errors.append("R2_TRACEABILITY: acceptance IDs must be 191 unique values")
    statuses = re.findall(r"^  implementation_status:\s*(\S+)\s*$", trace_text, re.MULTILINE)
    if len(statuses) != 191 or set(statuses) != {"NOT_IMPLEMENTED"}:
        errors.append("R2_TRACEABILITY: M2 implementation status must remain NOT_IMPLEMENTED")
    return expected


def _check_deferred_and_terms(root: Path, errors: list[str]) -> None:
    deferred_text = _read_text(
        root / "governance/r2/deferred-items.r2.yaml", errors, "R2_DEFERRED"
    )
    deferred = re.findall(r"^- deferred_id:\s*(\S+)\s*$", deferred_text, re.MULTILINE)
    if len(deferred) != 10 or len(set(deferred)) != 10:
        errors.append(f"R2_DEFERRED_IDS_UNIQUE: expected 10 unique IDs, found {len(deferred)}")
    statuses = _field_values(deferred_text, "status")
    if len(statuses) != 10 or set(statuses) != {"DEFERRED_WITH_FROZEN_BOUNDARY"}:
        errors.append("R2_DEFERRED: every item must retain a frozen deferred boundary")
    terms_text = _read_text(root / "governance/r2/terminology.r2.yaml", errors, "R2_TERMS")
    term_ids = re.findall(r"^- term_id:\s*(\S+)\s*$", terms_text, re.MULTILINE)
    if len(term_ids) != 33 or len(set(term_ids)) != 33:
        errors.append(f"R2_TERMS: expected 33 unique term IDs, found {len(term_ids)}")


def _check_sections(
    root: Path,
    package_root: Path,
    rows: Iterable[tuple[str, str, str]],
    errors: list[str],
) -> None:
    globally_seen: dict[str, str] = {}
    for path in sorted(root.rglob("*.md")):
        if any(part in {".git", "dist"} for part in path.parts):
            continue
        text = _read_text(path, errors, "R2_SECTION_IDS")
        for section_id in SECTION_PATTERN.findall(text):
            previous = globally_seen.get(section_id)
            relative = path.relative_to(root).as_posix()
            if previous is not None:
                errors.append(
                    f"R2_SECTION_IDS_UNIQUE: {section_id} occurs in both {previous} and {relative}"
                )
            globally_seen[section_id] = relative
    for source, disposition, target in rows:
        if disposition == "INSTALL_CANONICAL" and target.endswith(".md"):
            text = _read_text(root / target, errors, "R2_SECTION_IDS")
            if not SECTION_PATTERN.search(text):
                errors.append(f"R2_SECTION_IDS: installed Markdown lacks Section ID {target}")
        if disposition == "MERGE_INTO_EXISTING" and source.endswith(".md"):
            source_match = SECTION_PATTERN.search(_read_text(package_root / source, [], "source"))
            target_text = _read_text(root / target, errors, "R2_SECTION_IDS")
            if source_match is None or source_match.group(1) not in SECTION_PATTERN.findall(target_text):
                errors.append(f"R2_SECTION_IDS: merged Section ID missing {source} -> {target}")


def _walk_schema(node: Any, label: str, errors: list[str]) -> None:
    if isinstance(node, dict):
        if "type" in node:
            value = node["type"]
            allowed = {"null", "boolean", "object", "array", "number", "string", "integer"}
            if isinstance(value, str) and value not in allowed:
                errors.append(f"R2_SCHEMA_META: {label} has invalid type {value!r}")
            elif isinstance(value, list) and (
                not value or any(not isinstance(item, str) or item not in allowed for item in value)
            ):
                errors.append(f"R2_SCHEMA_META: {label} has invalid type array")
        if "required" in node and (
            not isinstance(node["required"], list)
            or any(not isinstance(item, str) for item in node["required"])
            or len(node["required"]) != len(set(node["required"]))
        ):
            errors.append(f"R2_SCHEMA_META: {label}.required must be unique strings")
        for key, value in node.items():
            _walk_schema(value, f"{label}/{key}", errors)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk_schema(value, f"{label}/{index}", errors)


def _check_schemas_and_json(root: Path, errors: list[str]) -> None:
    json_roots = [
        root / "schemas/r2",
        root / ".codex/routes",
        root / "workflow/examples",
    ]
    for base in json_roots:
        for path in sorted(base.glob("*.json")) if base.exists() else []:
            _read_json(path, errors, "R2_JSON_PARSE")
    schema_paths = sorted((root / "schemas/r2").glob("*.schema.json"))
    schema_paths.append(root / ".codex/schemas/reading-map-v1.schema.json")
    if len(schema_paths) != 10:
        errors.append(f"R2_SCHEMA: expected 10 machine-authoritative schemas, found {len(schema_paths)}")
    ids: dict[str, Path] = {}
    loaded: dict[Path, dict[str, Any]] = {}
    for path in schema_paths:
        schema = _read_json(path, errors, "R2_SCHEMA")
        if not isinstance(schema, dict):
            continue
        loaded[path] = schema
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"R2_SCHEMA_META: {path.relative_to(root)} is not Draft 2020-12")
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            errors.append(f"R2_SCHEMA_META: {path.relative_to(root)} lacks $id")
        elif schema_id in ids:
            errors.append(f"R2_SCHEMA_META: duplicate $id {schema_id}")
        else:
            ids[schema_id] = path
        _walk_schema(schema, path.relative_to(root).as_posix(), errors)
        if Draft202012Validator is not None:
            try:
                Draft202012Validator.check_schema(schema)
            except SchemaError as exc:
                errors.append(f"R2_SCHEMA_META: invalid schema {path.relative_to(root)}: {exc.message}")
    for path, schema in loaded.items():
        refs: list[str] = []

        def collect(node: Any) -> None:
            if isinstance(node, dict):
                if isinstance(node.get("$ref"), str):
                    refs.append(node["$ref"])
                for value in node.values():
                    collect(value)
            elif isinstance(node, list):
                for value in node:
                    collect(value)

        collect(schema)
        for reference in refs:
            if reference.startswith("#"):
                continue
            base = reference.split("#", 1)[0]
            if base not in ids:
                errors.append(
                    f"R2_SCHEMA_REFS: {path.relative_to(root)} references unknown schema {base}"
                )


def _check_authority_map(root: Path, errors: list[str]) -> None:
    text = _read_text(root / "governance/r2/authority-map.r2.yaml", errors, "R2_AUTHORITY_MAP")
    exact = [
        "governance/r2/decisions.r2.yaml",
        "docs/authority/r2/R2_TERMINOLOGY.md",
    ]
    for relative in exact:
        if relative not in text or not (root / relative).is_file():
            errors.append(f"R2_AUTHORITY_MAP: missing machine authority {relative}")
    required_roots = ["docs/authority/r2", "authoring", "schemas/r2", "game-package"]
    for relative in required_roots:
        if not (root / relative).is_dir():
            errors.append(f"R2_AUTHORITY_MAP: mapped root missing {relative}")
    for layer in ["PLAYER", "HOST", "MECHANICAL", "AUDIT"]:
        if f"id: {layer}" not in text:
            errors.append(f"R2_AUTHORITY_MAP: visibility layer missing {layer}")
    if "LOWER_RANK_MUST_CHANGE" not in text:
        errors.append("R2_AUTHORITY_MAP: conflict policy missing")


def _list_after_key(text: str, key: str, next_keys: Iterable[str]) -> list[str]:
    start = re.search(rf"^{re.escape(key)}:\s*$", text, re.MULTILINE)
    if start is None:
        return []
    tail = text[start.end() :]
    endpoints = [
        match.start()
        for candidate in next_keys
        if (match := re.search(rf"^{re.escape(candidate)}:\s*$", tail, re.MULTILINE)) is not None
    ]
    if endpoints:
        tail = tail[: min(endpoints)]
    return re.findall(r"^-\s+(.+?)\s*$", tail, re.MULTILINE)


def _check_safety(root: Path, errors: list[str]) -> None:
    text = _read_text(
        root / "governance/r2/content-safety-policy.r2.yaml", errors, "R2_CONTENT_SAFETY"
    )
    stages = _list_after_key(text, "repeat_filter_stages", ["player_safety_tools"])
    if len(stages) != 18 or set(stages) != EXPECTED_SAFETY_STAGES:
        errors.append(f"R2_CONTENT_SAFETY: expected exact 18 stages, found {stages}")
    prohibited_match = re.search(
        r"^  prohibited:\s*$([\s\S]*?)^  action:", text, re.MULTILINE
    )
    prohibited = (
        set(re.findall(r"^  -\s+(.+?)\s*$", prohibited_match.group(1), re.MULTILINE))
        if prohibited_match
        else set()
    )
    if prohibited != EXPECTED_MINOR_PROHIBITIONS:
        errors.append("R2_CONTENT_SAFETY: absolute minor sexual-harm red line is incomplete")
    if "BLOCK_AND_REDESIGN; LABEL_ONLY_NOT_ALLOWED" not in text:
        errors.append("R2_CONTENT_SAFETY: label-only retention is not forbidden")
    authority_text = _read_text(
        root / "docs/authority/r2/09_CONTENT_SAFETY_AND_ABSOLUTE_RED_LINES.md",
        errors,
        "R2_CONTENT_SAFETY",
    )
    for token in ["未成年", "性侵犯", "性剥削", "性胁迫", "性诱骗", "性交易", "性化奴役", "性化对象的呈现"]:
        if token not in authority_text:
            errors.append(f"R2_CONTENT_SAFETY: authority document lacks {token}")


def _check_supersession_and_layers(root: Path, errors: list[str]) -> None:
    decisions = _read_json(root / "governance/decisions.json", errors, "M1_SUPERSESSION")
    entries = decisions.get("decisions", []) if isinstance(decisions, dict) else []
    rr_o003 = next((item for item in entries if item.get("id") == "RR-O003"), None)
    if not isinstance(rr_o003, dict) or rr_o003.get("status") != "SUPERSEDED_BY_R2":
        errors.append("R2_M1_SUPERSESSION: RR-O003 is not SUPERSEDED_BY_R2")
    required_tokens = {
        "AGENTS.md": "governance/r2/deferred-items.r2.yaml",
        "docs/authority/00_PROJECT_CHARTER.md": "SUPERSEDED_BY_R2",
        "docs/authority/10_OPEN_DECISIONS.md": "SUPERSEDED_BY_R2",
        "authoring/story/00_STORY_BIBLE.md": "SUPERSEDED_BY_R2",
        "authoring/story/01_TRUTH_BIBLE.md": "SUPERSEDED_BY_R2",
        "authoring/story/02_MAIN_MYSTERY_GRAPH.md": "SUPERSEDED_BY_R2",
        "authoring/story/03_RETURN_HOME_ARC.md": "SUPERSEDED_BY_R2",
    }
    for relative, token in required_tokens.items():
        if token not in _read_text(root / relative, errors, "M1_SUPERSESSION"):
            errors.append(f"R2_M1_SUPERSESSION: {relative} lacks {token}")
    scope_text = _read_text(root / "governance/scope.json", errors, "M1_SUPERSESSION")
    if "M2 尚未实施" not in scope_text or "R2 已冻结" not in scope_text:
        errors.append("R2_M1_SUPERSESSION: scope does not distinguish frozen R2 from unstarted M2")
    forbidden_active_open = [
        "最终世界真相与回家条件仍为 OPEN",
        "真正归乡条件仍为 `OPEN`",
        "终极谜题仍为 `OPEN`",
        "当前无终极真相条目",
    ]
    active_paths = [
        root / "AGENTS.md",
        root / "docs/authority/00_PROJECT_CHARTER.md",
        root / "docs/authority/10_OPEN_DECISIONS.md",
        *sorted((root / "authoring/story").glob("0[0-4]_*.md")),
    ]
    combined = "\n".join(_read_text(path, errors, "M1_SUPERSESSION") for path in active_paths)
    for phrase in forbidden_active_open:
        if phrase in combined:
            errors.append(f"R2_M1_SUPERSESSION: conflicting active OPEN prose remains: {phrase}")
    truth_path = root / "authoring/story/01_TRUTH_BIBLE.md"
    truth = _read_text(truth_path, errors, "R2_TRUTH")
    truth_ids = re.findall(r"`(TRUTH-R2-[0-9]{3})`", truth)
    expected_truths = {f"TRUTH-R2-{number:03d}" for number in range(1, 13)}
    if set(truth_ids) != expected_truths or len(truth_ids) != 12:
        errors.append("R2_ACTIVE_TRUTHS: expected one active TRUTH-R2-001..012 set")
    for token in [
        "AUTHOR / GM / MECHANICAL ONLY",
        "高维世界坍缩后的维度残片",
        "现实及其他世界发生异常纠缠",
        "因果律武器表现载体",
        "失败主角团、牺牲者、维护者与扭曲因果聚合体",
        "外部悖论奇点制成的因果炸弹",
        "回归现实只能被接纳为共同梦境",
    ]:
        if token not in truth:
            errors.append(f"R2_ACTIVE_TRUTHS: Truth Bible lacks {token}")
    reveal = _read_text(root / "authoring/story/04_REVEAL_POLICY.md", errors, "R2_LAYERS")
    for layer in [
        "PUBLIC_WORLD",
        "CHARACTER_PRIVATE",
        "PARTY_SHARED",
        "HOST_ONLY",
        "MECHANICAL_ONLY",
        "AUDIT_ONLY",
    ]:
        if layer not in reveal:
            errors.append(f"R2_LAYERS: reveal policy lacks {layer}")
    runtime_text = "\n".join(
        _read_text(path, errors, "RUNTIME_BOUNDARY")
        for path in [root / "game-package/manifest.json", root / "game-package/package.lock.json"]
    )
    if "authoring/" in runtime_text or "TRUTH_BIBLE" in runtime_text or "Truth Bible" in runtime_text:
        errors.append("RUNTIME_BOUNDARY: authoring or Truth Bible leaked into runtime manifest/lock")


def _check_routes_and_handoffs(root: Path, package_root: Path, errors: list[str]) -> None:
    routes_text = _read_text(
        root / "governance/r2/progressive-disclosure-routes.r2.yaml", errors, "R2_ROUTES"
    )
    if not re.search(r"soft_ratio:\s*0\.55", routes_text) or not re.search(
        r"hard_ratio:\s*0\.7", routes_text
    ):
        errors.append("R2_ROUTES: governance ratios are not 55/70")
    if SOFT_LIMIT != 0.55 or HARD_LIMIT != 0.70:
        errors.append("R2_ROUTES: repository-native route engine ratios are not 55/70")
    for route_id in ["R2-AUTHORITY-INSTALL", "M2-VERTICAL-SLICE"]:
        if f"route_id: {route_id}" not in routes_text:
            errors.append(f"R2_ROUTES: governance route missing {route_id}")
    requests = [
        root / ".codex/routes/r2-authority-install-plan-request.json",
        root / ".codex/routes/r2-authority-install-implement-request.json",
        root / ".codex/routes/r2-authority-install-accept-request.json",
        root / ".codex/routes/r2-authority-install-repair-request.json",
    ]
    for request_path in requests:
        request = _read_json(request_path, errors, "R2_ROUTES")
        if not isinstance(request, dict):
            continue
        try:
            validate_request(request)
            if (root / ".git").exists():
                reading_map = generate_reading_map(
                    request,
                    repo_root=root,
                    allow_roots=(package_root,)
                    if request_path.name.endswith("plan-request.json")
                    else (),
                )
                ratio = reading_map["context_budget"]["ratio"]
                if ratio > 0.55:
                    errors.append(
                        f"R2_ROUTES: usable request exceeds soft limit {request_path.name}: {ratio}"
                    )
        except RouteError as exc:
            errors.append(f"R2_ROUTES: invalid request {request_path.name}: {exc.code}: {exc}")
    prompt_paths = [
        root / f".codex/prompts/r2/{milestone}/{role}.md"
        for milestone in ["R2-AUTHORITY-INSTALL", "M2-VERTICAL-SLICE"]
        for role in ["PLAN", "IMPLEMENT", "ACCEPT", "REPAIR"]
    ]
    for path in prompt_paths:
        if not path.is_file():
            errors.append(f"R2_PROMPTS: missing {path.relative_to(root)}")
    agent_paths = [
        root / ".opencode/r2/README.md",
        root / ".opencode/r2/SESSION_START.md",
        root / ".opencode/r2/RETURN_CONTRACT.md",
        root / ".grok/r2/README.md",
        root / ".grok/r2/SESSION_START.md",
        root / ".grok/r2/RETURN_CONTRACT.md",
        root / "docs/operations/agents/r2/portable-agent/README.md",
        root / "docs/operations/agents/r2/portable-agent/RETURN_CONTRACT.md",
        root / "docs/operations/agents/r2/RETURN_ENVELOPE_ADAPTER.md",
    ]
    for path in agent_paths:
        if not path.is_file():
            errors.append(f"R2_HANDOFFS: missing {path.relative_to(root)}")
    adapters = sorted((root / "docs/operations/agents/r2/portable-agent/adapters").glob("*_ADAPTER.md"))
    if len(adapters) != 5:
        errors.append(f"R2_HANDOFFS: expected 5 portable adapters, found {len(adapters)}")
    handoff_text = "\n".join(
        _read_text(path, errors, "R2_HANDOFFS") for path in agent_paths if path.is_file()
    ).lower()
    for token in ["candidate", "evidence", "limitations"]:
        if token not in handoff_text:
            errors.append(f"R2_HANDOFFS: return contracts lack {token}")


def _check_m2_and_acceptance(root: Path, errors: list[str]) -> None:
    m2_inputs = [
        "M2_VERTICAL_SLICE_INPUT_CONTRACT.md",
        "M2_REFERENCE_WORK_PACKAGES.yaml",
        "M2_TECHNICAL_VALIDATION_MATRIX.md",
        "M2_STOP_CONDITIONS.md",
    ]
    for name in m2_inputs:
        if not (root / "docs/implementation/r2" / name).is_file():
            errors.append(f"R2_M2_INPUT: missing {name}")
    provenance = _read_text(
        root / "governance/evidence/r2-authority-install/package-provenance.yaml",
        errors,
        "R2_PROVENANCE",
    )
    if "M2_IMPLEMENTATION_STARTED: false" not in provenance:
        errors.append("R2_M2_INPUT: M2_IMPLEMENTATION_STARTED is not false")
    forbidden_m2_runtime = [
        root / "game-package/modules/m2-slice",
        root / "game-package/scripts/m2",
    ]
    if any(path.exists() for path in forbidden_m2_runtime):
        errors.append("R2_M2_INPUT: M2 runtime implementation exists")
    acceptance_names = {
        "R2_AUTHORITY_INSTALL_ACCEPTANCE.md",
        "M2_VERTICAL_SLICE_STRICT_ACCEPTANCE.md",
        "PROGRESSIVE_DISCLOSURE_ACCEPTANCE.md",
        "CONTENT_SAFETY_FILTER_ACCEPTANCE.md",
        "TRACEABILITY_ACCEPTANCE.md",
        "FAILED_ACCEPTANCE_REPAIR_PROMPT.md",
        "README.md",
    }
    acceptance_root = root / "docs/acceptance/r2"
    found = {path.name for path in acceptance_root.glob("*.md")} if acceptance_root.exists() else set()
    if found != acceptance_names:
        errors.append(
            f"R2_ACCEPTANCE_PACKET: missing={sorted(acceptance_names - found)} extra={sorted(found - acceptance_names)}"
        )
    if (acceptance_root / "acceptance-result-v1.schema.json").exists():
        errors.append("R2_ACCEPTANCE_PACKET: duplicate acceptance schema must not be installed")


def _check_task_examples(root: Path, errors: list[str]) -> None:
    schema = _read_json(root / "workflow/task-packet.schema.json", errors, "R2_TASK_PACKET")
    if not isinstance(schema, dict):
        return
    for name, owner, task_type in [
        ("r2-script-task-packet.json", "opencode", "script"),
        ("r2-art-task-packet.json", "grok", "art"),
    ]:
        packet = _read_json(root / "workflow/examples" / name, errors, "R2_TASK_PACKET")
        if not isinstance(packet, dict):
            continue
        for issue in validate_schema_instance(packet, schema):
            errors.append(f"R2_TASK_PACKET: {name}: {issue}")
        if packet.get("owner") != owner or packet.get("task_type") != task_type:
            errors.append(f"R2_TASK_PACKET: {name} has incorrect role identity")
        combined = json.dumps(packet, ensure_ascii=False).lower()
        for token in ["candidate", "evidence", "limitations"]:
            if token not in combined:
                errors.append(f"R2_TASK_PACKET: {name} lacks return {token}")
        if "m2_implementation_started=no" not in combined:
            errors.append(f"R2_TASK_PACKET: {name} does not state M2 remains unstarted")


def _check_conflicts_and_provenance(root: Path, errors: list[str]) -> None:
    conflicts = _read_text(
        root / "governance/evidence/r2-authority-install/integration-conflicts.yaml",
        errors,
        "R2_CONFLICTS",
    )
    ids = re.findall(r"^- conflict_id:\s*(R2-INT-[0-9]{3})\s*$", conflicts, re.MULTILINE)
    expected = {f"R2-INT-{number:03d}" for number in range(1, 13)}
    if len(ids) != 12 or set(ids) != expected:
        errors.append("R2_CONFLICTS: expected exact R2-INT-001..012 classification")
    categories = re.findall(r"^  classification:\s*(\S+)\s*$", conflicts, re.MULTILINE)
    allowed = {
        "PACKAGE_DECLARABLE",
        "PLATFORM_CAPABILITY_PROBE",
        "PLATFORM_CHANGE_PROPOSAL",
        "R2_COMPATIBILITY_ADAPTER",
        "BLOCKED_DESIGN_CONFLICT",
    }
    if len(categories) != 12 or any(item not in allowed for item in categories):
        errors.append("R2_CONFLICTS: invalid or incomplete classifications")
    statuses = re.findall(r"^  status:\s*(\S+)\s*$", conflicts, re.MULTILINE)
    if len(statuses) != 12 or set(statuses) != {"DEFERRED_WITH_NON_BLOCKING_PROOF"}:
        errors.append("R2_CONFLICTS: every item must retain non-blocking proof")
    provenance = _read_text(
        root / "governance/evidence/r2-authority-install/package-provenance.yaml",
        errors,
        "R2_PROVENANCE",
    )
    required = [
        "package_version: 1.0.0",
        "package_manifest_sha256: a5adb9fad5439926e0c8d46f23f3e3e107812bdd9ce13097acea04b8cc0a7ba1",
        "sha256sums_sha256: 2d65a2ea9fefffc4f8e785fe2e55a0bdc83b7a54559afbb51162daedc0ab8e72",
        "source_policy: READ_ONLY",
        "byte_exact: 98",
        "repository_whitespace_normalized: 10",
        "record: governance/evidence/r2-authority-install/canonical-normalizations.yaml",
        "M2_IMPLEMENTATION_STARTED: false",
        "GAME_PACKAGE_RUNTIME_CHANGED: false",
        "PLATFORM_REPOSITORY_CHANGED: false",
    ]
    for token in required:
        if token not in provenance:
            errors.append(f"R2_PROVENANCE: missing {token}")


def _check_runtime_diff(root: Path, errors: list[str]) -> None:
    if not (root / ".git").exists():
        return
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", PINNED_SOURCE_COMMIT, "--"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        errors.append(f"RUNTIME_UNCHANGED: cannot diff pinned source: {result.stderr.strip()}")
        return
    paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    forbidden = [
        path
        for path in paths
        if path == "game-package/package.lock.json"
        or path.startswith("game-package/")
        or path.startswith("dist/")
        or path.endswith(".lua")
        or path.startswith("TRPG_PLATFORM/")
    ]
    if forbidden:
        errors.append(f"RUNTIME_UNCHANGED: forbidden source-to-candidate changes {forbidden}")


def validate_r2_install(
    project_root: Path = PROJECT_ROOT,
    package_root: Path = DEFAULT_PACKAGE_ROOT,
) -> list[str]:
    root = project_root.resolve()
    package = package_root.resolve()
    errors: list[str] = []
    _check_package_integrity(package, errors)
    rows = _parse_disposition(root, errors)
    _check_installed_bytes(root, package, rows, errors)
    _check_normalization_record(root, package, errors)
    _check_yaml_files(root, errors)
    _check_decisions_and_traceability(root, errors)
    _check_deferred_and_terms(root, errors)
    _check_sections(root, package, rows, errors)
    _check_schemas_and_json(root, errors)
    _check_authority_map(root, errors)
    _check_safety(root, errors)
    _check_supersession_and_layers(root, errors)
    _check_routes_and_handoffs(root, package, errors)
    _check_m2_and_acceptance(root, errors)
    _check_task_examples(root, errors)
    _check_conflicts_and_provenance(root, errors)
    _check_runtime_diff(root, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the repository-native R2 authority installation")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--package-root", type=Path, default=DEFAULT_PACKAGE_ROOT)
    args = parser.parse_args(argv)
    errors = validate_r2_install(args.project_root, args.package_root)
    if errors:
        print("R2_VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("R2_VALIDATION: PASS")
    print("- package integrity and 124-file disposition: PASS")
    print("- 191 decisions, exact groups, index, traceability, and deferred register: PASS")
    print("- YAML/JSON/Schema and stable Section IDs: PASS")
    print("- M1 supersession, active truth, visibility layers, and content safety: PASS")
    print("- Codex routes, agent handoffs, M2 inputs, and acceptance packet: PASS")
    print("- authoring/runtime boundary and pinned-source runtime diff: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
