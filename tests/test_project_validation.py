import unittest

from tools.validate_project import collect_errors


class ProjectValidationTests(unittest.TestCase):
    def test_project_has_no_validation_errors(self) -> None:
        self.assertEqual(collect_errors(), [])


if __name__ == "__main__":
    unittest.main()
