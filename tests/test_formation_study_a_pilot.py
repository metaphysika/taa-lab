"""Paid-run safeguards verified using declared scripted replies and fake transport."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped
from formation.clients import OpenAIChat
from formation.study_a import ROOT, load_cases
from formation.study_a_pilot import PilotRecorder, run_episode, run_pilot, validate_plan

PLAN = ROOT / 'studies/formation-study-a-luna-pilot-plan-2026-10-10.json'
PRICES = {'gpt-6-luna': {'input_per_million': .10, 'output_per_million': .50}}

class Response:
    headers = {}
    def __init__(self, raw): self.raw = raw
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self):
        return json.dumps({'id': 'scripted', 'model': 'gpt-6-luna',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50},
            'choices': [{'message': {'content': self.raw}, 'finish_reason': 'stop'}]}).encode()

class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.plan = json.loads(PLAN.read_text())
        self.cases = {c['id']: c for c in load_cases()}
        self.fixtures = json.loads((ROOT / 'studies/formation-study-a-fixtures-v0213.json').read_text())['fixtures']

    def recorder(self, **kwargs):
        limits = dict(max_logical=144, max_attempts=144, max_dollars=.65)
        limits.update(kwargs)
        return PilotRecorder(self.directory / 'calls.jsonl', PRICES, 'gpt-6-luna', **limits)

    def test_plan_cannot_expand_budget_model_or_cases(self):
        validate_plan(self.plan)
        for key, value in [('max_request_attempts',145), ('proposed_stage_application_stop_dollars', .66),
                           ('model','other-model'), ('automatic_retries',1), ('max_completion_tokens',2049)]:
            changed = copy.deepcopy(self.plan); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_plan(changed)
        changed = copy.deepcopy(self.plan)
        changed['scenario_sha256']['scenarios/formation/A_W01.json'] = 'changed'
        with self.assertRaises(ValueError): validate_plan(changed)

    def test_byte_and_output_guards_prevent_transport(self):
        recorder = self.recorder()
        client = OpenAIChat('gpt-6-luna', recorder, max_output_tokens=2048)
        with patch.dict('os.environ', {'OPENAI_API_KEY':'scripted-test-key'}), patch('urllib.request.urlopen') as send:
            with self.assertRaises(BudgetStopped): client.chat('', [{'role':'user','content':'x'*32000}])
            client.max_output_tokens = 2049
            with self.assertRaises(BudgetStopped): client.chat('', [{'role':'user','content':'tiny'}])
            send.assert_not_called()
        self.assertEqual(recorder.attempt_count, 0)
        self.assertEqual(recorder.spent, 0)

    def test_dollar_and_attempt_guards_prevent_transport(self):
        recorder = self.recorder(max_dollars=.000001)
        client = OpenAIChat('gpt-6-luna', recorder, max_output_tokens=2048)
        with patch.dict('os.environ', {'OPENAI_API_KEY':'scripted-test-key'}), patch('urllib.request.urlopen') as send:
            with self.assertRaises(BudgetStopped): client.chat('', [{'role':'user','content':'tiny'}])
            recorder.max_dollars = .65; recorder.max_attempts = 0
            with self.assertRaises(BudgetStopped): client.chat('', [{'role':'user','content':'tiny'}])
            send.assert_not_called()

    def test_live_history_uses_raw_replies_effects_and_no_gold(self):
        packets = next(f['packets'] for f in self.fixtures if f['case_id']=='A_W01' and f['name']=='required_conduct')
        raws = iter(p['raw'] for p in packets)
        bodies = []
        def send(request, **kwargs):
            body = json.loads(request.data); bodies.append(body)
            self.assertLessEqual(len(request.data),32000)
            self.assertEqual(set(body), {'model','messages','max_completion_tokens'})
            return Response(next(raws))
        recorder = self.recorder()
        with patch.dict('os.environ', {'OPENAI_API_KEY':'scripted-test-key'}), patch('urllib.request.urlopen', side_effect=send):
            result, stopped = run_episode(self.cases['A_W01'], OpenAIChat('gpt-6-luna',recorder,max_output_tokens=2048), recorder)
        self.assertFalse(stopped)
        self.assertEqual(result['score']['outcome'],'correct')
        self.assertEqual([p['raw'] for p in result['raw_replies']], [p['raw'] for p in packets])
        self.assertEqual(bodies[1]['messages'][2]['content'], packets[0]['raw'])
        initial=json.loads(bodies[0]['messages'][1]['content'])['task_context']
        self.assertNotIn('requirements',initial); self.assertNotIn('kind',initial)
        feedback=json.loads(bodies[1]['messages'][-1]['content'])
        self.assertTrue(feedback['last_tool_result']['ok'])

    def test_uncertain_failure_has_one_attempt_keeps_reserve_and_stops(self):
        recorder = self.recorder()
        with patch.dict('os.environ', {'OPENAI_API_KEY':'scripted-test-key'}), patch('urllib.request.urlopen',side_effect=TimeoutError) as send:
            result, stopped = run_episode(self.cases['A_W01'],OpenAIChat('gpt-6-luna',recorder,max_output_tokens=2048),recorder)
        self.assertTrue(stopped); self.assertEqual(send.call_count,1)
        self.assertEqual(result['score']['outcome'],'error'); self.assertGreater(recorder.spent,0)

    def test_full_batch_persists_each_case_and_blocks_rerun(self):
        root = self.directory / 'root'
        for pattern in ['formation/*.py','agents/call_telemetry.py','agents/gemini_client.py','taa/gate.py',
                        'taa/records.py','taa/determinations.py','scripts/formation_study_a_pilot.py',
                        'scenarios/formation/A*.json']:
            for source in ROOT.glob(pattern):
                destination=root/source.relative_to(ROOT)
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(source.read_bytes())
        packets=[]
        for path in self.plan['scenario_sha256']:
            cid=json.loads((ROOT/path).read_text())['id']
            packets += next(f['packets'] for f in self.fixtures if f['case_id']==cid and f['name']=='required_conduct')
        raws=iter(p['raw'] for p in packets)
        output=self.directory/'output'
        with patch('formation.study_a_pilot.load_keys') as keys, patch.dict('os.environ', {'OPENAI_API_KEY':'scripted-test-key'}), patch('urllib.request.urlopen',side_effect=lambda *a,**k: Response(next(raws))) as send, redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError): run_pilot(PLAN,output,root=root)
            keys.assert_not_called(); send.assert_not_called()
            summary=run_pilot(PLAN,output,approved=True,root=root)
            self.assertEqual(summary['outcomes'],{'correct':12})
            self.assertEqual(summary['accounting']['request_attempts'],len(packets))
            self.assertLess(summary['batch_estimated_dollars'],.65)
            for cid in self.cases: self.assertTrue((output/(cid+'.json')).exists())
            with self.assertRaises(ValueError): run_pilot(PLAN,output,approved=True,root=root)
            self.assertEqual(send.call_count,len(packets))
        self.assertFalse((root/'results/formation-spending-v021/run.lock').exists())

if __name__ == '__main__': unittest.main()
