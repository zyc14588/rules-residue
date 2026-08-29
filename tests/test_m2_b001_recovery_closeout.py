from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class M2B001RecoveryCloseoutBridgeTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def test_full_m2_probe_suite_is_bridged_fail_closed(self) -> None:
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
