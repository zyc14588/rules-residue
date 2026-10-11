from __future__ import annotations

import hashlib
import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))
PLAN_ROOT = PROJECT_ROOT / ".codex" / "plans" / "m2-vertical-slice"

REQUIRED_BATCH_FIELDS = {
    "id",
    "state",
    "objective",
    "dependencies",
    "authority_ids",
    "r2_decision_ids",
    "input_sections",
    "allowed_paths",
    "forbidden_paths",
    "codex_responsibilities",
    "opencode_responsibilities",
    "grok_responsibilities",
    "platform_probes",
    "schemas",
    "fixtures",
    "tests",
    "negative_tests",
    "acceptance_gates",
    "stop_conditions",
    "rollback_recovery",
    "expected_commit_boundary",
    "non_goals",
    "reading_map_request",
}

PROBE_RESULT_REQUIRED_FIELDS = [
    "probe_id",
    "r2_requirement",
    "classification",
    "target_system",
    "existing_capability",
    "probe_procedure",
    "commands_actions_actually_run",
    "evidence_paths",
    "observed_result",
    "expected_result",
    "execution_status",
    "root_cause",
    "adapter_feasibility",
    "platform_change_necessity",
    "downstream_blocked_batches",
]

PROBE_EXECUTION_STATUSES = [
    "PASS",
    "FAIL",
    "NOT_RUN",
    "BLOCKED_EXTERNAL",
    "BLOCKED_ENVIRONMENT",
]

BATCH_RESULTS = [
    "PASS",
    "FAIL",
    "BLOCKED_EXTERNAL",
    "BLOCKED_ENVIRONMENT",
    "BLOCKED_DESIGN_CONFLICT",
]

RECOVERY_EVIDENCE_PATH = (
    Path("reports")
    / "m2"
    / "probes"
    / "closeouts"
    / "m2-b001-recovery-closeout-001"
    / "evidence.json"
)
FROZEN_RECOVERY_PENDING = "FROZEN_WITH_RECOVERY_EVIDENCE_PENDING_LIFECYCLE_CLOSEOUT"
ACCEPTED_WITH_BLOCKERS = "ACCEPTED_WITH_DOWNSTREAM_BLOCKERS"
INVALID_MIXED_STATE = "INVALID_MIXED_STATE"
EXPECTED_RECOVERY_BLOCKERS = ["R2-INT-011", "R2-INT-012", "DEFER-R2-C14-001"]
SCHEMA_PREPARATION_BATCH = "M2-B017"
SCHEMA_PREPARATION_ACTION = "IMPLEMENT_M2_B017_C14_SCHEMA_PREPARATION"
SCHEMA_PREPARATION_PATHS = [
    "schemas/r2/exemption-protocol-v1.schema.json",
    "tests/m2/fixtures/schema/exemption-protocol-v1.json",
    "tests/m2/schema/test_exemption_protocol.py",
    "docs/implementation/m2/semantics/EXEMPTION_PROTOCOL_V1.md",
]
SCHEMA_PREPARATION_APPROVAL = ".codex/plans/m2-vertical-slice/evidence/owner-c14-template-approval.json"
SCHEMA_PREPARATION_ROUTE = ".codex/routes/m2-b017-schema-preparation-implement-request.json"
SCHEMA_PREPARATION_DOCUMENT = ".codex/plans/m2-vertical-slice/B017_C14_SCHEMA_PREPARATION.md"
SCHEMA_PREPARATION_SOURCE = {
    "commit": "6caf57cdc1127e84546459766949e0da664bb2f9",
    "tree": "ec6cb5e7fdc0c93f09862fcf032dbb61393293a1",
    "approval_path": SCHEMA_PREPARATION_APPROVAL,
    "approval_sha256": "d83651399f3676574a21dc581fe87640c2a3407b1ae7a938157e1691a16f2c7a",
    "approved_proposal_sha256": "855ad32fe59d26783bb4b37f411813155ed984b9b1b41d65ac7c6b5b2ae61ac3",
    "approved_section": "2",
}
LEGACY_BATCHES_SHA256 = "78abb82ae30e5866c55ef9c72bbbf9ad839c1b91a8a494c04bb9af9288634f7c"
SCHEMA_PREPARATION_ENVELOPE_SHA256 = "a4182c180ba2cb83c1c4ddc8d37bf52cf9bc6a826877398a904653ea6872138d"
SCHEMA_PREPARATION_REBIND_TEST = "tests/m2/probes/test_r2_int_010_platform_identity_rebind.py"
SCHEMA_PREPARATION_REBIND_TEST_SHA256 = "29acfe5a56e34476c6de655d2c5ea169e4dcb5b9780871863d66f54e8a5311e2"
# The historical bridge may run the fixed 6caf suite only while the current
# legacy implementation retains its accepted 6caf bytes. It imports no other
# repository implementation modules; the bridge's new bytes are pinned above.
SCHEMA_PREPARATION_LEGACY_IMPLEMENTATION_SHA256 = {
    "tests/m2/probes/validate_r2_int_010_platform_identity_rebind.py": "b4c1c4b5d3544335f1ba0d7d318a3d12a359e66d1dd8c54cd9c57f0b57ae9d4a",
}
# This allocation is one exact native PLAN transition, not a general exemption
# from preservation of previously accepted M2 state.
SCHEMA_PREPARATION_STATE_SHA256 = {
    ".codex/state/MILESTONE_PLAN.yaml": "7af9d061d23e20240baa30c3f35f163d9463d87a32206b0492f8c6f1bf912e16",
    ".codex/plans/m2-vertical-slice/M2_VERTICAL_SLICE_PLAN.md": "9f44d6da150b95c6c1983e9cf8d9bcd1d94180b4657da67c39081677f1057671",
    ".codex/plans/m2-vertical-slice/batches.json": "abce06071a63c54b16be70cd413de558322a7f93681feb1f8fc3fcd68855ca42",
    ".codex/plans/m2-vertical-slice/capability-probes.json": "e25046b5176224af105694cf1c244360a1608c0d173d754c1821a162915cae02",
    ".codex/plans/m2-vertical-slice/controls.json": "a6898b74ba1d0ccf2d2357c8120aac16ab708fd45a8d91e3674d7af47d787a3c",
}

# A second exact transition consumes the independent acceptance of the four
# files. The original PLAN bytes and frozen envelope above remain authoritative.
SCHEMA_ACCEPTED_RECEIPT = ".codex/plans/m2-vertical-slice/b017-accepted-lifecycle.json"
SCHEMA_ACCEPTED_RECEIPT_SHA256 = "d714515481fbd716ce51cc1aacd9c9ac24d7bef3fa7ed6632886a22ed7199f9b"
SCHEMA_ACCEPTED_CANDIDATE = {
    "commit": "0201c39cb67efc62b217930ad3059fb0695517b8",
    "tree": "6d728ce25febfdeea263e7b9193452dd4a235716",
}
SCHEMA_ACCEPTED_PLAN = {
    "commit": "d3ef96d81da9694c1d270dfc36e9ff888b786da3",
    "tree": "2eb60e9453f64dbc1a9abe73e7a23054e5e26318",
}
SCHEMA_ACCEPTED_ACTION = "PLAN_REMAINING_M2_B002_BLOCKERS_R2_INT_011_R2_INT_012_DEFER_R2_C14_001"
SCHEMA_ACCEPTED_STATE_SHA256 = {
    ".codex/state/MILESTONE_PLAN.yaml": "0ad6dccf744de63c385e07dc6dc3e6143af10392cf4cbf816f1efd573e409f3d",
    ".codex/plans/m2-vertical-slice/M2_VERTICAL_SLICE_PLAN.md": "49edb6d9b02942b59e28b53cd2fdd24f6da7acc951422dcb8a7aef84a129926a",
    ".codex/plans/m2-vertical-slice/batches.json": "19248bd0681808e5e7b6759402165a366e47481aecdff39b20a4d3f14c65d4bd",
    ".codex/plans/m2-vertical-slice/capability-probes.json": "a64ea1e047ff09074706e6e1488e0053a2b083e9bd64579cfc3d3b303a4350c3",
    ".codex/plans/m2-vertical-slice/controls.json": "0aa887ba9e9ed451febdb53218681f24871af880baca62349a3ddd4a2f446904",
}
SCHEMA_ACCEPTED_EVIDENCE_SHA256 = {
    "independent_report": "09db9be465ea5eec8f77e55c965684d9d2d37ce8f052ba588480435cf6457484",
    "independent_manifest": "c0693af1301db6b669394393f62fc7ad2d37b0c6641a7365fcc26f0f467b6412",
    "root_acceptance": "245bc5c1ead2f702b9a9b524bdc3aa49cbbfb5f36729355adde3d6ff0a6ef1f6",
}


# Exact additional PLAN transition. No production safety admission lives here.
CONTENT_SAFETY_BATCH = "M2-B018"
CONTENT_SAFETY_ACTION = "IMPLEMENT_M2_B018_CONTENT_SAFETY_ADMISSION"
CONTENT_SAFETY_SOURCE = {"commit": "7d5c3f58fa42c22288899e4f5be29e97b7a6b25c", "tree": "89e2bfaa03261e556b982aee8a9c305e69482099"}
CONTENT_SAFETY_CONTRACT = ".codex/plans/m2-vertical-slice/b018-registration-contract.json"
CONTENT_SAFETY_DOCUMENT = ".codex/plans/m2-vertical-slice/B018_CONTENT_SAFETY_ADMISSION.md"
CONTENT_SAFETY_ROUTE = ".codex/routes/m2-b018-content-safety-admission-implement-request.json"
CONTENT_SAFETY_SCHEMA = "schemas/story-construction/content-safety-receipt-v1.schema.json"
CONTENT_SAFETY_CONTRACT_SHA256 = "e058ef5fa75269261ea0646d2a0ac5c076732b6298c35fb9e22bc6e974c53aa0"
B018_LEGACY_EVIDENCE = {
    "docs/implementation/m2/probes/r2-int-010-platform-identity-rebind-v1.schema.json": "0273df7ac2b7de3980052e3c92ec29b2b8b1f8f6de2e4d29a82ba68bad4affad",
    "reports/m2/probes/external/r2-int-010-platform-identity-rebind/platform-acceptance.json": "e26aef955b6336cbf3431067e5c46cbafbdf010216aeea8270bd1b2dc87ac521",
    "reports/m2/probes/external/r2-int-010-platform-identity-rebind/rebind.json": "f219c7932e381fc086870c14e5737e81c95c892f287e5515518f26aecf00ae64",
    "reports/m2/probes/external/r2-int-010-platform-identity-rebind/evidence-manifest.json": "04d1fc81d5873424d2fd7b3a0f4ce09cd4d51e0407481fc944ca20f0e6a6df61",
    "reports/m2/probes/external/r2-int-010-platform-identity-rebind/execution-records.json": "f2d790c148edc4026e0d3921dc641294d1b781c844b9fda6daee3726cdca4fe0",
    "reports/m2/probes/external-evidence-index-v3.json": "1417d9f911ea5bc9015565b707598e18413af9431b14a4e8b64d0fafb1ecf609",
}


# One exact private lifecycle successor to the independently accepted B018 business.
CONTENT_SAFETY_ACCEPTED_RECEIPT = ".codex/plans/m2-vertical-slice/b018-accepted-lifecycle.json"
CONTENT_SAFETY_ACCEPTED_RECEIPT_SHA256 = "06f74dc6013f4c696ee87fa7dc6e650cae953a7cdae460dd4afa211e77834ff7"
CONTENT_SAFETY_ACCEPTED_PLAN = {
    "commit": "d84be09151b746326f7bcf14f629b15b9203ab3a",
    "tree": "94167e82faa85bb7f5ef5eaa2db3f0e0d3a3f800"
}
CONTENT_SAFETY_ACCEPTED_CANDIDATE = {
    "commit": "07b68734a5c6cf554636d9e8d1e994c58654c276",
    "tree": "75a6dc92ed164d28bb4cea0f3fda974405ea81df"
}
CONTENT_SAFETY_ACCEPTED_ENVELOPE_SHA256 = "01303f75b9a48fc71ad82dd2bf0be8b9ed1f028b63f03a98d2ba7f6e4f879e93"
CONTENT_SAFETY_ACCEPTED_ARTIFACTS = {
    "schemas/story-construction/content-safety-receipt-v1.schema.json": "fbfeacc563c54e3e204728afebf9a0aee98b85810e4f93d3671c2aed355a5aa8",
    "tools/lib/content_safety_evidence.py": "fc67bbdd1ba5ec6b49d0db2c3c69f5c6a3f8388123f9f3ca4980db69a2ee2360",
    "tools/content_safety_control.py": "9e8f9fab84603d5ced144d888651c073cb267f0020baa851ce2ef8dd40a2fbe3",
    "tools/content_safety_consumers.py": "a110b22f5b9f96dbfcf6af325c4c7d228b1c9ec5be8e47892d76c1e90cf27ca9",
    "tools/build_package.py": "28b0dd92887443c923dd37251d41923247a35e2c458bbe4ab885d06f800a846f",
    "tools/run_acceptance.py": "8b3b5ebdcce8fa03a1851ed379df9a85210b58997b12ce576fcca3a4195dfad9",
    "tests/test_content_safety_evidence.py": "c65f6b5621c0cb4fcee8a695912021e83a915a7ad9037cd11994e14475f35e3c",
    "tests/test_content_safety_consumers.py": "972c71823cfb0f17e222dd9359613b3a90489f43d7a63342de5fa919f63f0451",
    "tests/test_content_safety_entrypoints.py": "539fc37e125b7df5f60727dd3e4b108e874226019d012507a9bb5e1f784782a1",
    "docs/implementation/m2/semantics/CONTENT_SAFETY_EVIDENCE_V1.md": "ff5036b5888fa3cbbcc01fa3088323964312087a46f63b253bd3dbd31b14974d",
    "tests/test_package.py": "06fd6d3bbe012ec6d4e10d0cde4cb68053506f221cf381a2f43a6c19d23ae5d7",
    "tests/test_module_registry.py": "c83d1b00b88511c455a7f4621555b34e15fc6f593ef72075b73beb60904a939b",
    "tests/test_platform_v2_probe_adapter.py": "f9fae8b7561a3399e1cac37d4bde77ee7a7bde56c7a59a55d83832ed88a1d978"
}
CONTENT_SAFETY_ACCEPTED_GIT_BLOBS = {
    "schemas/story-construction/content-safety-receipt-v1.schema.json": {
        "mode": "100644",
        "blob": "fc9d356371890f4e900c518dfe546377d42a721d"
    },
    "tools/lib/content_safety_evidence.py": {
        "mode": "100644",
        "blob": "487f81d887241326e46ac35dd291ffb3c803ef86"
    },
    "tools/content_safety_control.py": {
        "mode": "100644",
        "blob": "991c7ca36c82ffc725dd214ce7e57f428acdd817"
    },
    "tools/content_safety_consumers.py": {
        "mode": "100644",
        "blob": "fd658069ddf351b53e73b53e0e538110049fb6a4"
    },
    "tools/build_package.py": {
        "mode": "100644",
        "blob": "96c2ca77b87bbb9dd4400f5e6b3ee4c67ddaf3cb"
    },
    "tools/run_acceptance.py": {
        "mode": "100644",
        "blob": "5696cc7caab2ee1ee16b18b37611acbe35eea0fa"
    },
    "tests/test_content_safety_evidence.py": {
        "mode": "100644",
        "blob": "6b422bfdd74ab2dc76fb926393b844bc761cf1eb"
    },
    "tests/test_content_safety_consumers.py": {
        "mode": "100644",
        "blob": "391a98187371804a5309c6672f7a75405414c061"
    },
    "tests/test_content_safety_entrypoints.py": {
        "mode": "100644",
        "blob": "b24da33b8c0ee9e06f738bed13de38de7a14a0dc"
    },
    "docs/implementation/m2/semantics/CONTENT_SAFETY_EVIDENCE_V1.md": {
        "mode": "100644",
        "blob": "1d9827b31d5a683b2d19d9b0188d11990ee6e10d"
    },
    "tests/test_package.py": {
        "mode": "100644",
        "blob": "7daa902ff9bccb698aa6255c4d83b43b681dcbba"
    },
    "tests/test_module_registry.py": {
        "mode": "100644",
        "blob": "894793e23bbe0734ed587e1bea0204bbcf1bbf57"
    },
    "tests/test_platform_v2_probe_adapter.py": {
        "mode": "100644",
        "blob": "e46a57535a6cb963ccc775809c9b7c7564233f78"
    }
}
CONTENT_SAFETY_ACCEPTED_STATE_SHA256 = {
    ".codex/state/MILESTONE_PLAN.yaml": "b10e682a12d4abe55f48e47cd95298d93fe7eea3d90448e57c4892d611edaea9",
    ".codex/plans/m2-vertical-slice/M2_VERTICAL_SLICE_PLAN.md": "758f2eec07c16b8d62c312fb639beff7558410b6539664d470b3b2c65c333ad6",
    ".codex/plans/m2-vertical-slice/batches.json": "93f2bc64eebde92f89b67516b4643971a19d64f6e004c8443de7f4260de94df4",
    ".codex/plans/m2-vertical-slice/capability-probes.json": "68031d372846873ccf4b60acc50fd40ee6e8e937129170c9ae80433c255a5f48",
    ".codex/plans/m2-vertical-slice/controls.json": "870f94c4c6ecf6e2363a58758b1bbc57722604b5d48b4eadba36b84927de704d"
}
CONTENT_SAFETY_ACCEPTED_EVIDENCE_SHA256 = {
    "root_reception": "696e2f2d25e255e0ca631b61ff0aea668c2bb3c1032591c1f94b67f1daa5c948",
    "independent_result": "36fdbb2e98b3c8527d828918d0d2a73ae2293c39f132e56ca4b89f0a346290a4",
    "independent_receipt": "bcbd122b2d2aca889f3095abd727f190a9d0775ae56bf6ce8845aa09349f30fa"
}


def _b018_json(raw: bytes) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("nonfinite JSON value")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def _actual_regular_bytes(root: Path, relative: str) -> bytes:
    path = root / relative
    for part in (path, *path.parents):
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError(f"non-regular/symlink path: {relative}")
    if not path.is_file():
        raise ValueError(f"missing or non-regular file: {relative}")
    return path.read_bytes()


def _b018_git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE,
                                   env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"})


def _b018_source_bytes(root: Path, path: str) -> bytes:
    return _b018_git(root, "show", CONTENT_SAFETY_SOURCE["commit"] + ":" + path)


def _raw_batch_rows(raw: bytes) -> list[bytes]:
    text = raw.decode("utf-8")
    match = re.search(r'"batches"\s*:\s*\[', text)
    if match is None:
        raise ValueError("batch array missing")
    pos = match.end()
    decoder = json.JSONDecoder()
    rows = []
    while True:
        while pos < len(text) and text[pos] in " \t\r\n,":
            pos += 1
        if text[pos] == "]":
            return rows
        _, end = decoder.raw_decode(text, pos)
        rows.append(text[pos:end].encode("utf-8"))
        pos = end


def has_content_safety_registration(root: Path, batches: Any = None) -> bool:
    if any((root / p).exists() or (root / p).is_symlink() for p in
           (CONTENT_SAFETY_CONTRACT, CONTENT_SAFETY_DOCUMENT, CONTENT_SAFETY_ROUTE)):
        return True
    return isinstance(batches, dict) and any(
        isinstance(item, dict) and item.get("id") == CONTENT_SAFETY_BATCH
        for item in batches.get("batches", []) if isinstance(batches.get("batches"), list)
    )


def legacy_evidence_byte_errors(root: Path) -> list[str]:
    errors = []
    for relative, expected in B018_LEGACY_EVIDENCE.items():
        try:
            if hashlib.sha256(_regular_bytes(root, relative)).hexdigest() != expected:
                errors.append(f"B018 legacy evidence byte drift: {relative}")
        except (OSError, ValueError) as exc:
            errors.append(f"B018 legacy evidence rejected: {exc}")
    return errors


def has_content_safety_accepted_lifecycle(root: Path, batches: Any = None) -> bool:
    """Partial presence is an obligation to validate, never permission to fall back."""
    receipt = root / CONTENT_SAFETY_ACCEPTED_RECEIPT
    if receipt.exists() or receipt.is_symlink():
        return True
    if isinstance(batches, dict):
        projection = batches.get("lifecycle_projection")
        if isinstance(projection, dict) and CONTENT_SAFETY_BATCH in projection:
            return True
    for relative in CONTENT_SAFETY_ACCEPTED_STATE_SHA256:
        try:
            raw = _regular_bytes(root, relative)
        except (OSError, ValueError):
            continue
        if (b"<!-- SECTION-ID: M2-B018-ACCEPTED-LIFECYCLE -->" in raw
                or (not relative.endswith(".md")
                    and re.search(rb'"M2-B018"\s*:\s*\{', raw) is not None)):
            return True
    return False


def _legacy_content_safety_accepted_evidence_errors(root: Path) -> list[str]:
    """Pure exact B018 evidence check; no scheduling, recovery or SCG recursion."""
    root = root.resolve()
    errors: list[str] = []
    try:
        raw = _regular_bytes(root, CONTENT_SAFETY_ACCEPTED_RECEIPT)
        receipt = _b018_json(raw)
        if hashlib.sha256(raw).hexdigest() != CONTENT_SAFETY_ACCEPTED_RECEIPT_SHA256:
            raise ValueError("lifecycle receipt byte drift")
        expected = {
            "schema_version": "rules-residue.m2-b018.accepted-lifecycle/1.0",
            "batch_id": CONTENT_SAFETY_BATCH, "lifecycle_state": "ACCEPTED",
            "accepted_plan": CONTENT_SAFETY_ACCEPTED_PLAN,
            "accepted_candidate": CONTENT_SAFETY_ACCEPTED_CANDIDATE,
            "envelope_sha256": CONTENT_SAFETY_ACCEPTED_ENVELOPE_SHA256,
            "registration_contract_sha256": CONTENT_SAFETY_CONTRACT_SHA256,
            "expected_artifacts": CONTENT_SAFETY_ACCEPTED_ARTIFACTS,
            "expected_git_blobs": CONTENT_SAFETY_ACCEPTED_GIT_BLOBS,
            "state_sha256": CONTENT_SAFETY_ACCEPTED_STATE_SHA256,
            "non_claims": {
                "formal_B002": False, "full18_status": "OPEN_NO_STAGE_CLOSED_BY_THIS_PLAN",
                "aggregate_M2_pass": False, "new_semantic_admission_granted": False,
                "public_action": False,
            },
        }
        if any(receipt.get(key) != value for key, value in expected.items()):
            raise ValueError("lifecycle source/envelope/artifact/state binding mismatch")
        contract_raw = _regular_bytes(root, CONTENT_SAFETY_CONTRACT)
        if hashlib.sha256(contract_raw).hexdigest() != CONTENT_SAFETY_CONTRACT_SHA256:
            raise ValueError("registration contract byte drift")
        contract = _b018_json(contract_raw)
        if (receipt["acceptance_scope"] != contract["batch"]["acceptance_scope"]
                or list(receipt["expected_artifacts"]) != contract["batch"]["allowed_paths"]
                or contract["batch"]["envelope_sha256"] != CONTENT_SAFETY_ACCEPTED_ENVELOPE_SHA256):
            raise ValueError("exact thirteen-path frozen business boundary mismatch")

        evidence = {}
        for name, digest in CONTENT_SAFETY_ACCEPTED_EVIDENCE_SHA256.items():
            item = receipt["evidence"][name]
            content = item["raw_utf8"].encode("utf-8")
            if (item["sha256"] != digest or item["bytes"] != len(content)
                    or hashlib.sha256(content).hexdigest() != digest):
                raise ValueError(f"embedded {name} original byte binding mismatch")
            evidence[name] = _b018_json(content)
        report = evidence["independent_result"]
        acceptance = evidence["independent_receipt"]
        reception = evidence["root_reception"]
        candidate = CONTENT_SAFETY_ACCEPTED_CANDIDATE
        plan = CONTENT_SAFETY_ACCEPTED_PLAN
        if (report["result"] != "PASS" or report["mode"] != "ACCEPT"
                or report["milestone"] != "M2" or report["batch"] != CONTENT_SAFETY_BATCH
                or report["candidate"] != candidate["commit"] or report["tree"] != candidate["tree"]
                or report["sole_parent"] != plan["commit"]
                or report["producer"] == report["reviewer"]
                or report["producer"] != "/root/game_b002_runtime_capability"
                or report["reviewer"] != "/root/game_b017_control_fix"
                or report["unresolved_required_findings"] != 0
                or report["finding_status"] != "CLOSED_ON_EXACT_07B_ONLY"
                or acceptance["decision"] != "PASS_EXACT_PRIVATE_IMPLEMENTATION_CANDIDATE"
                or acceptance["candidate"] != report["candidate"]
                or acceptance["tree"] != report["tree"]
                or acceptance["sole_parent"] != plan["commit"]
                or acceptance["result_sha256"] != CONTENT_SAFETY_ACCEPTED_EVIDENCE_SHA256["independent_result"]
                or acceptance["producer"] != report["producer"]
                or acceptance["reviewer"] != report["reviewer"]
                or acceptance["independent"] is not True
                or acceptance["root_local_reception_eligible"] is not True
                or acceptance["new_semantic_admission_granted"] is not False
                or reception["result"] != "RECEIVED_INDEPENDENTLY_ACCEPTED_PRIVATE_B018_BUSINESS"
                or reception["head"] != candidate["commit"] or reception["tree"] != candidate["tree"]
                or reception["parent"] != plan["commit"]
                or reception["source_clean"] is not True or reception["other_refs_unchanged"] is not True
                or reception["remote_action"] is not False):
            raise ValueError("independent ACCEPT/distinct reviewer/Root reception mismatch")

        # All actual current bytes are checked before any historical state check.
        for table in (CONTENT_SAFETY_ACCEPTED_STATE_SHA256, CONTENT_SAFETY_ACCEPTED_ARTIFACTS,
                      contract["current_consumers_sha256"], contract["original_schema_sha256"],
                      B018_LEGACY_EVIDENCE, SCHEMA_PREPARATION_LEGACY_IMPLEMENTATION_SHA256,
                      {SCHEMA_PREPARATION_REBIND_TEST: SCHEMA_PREPARATION_REBIND_TEST_SHA256},
                      {SCHEMA_ACCEPTED_RECEIPT: SCHEMA_ACCEPTED_RECEIPT_SHA256}):
            for relative, digest in table.items():
                if hashlib.sha256(_regular_bytes(root, relative)).hexdigest() != digest:
                    detail = "; installed receipt schema is not exact frozen bytes" if relative == CONTENT_SAFETY_SCHEMA else ""
                    raise ValueError(f"current accepted byte drift: {relative}{detail}")
        for relative, digest in contract["state_sha256"].items():
            if relative not in CONTENT_SAFETY_ACCEPTED_STATE_SHA256:
                if hashlib.sha256(_regular_bytes(root, relative)).hexdigest() != digest:
                    raise ValueError(f"current original contract byte drift: {relative}")
        batches = _b018_json(_regular_bytes(root, ".codex/plans/m2-vertical-slice/batches.json"))
        b017 = batches["batches"][16]
        for relative, digest in b017["expected_artifacts"].items():
            if hashlib.sha256(_regular_bytes(root, relative)).hexdigest() != digest:
                raise ValueError(f"current B017 artifact byte drift: {relative}")
        _check_schema_accepted_evidence(root, b017, lambda relative: _regular_bytes(root, relative), errors)
        if errors:
            return errors
        signer = _b018_json(_regular_bytes(root, SCHEMA_ACCEPTED_RECEIPT))["signer"]
        if receipt["signer"] != signer:
            raise ValueError("existing B017 signing identity changed")
        for source in (plan, candidate):
            if _b018_git(root, "rev-parse", source["commit"] + "^{tree}").decode().strip() != source["tree"]:
                raise ValueError("accepted B018 source Git tree mismatch")
        parents = _b018_git(root, "rev-list", "--parents", "-n", "1", candidate["commit"]).decode().split()
        if parents != [candidate["commit"], plan["commit"]]:
            raise ValueError("accepted B018 sole parent mismatch")
        _b018_git(root, "merge-base", "--is-ancestor", candidate["commit"], "HEAD")
        changed = _b018_git(root, "diff", "--name-only", plan["commit"], candidate["commit"]).decode().splitlines()
        if sorted(changed) != sorted(CONTENT_SAFETY_ACCEPTED_ARTIFACTS):
            raise ValueError("accepted B018 implementation is not the exact thirteen-path delta")
        _verify_schema_accepted_signatures(root, signer, (plan["commit"], candidate["commit"]))
        for relative, digest in CONTENT_SAFETY_ACCEPTED_ARTIFACTS.items():
            content = _b018_git(root, "show", candidate["commit"] + ":" + relative)
            row = _b018_git(root, "ls-tree", candidate["commit"], "--", relative).decode().strip()
            info, observed_path = row.split("\t")
            mode, kind, blob = info.split()
            if (hashlib.sha256(content).hexdigest() != digest or observed_path != relative or kind != "blob"
                    or {"mode": mode, "blob": blob} != CONTENT_SAFETY_ACCEPTED_GIT_BLOBS[relative]
                    or bool((root / relative).stat().st_mode & 0o111) != (mode == "100755")):
                raise ValueError(f"accepted B018 Git artifact/mode drift: {relative}")
        current_rows = _raw_batch_rows(_regular_bytes(root, ".codex/plans/m2-vertical-slice/batches.json"))
        signed_rows = _raw_batch_rows(_b018_git(root, "show", candidate["commit"] + ":.codex/plans/m2-vertical-slice/batches.json"))
        observed_rows = [{"id": f"M2-B{i:03}", "bytes": len(row), "sha256": hashlib.sha256(row).hexdigest()}
                         for i, row in enumerate(current_rows, 1)]
        if len(current_rows) != 18 or current_rows != signed_rows or observed_rows != receipt["historical18_raw_rows"]:
            raise ValueError("historical eighteen raw batch rows changed")
        if (batches["frozen_batches"] != ["M2-B001", SCHEMA_PREPARATION_BATCH, CONTENT_SAFETY_BATCH]
                or batches["accepted_batches"] != ["M2-B001", SCHEMA_PREPARATION_BATCH, CONTENT_SAFETY_BATCH]
                or batches["batches"][-1] != contract["batch"]):
            raise ValueError("B018 historical envelope/effective index mismatch")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError,
            subprocess.CalledProcessError) as exc:
        errors.append(f"B018 accepted lifecycle evidence rejected: {exc}")
    return errors


def _legacy_content_safety_contract_errors(root: Path) -> list[str]:
    """Pure complete binding check. Never calls collect_validation/SCG/recovery."""
    root = root.resolve()
    errors = legacy_evidence_byte_errors(root)
    accepted = has_content_safety_accepted_lifecycle(root)
    if accepted:
        errors.extend(content_safety_accepted_evidence_errors(root))
        if errors:
            return errors
    try:
        raw = _regular_bytes(root, CONTENT_SAFETY_CONTRACT)
        if hashlib.sha256(raw).hexdigest() != CONTENT_SAFETY_CONTRACT_SHA256:
            raise ValueError("registration contract byte drift")
        contract = _b018_json(raw)
        if contract["source"] != CONTENT_SAFETY_SOURCE:
            raise ValueError("source binding mismatch")
        source = CONTENT_SAFETY_SOURCE
        if _b018_git(root, "rev-parse", source["commit"] + "^{tree}").decode().strip() != source["tree"]:
            raise ValueError("source Git tree mismatch")
        _b018_git(root, "merge-base", "--is-ancestor", source["commit"], "HEAD")
        signer = _b018_json(_regular_bytes(root, SCHEMA_ACCEPTED_RECEIPT))["signer"]
        _verify_schema_accepted_signatures(root, signer, (source["commit"],))
        for table in (contract["state_sha256"], contract["current_consumers_sha256"],
                      contract["original_schema_sha256"], SCHEMA_PREPARATION_LEGACY_IMPLEMENTATION_SHA256,
                      {SCHEMA_PREPARATION_REBIND_TEST: SCHEMA_PREPARATION_REBIND_TEST_SHA256}):
            for relative, expected in table.items():
                current = (_b018_git(root, "show", CONTENT_SAFETY_ACCEPTED_CANDIDATE["commit"] + ":" + relative)
                           if accepted and relative in CONTENT_SAFETY_ACCEPTED_STATE_SHA256
                           else _regular_bytes(root, relative))
                if hashlib.sha256(current).hexdigest() != expected:
                    raise ValueError(f"current bound byte drift: {relative}")
        authority = contract["planning_authority_raw_utf8"].encode("utf-8")
        if hashlib.sha256(authority).hexdigest() != "b44689e7ef37d0062cf0c43f88154a97c49a5b8effffa9966ccf9541dcbadeb3":
            raise ValueError("planning authority binding mismatch")
        current_raw = _regular_bytes(root, ".codex/plans/m2-vertical-slice/batches.json")
        baseline_raw = _b018_source_bytes(root, ".codex/plans/m2-vertical-slice/batches.json")
        rows = _raw_batch_rows(current_raw)
        if len(rows) != 18 or rows[:17] != _raw_batch_rows(baseline_raw):
            raise ValueError("original17 raw batch rows changed or additional batch present")
        batches = _b018_json(current_raw)
        ids = [x["id"] for x in batches["batches"]]
        if ids != [f"M2-B{i:03}" for i in range(1, 19)] or ids.count("M2-B017") != 1:
            raise ValueError("exact18 ordered IDs/unique B017 required")
        batch = batches["batches"][-1]
        if batch != contract["batch"] or envelope_digest(batch) != batch["envelope_sha256"]:
            raise ValueError("frozen B018 envelope mismatch")
        document = _regular_bytes(root, CONTENT_SAFETY_DOCUMENT).decode()
        match = re.search(r"```json\n(.*?)\n```", document, re.DOTALL)
        if match is None or _b018_json(match.group(1).encode()) != batch:
            raise ValueError("document/envelope mismatch")
        route = _b018_json(_regular_bytes(root, CONTENT_SAFETY_ROUTE))
        if tuple(route.get(k) for k in ("route_id", "mode", "milestone", "batch_id")) != (
                "M2-B018-CONTENT-SAFETY-ADMISSION-IMPLEMENT", "IMPLEMENT", "M2", CONTENT_SAFETY_BATCH):
            raise ValueError("route identity mismatch")
        schema_raw = (json.dumps(contract["receipt_schema"], indent=2, ensure_ascii=False) + "\n").encode()
        if hashlib.sha256(schema_raw).hexdigest() != batch["expected_receipt_schema"]["sha256"]:
            raise ValueError("frozen receipt schema mismatch")
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(contract["receipt_schema"])
        schema_path = root / CONTENT_SAFETY_SCHEMA
        if schema_path.exists() or schema_path.is_symlink():
            if _regular_bytes(root, CONTENT_SAFETY_SCHEMA) != schema_raw:
                raise ValueError("installed receipt schema is not exact frozen bytes")
        # Original accepted B017 files, receipt, source, signatures and order are
        # checked using the unchanged B017 logic, with only five verified state
        # projections read from signed7d. No historical implementation is loaded.
        old_batches = _b018_json(baseline_raw)
        projected = lambda relative: (_b018_source_bytes(root, relative)
                                     if relative in SCHEMA_ACCEPTED_STATE_SHA256
                                     else _regular_bytes(root, relative))
        _check_schema_accepted_evidence(root, old_batches["batches"][16], projected, errors)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError,
            ImportError, subprocess.CalledProcessError) as exc:
        errors.append(f"B018 registration rejected: {exc}")
    return errors


def content_safety_schema_errors(root: Path) -> list[str]:
    return content_safety_contract_errors(root)


def _b018_project_b017(root: Path, batches: dict[str, Any], read=None):
    errors = content_safety_contract_errors(root)
    if errors:
        raise ValueError("; ".join(errors))
    old = _b018_json(_b018_source_bytes(root, ".codex/plans/m2-vertical-slice/batches.json"))
    reader = lambda relative: (_b018_source_bytes(root, relative)
                              if relative in SCHEMA_ACCEPTED_STATE_SHA256
                              else (read(relative) if read else _regular_bytes(root, relative)))
    return old, reader


def _legacy_content_safety_native_errors(root: Path) -> list[str]:
    errors = content_safety_contract_errors(root)
    if errors:
        return errors
    from tools.codex_route import RouteError, generate_reading_map, check_reading_map
    try:
        request = _b018_json(_regular_bytes(root, CONTENT_SAFETY_ROUTE))
        route = generate_reading_map(request, repo_root=root)
        check_reading_map(route, repo_root=root, expected_route_id=request["route_id"],
                         expected_mode="IMPLEMENT", expected_milestone="M2", expected_batch_id=CONTENT_SAFETY_BATCH)
    except (OSError, ValueError, KeyError, RouteError) as exc:
        errors.append(f"B018 route rejected: {exc}")
    return errors


def check_content_safety_implementation(root: Path, source: str) -> list[str]:
    errors = content_safety_native_errors(root)
    if errors:
        return errors
    try:
        if re.fullmatch(r"[0-9a-f]{40}", source) is None:
            raise ValueError("implementation source must be exact commit")
        if _b018_git(root, "status", "--porcelain").strip():
            raise ValueError("implementation candidate must be clean")
        _b018_git(root, "merge-base", "--is-ancestor", source, "HEAD")
        contract = _b018_json(_regular_bytes(root, CONTENT_SAFETY_CONTRACT))
        if _b018_git(root, "show", source + ":" + CONTENT_SAFETY_CONTRACT) != _regular_bytes(root, CONTENT_SAFETY_CONTRACT):
            raise ValueError("source is not this exact frozen B018 PLAN")
        signer = _b018_json(_regular_bytes(root, SCHEMA_ACCEPTED_RECEIPT))["signer"]
        _verify_schema_accepted_signatures(root, signer, (source,))
        changed = _b018_git(root, "diff", "--name-only", source, "HEAD").decode().splitlines()
        if sorted(changed) != sorted(contract["batch"]["allowed_paths"]):
            raise ValueError("implementation diff must contain exactly thirteen B018 paths")
        for relative in contract["batch"]["allowed_paths"]:
            _regular_bytes(root, relative)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        errors.append(f"B018 implementation scope rejected: {exc}")
    return errors


def _has_schema_lifecycle(batches: dict[str, Any]) -> bool:
    projection = batches.get("lifecycle_projection")
    return isinstance(projection, dict) and SCHEMA_PREPARATION_BATCH in projection


def _verify_schema_accepted_signatures(root: Path, signer: dict[str, str], commits: tuple[str, ...]) -> None:
    environment = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"}
    # Carry the already trusted public identity with the evidence. This is
    # transient verification configuration, not a new key or global trust.
    public_key = signer["public_key"] + "\n"
    fingerprint = "SHA256:zR55HATrI3+mzVZW3uc8MsCxE+g5fyImXdD8X7WKkt4"
    if (hashlib.sha256(public_key.encode("ascii")).hexdigest() != "eae9554a6a3c2866568a560fa1b0bd9f9516328e500b3d2295983d7de4847a2c"
            or signer["fingerprint"] != fingerprint):
        raise ValueError("existing signing identity changed")
    with tempfile.TemporaryDirectory(prefix="b017-existing-signature-") as temporary:
        key_path = Path(temporary) / "existing-public-key"
        key_path.write_text(public_key, encoding="ascii")
        observed = subprocess.check_output(["ssh-keygen", "-lf", str(key_path), "-E", "sha256"], stderr=subprocess.PIPE).decode()
        if fingerprint not in observed.split():
            raise ValueError("existing signing fingerprint mismatch")
        allowed = Path(temporary) / "allowed-signers"
        allowed.write_text("rules-b017 " + public_key, encoding="ascii")
        for commit in commits:
            verification = subprocess.run(["git", "-c", f"gpg.ssh.allowedSignersFile={allowed}", "verify-commit", commit],
                                          cwd=root, env=environment, capture_output=True)
            if verification.returncode:
                raise ValueError(f"accepted source signature verification failed: {commit}")


def _check_schema_accepted_evidence(root: Path, batch: dict[str, Any], read, errors: list[str]) -> None:
    """Verify portable exact evidence without calling any downstream validator."""
    try:
        receipt_path = root / SCHEMA_ACCEPTED_RECEIPT
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise ValueError("lifecycle receipt is missing or not a regular file")
        raw = read(SCHEMA_ACCEPTED_RECEIPT)
        if hashlib.sha256(raw).hexdigest() != SCHEMA_ACCEPTED_RECEIPT_SHA256:
            raise ValueError("lifecycle receipt byte drift")
        receipt = json.loads(raw)
        if (receipt["accepted_candidate"] != SCHEMA_ACCEPTED_CANDIDATE
                or receipt["accepted_plan"] != SCHEMA_ACCEPTED_PLAN
                or receipt["envelope_sha256"] != SCHEMA_PREPARATION_ENVELOPE_SHA256
                or receipt["expected_artifacts"] != batch["expected_artifacts"]):
            raise ValueError("lifecycle source/envelope/artifact binding mismatch")
        evidence = {}
        for name, digest in SCHEMA_ACCEPTED_EVIDENCE_SHA256.items():
            item = receipt["evidence"][name]
            content = item["raw_utf8"].encode("utf-8")
            if item["sha256"] != digest or hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"embedded {name} original byte binding mismatch")
            evidence[name] = json.loads(content)
        report = evidence["independent_report"]
        manifest = evidence["independent_manifest"]
        authority = evidence["root_acceptance"]
        if (report["result"] != "PASS" or report["role"] != "ACCEPT"
                or report["candidate_commit"] != SCHEMA_ACCEPTED_CANDIDATE["commit"]
                or report["candidate_tree"] != SCHEMA_ACCEPTED_CANDIDATE["tree"]
                or report["source_commit"] != SCHEMA_ACCEPTED_PLAN["commit"]
                or report["expected_artifacts"] != batch["expected_artifacts"]
                or sorted(report["changed_paths"]) != sorted(SCHEMA_PREPARATION_PATHS)
                or authority["status"] != "ROOT_ACCEPTED_EXACT_B017_IMPLEMENTATION"
                or authority["candidate_commit"] != report["candidate_commit"]
                or authority["candidate_tree"] != report["candidate_tree"]
                or authority["independent_report"]["sha256"] != SCHEMA_ACCEPTED_EVIDENCE_SHA256["independent_report"]):
            raise ValueError("independent ACCEPT/root authority mismatch")
        report_members = [item for item in manifest["members"] if item["path"] == "review-result.json"]
        if report_members != [{"path": "review-result.json", "bytes": len(receipt["evidence"]["independent_report"]["raw_utf8"].encode()),
                               "sha256": SCHEMA_ACCEPTED_EVIDENCE_SHA256["independent_report"]}]:
            raise ValueError("independent manifest does not bind the exact report")

        environment = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"}
        def git(*args: str) -> bytes:
            return subprocess.check_output(["git", *args], cwd=root, env=environment, stderr=subprocess.PIPE)
        for source in (SCHEMA_ACCEPTED_PLAN, SCHEMA_ACCEPTED_CANDIDATE):
            if git("rev-parse", source["commit"] + "^{tree}").decode().strip() != source["tree"]:
                raise ValueError("accepted source Git tree mismatch")
        if git("rev-parse", SCHEMA_ACCEPTED_CANDIDATE["commit"] + "^").decode().strip() != SCHEMA_ACCEPTED_PLAN["commit"]:
            raise ValueError("accepted implementation parent mismatch")
        git("merge-base", "--is-ancestor", SCHEMA_ACCEPTED_CANDIDATE["commit"], "HEAD")
        changed = git("diff", "--name-only", SCHEMA_ACCEPTED_PLAN["commit"], SCHEMA_ACCEPTED_CANDIDATE["commit"]).decode().splitlines()
        if sorted(changed) != sorted(SCHEMA_PREPARATION_PATHS):
            raise ValueError("accepted implementation is not the exact four-path delta")
        for relative, digest in batch["expected_artifacts"].items():
            path = root / relative
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"accepted artifact is missing or not regular: {relative}")
            if hashlib.sha256(read(relative)).hexdigest() != digest:
                raise ValueError(f"accepted artifact byte drift: {relative}")
            if hashlib.sha256(git("show", f"{SCHEMA_ACCEPTED_CANDIDATE['commit']}:{relative}")).hexdigest() != digest:
                raise ValueError(f"accepted Git artifact byte drift: {relative}")
        for relative, digest in SCHEMA_PREPARATION_STATE_SHA256.items():
            if hashlib.sha256(git("show", f"{SCHEMA_ACCEPTED_PLAN['commit']}:{relative}")).hexdigest() != digest:
                raise ValueError(f"accepted PLAN historical byte drift: {relative}")

        _verify_schema_accepted_signatures(root, receipt["signer"], (SCHEMA_ACCEPTED_PLAN["commit"], SCHEMA_ACCEPTED_CANDIDATE["commit"]))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, subprocess.CalledProcessError) as exc:
        errors.append(f"B017 accepted lifecycle evidence rejected: {exc}")


def _legacy_schema_preparation_lifecycle(batches: dict[str, Any], root: Path, artifact_reader=None) -> dict[str, Any]:
    """Expose an effective action/index only after the complete contract passes."""
    errors: list[str] = []
    if not check_schema_preparation(batches, root, errors, artifact_reader) or errors:
        raise ValueError("; ".join(errors) or "B017 allocation is absent")
    accepted = _has_schema_lifecycle(batches)
    safety = len(batches.get("batches", [])) == 18
    safety_accepted = safety and has_content_safety_accepted_lifecycle(root, batches)
    action = (SCHEMA_ACCEPTED_ACTION if safety_accepted else CONTENT_SAFETY_ACTION if safety
              else SCHEMA_ACCEPTED_ACTION if accepted else SCHEMA_PREPARATION_ACTION)
    accepted_batches = ["M2-B001", SCHEMA_PREPARATION_BATCH] if accepted else ["M2-B001"]
    if safety_accepted:
        accepted_batches.append(CONTENT_SAFETY_BATCH)
    return {"state": "ACCEPTED" if accepted else "FROZEN",
            "next_allowed_action": action,
            "accepted_batches": accepted_batches}


def envelope_digest(batch: dict[str, Any]) -> str:
    value = {key: item for key, item in batch.items() if key != "envelope_sha256"}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _legacy_check_schema_preparation(
    batches: dict[str, Any], root: Path, errors: list[str], artifact_reader=None,
) -> bool:
    """Validate the one native next-ID allocation; legacy plans stay unchanged."""
    items = batches.get("batches", [])
    if isinstance(items, list) and len(items) == 18:
        try:
            batches, artifact_reader = _b018_project_b017(root, batches, artifact_reader)
            items = batches["batches"]
        except ValueError as exc:
            errors.append(str(exc))
            return False
    if not isinstance(items, list) or len(items) != 17:
        return False
    read = artifact_reader or (lambda relative: _regular_bytes(root, relative))
    batch = items[-1]
    if not isinstance(batch, dict):
        errors.append("B017 envelope must be an object")
        return False
    start = len(errors)
    preserved = copy.deepcopy(items[:16])
    if not all(isinstance(item, dict) for item in preserved):
        errors.append("B017 legacy batch prefix contains a non-object")
        return False
    if preserved[1].get("dependencies") != ["M2-B001", SCHEMA_PREPARATION_BATCH]:
        errors.append("B002 must retain B001 and add only the B017 preparation dependency")
    preserved[1]["dependencies"] = ["M2-B001"]
    legacy_digest = hashlib.sha256(json.dumps(preserved, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if legacy_digest != LEGACY_BATCHES_SHA256:
        errors.append("B017 allocation changed a legacy batch contract or B002 gate")
    required = {
        "id": SCHEMA_PREPARATION_BATCH, "state": "FROZEN",
        "implementation_state": "NOT_STARTED", "ready": "YES",
        "dependencies": ["M2-B001"], "parallel_safe": False,
        "allowed_paths": SCHEMA_PREPARATION_PATHS,
        "source_binding": SCHEMA_PREPARATION_SOURCE,
        "acceptance_scope": "UNREGISTERED_C14_STRUCTURE_ONLY",
        "formal_B002": False,
        "candidate_binding": {"strategy": "EXACT_HEAD_AT_VALIDATION", "clean_worktree_required": True,
                              "implementation_source": "INDEPENDENTLY_ACCEPTED_FROZEN_PLAN_COMMIT"},
    }
    for key, expected in required.items():
        if batch.get(key) != expected:
            errors.append(f"B017 {key} does not match the frozen preparation boundary")
    if batches.get("frozen_batches") != ["M2-B001", SCHEMA_PREPARATION_BATCH]:
        errors.append("B017 native frozen batch index is inconsistent")
    if batch.get("envelope_sha256") != envelope_digest(batch):
        errors.append("B017 envelope digest mismatch")
    if envelope_digest(batch) != SCHEMA_PREPARATION_ENVELOPE_SHA256:
        errors.append("B017 envelope differs from the concrete native allocation")
    artifacts = batch.get("expected_artifacts")
    if not isinstance(artifacts, dict) or list(artifacts) != SCHEMA_PREPARATION_PATHS or any(
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
        for value in artifacts.values()
    ):
        errors.append("B017 expected artifacts must bind the four exact paths and hashes")
    try:
        accepted = _has_schema_lifecycle(batches)
        state_hashes = SCHEMA_ACCEPTED_STATE_SHA256 if accepted else SCHEMA_PREPARATION_STATE_SHA256
        for relative, expected in state_hashes.items():
            if hashlib.sha256(read(relative)).hexdigest() != expected:
                errors.append(f"B017 exact native PLAN transition drift: {relative}")
        if accepted:
            _check_schema_accepted_evidence(root, batch, read, errors)
        elif artifact_reader is None and ((root / SCHEMA_ACCEPTED_RECEIPT).exists() or (root / SCHEMA_ACCEPTED_RECEIPT).is_symlink()):
            errors.append("B017 lifecycle receipt exists without an accepted projection")
        if hashlib.sha256(read(SCHEMA_PREPARATION_APPROVAL)).hexdigest() != SCHEMA_PREPARATION_SOURCE["approval_sha256"]:
            errors.append("B017 approved C14 source hash mismatch")
        route_bytes = read(SCHEMA_PREPARATION_ROUTE)
        if hashlib.sha256(route_bytes).hexdigest() != "e1bd6087da7177f467dff460902aa304c11a3e97b3400eba17022449c6b07c48":
            errors.append("B017 IMPLEMENT route differs from the concrete native allocation")
        route = json.loads(route_bytes)
        if tuple(route.get(key) for key in ("route_id", "mode", "milestone", "batch_id")) != (
            "M2-B017-C14-SCHEMA-PREPARATION-IMPLEMENT", "IMPLEMENT", "M2", SCHEMA_PREPARATION_BATCH,
        ):
            errors.append("B017 IMPLEMENT route identity mismatch")
        if not any(item.get("path") == SCHEMA_PREPARATION_DOCUMENT and item.get("required_sections") == ["M2-B017-C14-SCHEMA-PREPARATION"] for item in route.get("documents", [])):
            errors.append("B017 IMPLEMENT route omits the frozen envelope")
        document = read(SCHEMA_PREPARATION_DOCUMENT).decode("utf-8")
        match = re.search(r"```json\n(.*?)\n```", document, re.DOTALL)
        if match is None or json.loads(match.group(1)) != batch:
            errors.append("B017 routed envelope differs from the native batch registry")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"B017 source/route binding unavailable: {exc}")
    return len(errors) == start


def check_implementation_scope(root: Path, source: str, batch: dict[str, Any]) -> list[str]:
    """Check an immutable implementation against its accepted frozen PLAN source."""
    errors: list[str] = []
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)
    try:
        if re.fullmatch(r"[0-9a-f]{40}", source) is None:
            return ["implementation source must be an exact commit"]
        if git("status", "--porcelain").strip():
            errors.append("implementation candidate must be clean")
        git("merge-base", "--is-ancestor", source, "HEAD")
        frozen = json.loads(git("show", f"{source}:.codex/plans/m2-vertical-slice/batches.json"))["batches"]
        if len(frozen) != 17 or frozen[-1] != batch:
            errors.append("implementation source does not bind this frozen B017 envelope")
        changed = git("diff", "--name-only", source, "HEAD").decode().splitlines()
        if sorted(changed) != sorted(SCHEMA_PREPARATION_PATHS):
            errors.append("implementation diff must contain exactly the four B017 paths")
        for relative, digest in batch.get("expected_artifacts", {}).items():
            if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
                errors.append(f"implementation artifact hash mismatch: {relative}")
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        errors.append(f"implementation source/candidate binding failed: {exc}")
    return errors


def _read_json(path: Path, errors: list[str]) -> Any:
    try:
        return _b018_json(_regular_bytes(PROJECT_ROOT, str(path.relative_to(PROJECT_ROOT))))
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"{path.relative_to(PROJECT_ROOT)} is not valid JSON: {exc}")
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_projection_parity(errors: list[str]) -> None:
    projection_path = PLAN_ROOT / "ROUTED_INPUT_PROJECTIONS.md"
    try:
        text = projection_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read routed input projections: {exc}")
        return

    sources = {
        "R2-M2-REFERENCE-WORK-PACKAGES": PROJECT_ROOT
        / "docs"
        / "implementation"
        / "r2"
        / "M2_REFERENCE_WORK_PACKAGES.yaml",
        "R2-INSTALL-INTEGRATION-CONFLICT-EVIDENCE": PROJECT_ROOT
        / "governance"
        / "evidence"
        / "r2-authority-install"
        / "integration-conflicts.yaml",
    }
    marker_re = re.compile(
        r"^<!-- SECTION-ID: ([A-Z0-9]+(?:-[A-Z0-9]+)+) -->$", re.MULTILINE
    )
    matches = list(marker_re.finditer(text))
    found_ids = [match.group(1) for match in matches]
    if found_ids != list(sources):
        errors.append(
            "routed input projection Section IDs/order differ from the two frozen sources"
        )
        return

    for index, match in enumerate(matches):
        section_id = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start() : end]
        source_path = sources[section_id]
        digest = _sha256(source_path)
        if f"source SHA-256: `{digest}`" not in section:
            errors.append(f"{section_id} does not bind the current source SHA-256")
        fenced = re.search(r"```yaml\n(.*?)```", section, re.DOTALL)
        if fenced is None:
            errors.append(f"{section_id} lacks a YAML projection payload")
            continue
        payload = fenced.group(1).encode("utf-8")
        try:
            source = source_path.read_bytes()
        except OSError as exc:
            errors.append(f"cannot read projection source {source_path}: {exc}")
            continue
        if payload != source:
            errors.append(f"{section_id} is not byte-identical to {source_path.relative_to(PROJECT_ROOT)}")


def _legacy_check_dag(batches: dict[str, Any], errors: list[str]) -> None:
    graph = batches.get("dependency_graph")
    items = batches.get("batches")
    extended = isinstance(items, list) and len(items) in (17, 18)
    safety = extended and len(items) == 18
    expected_ids = [f"M2-B{index:03d}" for index in range(1, 19 if safety else 18 if extended else 17)]
    if not isinstance(graph, dict) or list(graph) != expected_ids:
        errors.append("M2 dependency graph must preserve B001--B016 and allow only the next B017 ID")
        return
    if not isinstance(items, list) or [item.get("id") for item in items if isinstance(item, dict)] != expected_ids:
        errors.append("M2 batch registry must preserve B001--B016 and allow only the next B017 ID")
        return

    order = {batch_id: index for index, batch_id in enumerate(expected_ids)}
    for item in items:
        if not isinstance(item, dict):
            errors.append("M2 batch registry contains a non-object")
            continue
        missing = REQUIRED_BATCH_FIELDS - set(item)
        if missing:
            errors.append(f"{item.get('id')} lacks fields: {sorted(missing)}")
        batch_id = item.get("id")
        dependencies = item.get("dependencies")
        if dependencies != graph.get(batch_id):
            errors.append(f"{batch_id} dependencies differ from dependency_graph")
        if isinstance(dependencies, list):
            for dependency in dependencies:
                preparation_edge = extended and batch_id == "M2-B002" and dependency == SCHEMA_PREPARATION_BATCH
                if dependency not in order or (order[dependency] >= order.get(batch_id, -1) and not preparation_edge):
                    errors.append(f"{batch_id} has unknown, self, forward, or cyclic dependency {dependency}")
        for field in REQUIRED_BATCH_FIELDS - {"dependencies", "opencode_responsibilities", "grok_responsibilities"}:
            value = item.get(field)
            if value in (None, "", []):
                errors.append(f"{batch_id}.{field} must not be empty")

    frozen = [item.get("id") for item in items if item.get("state") == "FROZEN"]
    planned = [item.get("id") for item in items if item.get("state") == "PLANNED"]
    expected_frozen = ["M2-B001", SCHEMA_PREPARATION_BATCH] if extended else ["M2-B001"]
    if safety:
        expected_frozen.append(CONTENT_SAFETY_BATCH)
    if frozen != expected_frozen or planned != [f"M2-B{index:03d}" for index in range(2, 17)]:
        errors.append("preserve B001 historical freeze and B002--B016 PLANNED; only allocated B017 may newly freeze")
    remaining = {key: set(value) for key, value in graph.items() if isinstance(value, list)}
    while remaining:
        ready = {key for key, dependencies in remaining.items() if not dependencies}
        if not ready:
            errors.append("M2 dependency graph has unknown, self, forward, or cyclic dependency")
            break
        remaining = {key: dependencies - ready for key, dependencies in remaining.items() if key not in ready}
    if batches.get("implementation_state") != "NOT_STARTED":
        errors.append("M2 implementation_state must remain NOT_STARTED")


def _check_controls(controls: dict[str, Any], errors: list[str]) -> None:
    acceptance = controls.get("acceptance_matrix")
    expected_acceptance = [f"M2-ACC-{index:03d}" for index in range(1, 32)]
    if not isinstance(acceptance, list) or [item.get("id") for item in acceptance if isinstance(item, dict)] != expected_acceptance:
        errors.append("acceptance matrix must contain ordered M2-ACC-001--031")
    elif any(item.get("status") != "PLANNED_NOT_RUN" for item in acceptance):
        errors.append("all M2 acceptance entries must remain PLANNED_NOT_RUN in PLAN")

    gates = controls.get("external_gates")
    if not isinstance(gates, list) or not gates:
        errors.append("M2 external gates must be a non-empty array")
    elif any(item.get("status") != "NOT_RUN" for item in gates):
        errors.append("all M2 external gates must remain NOT_RUN in PLAN")

    deferred = controls.get("deferred_consumption")
    if not isinstance(deferred, list) or len(deferred) != 10:
        errors.append("M2 deferred consumption plan must contain exactly 10 entries")
    elif any(not item.get("plan") or not item.get("checkpoint") for item in deferred):
        errors.append("every deferred item must have an explicit plan and checkpoint")

    packets = controls.get("task_packet_plan")
    if not isinstance(packets, list) or len(packets) != 8:
        errors.append("M2 Task Packet plan must contain six OpenCode and two Grok packets")
    else:
        owned_paths: dict[str, str] = {}
        for packet in packets:
            owner = packet.get("owner")
            task_type = packet.get("task_type")
            if packet.get("status") != "PLANNED_NOT_ISSUED" or packet.get("self_approval") is not False:
                errors.append(f"{packet.get('packet_id')} must be unissued and forbid self-approval")
            if (owner, task_type) not in {("opencode", "script"), ("grok", "art")}:
                errors.append(f"{packet.get('packet_id')} has an invalid owner/task_type pair")
            for path in packet.get("allowed_paths", []):
                previous = owned_paths.get(path)
                if previous is not None:
                    errors.append(f"Task Packet path {path} is owned by both {previous} and {packet.get('packet_id')}")
                owned_paths[path] = packet.get("packet_id", "")

    review = controls.get("self_review")
    if not isinstance(review, dict):
        errors.append("M2 self_review must be an object")
    else:
        forbidden_true = {
            "r2_modified",
            "oversized_batch",
            "cycle",
            "lua_before_schema",
            "unknown_platform_used_before_probe",
            "deferred_defaulted",
            "unbound_implementation_package",
        }
        required_true = {
            "required_scope_covered",
            "seed_and_secret_gates_covered",
            "repeat_safety_covered",
            "all_31_acceptance_ids_mapped",
            "only_first_batch_frozen",
        }
        if any(review.get(key) is not False for key in forbidden_true):
            errors.append("M2 self-review reports a freeze-blocking defect")
        if any(review.get(key) is not True for key in required_true):
            errors.append("M2 self-review lacks a required positive assertion")


def _check_probe_contract(probes: dict[str, Any], errors: list[str]) -> None:
    rules = probes.get("rules")
    if not isinstance(rules, dict):
        errors.append("capability probe matrix rules must be an object")
        return
    if rules.get("not_run_is_pass") is not False:
        errors.append("capability probe matrix must explicitly forbid NOT_RUN as PASS")
    if rules.get("allowed_batch_results") != BATCH_RESULTS:
        errors.append("M2 batch results must preserve the repository five-state contract")
    if rules.get("allowed_probe_execution_statuses") != PROBE_EXECUTION_STATUSES:
        errors.append(
            "probe execution statuses must be PASS/FAIL/NOT_RUN/"
            "BLOCKED_EXTERNAL/BLOCKED_ENVIRONMENT"
        )
    if rules.get("probe_result_required_fields") != PROBE_RESULT_REQUIRED_FIELDS:
        errors.append("probe result contract does not preserve every required evidence field")


def _classify_lifecycle(
    milestone: dict[str, Any],
    recovery: dict[str, Any],
    errors: list[str],
) -> str:
    if recovery.get("evidence_id") != "M2-B001-RECOVERY-CLOSEOUT-001-E002":
        errors.append("recovery closeout evidence identity is missing or stale")
    if recovery.get("task_id") != "RULES-RESIDUE-M2-B001-RECOVERY-CLOSEOUT-IMPLEMENT-002":
        errors.append("recovery closeout task identity is missing or stale")
    if recovery.get("closeout_id") != "M2-B001-RECOVERY-CLOSEOUT-001" or recovery.get("attempt_number") != 2:
        errors.append("recovery closeout/attempt identity is missing or stale")
    if recovery.get("historical_projection") != {
        "R2-INT-010": "FAIL",
        "source_path": "reports/m2/probes/probe-results.json",
        "source_sha256": "154e7c0ddf8ce7b2243ad6c78d10ceb6cddf02c3aeb6592716dcc5ad8fc64218",
    }:
        errors.append("recovery closeout must preserve historical R2-INT-010=FAIL")
    if recovery.get("effective_projection", {}).get("R2-INT-010") != "RESOLVED_ADAPTER":
        errors.append("recovery closeout must project effective R2-INT-010=RESOLVED_ADAPTER")
    if recovery.get("non_claims") != {
        "formal_B002": False,
        "formal_B009": False,
        "aggregate_M2_pass": False,
        "aggregate_external_capability_pass": False,
    }:
        errors.append("recovery closeout overclaims formal or aggregate readiness")
    if recovery.get("readiness") != {
        "M2-B002": "NOT_STARTED",
        "M2-B002_READY": "NO",
        "blocking_ids": EXPECTED_RECOVERY_BLOCKERS,
    }:
        errors.append("recovery closeout downstream blockers or readiness changed")
    if recovery.get("candidate_binding") != {
        "strategy": "EXACT_HEAD_AT_VALIDATION",
        "execution_status": "NOT_RUN",
        "required_phase": "INDEPENDENT_ACCEPT",
        "must_bind_exact_commit_tree": True,
        "clean_worktree_required": True,
    }:
        errors.append("recovery closeout candidate binding is not pending exact-HEAD validation")

    active = milestone.get("active_plan")
    active_state = active.get("implementation_state") if isinstance(active, dict) else None
    lifecycle_pair = (milestone.get("state"), active_state)
    if lifecycle_pair == ("FROZEN", "NOT_STARTED"):
        if recovery.get("lifecycle") != {
            "candidate_state": FROZEN_RECOVERY_PENDING,
            "lifecycle_closeout_executed": False,
            "independent_acceptance": "NOT_RUN",
        }:
            errors.append("frozen recovery evidence falsely claims lifecycle closeout")
        return FROZEN_RECOVERY_PENDING
    if lifecycle_pair == ("ACCEPTED", "ACCEPTED"):
        return ACCEPTED_WITH_BLOCKERS

    errors.append(
        f"{INVALID_MIXED_STATE}: milestone state and active implementation state are {lifecycle_pair!r}"
    )
    return INVALID_MIXED_STATE


def _legacy_collect_validation(project_root: Path = PROJECT_ROOT) -> tuple[list[str], str]:
    global PROJECT_ROOT, PLAN_ROOT
    original_root = PROJECT_ROOT
    original_plan_root = PLAN_ROOT
    PROJECT_ROOT = project_root.resolve()
    PLAN_ROOT = PROJECT_ROOT / ".codex" / "plans" / "m2-vertical-slice"
    errors: list[str] = []
    lifecycle_state = INVALID_MIXED_STATE
    try:
        batches = _read_json(PLAN_ROOT / "batches.json", errors)
        probes = _read_json(PLAN_ROOT / "capability-probes.json", errors)
        controls = _read_json(PLAN_ROOT / "controls.json", errors)
        milestone = _read_json(PROJECT_ROOT / ".codex" / "state" / "MILESTONE_PLAN.yaml", errors)
        route = _read_json(PROJECT_ROOT / ".codex" / "routes" / "m2-vertical-slice-plan-request.json", errors)
        recovery = _read_json(PROJECT_ROOT / RECOVERY_EVIDENCE_PATH, errors)

        if isinstance(batches, dict):
            safety = has_content_safety_registration(PROJECT_ROOT, batches)
            if safety:
                errors.extend(content_safety_contract_errors(PROJECT_ROOT))
            _check_dag(batches, errors)
            valid_preparation = check_schema_preparation(batches, PROJECT_ROOT, errors)
            extended = isinstance(batches.get("batches"), list) and len(batches["batches"]) in (17, 18)
            if extended:
                accepted = valid_preparation and _has_schema_lifecycle(batches)
                safety_accepted = accepted and safety and has_content_safety_accepted_lifecycle(PROJECT_ROOT, batches)
                next_action = (SCHEMA_ACCEPTED_ACTION if safety_accepted else CONTENT_SAFETY_ACTION if safety
                               else SCHEMA_ACCEPTED_ACTION if accepted else SCHEMA_PREPARATION_ACTION)
                for label, projection in [
                    ("batches", batches.get("lifecycle_projection", {})),
                    ("controls", controls.get("lifecycle_projection", {}) if isinstance(controls, dict) else {}),
                    ("probes", probes.get("lifecycle_projection", {}) if isinstance(probes, dict) else {}),
                    ("milestone", milestone.get("active_plan", {}) if isinstance(milestone, dict) else {}),
                ]:
                    if projection.get("next_allowed_action") != next_action:
                        errors.append(f"{label} next action is not bound to the validated B017 envelope")
                active = milestone.get("active_plan", {}) if isinstance(milestone, dict) else {}
                if active.get("frozen_batches") != ([] if safety_accepted else [CONTENT_SAFETY_BATCH] if safety else [] if accepted else [SCHEMA_PREPARATION_BATCH]):
                    errors.append("milestone current frozen batch index does not match B017 effective lifecycle")
                accepted_batches = ["M2-B001", SCHEMA_PREPARATION_BATCH] if accepted else ["M2-B001"]
                if safety_accepted:
                    accepted_batches.append(CONTENT_SAFETY_BATCH)
                if active.get("accepted_batches") != accepted_batches or batches.get("accepted_batches") != accepted_batches:
                    errors.append("B017 effective accepted batch index is inconsistent")
                for label, projection in [
                    ("batches", batches.get("lifecycle_projection", {})),
                    ("controls", controls.get("lifecycle_projection", {}) if isinstance(controls, dict) else {}),
                    ("probes", probes.get("lifecycle_projection", {}) if isinstance(probes, dict) else {}),
                    ("milestone", active.get("lifecycle_projection", {})),
                ]:
                    if projection.get("blocking_ids") != EXPECTED_RECOVERY_BLOCKERS or projection.get("formal_B002") is not False:
                        errors.append(f"{label} B002 blockers or non-claim changed")
                    expected_b002 = {"state": "PLANNED", "implementation_state": "NOT_STARTED", "ready": "NO"}
                    if label == "milestone":
                        if projection.get("M2-B002") != expected_b002:
                            errors.append("milestone B002 readiness changed")
                    elif (projection.get("M2-B002"), projection.get("M2-B002_implementation"), projection.get("M2-B002_READY")) != ("PLANNED", "NOT_STARTED", "NO"):
                        errors.append(f"{label} B002 readiness changed")
        if isinstance(probes, dict):
            _check_probe_contract(probes, errors)
            probe_items = probes.get("probes")
            expected = [f"R2-INT-{index:03d}" for index in range(1, 13)]
            if not isinstance(probe_items, list) or [item.get("id") for item in probe_items if isinstance(item, dict)] != expected:
                errors.append("capability probe matrix must contain ordered R2-INT-001--012")
            elif any(item.get("current_status") != "DEFERRED_WITH_NON_BLOCKING_PROOF" for item in probe_items):
                errors.append("R2 integration probe statuses must preserve installation classifications")
        if isinstance(controls, dict):
            _check_controls(controls, errors)
        if isinstance(milestone, dict):
            if (milestone.get("milestone"), milestone.get("batch_id")) != ("M2", "M2-B001"):
                errors.append("milestone machine source must remain M2 / M2-B001")
            active = milestone.get("active_plan")
            if not isinstance(active, dict):
                errors.append("active M2 plan must remain an object")
            if isinstance(recovery, dict):
                lifecycle_state = _classify_lifecycle(milestone, recovery, errors)
        if isinstance(route, dict):
            identity = (route.get("route_id"), route.get("mode"), route.get("milestone"), route.get("batch_id"))
            if identity != ("M2-VERTICAL-SLICE-PLAN", "PLAN", "M2", "M2-B001"):
                errors.append("M2 PLAN route request identity is invalid")
            for document in route.get("documents", []):
                path = document.get("path", "") if isinstance(document, dict) else ""
                if Path(path).is_absolute():
                    errors.append(f"persistent M2 route request contains an absolute path: {path}")

        _check_projection_parity(errors)
        required_markdown = [
            PLAN_ROOT / "M2_VERTICAL_SLICE_PLAN.md",
            PLAN_ROOT / "READING_MAP_REQUESTS.md",
        ]
        for path in required_markdown:
            if not path.is_file():
                errors.append(f"missing M2 plan artifact: {path.relative_to(PROJECT_ROOT)}")
    finally:
        PROJECT_ROOT = original_root
        PLAN_ROOT = original_plan_root
    return errors, lifecycle_state


def collect_errors(project_root: Path = PROJECT_ROOT) -> list[str]:
    return collect_validation(project_root)[0]


def _legacy_schema_preparation_contract_errors(root: Path) -> list[str]:
    """Bind current B017 semantics, original Git source and native route.

    This verifies a PLAN candidate; it does not supply independent acceptance
    or authorize IMPLEMENT from an unaccepted/dirty plan checkout.
    """
    from tools.codex_route import RouteError, generate_reading_map, check_reading_map
    root = root.resolve()
    errors, _ = collect_validation(root)
    try:
        batches = _b018_json(_regular_bytes(root, ".codex/plans/m2-vertical-slice/batches.json"))
        if not check_schema_preparation(batches, root, errors):
            errors.append("current plan is not the concrete B017 allocation")
        if errors:
            return errors
        if hashlib.sha256((root / SCHEMA_PREPARATION_REBIND_TEST).read_bytes()).hexdigest() != SCHEMA_PREPARATION_REBIND_TEST_SHA256:
            return ["B017 historical rebind test bridge byte drift"]
        for relative, expected in SCHEMA_PREPARATION_LEGACY_IMPLEMENTATION_SHA256.items():
            current = root / relative
            if current.is_symlink() or not current.is_file():
                return [f"B017 fixed legacy implementation is missing or not a regular file: {relative}"]
            if hashlib.sha256(current.read_bytes()).hexdigest() != expected:
                return [f"B017 fixed legacy implementation byte drift: {relative}"]
        evidence_errors = legacy_evidence_byte_errors(root)
        if evidence_errors:
            return evidence_errors
        environment = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"}
        tree = subprocess.check_output(
            ["git", "rev-parse", SCHEMA_PREPARATION_SOURCE["commit"] + "^{tree}"],
            cwd=root, stderr=subprocess.PIPE, env=environment,
        ).decode().strip()
        if tree != SCHEMA_PREPARATION_SOURCE["tree"]:
            errors.append("B017 original source Git tree mismatch")
        subprocess.check_output(
            ["git", "merge-base", "--is-ancestor", SCHEMA_PREPARATION_SOURCE["commit"], "HEAD"],
            cwd=root, stderr=subprocess.PIPE, env=environment,
        )
        request = json.loads((root / SCHEMA_PREPARATION_ROUTE).read_bytes())
        reading_map = generate_reading_map(request, repo_root=root)
        check_reading_map(
            reading_map, repo_root=root, expected_route_id=request["route_id"],
            expected_mode="IMPLEMENT", expected_milestone="M2", expected_batch_id=SCHEMA_PREPARATION_BATCH,
        )
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError, RouteError) as exc:
        errors.append(f"B017 native source/route contract failed: {exc}")
    return errors


# Only this explicitly signed, validation-only suffix protocol is supported.
# A registration descriptor is not a PLAN acceptance receipt or a code grant.
SUFFIX_SCHEMA = "rules-residue.m2.registered-suffix/1.0"
SUFFIX_CONTRACT_SCHEMA = "rules-residue.m2.validation-prefix-contract/1.0"
SUFFIX_SCOPE = "TUTORIAL_PLATFORM_VALIDATION_ONLY"
SUFFIX_OWNER_SHA256 = "840bfea9116e589dbb620ef8aad895dd81547bf4b1ef22eda612850dfbb95f0a"
SUFFIX_BASE = {"commit": "1e2110ff6320e96833608b84ddf56fca3a3e3a56",
               "tree": "8a467ced293f2391cc9e26f0d3a769546e9b8243"}
SUFFIX_JSON_PATHS = (
    ".codex/plans/m2-vertical-slice/batches.json",
    ".codex/plans/m2-vertical-slice/controls.json",
    ".codex/plans/m2-vertical-slice/capability-probes.json",
    ".codex/state/MILESTONE_PLAN.yaml",
)
SUFFIX_MARKDOWN_PATHS = (
    ".codex/plans/m2-vertical-slice/M2_VERTICAL_SLICE_PLAN.md",
    ".codex/plans/m2-vertical-slice/READING_MAP_REQUESTS.md",
)
SUFFIX_CONTROL_PATHS = SUFFIX_JSON_PATHS + SUFFIX_MARKDOWN_PATHS
_SUFFIX_VIEW = ContextVar("validated_m2_suffix_view", default=None)
_SUFFIX_AUDIT_STACK = ContextVar("m2_suffix_receipt_source_stack", default=())


# The public grant binds only this signed implementation and its single
# canonical binding successor. It is code provenance, never a batch receipt.
NATIVE_CONSUMER_BASE = {"commit": "35688e789822bffcf35d4d40288b5c4a8332dd4a",
                        "tree": "33902e312e29658cd72e64438ec0d69ca7a141e3"}
NATIVE_CONSUMER_PATHS = (
    "tools/validate_m2_plan.py",
    "tools/validate_story_construction_governance.py",
    "tests/test_m2_b019_registration.py",
    "tests/m2/probes/validate_m2_b001_recovery_closeout.py",
    "tests/m2/probes/test_m2_b001_recovery_closeout.py",
)
NATIVE_PUBLIC_SIGNER = {
    "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHJZDkynhU9W7HUJvvVniwsft8BhUvrtT05dJgrEbsFh",
    "fingerprint": "SHA256:zR55HATrI3+mzVZW3uc8MsCxE+g5fyImXdD8X7WKkt4",
}
NATIVE_LEGACY_CODE_ANCHORS = (
    {"commit": "e90a717d3863e4fb0e5e1a0fcc01661f24d2157d",
     "tree": "7a1ce74ad0b82c7c288b94c47c966028e916137d"},
    {"commit": "45bcf298c19811c30c278deb1a881f673aff4159",
     "tree": "f55158c42f27ac1320fdaf2e5b69bdd5433dd2be"},
    NATIVE_CONSUMER_BASE,
)
# BEGIN EXACT NATIVE CONSUMER REVISION
NATIVE_CONSUMER_REVISION = {
    "artifacts": {
        "tests/m2/probes/test_m2_b001_recovery_closeout.py": "81fa650d6a981f183382b5410f768cc991285dde126a48ce70944db35ef92133",
        "tests/m2/probes/validate_m2_b001_recovery_closeout.py": "8e851f8997c3068a1144d295453a9dd5b8efd71e9f676f25d56e19b93b36ecbf",
        "tests/test_m2_b019_registration.py": "812f757cabc76829ed97a2d00534c0107fbd7b0646a1aedaabee14e688caeff9",
        "tools/validate_m2_plan.py": "24d96273663a3e9bc9376bcb5623a12906cb376bf080d933a86dc96744ad8396",
        "tools/validate_story_construction_governance.py": "14888570c17443bee642cb20f1fe4b1ea7ee4c6083d01580d35582539fc0a7f0"
    },
    "commit": "5c7364c9f103c855689bd0ec2b32d9b64f21e97f",
    "parent": {
        "commit": "35688e789822bffcf35d4d40288b5c4a8332dd4a",
        "tree": "33902e312e29658cd72e64438ec0d69ca7a141e3"
    },
    "tree": "89a6b64f638ecb52c65ef1ef91d5667d54890f5b"
}
# END EXACT NATIVE CONSUMER REVISION
_NATIVE_REVISION_VIEW = ContextVar("exact_public_native_consumer_revision", default=None)


def _native_binding_bytes(implementation: bytes, revision: dict[str, Any]) -> bytes:
    placeholder = b"# BEGIN EXACT NATIVE CONSUMER REVISION\nNATIVE_CONSUMER_REVISION = None\n# END EXACT NATIVE CONSUMER REVISION"
    _suffix_require(implementation.count(placeholder) == 1, "native implementation binding placeholder drift")
    binding = ("# BEGIN EXACT NATIVE CONSUMER REVISION\nNATIVE_CONSUMER_REVISION = "
               + json.dumps(revision, sort_keys=True, indent=4)
               + "\n# END EXACT NATIVE CONSUMER REVISION").encode()
    return implementation.replace(placeholder, binding)


def _native_tree_entries(root: Path, source: str) -> dict[str, tuple[str, str, str]]:
    entries = {}
    for line in _b018_git(root, "ls-tree", "-r", source).decode().splitlines():
        metadata, path = line.split("\t", 1)
        mode, kind, blob = metadata.split()
        entries[path] = (mode, kind, blob)
    return entries


def _native_preserved_entries(root: Path) -> dict[str, tuple[str, str, str]]:
    return {path: entry for path, entry in _native_tree_entries(root, NATIVE_CONSUMER_BASE["commit"]).items()
            if path not in NATIVE_CONSUMER_PATHS and path not in SUFFIX_CONTROL_PATHS}


def _native_regular_matches(root: Path, path: str, entry: tuple[str, str, str]) -> bool:
    raw = _actual_regular_bytes(root, path)
    mode, kind, blob = entry
    observed = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    return (kind == "blob" and mode in {"100644", "100755"} and observed == blob
            and bool((root / path).stat().st_mode & 0o111) == (mode == "100755"))


def _native_legacy_code_source(root: Path) -> None:
    """Historical data keeps only its finite source objects and unchanged code."""
    base = NATIVE_CONSUMER_BASE
    _suffix_require(_b018_git(root, "rev-parse", base["commit"] + "^{tree}").decode().strip() == base["tree"],
                    "native legacy public base tree mismatch")
    _verify_schema_accepted_signatures(root, NATIVE_PUBLIC_SIGNER, (base["commit"],))
    head = _b018_git(root, "rev-parse", "HEAD").decode().strip()
    anchor = None
    for historical in reversed(NATIVE_LEGACY_CODE_ANCHORS):
        ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", historical["commit"], head],
                                  cwd=root, capture_output=True, env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"})
        if ancestry.returncode == 0:
            anchor = historical
            break
    _suffix_require(anchor is not None, "native current revision source/ancestry mismatch: unknown legacy code history")
    _b018_git(root, "merge-base", "--is-ancestor", anchor["commit"], base["commit"])
    _suffix_require(_b018_git(root, "rev-parse", anchor["commit"] + "^{tree}").decode().strip() == anchor["tree"],
                    "native legacy fixed source tree mismatch")
    _suffix_require(not _b018_git(root, "log", "--format=%H", "--full-history", "--no-renames",
                                  anchor["commit"] + ".." + head, "--", *NATIVE_CONSUMER_PATHS).strip(),
                    "native current revision source/ancestry mismatch: code history touched/reverted")
    fixed = _native_tree_entries(root, anchor["commit"])
    actual = _native_tree_entries(root, head)
    for path in NATIVE_CONSUMER_PATHS:
        _suffix_require(actual.get(path) == fixed.get(path), "native legacy fixed source object drift: " + path)
        current = root / path
        if path not in fixed:
            _suffix_require(not current.exists() and not current.is_symlink(), "native extra legacy code path: " + path)
        else:
            _suffix_require(_native_regular_matches(root, path, fixed[path]), "native legacy code byte/mode drift: " + path)


def _native_consumer_revision(root: Path) -> dict[str, Any] | None:
    """Authenticate the actual finite public implementation and binding."""
    root = root.resolve()
    active = _NATIVE_REVISION_VIEW.get()
    if active is not None and active[0] == root:
        return active[1]
    revision = NATIVE_CONSUMER_REVISION
    if revision is None or not (root / ".git").exists():
        return None
    _suffix_keys(revision, {"commit", "tree", "parent", "artifacts"}, "native consumer revision")
    commit = _suffix_hash(revision["commit"], 40)
    _suffix_hash(revision["tree"], 40)
    _suffix_require(_suffix_json_equal(revision["parent"], NATIVE_CONSUMER_BASE), "native consumer fixed parent mismatch")
    _suffix_keys(revision["artifacts"], set(NATIVE_CONSUMER_PATHS), "native consumer finite artifacts")
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                              cwd=root, capture_output=True, env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"})
    if ancestry.returncode:
        _native_legacy_code_source(root)
        return None
    base = NATIVE_CONSUMER_BASE
    _suffix_require(_b018_git(root, "rev-parse", commit + "^{tree}").decode().strip() == revision["tree"],
                    "native implementation tree mismatch")
    _suffix_require(_b018_git(root, "rev-parse", base["commit"] + "^{tree}").decode().strip() == base["tree"],
                    "native public base tree mismatch")
    _suffix_require(_b018_git(root, "rev-list", "--parents", "-n", "1", commit).decode().split() == [commit, base["commit"]],
                    "native implementation sole parent mismatch")
    changed = _b018_git(root, "diff", "--name-only", "--no-renames", base["commit"], commit).decode().splitlines()
    _suffix_require(set(changed) == set(NATIVE_CONSUMER_PATHS), "native implementation exact five-path boundary mismatch")
    _verify_schema_accepted_signatures(root, NATIVE_PUBLIC_SIGNER, (base["commit"], commit))
    expected = {}
    for path, digest in revision["artifacts"].items():
        raw = _b018_git(root, "show", commit + ":" + path)
        _suffix_require(hashlib.sha256(raw).hexdigest() == _suffix_hash(digest), "native implementation file hash mismatch: " + path)
        expected[path] = _native_binding_bytes(raw, revision) if path == NATIVE_CONSUMER_PATHS[0] else raw
    touches = _b018_git(root, "log", "--format=%H", "--full-history", "--no-renames",
                        commit + "..HEAD", "--", *NATIVE_CONSUMER_PATHS).decode().splitlines()
    _suffix_require(len(touches) == 1, "native binding missing or code history touched/reverted")
    binding = touches[0]
    _suffix_require(_b018_git(root, "rev-list", "--parents", "-n", "1", binding).decode().split() == [binding, commit],
                    "native binding sole parent mismatch")
    _suffix_require(_b018_git(root, "diff", "--name-only", "--no-renames", commit, binding).decode().splitlines()
                    == [NATIVE_CONSUMER_PATHS[0]], "native binding changed other paths")
    head = _b018_git(root, "rev-parse", "HEAD").decode().strip()
    _verify_schema_accepted_signatures(root, NATIVE_PUBLIC_SIGNER, tuple(dict.fromkeys((binding, head))))
    for source in (commit, binding, head):
        entries = _native_tree_entries(root, source)
        for path in NATIVE_CONSUMER_PATHS:
            _suffix_require(entries.get(path, ())[:2] == ("100644", "blob"), "native source mode mismatch: " + path)
            if source != commit:
                _suffix_require(_b018_git(root, "show", source + ":" + path) == expected[path], "native bound source bytes mismatch: " + path)
    _suffix_require(not _b018_git(root, "diff", "--name-only", head, "--", *NATIVE_CONSUMER_PATHS).strip()
                    and not _b018_git(root, "diff", "--cached", "--name-only", head, "--", *NATIVE_CONSUMER_PATHS).strip(),
                    "native current code staged or uncommitted change")
    for path, raw in expected.items():
        _suffix_require(_actual_regular_bytes(root, path) == raw and not (root / path).stat().st_mode & 0o111,
                        "native current code byte/mode drift: " + path)
    preserved = _native_preserved_entries(root)
    entries = _native_tree_entries(root, head)
    for path, entry in preserved.items():
        _suffix_require(entries.get(path) == entry and _native_regular_matches(root, path, entry),
                        "native preserved input byte/mode drift: " + path)
    _suffix_require(not _b018_git(root, "log", "--format=%H", "--full-history", "--no-renames",
                                  base["commit"] + "..HEAD", "--", *sorted(preserved)).strip(),
                    "native preserved input history touched/reverted")
    return {"revision": revision, "binding_commit": binding, "head": head, "expected": expected,
            "current_sha256": {path: hashlib.sha256(raw).hexdigest() for path, raw in expected.items()}}


@contextmanager
def _native_revision_context(root: Path):
    proof = _native_consumer_revision(root)
    token = _NATIVE_REVISION_VIEW.set((root.resolve(), proof))
    try:
        yield proof
    finally:
        _NATIVE_REVISION_VIEW.reset(token)


def _current_pin_matches(root: Path, path: str, digest: str, raw: bytes | None = None) -> bool:
    current = _regular_bytes(root, path) if raw is None else raw
    observed = hashlib.sha256(current).hexdigest()
    if observed == digest:
        return True
    if path not in NATIVE_CONSUMER_PATHS:
        return False
    old = _b018_git(root, "show", NATIVE_CONSUMER_BASE["commit"] + ":" + path)
    if hashlib.sha256(old).hexdigest() != digest:
        return False
    proof = _native_consumer_revision(root)
    return proof is not None and observed == proof["current_sha256"][path]


def _native_receipt_candidate(root: Path, candidate: str, preserved: dict[str, str]) -> None:
    """A receipt cannot substitute an old reader or unbound candidate source."""
    proof = _native_consumer_revision(root)
    if proof is not None:
        _b018_git(root, "merge-base", "--is-ancestor", proof["binding_commit"], candidate)
        _verify_schema_accepted_signatures(root, NATIVE_PUBLIC_SIGNER, (candidate,))
        _suffix_require(not _b018_git(root, "log", "--format=%H", "--full-history", "--no-renames",
                                      proof["binding_commit"] + ".." + candidate, "--", *NATIVE_CONSUMER_PATHS).strip(),
                        "suffix candidate native source history touched/reverted")
        entries = _native_tree_entries(root, candidate)
        for path, raw in proof["expected"].items():
            _suffix_require(entries.get(path, ())[:2] == ("100644", "blob")
                            and _b018_git(root, "show", candidate + ":" + path) == raw,
                            "suffix candidate native source byte/mode mismatch: " + path)
    for path, digest in preserved.items():
        wanted = proof["current_sha256"][path] if proof is not None and path in proof["expected"] else digest
        _suffix_require(hashlib.sha256(_b018_git(root, "show", candidate + ":" + path)).hexdigest() == wanted,
                        "suffix accepted candidate changed a preserved current business/evidence file")


def _current_suffix_history(root: Path, proof: dict[str, Any] | None, revision: dict[str, Any] | None) -> None:
    if revision is None:
        return
    anchor = revision["binding_commit"]
    commits = _b018_git(root, "rev-list", "--reverse", "--full-history", anchor + "..HEAD", "--", *SUFFIX_CONTROL_PATHS).decode().splitlines()
    if not commits:
        _suffix_require(proof is None, "native current control history/registration mismatch")
        return
    previous = []
    seen = {tuple(hashlib.sha256(_b018_git(root, "show", anchor + ":" + path)).hexdigest()
                  for path in SUFFIX_CONTROL_PATHS)}
    for commit in commits:
        parents = _b018_git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()
        _suffix_require(len(parents) == 2, "native control history merge/parent mismatch")
        changed = _b018_git(root, "diff", "--name-only", "--no-renames", parents[1], commit, "--", *SUFFIX_CONTROL_PATHS).decode().splitlines()
        _suffix_require(set(changed) == set(SUFFIX_CONTROL_PATHS), "native control history requires the complete six-file transition")
        _verify_schema_accepted_signatures(root, _suffix_signer(root), (commit,))
        historical = _load_registered_suffix(root, commit)
        _suffix_require(historical is not None, "native control history contains an unregistered/reverted state")
        observed = historical["entries"]
        _suffix_require(len(observed) >= len(previous), "native control history removed registration")
        for old, new in zip(previous, observed):
            _suffix_require(old["id"] == new["id"] and old["contract"] == new["contract"],
                            "native control history rebound an immutable registration")
            for field in ("plan_acceptance", "implementation_acceptance"):
                _suffix_require(old[field] is None or old[field] == new[field], "native control history removed/rebound a receipt")
        hashes = tuple(hashlib.sha256(historical["control_bytes"][path]).hexdigest() for path in SUFFIX_CONTROL_PATHS)
        _suffix_require(hashes not in seen and observed != previous, "native control history touched/reverted without a proven lifecycle transition")
        for path in SUFFIX_CONTROL_PATHS:
            entry = _b018_git(root, "ls-tree", commit, "--", path).decode().strip()
            _suffix_require(entry.split("\t")[-1] == path and entry.split()[:2] == ["100644", "blob"], "native control history mode drift")
        seen.add(hashes)
        previous = observed
    _suffix_require(previous == (proof["entries"] if proof else []), "native current control history/registration mismatch")


def validated_current_m2_proof(root: Path) -> dict[str, Any]:
    """Current consumers receive only authenticated real source/control data."""
    root = root.resolve()
    with _native_revision_context(root) as revision:
        errors, _ = collect_validation(root)
        _suffix_require(not errors, "; ".join(errors))
        proof = _load_registered_suffix(root)
        _current_suffix_history(root, proof, revision)
        head = _b018_git(root, "rev-parse", "HEAD").decode().strip()
        tree = _b018_git(root, "rev-parse", "HEAD^{tree}").decode().strip()
        _verify_schema_accepted_signatures(root, NATIVE_PUBLIC_SIGNER, (head,))
        control_bytes = {path: _actual_regular_bytes(root, path) for path in SUFFIX_CONTROL_PATHS}
        for path, raw in control_bytes.items():
            entry = _b018_git(root, "ls-tree", head, "--", path).decode().strip()
            _suffix_require(entry.split("\t")[-1] == path and entry.split()[:2] == ["100644", "blob"]
                            and not (root / path).stat().st_mode & 0o111
                            and _b018_git(root, "show", head + ":" + path) == raw,
                            "native current control source/byte/mode mismatch: " + path)
        _suffix_require(not _b018_git(root, "diff", "--cached", "--name-only", head, "--", *SUFFIX_CONTROL_PATHS).strip(),
                        "native current control staged change")
        batches = _b018_json(control_bytes[SUFFIX_JSON_PATHS[0]])
        lifecycle = schema_preparation_lifecycle(batches, root) if len(batches.get("batches", [])) > 16 else {
            "state": "ACCEPTED", "accepted_batches": ["M2-B001"], "next_allowed_action": SCHEMA_ACCEPTED_ACTION}
        return {"root": root, "source": {"commit": head, "tree": tree}, "suffix": proof,
                "revision": revision, "control_bytes": control_bytes, "batches": batches, "lifecycle": lifecycle}


def _suffix_require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _suffix_keys(value: Any, keys: set[str], name: str) -> None:
    _suffix_require(isinstance(value, dict) and set(value) == keys, f"{name}: missing/unknown fields")


def _suffix_json_equal(left: Any, right: Any) -> bool:
    """Keep bool, integer and float distinct at every JSON container boundary."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return (all(type(key) is str for key in left) and all(type(key) is str for key in right)
                and left.keys() == right.keys()
                and all(_suffix_json_equal(left[key], right[key]) for key in left))
    if type(left) is list:
        return len(left) == len(right) and all(_suffix_json_equal(a, b) for a, b in zip(left, right))
    return type(left) in (str, bool, int, float, type(None)) and left == right


def _suffix_string_list(value: Any, field: str, *, allow_empty: bool = False) -> None:
    _suffix_require(type(value) is list and (allow_empty or bool(value))
                    and all(type(item) is str and bool(item.strip()) for item in value)
                    and len(set(value)) == len(value), "suffix malformed string-list envelope field: " + field)


def _suffix_hash(value: Any, width: int = 64) -> str:
    _suffix_require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{" + str(width) + r"}", value) is not None,
                    "suffix hash must be an exact lowercase digest")
    return value


def _suffix_path(value: Any) -> str:
    _suffix_require(isinstance(value, str) and value and not any(c in value for c in "\\:*?[]")
                    and all(ord(c) >= 32 and ord(c) != 127 for c in value),
                    "suffix path is not an exact file")
    path = Path(value)
    _suffix_require(not path.is_absolute() and path.as_posix() == value
                    and all(part not in {".", "..", ".git"} for part in path.parts),
                    "suffix path must be canonical and repository relative")
    return value


def _suffix_signer(root: Path) -> dict[str, str]:
    # This is the existing immutable trust identity, not a new suffix trust root.
    raw = _actual_regular_bytes(root, SCHEMA_ACCEPTED_RECEIPT)
    _suffix_require(hashlib.sha256(raw).hexdigest() == SCHEMA_ACCEPTED_RECEIPT_SHA256,
                    "current B017 signing receipt drift")
    return _b018_json(raw)["signer"]


def _suffix_source(root: Path, source: Any) -> None:
    _suffix_keys(source, {"commit", "tree"}, "suffix signed source")
    commit = _suffix_hash(source["commit"], 40)
    _suffix_hash(source["tree"], 40)
    _suffix_require(_b018_git(root, "rev-parse", commit + "^{tree}").decode().strip() == source["tree"],
                    "suffix source tree mismatch")
    _b018_git(root, "merge-base", "--is-ancestor", SUFFIX_BASE["commit"], commit)
    _b018_git(root, "merge-base", "--is-ancestor", commit, "HEAD")
    _verify_schema_accepted_signatures(root, _suffix_signer(root), (commit,))


def _suffix_bound_bytes(root: Path, source: dict[str, str], path: str, digest: str) -> bytes:
    path = _suffix_path(path)
    _suffix_hash(digest)
    current = _actual_regular_bytes(root, path)
    signed = _b018_git(root, "show", source["commit"] + ":" + path)
    mode = _b018_git(root, "ls-tree", source["commit"], "--", path).decode().strip()
    _suffix_require(mode.split("\t")[-1] == path and mode.split()[:2] == ["100644", "blob"],
                    "suffix bound path is not a regular non-executable Git blob")
    _suffix_require(not (root / path).stat().st_mode & 0o111 and signed == current
                    and hashlib.sha256(current).hexdigest() == digest, "suffix source/current/hash mismatch: " + path)
    return current


def _suffix_reference(root: Path, value: Any) -> tuple[dict[str, Any], bytes]:
    _suffix_keys(value, {"source", "path", "sha256"}, "suffix immutable reference")
    _suffix_source(root, value["source"])
    raw = _suffix_bound_bytes(root, value["source"], value["path"], value["sha256"])
    _suffix_require(not _b018_git(root, "log", "--format=%H", "--full-history", "--no-renames",
                                  value["source"]["commit"] + "..HEAD", "--", value["path"]).strip(),
                    "suffix immutable reference history touched/reverted: " + value["path"])
    return _b018_json(raw), raw


def _suffix_scope_path(path: str, kind: str) -> bool:
    if path.startswith("tests/test_native_task_prefix_") and path.endswith(".py"):
        return True
    if not path.startswith("platform-validation/task-prefix/"):
        return False
    is_lua = path.startswith("platform-validation/task-prefix/lua/") and path.endswith(".lua")
    return is_lua if kind == "HOST1_LUA" else not path.endswith(".lua") and "/lua/" not in path


def _suffix_preserved_inputs(root: Path, legacy: dict[str, Any]) -> dict[str, str]:
    raw = _actual_regular_bytes(root, CONTENT_SAFETY_CONTRACT)
    _suffix_require(hashlib.sha256(raw).hexdigest() == CONTENT_SAFETY_CONTRACT_SHA256,
                    "current B018 registration contract byte drift")
    contract = _b018_json(raw)
    tables = (CONTENT_SAFETY_ACCEPTED_STATE_SHA256, CONTENT_SAFETY_ACCEPTED_ARTIFACTS,
              SCHEMA_PREPARATION_LEGACY_IMPLEMENTATION_SHA256, B018_LEGACY_EVIDENCE,
              contract["current_consumers_sha256"], contract["original_schema_sha256"], contract.get("state_sha256", {}),
              legacy["batches"][16].get("expected_artifacts", {}),
              {SCHEMA_PREPARATION_REBIND_TEST: SCHEMA_PREPARATION_REBIND_TEST_SHA256,
               SCHEMA_ACCEPTED_RECEIPT: SCHEMA_ACCEPTED_RECEIPT_SHA256,
               CONTENT_SAFETY_ACCEPTED_RECEIPT: CONTENT_SAFETY_ACCEPTED_RECEIPT_SHA256,
               CONTENT_SAFETY_CONTRACT: CONTENT_SAFETY_CONTRACT_SHA256})
    preserved = {}
    for table in tables:
        for path, digest in table.items():
            if path not in SUFFIX_CONTROL_PATHS:
                _suffix_require(path not in preserved or preserved[path] == digest, "conflicting preserved input pins")
                preserved[path] = digest
    return preserved


def _suffix_receipt(root: Path, reference: Any, contract: dict[str, Any], phase: str,
                    contract_hash: str, plan_receipt=None) -> dict[str, Any] | None:
    if reference is None:
        return None
    receipt, _ = _suffix_reference(root, reference)
    _suffix_keys(receipt, {"schema_version", "phase", "batch_id", "scope", "decision", "candidate", "source",
                          "contract_sha256", "envelope_sha256", "producer", "reviewer", "independent",
                          "required_checks", "unresolved_findings", "control_inputs", "artifacts", "root_reception"},
                 "suffix independent receipt")
    _suffix_require(receipt["schema_version"] == "rules-residue.m2.suffix-independent-receipt/1.0"
                    and receipt["phase"] == phase and receipt["scope"] == SUFFIX_SCOPE
                    and receipt["decision"] == "PASS" and receipt["batch_id"] == contract["batch"]["id"]
                    and receipt["contract_sha256"] == contract_hash
                    and receipt["envelope_sha256"] == contract["batch"]["envelope_sha256"]
                    and receipt["independent"] is True and type(receipt["unresolved_findings"]) is int
                    and receipt["unresolved_findings"] == 0
                    and isinstance(receipt["producer"], str) and receipt["producer"].startswith("/root/")
                    and isinstance(receipt["reviewer"], str) and receipt["reviewer"].startswith("/root/")
                    and receipt["producer"] != receipt["reviewer"], "suffix receipt phase/source/independence mismatch")
    _suffix_source(root, receipt["candidate"])
    _suffix_source(root, receipt["source"])
    _b018_git(root, "merge-base", "--is-ancestor", receipt["candidate"]["commit"], reference["source"]["commit"])
    required = contract["plan_checks"] if phase == "PLAN" else contract["batch"]["tests"] + contract["batch"]["negative_tests"]
    _suffix_require(_suffix_json_equal(receipt["required_checks"], [{"command": command, "exit_code": 0} for command in required]),
                    "suffix receipt lacks exact complete required checks")
    _suffix_require(all(type(check["exit_code"]) is int for check in receipt["required_checks"]),
                    "suffix receipt exit codes must be integers")
    _suffix_require(_suffix_json_equal(receipt["root_reception"], {"decision": "RECEIVED_EXACT_INDEPENDENT_PASS", "root": "/root",
                                                                  "candidate": receipt["candidate"], "phase": phase}),
                    "suffix receipt lacks exact Root reception")
    candidate = receipt["candidate"]["commit"]
    _suffix_require(candidate != reference["source"]["commit"], "receipt must follow its distinct candidate")
    _b018_git(root, "merge-base", "--is-ancestor", receipt["source"]["commit"], candidate)
    legacy = _b018_json(_b018_git(root, "show", SUFFIX_BASE["commit"] + ":" + SUFFIX_JSON_PATHS[0]))
    _native_receipt_candidate(root, candidate, _suffix_preserved_inputs(root, legacy))
    _suffix_require(isinstance(receipt["control_inputs"], dict) and isinstance(receipt["artifacts"], dict)
                    and set(receipt["control_inputs"]) == set(SUFFIX_CONTROL_PATHS), "suffix receipt missing control input hashes/artifact table")
    for path, digest in receipt["control_inputs"].items():
        _suffix_require(hashlib.sha256(_b018_git(root, "show", candidate + ":" + path)).hexdigest() == _suffix_hash(digest),
                        "suffix independent candidate control hash mismatch")
    registry = _b018_json(_b018_git(root, "show", candidate + ":" + SUFFIX_JSON_PATHS[0]))
    _suffix_require(any(_suffix_json_equal(row, contract["batch"]) for row in registry["batches"]), "suffix receipt candidate envelope mismatch")
    if phase == "PLAN":
        planned = _load_registered_suffix(root, candidate)
        _suffix_require(_suffix_json_equal(receipt["artifacts"], {}) and planned is not None
                        and next(e for e in planned["entries"] if e["id"] == receipt["batch_id"])["plan_acceptance"] is None
                        and planned["lifecycle"]["frozen_batches"] == [receipt["batch_id"]],
                        "PLAN receipt must bind a valid first frozen candidate, not future implementation")
    else:
        _suffix_require(plan_receipt is not None, "implementation receipt lacks independent PLAN acceptance")
        frozen = _load_registered_suffix(root, receipt["source"]["commit"])
        _suffix_require(frozen is not None and _suffix_json_equal(frozen["plan_receipts"].get(receipt["batch_id"]), plan_receipt)
                        and frozen["lifecycle"]["frozen_batches"] == [receipt["batch_id"]]
                        and frozen["lifecycle"]["next_allowed_action"] == "IMPLEMENT_" + receipt["batch_id"],
                        "implementation source is not the received frozen PLAN successor")
        changed = _b018_git(root, "diff", "--name-only", receipt["source"]["commit"], candidate).decode().splitlines()
        _suffix_require(sorted(changed) == sorted(contract["batch"]["allowed_paths"])
                        and set(receipt["artifacts"]) == set(changed), "suffix implementation path boundary mismatch")
        for path, digest in receipt["artifacts"].items():
            _suffix_require(hashlib.sha256(_b018_git(root, "show", candidate + ":" + path)).hexdigest() == _suffix_hash(digest)
                            and hashlib.sha256(_actual_regular_bytes(root, path)).hexdigest() == digest,
                            "suffix accepted artifact is absent or changed")
    return receipt


def _suffix_receipt_markdown(registry: dict[str, Any], lifecycle: dict[str, Any], path: str) -> bytes:
    """Both Markdown controls project the same already validated receipts."""
    references = [{key: entry[key] for key in ("id", "plan_acceptance", "implementation_acceptance")}
                  for entry in registry["entries"]]
    if not any(item["plan_acceptance"] is not None or item["implementation_acceptance"] is not None
               for item in references):
        return b""
    projection = {"lifecycle": lifecycle, "receipts": references}
    canonical = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    section = "PLAN" if path == SUFFIX_MARKDOWN_PATHS[0] else "ROUTES"
    text = ("\n<!-- SECTION-ID: M2-SUFFIX-RECEIPT-LIFECYCLE-" + section + " -->\n"
            "# Registered suffix receipt lifecycle\n\n"
            "Validated receipt references and lifecycle SHA-256: `" + digest + "`.\n\n```json\n"
            + json.dumps(projection, ensure_ascii=False, sort_keys=True, indent=2) + "\n```\n")
    return text.encode()


def _suffix_expected_controls(base: dict[str, bytes], registry: dict[str, Any], contracts: list[dict[str, Any]],
                              lifecycle: dict[str, Any]) -> dict[str, Any]:
    """Exact six-file transition; no arbitrary operations or JSON patch language."""
    expected = {path: _b018_json(base[path]) for path in SUFFIX_JSON_PATHS}
    batches = expected[SUFFIX_JSON_PATHS[0]]
    batches["registered_suffix"] = registry
    for contract in contracts:
        row = contract["batch"]
        batches["batches"].append(row)
        batches["dependency_graph"][row["id"]] = row["dependencies"]
    accepted = ["M2-B001", SCHEMA_PREPARATION_BATCH, CONTENT_SAFETY_BATCH] + lifecycle["accepted_batches"]
    batches["accepted_batches"] = accepted
    for path in SUFFIX_JSON_PATHS:
        item = expected[path]
        item["registered_suffix_projection"] = lifecycle
        target = item["active_plan"] if path == SUFFIX_JSON_PATHS[3] else item
        target["next_allowed_action"] = lifecycle["next_allowed_action"] if path == SUFFIX_JSON_PATHS[3] else target.get("next_allowed_action")
        if path != SUFFIX_JSON_PATHS[3]:
            # Do not invent a previously absent top-level next-action field.
            if target["next_allowed_action"] is None:
                del target["next_allowed_action"]
        target["lifecycle_projection"]["next_allowed_action"] = lifecycle["next_allowed_action"]
        if path == SUFFIX_JSON_PATHS[3]:
            target["accepted_batches"] = accepted
            target["frozen_batches"] = lifecycle["frozen_batches"]
    for path in SUFFIX_MARKDOWN_PATHS:
        expected[path] = (base[path] + b"".join(c["appendices"][path].encode() for c in contracts)
                          + _suffix_receipt_markdown(registry, lifecycle, path))
    return expected


def _decode_registered_suffix(root: Path, control_source: str | None = None) -> dict[str, Any] | None:
    """Authenticate all current projections before enabling any legacy view."""
    root = root.resolve()
    active = _SUFFIX_VIEW.get()
    if control_source is None and active is not None and active["root"] == root:
        return active
    if control_source is not None:
        _suffix_hash(control_source, 40)
        _suffix_source(root, {"commit": control_source,
                              "tree": _b018_git(root, "rev-parse", control_source + "^{tree}").decode().strip()})
    raw = (_actual_regular_bytes(root, SUFFIX_JSON_PATHS[0]) if control_source is None else
           _b018_git(root, "show", control_source + ":" + SUFFIX_JSON_PATHS[0]))
    # Old16/17/18 callers keep their exact historical validation and errors,
    # without a new requirement for suffix source/authority objects. Malformed
    # old input still reaches the original rejecting validators, never a view.
    try:
        peek = json.loads(raw)
    except (ValueError, UnicodeError):
        return None
    if isinstance(peek, dict) and "registered_suffix" not in peek:
        return None
    batches = _b018_json(raw)
    _suffix_require(isinstance(batches, dict), "suffix registry must be an object")
    items = batches.get("batches")
    registry = batches.get("registered_suffix")
    _suffix_keys(registry, {"schema_version", "scope", "entries"}, "registered suffix")
    entries = registry["entries"]
    _suffix_require(registry["schema_version"] == SUFFIX_SCHEMA and registry["scope"] == SUFFIX_SCOPE
                    and isinstance(items, list) and isinstance(entries, list) and bool(entries)
                    and len(items) == 18 + len(entries), "suffix count/scope/registry mismatch")
    current_controls = {path: (_actual_regular_bytes(root, path) if control_source is None else
                              _b018_git(root, "show", control_source + ":" + path)) for path in SUFFIX_CONTROL_PATHS}
    _suffix_source(root, SUFFIX_BASE)
    base = {path: _b018_git(root, "show", SUFFIX_BASE["commit"] + ":" + path) for path in SUFFIX_CONTROL_PATHS}
    legacy = _b018_json(base[SUFFIX_JSON_PATHS[0]])
    _suffix_require(_raw_batch_rows(raw)[:18] == _raw_batch_rows(base[SUFFIX_JSON_PATHS[0]]),
                    "suffix changed historical eighteen raw rows")
    ids = [f"M2-B{i:03d}" for i in range(19, 19 + len(entries))]
    _suffix_require([entry.get("id") for entry in entries if isinstance(entry, dict)] == ids
                    and [row.get("id") for row in items if isinstance(row, dict)] == [row["id"] for row in legacy["batches"]] + ids,
                    "suffix IDs are missing, duplicate, skipped or out of order")
    contracts = []
    accepted = {}
    plan_receipts = {}
    written = set()
    previous_hash = hashlib.sha256(base[SUFFIX_JSON_PATHS[0]]).hexdigest()
    previous_source = SUFFIX_BASE["commit"]
    first_pending = None
    active_frozen = []
    for entry, row in zip(entries, items[18:]):
        _suffix_keys(entry, {"id", "contract", "plan_acceptance", "implementation_acceptance"}, "suffix entry")
        contract, _ = _suffix_reference(root, entry["contract"])
        if control_source is not None:
            _b018_git(root, "merge-base", "--is-ancestor", entry["contract"]["source"]["commit"], control_source)
            for key in ("plan_acceptance", "implementation_acceptance"):
                if entry[key] is not None:
                    _b018_git(root, "merge-base", "--is-ancestor", entry[key]["source"]["commit"], control_source)
        contract_digest = entry["contract"]["sha256"]
        _b018_git(root, "merge-base", "--is-ancestor", previous_source, entry["contract"]["source"]["commit"])
        _suffix_keys(contract, {"schema_version", "scope", "kind", "previous_contract_sha256", "owner_authority",
                               "batch", "source_bindings", "inputs", "prerequisite_artifacts", "routes", "document", "appendices", "plan_checks"},
                     "suffix contract")
        _suffix_require(contract["schema_version"] == SUFFIX_CONTRACT_SCHEMA and contract["scope"] == SUFFIX_SCOPE
                        and contract["kind"] in {"HOST1_CONTRACT", "HOST1_LUA"}
                        and contract["previous_contract_sha256"] == previous_hash,
                        "suffix unknown kind/scope or broken contract chain")
        authority = contract["owner_authority"]
        _suffix_keys(authority, {"path", "sha256"}, "suffix owner authority")
        _suffix_require(authority["sha256"] == SUFFIX_OWNER_SHA256, "suffix unknown owner/content authority")
        _suffix_bound_bytes(root, entry["contract"]["source"], authority["path"], authority["sha256"])
        _suffix_keys(contract["source_bindings"], {"path", "sha256"}, "suffix native source bindings")
        binding_ref = contract["source_bindings"]
        bindings = _b018_json(_suffix_bound_bytes(root, entry["contract"]["source"], binding_ref["path"], binding_ref["sha256"]))
        _suffix_keys(bindings, {"schema_version", "game", "host", "host_file_hashes", "qualification"}, "suffix native source evidence")
        _suffix_keys(bindings["host"], {"commit", "tree", "api_version"}, "suffix Host source")
        _suffix_hash(bindings["host"]["commit"], 40); _suffix_hash(bindings["host"]["tree"], 40)
        _suffix_require(bindings["schema_version"] == "rules-residue.native-host-source-bindings/1.0"
                        and _suffix_json_equal(bindings["game"], SUFFIX_BASE) and bindings["host"]["api_version"] == "1.0"
                        and bindings["qualification"] == "STATIC_SOURCE_ONLY" and isinstance(bindings["host_file_hashes"], dict)
                        and bool(bindings["host_file_hashes"]), "suffix missing exact native Host1.0 source evidence")
        for path, host_digest in bindings["host_file_hashes"].items():
            _suffix_path(path); _suffix_hash(host_digest)
        _suffix_keys(row, REQUIRED_BATCH_FIELDS | {"implementation_state", "ready", "parallel_safe", "formal_B002",
                                                  "acceptance_scope", "source_binding", "candidate_binding", "envelope_sha256"},
                     "suffix native envelope")
        _suffix_require(_suffix_json_equal(row, contract["batch"]) and REQUIRED_BATCH_FIELDS <= set(row)
                        and row["envelope_sha256"] == envelope_digest(row) and row["id"] == entry["id"],
                        "suffix envelope/mandatory-field/digest mismatch")
        _suffix_require(row["acceptance_scope"] == "NATIVE_HOST1_PLATFORM_VALIDATION_PREFIX_ONLY"
                        and _suffix_json_equal(row["source_binding"], {"game": SUFFIX_BASE, "host": bindings["host"],
                                                                   "path": binding_ref["path"], "sha256": binding_ref["sha256"]})
                        and _suffix_json_equal(row["candidate_binding"], {"strategy": "EXACT_HEAD_AT_VALIDATION", "clean_worktree_required": True,
                                                                      "implementation_source": "ROOT_RECEIVED_INDEPENDENT_FROZEN_PLAN_SUCCESSOR"}),
                        "suffix envelope source/candidate scope mismatch")
        # Preserve the stable TaskEnvelope shapes used by all historical18 rows.
        for field in ("id", "state", "objective", "rollback_recovery", "expected_commit_boundary"):
            _suffix_require(type(row[field]) is str and bool(row[field].strip()),
                            "suffix malformed string envelope field: " + field)
        for field in ("authority_ids", "r2_decision_ids", "input_sections", "allowed_paths", "forbidden_paths",
                      "codex_responsibilities", "platform_probes", "schemas", "fixtures", "tests", "negative_tests",
                      "acceptance_gates", "stop_conditions", "non_goals", "dependencies"):
            _suffix_string_list(row[field], field)
        for field in ("opencode_responsibilities", "grok_responsibilities"):
            _suffix_string_list(row[field], field, allow_empty=True)
        _suffix_keys(row["reading_map_request"], {"route_id", "mode", "milestone", "batch_id", "request"},
                     "suffix native TaskEnvelope reading_map_request")
        _suffix_require(row.get("formal_B002") is False and row.get("implementation_state") == "NOT_STARTED"
                        and row.get("parallel_safe") is False and row.get("state") in {"PLANNED", "FROZEN"}
                        and row.get("ready") == ("YES" if row["state"] == "FROZEN" else "NO"),
                        "suffix lifecycle/ownership/nonclaim boundary mismatch")
        deps = row["dependencies"]
        _suffix_require(isinstance(deps, list) and bool(deps) and len(set(deps)) == len(deps)
                        and all(dep in {"M2-B001", SCHEMA_PREPARATION_BATCH, CONTENT_SAFETY_BATCH} | set(ids[:len(contracts)]) for dep in deps),
                        "suffix unknown, unaccepted legacy, self, forward or cyclic dependency")
        paths = row["allowed_paths"]
        _suffix_require(isinstance(paths, list) and bool(paths) and len(set(paths)) == len(paths), "suffix duplicate/empty write paths")
        for path in paths:
            _suffix_path(path)
            _suffix_require(_suffix_scope_path(path, contract["kind"]) and path not in written,
                            "suffix path outside approved native-prefix ownership or conflicting writer")
        written.update(paths)
        for field in ("inputs", "prerequisite_artifacts"):
            table = contract[field]
            _suffix_require(isinstance(table, dict) and (bool(table) or field == "prerequisite_artifacts"), "suffix missing input bindings")
            for path, wanted in table.items():
                _suffix_require(hashlib.sha256(_actual_regular_bytes(root, _suffix_path(path))).hexdigest() == _suffix_hash(wanted),
                                "suffix actual input/prerequisite drift")
                if field == "inputs":
                    _suffix_bound_bytes(root, entry["contract"]["source"], path, wanted)
        prerequisite = {p: h for dep in deps if dep in accepted for p, h in accepted[dep]["artifacts"].items()}
        _suffix_require(all(prerequisite.get(p) == h for p, h in contract["prerequisite_artifacts"].items()),
                        "suffix prerequisite lacks exact independently accepted artifact")
        if contract["kind"] == "HOST1_LUA":
            _suffix_require(bool(prerequisite) and all(contract["prerequisite_artifacts"].get(p) == h for p, h in prerequisite.items())
                            and any(c["kind"] == "HOST1_CONTRACT" and c["batch"]["id"] in deps for c in contracts),
                            "Lua suffix requires received native contract/schema/fixtures, not an unregistered placeholder")
        _suffix_keys(contract["routes"], {"PLAN", "IMPLEMENT", "ACCEPT", "REPAIR"}, "suffix phase routes")
        _suffix_keys(contract["document"], {"path", "sha256", "section_id"}, "suffix routed envelope document")
        doc = contract["document"]
        _suffix_require(isinstance(doc["section_id"], str)
                        and re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", doc["section_id"]) is not None,
                        "suffix malformed document Section ID")
        document = _suffix_bound_bytes(root, entry["contract"]["source"], doc["path"], doc["sha256"])
        _suffix_require(b"<!-- SECTION-ID: " + doc["section_id"].encode() + b" -->" in document,
                        "suffix document Section ID missing")
        fence = re.search(rb"```json\n(.*?)\n```", document, re.DOTALL)
        _suffix_require(fence is not None and _suffix_json_equal(_b018_json(fence.group(1)), row), "suffix document/envelope mismatch")
        from tools.codex_route import RouteError, validate_request
        for mode, ref in contract["routes"].items():
            _suffix_keys(ref, {"path", "sha256"}, "suffix route")
            request = _b018_json(_suffix_bound_bytes(root, entry["contract"]["source"], ref["path"], ref["sha256"]))
            _suffix_require(isinstance(request, dict), "suffix route request must be an object")
            try:
                validate_request(request)
            except RouteError as exc:
                raise ValueError("suffix invalid native phase request: " + str(exc)) from exc
            _suffix_require(tuple(request.get(k) for k in ("mode", "milestone", "batch_id")) == (mode, "M2", entry["id"])
                            and isinstance(request.get("route_id"), str) and request["route_id"].startswith(entry["id"] + "-")
                            and any(d.get("path") == doc["path"] and d.get("required_sections") == [doc["section_id"]]
                                    for d in request.get("documents", []) if isinstance(d, dict)),
                            "suffix route identity/envelope selection mismatch")
            _suffix_require(all(isinstance(d, dict) and _suffix_path(d.get("path")) for d in request["documents"]),
                            "suffix route uses an unknown/nonrelative document")
            if mode == "IMPLEMENT":
                expected_request = {key: request[key] for key in ("route_id", "mode", "milestone", "batch_id")}
                expected_request["request"] = ref["path"]
                _suffix_require(_suffix_json_equal(row["reading_map_request"], expected_request),
                                "suffix native TaskEnvelope IMPLEMENT route identity/path drift")
        _suffix_keys(contract["appendices"], set(SUFFIX_MARKDOWN_PATHS), "suffix append-only Markdown")
        for path, text in contract["appendices"].items():
            _suffix_require(isinstance(text, str) and text.startswith("\n<!-- SECTION-ID: " + entry["id"] + "-")
                            and text.endswith("\n"), "suffix appendix Section ID/boundary missing")
        _suffix_require(isinstance(contract["plan_checks"], list) and bool(contract["plan_checks"])
                        and len(set(contract["plan_checks"])) == len(contract["plan_checks"])
                        and all(isinstance(command, str) and command for command in contract["plan_checks"]),
                        "suffix exact PLAN checks are missing")
        plan_receipt = _suffix_receipt(root, entry["plan_acceptance"], contract, "PLAN", contract_digest)
        impl_receipt = _suffix_receipt(root, entry["implementation_acceptance"], contract, "IMPLEMENT", contract_digest, plan_receipt)
        plan_receipts[entry["id"]] = plan_receipt
        if impl_receipt is not None:
            _suffix_require(first_pending is None and row["state"] == "FROZEN", "suffix accepted lifecycle is not a contiguous frozen prefix")
            accepted[entry["id"]] = impl_receipt
        else:
            if first_pending is None:
                first_pending = entry["id"]
            if row["state"] == "FROZEN":
                _suffix_require(first_pending == entry["id"] and all(dep not in ids or dep in accepted for dep in deps),
                                "only the first constructible suffix batch may freeze")
                active_frozen.append(entry["id"])
            else:
                _suffix_require(plan_receipt is None, "PLANNED suffix cannot attest an executable frozen PLAN")
        contracts.append(contract)
        previous_hash = contract_digest
        previous_source = entry["contract"]["source"]["commit"]
    _suffix_require(len(active_frozen) <= 1, "suffix concurrent active freezes")
    action = (SCHEMA_ACCEPTED_ACTION if first_pending is None else "PLAN_" + first_pending
              if not active_frozen else "IMPLEMENT_" + first_pending if plan_receipts[first_pending] is not None
              else "ACCEPT_PLAN_" + first_pending)
    lifecycle = {"state": "ACCEPTED" if first_pending is None else "PLAN_PENDING" if not active_frozen
                 else "FROZEN_ACCEPTED_PLAN" if plan_receipts[first_pending] is not None else "FROZEN_PLAN_PENDING_ACCEPTANCE",
                 "accepted_batches": list(accepted), "frozen_batches": active_frozen,
                 "next_allowed_action": action, "formal_B002": False, "blocking_ids": EXPECTED_RECOVERY_BLOCKERS,
                 "runtime_status": "NOT_RUN", "aggregate_M2_pass": False}
    expected = _suffix_expected_controls(base, registry, contracts, lifecycle)
    for path, wanted in expected.items():
        if path in SUFFIX_JSON_PATHS:
            _suffix_require(_suffix_json_equal(_b018_json(current_controls[path]), wanted), "suffix actual control projection drift: " + path)
        else:
            _suffix_require(current_controls[path] == wanted, "suffix rewrote old Markdown or unsigned appendix: " + path)
    # Business, consumer, schema and evidence pins are actual current files and
    # all pass before the six-control-file legacy view can be activated.
    for path, digest in _suffix_preserved_inputs(root, legacy).items():
        _suffix_require(hashlib.sha256(_actual_regular_bytes(root, path)).hexdigest() == digest,
                        "suffix current preserved business/evidence drift before historical view: " + path)
    return {"root": root, "base": base, "legacy_batches": legacy, "current_batches": batches,
            "contracts": contracts, "entries": entries, "lifecycle": lifecycle, "plan_receipts": plan_receipts,
            "accepted": accepted, "control_bytes": current_controls}


def _load_registered_suffix(root: Path, control_source: str | None = None) -> dict[str, Any] | None:
    active = _SUFFIX_VIEW.get()
    if control_source is None and active is not None and active["root"] == root.resolve():
        return active
    key = (str(root.resolve()), control_source or "CURRENT")
    stack = _SUFFIX_AUDIT_STACK.get()
    _suffix_require(key not in stack, "suffix receipt/source validation cycle")
    token = _SUFFIX_AUDIT_STACK.set(stack + (key,))
    try:
        return _decode_registered_suffix(root, control_source)
    finally:
        _SUFFIX_AUDIT_STACK.reset(token)


@contextmanager
def _suffix_legacy_view(proof: dict[str, Any] | None):
    token = _SUFFIX_VIEW.set(proof)
    try:
        yield
    finally:
        _SUFFIX_VIEW.reset(token)


def _regular_bytes(root: Path, relative: str) -> bytes:
    proof = _SUFFIX_VIEW.get()
    if proof is not None and proof["root"] == root.resolve() and relative in SUFFIX_CONTROL_PATHS:
        return proof["base"][relative]
    return _actual_regular_bytes(root, relative)


def _suffix_errors(root: Path, legacy) -> list[str]:
    try:
        with _native_revision_context(root):
            proof = _load_registered_suffix(root)
            with _suffix_legacy_view(proof):
                return legacy(root)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError, subprocess.CalledProcessError) as exc:
        return ["registered suffix rejected: " + str(exc)]


def content_safety_accepted_evidence_errors(root: Path) -> list[str]:
    return _suffix_errors(root, _legacy_content_safety_accepted_evidence_errors)


def content_safety_contract_errors(root: Path) -> list[str]:
    return _suffix_errors(root, _legacy_content_safety_contract_errors)


def content_safety_native_errors(root: Path) -> list[str]:
    return _suffix_errors(root, _legacy_content_safety_native_errors)


def schema_preparation_contract_errors(root: Path) -> list[str]:
    return _suffix_errors(root, _legacy_schema_preparation_contract_errors)


def check_schema_preparation(batches: dict[str, Any], root: Path, errors: list[str], artifact_reader=None) -> bool:
    if _SUFFIX_VIEW.get() is not None:
        return _legacy_check_schema_preparation(batches, root, errors, artifact_reader)
    try:
        proof = _load_registered_suffix(root)
        if proof is not None:
            _suffix_require(_suffix_json_equal(batches, proof["current_batches"]) and artifact_reader is None, "suffix caller supplied a different registry/reader")
        with _suffix_legacy_view(proof):
            return _legacy_check_schema_preparation(proof["legacy_batches"] if proof else batches, root, errors, artifact_reader)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError, subprocess.CalledProcessError) as exc:
        errors.append("registered suffix rejected: " + str(exc))
        return False


def schema_preparation_lifecycle(batches: dict[str, Any], root: Path, artifact_reader=None) -> dict[str, Any]:
    proof = _load_registered_suffix(root)
    if proof is None:
        return _legacy_schema_preparation_lifecycle(batches, root, artifact_reader)
    _suffix_require(_suffix_json_equal(batches, proof["current_batches"]) and artifact_reader is None, "suffix lifecycle registry/reader mismatch")
    errors, _ = collect_validation(root)
    _suffix_require(not errors, "; ".join(errors))
    result = dict(proof["lifecycle"])
    result["accepted_batches"] = ["M2-B001", SCHEMA_PREPARATION_BATCH, CONTENT_SAFETY_BATCH] + result["accepted_batches"]
    return result


def _check_dag(batches: dict[str, Any], errors: list[str]) -> None:
    items = batches.get("batches")
    if isinstance(items, list) and len(items) <= 18 and "registered_suffix" not in batches:
        return _legacy_check_dag(batches, errors)
    try:
        proof = _load_registered_suffix(PROJECT_ROOT)
        _suffix_require(proof is not None and _suffix_json_equal(batches, proof["current_batches"]), "unregistered suffix DAG")
        _legacy_check_dag(proof["legacy_batches"], errors)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError, subprocess.CalledProcessError) as exc:
        errors.append("registered suffix DAG rejected: " + str(exc))


def collect_validation(project_root: Path = PROJECT_ROOT) -> tuple[list[str], str]:
    try:
        with _native_revision_context(project_root) as revision:
            proof = _load_registered_suffix(project_root)
            if proof is None:
                # Preserve the old fail-fast unregistered-data path: reject
                # its actual bytes before selecting any historical controls.
                result = _legacy_collect_validation(project_root)
                if not result[0]:
                    _current_suffix_history(project_root, None, revision)
                return result
            _current_suffix_history(project_root, proof, revision)
            with _suffix_legacy_view(proof):
                # Current code validates every input; only the authenticated
                # six control projections use immutable historical bytes.
                return _legacy_collect_validation(project_root)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError, subprocess.CalledProcessError) as exc:
        return ["registered suffix rejected: " + str(exc)], INVALID_MIXED_STATE


def registered_suffix_batch_errors(root: Path, batch_id: str, implementation_source: str | None = None) -> list[str]:
    errors, _ = collect_validation(root)
    if errors:
        return errors
    from tools.codex_route import RouteError, generate_reading_map, check_reading_map
    try:
        proof = _load_registered_suffix(root)
        _suffix_require(proof is not None, "batch has no authenticated suffix registration")
        index = next(i for i, c in enumerate(proof["contracts"]) if c["batch"]["id"] == batch_id)
        contract = proof["contracts"][index]
        mode = "IMPLEMENT" if implementation_source else "PLAN"
        ref = contract["routes"][mode]
        request = _b018_json(_actual_regular_bytes(root, ref["path"]))
        route = generate_reading_map(request, repo_root=root)
        check_reading_map(route, repo_root=root, expected_route_id=request["route_id"], expected_mode=mode,
                         expected_milestone="M2", expected_batch_id=batch_id)
        if implementation_source:
            _suffix_hash(implementation_source, 40)
            receipt = proof["plan_receipts"][batch_id]
            source_proof = _load_registered_suffix(root, implementation_source)
            _suffix_require(receipt is not None and source_proof is not None
                            and source_proof["control_bytes"] == proof["control_bytes"]
                            and source_proof["plan_receipts"].get(batch_id) == receipt
                            and proof["lifecycle"]["frozen_batches"] == [batch_id]
                            and proof["lifecycle"]["next_allowed_action"] == "IMPLEMENT_" + batch_id,
                            "IMPLEMENT requires this exact independently received first frozen PLAN successor")
            _suffix_require(not _b018_git(root, "status", "--porcelain").strip(), "suffix implementation candidate must be clean")
            _b018_git(root, "merge-base", "--is-ancestor", implementation_source, "HEAD")
            changed = _b018_git(root, "diff", "--name-only", implementation_source, "HEAD").decode().splitlines()
            _suffix_require(sorted(changed) == sorted(contract["batch"]["allowed_paths"]), "suffix implementation diff outside exact batch paths")
            for path in changed:
                _actual_regular_bytes(root, path)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError, StopIteration, subprocess.CalledProcessError, RouteError) as exc:
        errors.append("registered suffix batch/source/route rejected: " + str(exc))
    return errors
def classify_lifecycle(project_root: Path = PROJECT_ROOT) -> str:
    errors, lifecycle_state = collect_validation(project_root)
    if errors:
        return INVALID_MIXED_STATE
    return lifecycle_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", help="B017/B018 or an authenticated contiguous registered suffix ID")
    parser.add_argument("--implementation-source")
    args = parser.parse_args()
    errors, lifecycle_state = collect_validation(PROJECT_ROOT)
    if args.batch == CONTENT_SAFETY_BATCH:
        errors.extend(content_safety_native_errors(PROJECT_ROOT))
        if args.implementation_source:
            errors.extend(check_content_safety_implementation(PROJECT_ROOT, args.implementation_source))
    elif args.batch == SCHEMA_PREPARATION_BATCH:
        errors.extend(schema_preparation_contract_errors(PROJECT_ROOT))
        batches = _read_json(PLAN_ROOT / "batches.json", errors)
        if not isinstance(batches, dict) or not check_schema_preparation(batches, PROJECT_ROOT, errors):
            errors.append("B017 is not a valid frozen native envelope")
        elif args.implementation_source:
            errors.extend(check_implementation_scope(PROJECT_ROOT, args.implementation_source, next(x for x in batches["batches"] if x["id"] == SCHEMA_PREPARATION_BATCH)))
    elif args.batch:
        errors.extend(registered_suffix_batch_errors(PROJECT_ROOT, args.batch, args.implementation_source))
    elif args.implementation_source:
        errors.append("--implementation-source requires an exact registered --batch")
    if errors:
        print("M2_PLAN_VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("M2_PLAN_VALIDATION: PASS")
    print("- legacy B001--B016 contracts and native next-ID allocation/DAG: PASS")
    print("- 12 integration probes and 31 acceptance gates: PASS")
    print("- Task Packet ownership, deferred checkpoints, and external NOT_RUN states: PASS")
    print("- routed machine-input projections match their repository sources byte-for-byte: PASS")
    print(f"- M2-B001 lifecycle state: {lifecycle_state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
