from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import platform
import subprocess
import sys
import tempfile
from datetime import date

from tools.build_package import _quarantine_encode as build_package, default_output
from tools.lib.common import PROJECT_ROOT, REPORT_ROOT, read_json, sha256_file, write_json


def run_command(command: list[str]) -> dict[str, object]:
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    for path in REPORT_ROOT.glob("acceptance.*"):
        path.unlink()

    commands = [
        run_command([sys.executable, "tools/validate_project.py"]),
        run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]),
    ]
    failed = [item for item in commands if item["exit_code"] != 0]

    reproducible = False
    digest_a = None
    digest_b = None
    package_output = default_output()
    package_digest = None
    build_error = None
    if not failed:
        try:
            with tempfile.TemporaryDirectory(prefix="rules-residue-acceptance-") as directory:
                first = Path(directory) / "a.trpgpkg"
                second = Path(directory) / "b.trpgpkg"
                digest_a = build_package(first, validate_first=True)
                digest_b = build_package(second, validate_first=True)
                reproducible = digest_a == digest_b and first.read_bytes() == second.read_bytes()
                if not reproducible:
                    build_error = "deterministic package builds differ"
            if reproducible:
                package_digest = build_package(package_output, validate_first=True)
        except Exception as exc:  # acceptance must report the exact blocker
            build_error = f"{type(exc).__name__}: {exc}"

    local_pass = not failed and reproducible and build_error is None
    manifest = read_json(PROJECT_ROOT / "game-package" / "manifest.json")
    report = {
        "schema_version": "rules-residue.acceptance-report/1.0",
        "project": manifest["id"],
        "version": manifest["version"],
        "date": date.today().isoformat(),
        "result": "PASS_LOCAL_PROJECT_INITIALIZED" if local_pass else "FAIL_LOCAL",
        "public_release": "BLOCKED_BY_DESIGN",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "commands": commands,
        "deterministic_build": {
            "pass": reproducible,
            "first_sha256": digest_a,
            "second_sha256": digest_b,
            "error": build_error,
        },
        "artifact": {
            "path": package_output.relative_to(PROJECT_ROOT).as_posix() if package_digest else None,
            "sha256": package_digest,
        },
        "content_safety_admission": {"status":"NOT_CLAIMED", "scope":"structural tests and raw quarantined deterministic package only; production consumers require current independently received receipts"},
        "external_gates": [
            {"id":"GATE-PLATFORM-001","status":"NOT_RUN","reason":"requires TRPG_PLATFORM Lua 5.5 sandbox and Host API"},
            {"id":"GATE-CREATOR-001","status":"NOT_RUN","reason":"requires Creator Tool import/edit/export roundtrip"},
            {"id":"GATE-REL-001","status":"BLOCKED_DECISION","reason":"final first-party license is open"},
            {"id":"GATE-REL-002","status":"BLOCKED_EXTERNAL","reason":"formal Game Package API is not frozen"},
        ],
    }
    write_json(REPORT_ROOT / "acceptance.json", report)

    command_lines: list[str] = []
    for item in commands:
        status = "PASS" if item["exit_code"] == 0 else "FAIL"
        command_lines.append(f"- `{ ' '.join(item['command']) }`: {status} (exit {item['exit_code']})")
    markdown = "# M0 Initialization Acceptance\n\n"
    markdown += f"- Result: **{report['result']}**\n"
    markdown += f"- Project: `{report['project']}`\n"
    markdown += f"- Version: `{report['version']}`\n"
    markdown += f"- Public release: **BLOCKED BY DESIGN**\n\n"
    markdown += "## Local evidence\n\n" + "\n".join(command_lines) + "\n\n"
    markdown += f"- Deterministic build: {'PASS' if reproducible else 'FAIL'}\n"
    markdown += f"- Game Package SHA-256: `{package_digest or 'not generated'}`\n\n"
    markdown += "## External gates not claimed\n\n"
    markdown += "- Real Lua 5.5 platform sandbox execution: NOT RUN\n"
    markdown += "- Creator Tool semantic roundtrip: NOT RUN\n"
    markdown += "- Final content license: OPEN / release blocker\n"
    markdown += "- Formal Host API compatibility certification: BLOCKED EXTERNAL\n"
    (REPORT_ROOT / "acceptance.md").write_text(markdown, encoding="utf-8", newline="\n")

    print(report["result"])
    for item in commands:
        print(f"[{item['exit_code']}] {' '.join(item['command'])}")
        if item["stdout"]:
            print(item["stdout"].rstrip())
        if item["stderr"]:
            print(item["stderr"].rstrip(), file=sys.stderr)
    print("semantic admission: NOT_CLAIMED (raw structural archive has no consumption authority)")
    print(f"deterministic build: {'PASS' if reproducible else 'FAIL'}")
    if package_digest:
        print(f"package: {package_output}")
        print(f"sha256: {package_digest}")
    if build_error:
        print(f"build error: {build_error}", file=sys.stderr)
    return 0 if local_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
