"""Declared Gemma native fixtures, quota clocks and failures; no real API calls."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from agents.call_telemetry import BudgetStopped
from formation.evaluation_gemma_v0222 import (MODEL, ROOT, PRICES, GemmaQuota, GemmaChat,
    GemmaRecorder, body_hash, reset_seconds, journal_guard, run, sha, name)
from formation.evaluation_runner_v0218 import execute_cell
from formation.study_a import load_cases, replay_episode
from formation.study_a_pilot import SYSTEM
from formation.limits import RatePaused


class Response:
    headers = {}
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self):
        return json.dumps(self.data).encode()


def native(raw, **changes):
    data = {'modelVersion': MODEL, 'responseId': 'fixture',
            'usageMetadata': {'promptTokenCount': 100, 'candidatesTokenCount': 50,
                              'thoughtsTokenCount': 10, 'totalTokenCount': 160},
            'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': raw}]}}]}
    data.update(changes)
    return Response(data)


def rejection(delay='2s', headers=None):
    details = [] if delay is None else [
        {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': delay}]
    return urllib.error.HTTPError('https://example.invalid', 429, 'fixture', headers or {},
                                  io.BytesIO(json.dumps({'error': {'details': details}}).encode()))


class GemmaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.clock = [1000.]
        self.quota = GemmaQuota(self.folder / 'quota.json', self.folder / 'counts.jsonl', now=lambda: self.clock[0])
        self.rec = GemmaRecorder(self.folder / 'calls.jsonl', PRICES, MODEL,
                                 max_logical=2916, max_attempts=2916, max_dollars=8, prior_spend=.631178075)
        self.client = GemmaChat(self.rec, self.quota)
        self.key = patch.object(GemmaChat, '_key', return_value='fixture-only')
        self.key.start()
        self.addCleanup(self.key.stop)
        plan = json.loads((ROOT / 'studies/formation-study-a-evaluation-plan-v0217.json').read_text())
        self.cells = [dict(c, model=MODEL) for c in plan['cells'] if c['model'] == 'gpt-6-luna']
        self.cases = {c['id']: c for c in load_cases([ROOT / p for p in {c['path'] for c in self.cells}])}
        fixtures = []
        for path in ('studies/formation-study-a-fixtures-v0213.json', 'studies/formation-study-a-pressure-fixtures-v0215.json'):
            fixtures += json.loads((ROOT / path).read_text())['fixtures']
        self.good = {f['case_id']: f['packets'] for f in fixtures if f['name'] == 'required_conduct'}

    def test_sliding_token_and_request_guards_preserve_events(self):
        self.quota.reserve('generation', 7000)
        self.quota.reserve('generation', 7000)
        with self.assertRaises(RatePaused):
            self.quota.reserve('generation', 500)
        self.assertEqual(self.quota.ready_at, 1061)
        self.clock[0] += 61
        self.quota.reserve('generation', 500)
        self.assertEqual(len(self.quota.state['events']), 3)
        for _ in range(23):
            self.quota.reserve('countTokens')
        with self.assertRaises(RatePaused):
            self.quota.reserve('countTokens')
        restored = GemmaQuota(self.quota.path, self.quota.receipts, now=lambda: self.clock[0])
        self.assertEqual(len(restored.state['events']), 26)
        restored.state['events'] = [{'at': 900, 'tokens': 0, 'kind': 'countTokens', 'index': i} for i in range(12960)]
        with self.assertRaises(RatePaused):
            restored.reserve('countTokens')
        self.assertEqual(restored.ready_at, 87300)

    def test_reset_information_and_persistent_safety_limits(self):
        self.assertEqual(reset_seconds({'retry-after': '11'}, [], 1000), 11)
        self.assertEqual(reset_seconds({'retry-after': 'Thu, 01 Jan 1970 00:17:00 GMT'}, [], 1000), 20)
        self.assertEqual(reset_seconds({'x-ratelimit-reset-tokens': '1m2s'}, [], 0), 62)
        self.assertIsNone(reset_seconds({}, [], 1000))
        self.quota.reject({'retry-after': '2'}, [], 'generation')
        self.quota.success = lambda *a: None
        restored = GemmaQuota(self.quota.path, self.quota.receipts, now=lambda: self.clock[0])
        restored.reject({'retry-after': '2'}, [], 'generation')
        self.assertTrue(restored.state['stopped_for_review'])
        self.assertEqual(restored.state['rate_errors'], 2)
        restored.state.update(stopped_for_review=False, consecutive_rate_errors=0, rate_errors=3)
        restored.reject({'retry-after': '2'}, [], 'generation')
        self.assertTrue(restored.state['stopped_for_review'])

    def test_exact_count_cache_and_oversize_no_generation(self):
        with patch('urllib.request.urlopen', return_value=Response({'totalTokens': 13825})) as send:
            with self.assertRaises(BudgetStopped):
                self.client.chat(SYSTEM, [{'role': 'user', 'content': 'fixture'}])
            self.assertEqual(send.call_count, 1)
            with self.assertRaises(BudgetStopped):
                self.client.chat(SYSTEM, [{'role': 'user', 'content': 'fixture'}])
            self.assertEqual(send.call_count, 1)
        self.assertEqual(self.rec.attempt_count, 0)

    def test_pre_request_pause_resume_preserves_history_and_no_duplicate_generation(self):
        cell = next(c for c in self.cells if c['case_id'] == 'P_R01')
        raws = iter(p['raw'] for p in self.good[cell['case_id']])
        bodies = []
        def send(request, **kwargs):
            body = json.loads(request.data)
            if request.full_url.endswith(':countTokens'):
                return Response({'totalTokens': 7000})
            bodies.append(body)
            return native(next(raws))
        state_path = self.folder / 'checkpoint.json'
        with patch('urllib.request.urlopen', side_effect=send):
            while True:
                result, status = execute_cell(cell, self.cases[cell['case_id']], self.client, self.rec, state_path)
                if result is not None:
                    break
                self.assertEqual(status, 'paused')
                self.clock[0] = self.quota.ready_at
            self.assertEqual(result['score'], replay_episode(self.cases[cell['case_id']], self.good[cell['case_id']])['score'])
            self.assertEqual(len(result['issuer_message_deliveries']), 1)
            self.assertEqual(len(bodies), len(self.good[cell['case_id']]))
            execute_cell(cell, self.cases[cell['case_id']], self.client, self.rec, state_path)
            self.assertEqual(len(bodies), len(self.good[cell['case_id']]))
        for b in bodies:
            self.assertEqual(b['systemInstruction']['parts'][0]['text'], SYSTEM)
            self.assertEqual(b['generationConfig'], {'responseMimeType': 'application/json', 'maxOutputTokens': 2048})
            self.assertNotIn('temperature', b)
            self.assertNotIn('thinkingConfig', b['generationConfig'])

    def test_count_429_is_pre_request_and_uses_retry_info(self):
        with patch('urllib.request.urlopen', side_effect=rejection('3.5s')):
            with self.assertRaises(RatePaused):
                self.client.chat(SYSTEM, [{'role': 'user', 'content': 'fixture'}])
        self.assertEqual(self.rec.attempt_count, 0)
        self.assertEqual(self.quota.state['paused_until'], 1003.5)
        self.assertIsNone(self.quota.state['metadata_inflight'])
        self.assertFalse(self.client.last_issued_429)

    def test_issued_429_retained_no_retry_and_missing_reset_stops(self):
        for reset in ('2s', None):
            self.clock[0] += 61
            self.quota.state.update(paused_until=0, consecutive_rate_errors=0)
            body = self.client.body(SYSTEM, [{'role': 'user', 'content': 'fixture-' + str(reset)}])
            self.quota.counts[body_hash(body)] = 100
            with patch('urllib.request.urlopen', side_effect=rejection(reset)) as send:
                with self.assertRaises(RatePaused):
                    self.client.chat(SYSTEM, [{'role': 'user', 'content': 'fixture-' + str(reset)}])
                self.assertEqual(send.call_count, 1)
            self.assertTrue(self.client.last_issued_429)
        self.assertTrue(self.quota.state['stopped_for_review'])
        journal_guard(self.rec.path)  # Closed retained 429s allowed; never retried.

    def test_uncertain_metadata_and_generation_never_repeat(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError) as send:
            with self.assertRaises(BudgetStopped):
                self.client.chat(SYSTEM, [{'role': 'user', 'content': 'fixture'}])
            with self.assertRaises(BudgetStopped):
                self.client.chat(SYSTEM, [{'role': 'user', 'content': 'fixture'}])
            self.assertEqual(send.call_count, 1)
        self.quota.state['metadata_inflight'] = None
        body = self.client.body(SYSTEM, [{'role': 'user', 'content': 'generation timeout fixture'}])
        self.quota.counts[body_hash(body)] = 100
        with patch('urllib.request.urlopen', side_effect=TimeoutError):
            from formation.clients import ProviderError
            with self.assertRaises(ProviderError):
                self.client.chat(SYSTEM, [{'role': 'user', 'content': 'generation timeout fixture'}])
        with self.assertRaises(BudgetStopped):
            journal_guard(self.rec.path)

    def test_native_identity_usage_reservation_and_thought_only_failure(self):
        self.rec.logical('fixture', 'fixture')
        aid = self.rec.before_attempt(self.client.body(SYSTEM, [{'role': 'user', 'content': 'fixture'}]))
        response = native('', candidates=[{'finishReason': 'MAX_TOKENS', 'content': {
            'parts': [{'thought': True, 'text': 'declared fixture thought'}]}}],
            usageMetadata={'promptTokenCount': 100, 'thoughtsTokenCount': 2048, 'totalTokenCount': 2148}).data
        self.rec.finish_native(aid, response, 'google')
        events = [json.loads(l) for l in self.rec.path.read_text().splitlines()]
        self.assertEqual(next(e['response'] for e in events if e['event'] == 'native_response'), response)
        self.assertEqual(events[-1]['usage']['completion_tokens'], 2048)
        self.assertTrue(any(e['event'] == 'derived_zero_final_tokens' for e in events))
        self.rec.logical('fixture', 'fixture')
        aid = self.rec.before_attempt(self.client.body(SYSTEM, [{'role': 'user', 'content': 'fixture'}]))
        with self.assertRaises(BudgetStopped):
            self.rec.finish_native(aid, native('{}', modelVersion='wrong-model').data, 'google')
        with self.assertRaises(BudgetStopped):
            journal_guard(self.rec.path)

    def fixture_plan(self):
        root = self.folder / 'root'
        root.mkdir()
        for cell in self.cells:
            p = root / cell['path']
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((ROOT / cell['path']).read_bytes())
        ledger = root / 'results/formation-spending-v021/google.json'
        ledger.parent.mkdir(parents=True)
        ledger.write_text(json.dumps({'estimated_api_dollars': .631178075}))
        plan = {'checkout_root': str(root), 'output': 'output', 'plan_path': 'plan.json',
                'approval_path': 'approval.json', 'google_prior_dollars': .631178075,
                'sha256': {}, 'cells': self.cells, 'maintenance_hold': str(self.folder / 'hold')}
        (root / 'plan.json').write_text(json.dumps(plan))
        (root / 'approval.json').write_text(json.dumps({'plan_sha256': sha(root / 'plan.json'), 'approved': True}))
        return root, plan

    def test_full_240_matrix_and_one_end_replacement_then_resume(self):
        root, plan = self.fixture_plan()
        raw_queues = {c['case_id']: [p['raw'] for p in self.good[c['case_id']]] for c in self.cells}
        generation_order, turns, failed = [], {}, [False]
        def send(request, **kwargs):
            b = json.loads(request.data)
            if request.full_url.endswith(':countTokens'):
                self.assertEqual(b['generateContentRequest']['model'], 'models/' + MODEL)
                return Response({'totalTokens': 100})
            view = json.loads(b['contents'][0]['parts'][0]['text'])['task_context']
            # Identify fixtures from scenario data; recorder context is unambiguous.
            events = [json.loads(l) for l in (root / 'output/calls.jsonl').read_text().splitlines()]
            ctx = next(e['context'] for e in reversed(events) if e['event'] == 'logical_start')
            slot = name(ctx)
            generation_order.append(slot)
            self.clock[0] += 61
            if not failed[0]:
                failed[0] = True
                raise rejection('2s')
            turn = turns.get(slot, 0)
            turns[slot] = turn + 1
            return native(raw_queues[ctx['case_id']][turn])
        def sleep(delay):
            self.clock[0] += delay
        with patch('urllib.request.urlopen', side_effect=send) as transport:
            result = run(plan, root / 'output', root=root, now=lambda: self.clock[0], sleep=sleep)
            self.assertEqual(result['completed_cells'], 240)
            self.assertEqual(result['replacement_completed_cells'], 1)
            self.assertEqual(result['records'][0]['outcome'], 'error')
            self.assertTrue(result['records'][0]['rate_lost'])
            self.assertEqual(result['records'][-1]['outcome'], 'correct')
            self.assertTrue(generation_order[-1].endswith('-replacement-01'))
            self.assertFalse(any('-replacement-' in x for x in generation_order[:-len(self.good[self.cells[0]['case_id']])]))
            from scripts.formation_study_a_gemma31_audit import audit
            with patch('scripts.formation_study_a_gemma31_audit.ROOT', root):
                checked = audit(root / 'output', root / 'plan.json')
            self.assertTrue(checked['deterministic_replay_and_full_history_equal'])
            self.assertEqual(checked['primary_completed_cells'], 240)
            self.assertEqual(checked['replacement_completed_cells'], 1)
            original = (root / 'output' / (name(self.cells[0]) + '.json')).read_bytes()
            calls = transport.call_count
            again = run(plan, root / 'output', root=root, now=lambda: self.clock[0], sleep=sleep)
            self.assertEqual(transport.call_count, calls)
            self.assertEqual(again['completed_cells'], 240)
            self.assertEqual((root / 'output' / (name(self.cells[0]) + '.json')).read_bytes(), original)
        self.assertEqual(json.loads((root / 'results/formation-spending-v021/google.json').read_text())['estimated_api_dollars'], .631178075)

    def test_failed_replacement_gets_no_second_replacement(self):
        root, plan = self.fixture_plan()
        # A two-cell declared fixture isolates queue behavior; production plan binds 240.
        plan['cells'] = self.cells[:2]
        (root / 'plan.json').write_text(json.dumps(plan))
        (root / 'approval.json').write_text(json.dumps({'plan_sha256': sha(root / 'plan.json'), 'approved': True}))
        seen, turns = [], {}
        def send(request, **kwargs):
            if request.full_url.endswith(':countTokens'):
                return Response({'totalTokens': 100})
            events = [json.loads(l) for l in (root / 'output/calls.jsonl').read_text().splitlines()]
            ctx = next(e['context'] for e in reversed(events) if e['event'] == 'logical_start')
            seen.append(name(ctx))
            self.clock[0] += 61
            if ctx['repeat'] == self.cells[0]['repeat'] and ctx['case_id'] == self.cells[0]['case_id']:
                raise rejection('2s')
            slot = name(ctx)
            turn = turns.get(slot, 0)
            turns[slot] = turn + 1
            return native(self.good[ctx['case_id']][turn]['raw'])
        with patch('urllib.request.urlopen', side_effect=send):
            final = run(plan, root / 'output', root=root, now=lambda: self.clock[0],
                        sleep=lambda n: self.clock.__setitem__(0, self.clock[0] + n))
        self.assertEqual(final['completed_cells'], 2)
        self.assertEqual(final['replacement_completed_cells'], 1)
        self.assertEqual(final['records'][-1]['outcome'], 'error')
        self.assertEqual(sum('-replacement-' in s for s in seen), 1)
        self.assertEqual(final['rate_errors'], 2)

    def test_malformed_refusal_usage_and_native_reservation_failures(self):
        cell = self.cells[0]
        for index, response in enumerate((native('not JSON'), native('', candidates=[{
                'finishReason': 'SAFETY', 'content': {'parts': []}}]))):
            self.clock[0] += 61
            def send(request, **kwargs):
                if request.full_url.endswith(':countTokens'):
                    return Response({'totalTokens': 100})
                return response
            with patch('urllib.request.urlopen', side_effect=send):
                result, state = execute_cell(cell, self.cases[cell['case_id']], self.client, self.rec,
                                              self.folder / ('nonrate-%d.json' % index))
            self.assertEqual(state, 'complete')
            self.assertFalse(result['fatal_transport'])
            self.assertFalse(self.client.last_issued_429)
            self.assertIn(result['score']['terminal_status'], ('malformed_reply', 'provider_refusal'))
        self.rec.logical('fixture', 'fixture')
        aid = self.rec.before_attempt(self.client.body(SYSTEM, [{'role': 'user', 'content': 'fixture'}]))
        with self.assertRaises(BudgetStopped):
            self.rec.finish_native(aid, native('{}', usageMetadata={
                'promptTokenCount': -1, 'candidatesTokenCount': 10, 'totalTokenCount': 9}).data, 'google')
        self.quota.reserve('generation', 228)
        with self.assertRaises(BudgetStopped):
            self.quota.success(229)
        self.assertTrue(self.quota.state['stopped_for_review'])

    def test_second_consecutive_429_stops_and_never_restarts(self):
        root, plan = self.fixture_plan()
        def send(request, **kwargs):
            if request.full_url.endswith(':countTokens'):
                return Response({'totalTokens': 100})
            self.clock[0] += 61
            raise rejection('2s')
        with patch('urllib.request.urlopen', side_effect=send) as transport:
            with self.assertRaises(BudgetStopped):
                run(plan, root / 'output', root=root, now=lambda: self.clock[0], sleep=lambda n: self.clock.__setitem__(0, self.clock[0] + n))
            calls = transport.call_count
            with self.assertRaises(BudgetStopped):
                run(plan, root / 'output', root=root)
            self.assertEqual(transport.call_count, calls)
        self.assertEqual(json.loads((root / 'output/gemma-quota.json').read_text())['rate_errors'], 2)
        self.assertEqual(json.loads((root / 'output/progress-summary.json').read_text())['completed_cells'], 2)

    def test_approval_lock_and_checkpoint_guards_block_transport(self):
        root, plan = self.fixture_plan()
        with patch('urllib.request.urlopen') as transport:
            (root / 'approval.json').write_text(json.dumps({'approved': False, 'plan_sha256': sha(root / 'plan.json')}))
            with self.assertRaises(ValueError):
                run(plan, root / 'output', root=root)
            (root / 'approval.json').write_text(json.dumps({'approved': True, 'plan_sha256': sha(root / 'plan.json')}))
            lock = root / 'results/formation-spending-v021/run.lock'
            lock.write_text('preserve-fixture-lock')
            with self.assertRaises(FileExistsError):
                run(plan, root / 'output', root=root)
            self.assertEqual(lock.read_text(), 'preserve-fixture-lock')
            lock.unlink()  # Fixture owns this lock.
            output = root / 'output'
            (output / 'bad-checkpoint.json').write_text('{"phase":"inflight"}')
            with self.assertRaises(BudgetStopped):
                run(plan, output, root=root)
            transport.assert_not_called()


if __name__ == '__main__':
    unittest.main()
