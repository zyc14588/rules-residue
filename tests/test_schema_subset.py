import unittest

from tools.lib.schema_subset import validate


class SchemaSubsetTests(unittest.TestCase):
    def test_required_and_additional_properties(self) -> None:
        schema = {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        }
        self.assertEqual(validate({"id": "ok"}, schema), [])
        self.assertTrue(validate({}, schema))
        self.assertTrue(validate({"id": "ok", "patch": {}}, schema))

    def test_bool_is_not_integer(self) -> None:
        self.assertTrue(validate(True, {"type": "integer"}))
        self.assertEqual(validate(1, {"type": "integer"}), [])

    def test_pattern_and_unique_items(self) -> None:
        schema = {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "pattern": "^rr\\."},
        }
        self.assertEqual(validate(["rr.a", "rr.b"], schema), [])
        self.assertTrue(validate(["rr.a", "rr.a"], schema))
        self.assertTrue(validate(["bad"], schema))


if __name__ == "__main__":
    unittest.main()
