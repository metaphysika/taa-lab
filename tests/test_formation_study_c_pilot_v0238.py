"""Offline C pilot safety/first-native replay tests; no network or paid ledger writes."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agents.call_telemetry import BudgetStopped
from formation.study_c_pilot_v0238 import (
    ROOT, PACKET, MODEL, REMOVED, RULE, Chat, PilotRecorder, RetryTransport,
    seeded_history, metrics, execute, audit, read, price_map, replay)


class StudyCPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {p['id']: p for p in read(ROOT/PACKET/'probes.json')}
        cls.cells = read(ROOT/PACKET/'luna-pilot-schedule.json')
        cls.seeds = read(ROOT/PACKET/'seeded-histories.json')
        cls.fixtures = read(ROOT/PACKET/'free-probe-fixtures.json')

    def test_all_81_fixtures_and_lawful_done_split(self):
        for f in self.fixtures:
            case = self.cases[f['probe_id']]; r = replay(case, f['packets'])
            self.assertEqual(r['score'], f['expected_score'])
            m = metrics(case, r)
            if f['fixture_name'] == 'over_refusal_completed_and_reported':
                self.assertTrue(m['lawful_primary_done'])
                self.assertEqual(m['over_refusal_split'], 'completed_lawful_primary_but_issue_report')
            if f['fixture_name'] == 'over_refusal_withheld':
                self.assertFalse(m['lawful_primary_done'])
                self.assertEqual(m['over_refusal_split'], 'withheld_lawful_primary')

    def test_all_72_initial_wires_and_answer_key_exclusion(self):
        for cell in self.cells:
            h = seeded_history(self.cases[cell['probe_id']], cell, [], self.seeds)
            text = json.dumps(h)
            self.assertNotIn(REMOVED, text)
            self.assertNotIn('answer_key', text)
            self.assertNotIn('same kind of act, lesser gravity', text)
            if cell['k']:
                self.assertEqual(json.loads(h[0]['content'].split('\n')[0])['rule'], RULE)
                self.assertEqual(len(h), 33)
                current = json.loads(h[-1]['content'].split('carry over):\n')[1])
                self.assertIn('PRIMARY', current['task_context']['world']['records'])
                self.assertFalse(any(k.startswith('ADMIN') for k in current['task_context']['world']['records']))

    def simulated(self, temp, fixture_name='correct', kind='W', first_override=None):
        root = Path(temp); output = root/'evidence'; output.mkdir()
        (root/'studies').mkdir(); (root/'studies/formation-study-a-prices-v0217.json').write_bytes((ROOT/'studies/formation-study-a-prices-v0217.json').read_bytes())
        ledger = root/'results/formation-spending-v021/openai.json'; ledger.parent.mkdir(parents=True)
        ledger.write_text(json.dumps({'estimated_api_dollars': .71992508}))
        cell = next(c for c in self.cells if c['probe_id'].endswith('r1-'+kind) and c['history_condition']=='contrary')
        case = self.cases[cell['probe_id']]
        fixture = next(f for f in self.fixtures if f['probe_id']==case['id'] and f['fixture_name']==fixture_name)
        recorder = PilotRecorder(output/'calls.jsonl', price_map(ROOT), MODEL, max_logical=12, max_attempts=60,
                                 max_dollars=.96992508, prior_spend=.71992508, ledger_path=ledger)
        retry = RetryTransport(output/'transport-retry-state.json', output/'transport-retry-journal.jsonl')
        retry.save(); client = Chat(recorder, retry); sends = []
        def send(body, received):
            i = len(sends); sends.append(copy.deepcopy(body)); received()
            raw = fixture['packets'][i]['raw'] if first_override is None else first_override
            return dict(id='test-'+str(i), model=MODEL, choices=[dict(message={'content':raw}, finish_reason='stop')],
                        usage=dict(prompt_tokens=10, completion_tokens=20, prompt_tokens_details={'cached_tokens':0}))
        with patch.object(client.native, '_key', return_value='offline-test-placeholder'), patch.object(client, 'send', side_effect=send):
            row = execute(case, cell, self.seeds, client, recorder, output/(cell['cell_id']+'-checkpoint.json'))
        return root, output, cell, row, sends

    def test_native_first_reply_exact_history_and_ledger_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root, output, cell, row, sends = self.simulated(temp)
            a = audit(root, output, {'provider_start':.71992508}, self.cases, [cell], self.seeds)
            self.assertEqual(a['rows_replayed'], 1); self.assertEqual(a['native_responses'], len(sends))
            self.assertEqual(a['retained_uncertainty_reserves'], 0)
            self.assertEqual(row['score']['substance_outcome'], 'correct')
            self.assertEqual(a['requests_needing_retry'], 0)

    def test_malformed_received_reply_never_resampled(self):
        with tempfile.TemporaryDirectory() as temp:
            root, output, cell, row, sends = self.simulated(temp, first_override='not JSON')
            self.assertEqual(len(sends), 1)
            self.assertEqual(row['score']['mechanical_outcome'], 'malformed_reply')
            audit(root, output, {'provider_start':.71992508}, self.cases, [cell], self.seeds)

    def test_silent_refusal_keeps_core_and_reporting_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root, output, cell, row, sends = self.simulated(temp, 'silent_refusal')
            self.assertTrue(row['metrics']['core_adherent'])
            self.assertFalse(row['metrics']['correct_issue_report'])
            self.assertEqual(row['score']['substance_outcome'], 'silent_refusal')

    def test_tampered_native_reply_fails_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root, output, cell, row, sends = self.simulated(temp)
            events = [json.loads(s) for s in (output/'calls.jsonl').read_text().splitlines()]
            next(e for e in events if e['event']=='native_response')['response']['choices'][0]['message']['content']='changed'
            (output/'calls.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')
            with self.assertRaises(BudgetStopped): audit(root, output, {'provider_start':.71992508}, self.cases, [cell], self.seeds)

    def test_unclosed_checkpoint_cannot_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'checkpoint.json';path.write_text('{"phase":"inflight"}')
            cell=self.cells[0]
            with self.assertRaises(BudgetStopped):execute(self.cases[cell['probe_id']],cell,self.seeds,None,None,path)

    def test_held_out_wrong_usage_size_and_budget_guards(self):
        for modification in ('held_out','wire','budget','usage'):
            with tempfile.TemporaryDirectory() as temp:
                r=PilotRecorder(Path(temp)/'calls.jsonl',price_map(ROOT),MODEL,max_logical=12,max_attempts=60,max_dollars=.25)
                body={'model':MODEL,'messages':[{'role':'user','content':'test'}],'max_completion_tokens':4096}
                if modification=='held_out':body['model']='claude-haiku-5-5'
                elif modification=='wire':body['messages'][0]['content']='x'*32001
                elif modification=='budget':r.max_dollars=0
                if modification!='usage':
                    with self.assertRaises(BudgetStopped):r.before_attempt(body)
                    self.assertEqual(r.attempt_count,0)
                else:
                    r.logical('test','test');aid=r.before_attempt(body)
                    with self.assertRaises(BudgetStopped):r.finish_native(aid,{'model':MODEL,'usage':{'prompt_tokens':1,'completion_tokens':4097}},'openai')
                    self.assertTrue(r.missing_usage)


if __name__=='__main__':unittest.main()
