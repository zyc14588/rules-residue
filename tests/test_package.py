import tempfile
import unittest
from pathlib import Path

from tools.build_package import build_package
from tools.lib.common import GAME_PACKAGE_ROOT, compute_lock_document, read_json


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


if __name__ == "__main__":
    unittest.main()
