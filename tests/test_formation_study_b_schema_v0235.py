"""Neutral native syntax, tested without credentials or transport."""
import inspect
import json
import unittest
from pathlib import Path
from formation.study_a import StudyAWorld, TOOL_SPECS
from formation.study_b_schema_v0235 import StructuredClaudeChat, reply_schema
from formation.clients import ClaudeChat
from formation.study_a_pilot import SYSTEM

ROOT = Path(__file__).resolve().parents[1]


class NeutralSchemaTests(unittest.TestCase):
    def test_every_tool_and_only_visible_tool_constants(self):
        schema = reply_schema()
        self.assertEqual(schema, json.loads((ROOT/'studies/formation-study-b-haiku-json-schema-v0235.json').read_text()))
        branches = schema['anyOf']
        self.assertEqual([b['properties']['tool'].get('const') for b in branches[:-1]], list(TOOL_SPECS))
        for name, branch in zip(TOOL_SPECS, branches):
            args = branch['properties']['args']
            parameters = list(inspect.signature(getattr(StudyAWorld, name)).parameters)[1:]
            self.assertEqual(args['required'], parameters)
            self.assertEqual(args['properties'], {p: {'type': 'string'} for p in parameters})
            self.assertFalse(args['additionalProperties'])
        self.assertEqual(branches[-1]['properties']['tool'], {'type': 'null'})
        for branch in branches:
            self.assertEqual(set(branch['properties']), {'tool', 'args', 'reason'})
            self.assertEqual(branch['required'], ['tool', 'args'])
            self.assertEqual(branch['properties']['reason'], {'type': 'string'})
            self.assertFalse(branch['additionalProperties'])

    def test_request_changes_only_native_format_no_forced_tool_or_thinking_override(self):
        rec = type('OfflineRecorder', (), {'model': 'claude-haiku-5-5'})()
        history = [{'role': 'user', 'content': 'unchanged full history'}]
        original = ClaudeChat(rec.model, rec, max_output_tokens=4096).body(SYSTEM, history)
        amended = StructuredClaudeChat(rec.model, rec, max_output_tokens=4096).body(SYSTEM, history)
        self.assertEqual(amended.pop('output_config'), {'format': {'type': 'json_schema', 'schema': reply_schema()}})
        self.assertEqual(amended, original)
        self.assertFalse({'thinking', 'effort', 'temperature', 'tools', 'tool_choice'} & set(amended))

if __name__ == '__main__':
    unittest.main()
