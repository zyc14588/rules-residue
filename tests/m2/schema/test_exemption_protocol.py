"""Structural C14 contract vectors, not a runtime or authority validator."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.lib.schema_subset import validate


class ExemptionProtocolContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / 'schemas/r2/exemption-protocol-v1.schema.json').read_text())
        cls.fixture = json.loads((ROOT / 'tests/m2/fixtures/schema/exemption-protocol-v1.json').read_text())

    def test_approved_boundary_positive_and_negative_vectors(self):
        self.assertEqual(len(self.fixture['cases']), 22)
        for case in self.fixture['cases']:
            with self.subTest(case=case['case_id']):
                issues = validate(case['value'], self.schema)
                self.assertEqual(not issues, case['expected_schema_valid'], str(issues))

    def test_json_serialization_does_not_change_verdict(self):
        for case in self.fixture['cases']:
            with self.subTest(case=case['case_id']):
                value = json.loads(json.dumps(case['value'], sort_keys=True, separators=(',', ':')))
                self.assertEqual(not validate(value, self.schema), case['expected_schema_valid'])

    def test_all_positive_shapes_reject_unknown_fields(self):
        for case in self.fixture['cases']:
            if case['expected_schema_valid']:
                with self.subTest(case=case['case_id']):
                    value = deepcopy(case['value'])
                    value['agent_authoritative_override'] = True
                    self.assertTrue(validate(value, self.schema))

    def test_no_unimplemented_schema_keyword_is_used_for_enforcement(self):
        supported = {'$schema', '$id', 'title', 'description', 'type', 'const', 'enum',
                     'additionalProperties', 'required', 'properties', 'oneOf', 'items',
                     'minItems', 'maxItems', 'uniqueItems', 'minLength', 'maxLength',
                     'pattern', 'minimum', 'maximum'}

        def inspect(schema):
            self.assertFalse(set(schema) - supported)
            for child in schema.get('properties', {}).values():
                inspect(child)
            for child in schema.get('oneOf', []):
                inspect(child)
            if isinstance(schema.get('items'), dict):
                inspect(schema['items'])

        inspect(self.schema)


if __name__ == '__main__':
    unittest.main()
