from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tools.validate_m2_plan import (
    ACCEPTED_WITH_BLOCKERS,
    FROZEN_RECOVERY_PENDING,
    collect_validation,
)


CURRENT_RECOVERY_CANDIDATE = "CURRENT_RECOVERY_CANDIDATE"
HISTORICAL_ACCEPTED_RECOVERY = "HISTORICAL_ACCEPTED_RECOVERY"


class M2B001RecoveryCloseoutBridgeTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def lifecycle_validation_mode(self) -> str:
        errors, state = collect_validation(self.root)
        self.assertEqual(errors, [], "M2 lifecycle state is invalid before recovery validation")
        if state == FROZEN_RECOVERY_PENDING:
            return CURRENT_RECOVERY_CANDIDATE
        if state == ACCEPTED_WITH_BLOCKERS:
            return HISTORICAL_ACCEPTED_RECOVERY
        self.fail(f"unsupported M2 lifecycle state for recovery validation: {state}")

    def run_actual_recovery_validation(self) -> None:
        mode = self.lifecycle_validation_mode()
        command = [
            sys.executable,
            "tests/m2/probes/validate_m2_b001_recovery_closeout.py",
            "--validate",
            "--mode",
            mode,
        ]
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=self.root,
            text=True,
        ).strip()
        if not status:
            command.extend(
                [
                    "--candidate",
                    subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], cwd=self.root, text=True
                    ).strip(),
                    "--candidate-tree",
                    subprocess.check_output(
                        ["git", "rev-parse", "HEAD^{tree}"], cwd=self.root, text=True
                    ).strip(),
                ]
            )
        result = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(
                "actual lifecycle-aware recovery validation failed\n"
                f"command: {' '.join(command)}\n"
                f"exit_code: {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

    def test_full_m2_probe_suite_is_bridged_fail_closed(self) -> None:
        self.run_actual_recovery_validation()
        command = [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/m2/probes",
            "-p",
            "test_*.py",
            "-v",
        ]
        result = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(
                "nested M2 probe suite failed\n"
                f"command: {' '.join(command)}\n"
                f"exit_code: {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
