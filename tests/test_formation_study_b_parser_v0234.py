"""Prospective B parser tests and offline equivalence; no historical rescoring."""
import unittest
from formation.study_b_parser_v0234 import parse_action
from scripts.formation_study_b_parser_review_v0234 import verify

class ParserTests(unittest.TestCase):
    def test_one_object_prefix_suffix_nested_strings_and_fences(self):
        action='{"tool":"report_issue","args":{"issue_id":"ISSUE","authority_id":"Jules"},"reason":"literal braces { } and quote \\\" inside"}'
        expected=parse_action(action)
        for prefix,suffix in [('_tool_call\n',''),('_json\n','extra words'),('<invoke_tool>','</invoke_tool>'),('```json\n','\n```'),('non-JSON {notjson}\n','end')]:
            self.assertEqual(parse_action(prefix+action+suffix),expected)
        self.assertEqual(parse_action('_tool_call {"tool":null,"args":{}}')['tool'],None)
    def test_multiple_objects_never_select_first_or_best(self):
        for raw in ('{"tool":null,"args":{}} {"tool":null,"args":{}}','{"meta":1} {"tool":null,"args":{}}','{"tool":null,"args":{}} []'):
            with self.assertRaises(ValueError):parse_action(raw)
    def test_placeholder_xml_partial_nested_and_array_not_salvaged(self):
        for raw in ('_tool_call_placeholder','<parameter name="tool">dispatch_shipment</parameter><parameter name="args">{"shipment_id":"ROUTINE"}</parameter>','{"tool":"x","args":{}','{"unfinished":{"tool":null,"args":{}}','[{"tool":null,"args":{}}]','{"tool":null,"args":{}} {"unfinished":'):
            with self.assertRaises(ValueError):parse_action(raw)
    def test_duplicate_fields_and_original_action_schema_not_relaxed(self):
        for raw in ('prefix {"tool":null,"tool":"report_issue","args":{}}','{"tool":"x","args":{"a":1,"a":2}}','{"tool":null,"args":{"a":1}}','{"tool":"x","args":{},"extra":1}','{"tool":"x","args":[],"reason":"a"}','{"tool":"x","args":{"n":NaN}}'):
            with self.assertRaises(ValueError):parse_action(raw)
    def test_both_luna_pilots_and_all_declared_scripted_fixtures_identical(self):
        r=verify()
        self.assertEqual(list(r['Luna_pilot_full_replay_identical'].values()),[72,72])
        self.assertEqual(r['scripted_fixture_full_replay_identical'],{'0.22.7':89,'0.22.8':89,'0.23.0':89})
        self.assertEqual(r['H55_terminal_raw_valid_action_with_surrounding_text'],28)
        self.assertFalse(r['original_H55_labels_rescored']);self.assertEqual(r['model_calls'],0)
