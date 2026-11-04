"""Offline backend checks: no Modal import, sockets or model loading."""
from copy import deepcopy
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from exploratory.step4_harness import modal_backend as b
from exploratory.step4_harness.runner import plan
from exploratory.step4_harness.guard import LaunchGuard, binding


class BackendTests(unittest.TestCase):
    def test_split_preserves_all_cells(self):
        identity = lambda rows: {json.dumps(r, sort_keys=True) for r in rows}
        left, right = map(identity, (plan(b.STAGES[1]), plan(b.STAGES[2])))
        self.assertFalse(left & right)
        self.assertEqual(left | right, identity(plan('main')))
        self.assertEqual([len(plan(s)) for s in b.STAGES], [32, 384, 384, 64, 10])

    def test_cap_and_resume(self):
        checkpoints = {'base': {'available': True}}
        expected = binding('a'*40, 'development', checkpoints)
        receipt = dict(expected, approved_by='Chris Lahn', dollar_cap=1)
        events = []
        guard = LaunchGuard(receipt, expected, checkpoints, events.append, owner_approved=True)
        self.assertEqual(guard.call('base', 1, lambda: 'first'), 'first')
        with self.assertRaises(ValueError):
            guard.call('base', 1, lambda: self.fail('cap bypass'))
        with self.assertRaises(ValueError):
            LaunchGuard(receipt, expected, checkpoints, events.append, owner_approved=True, existing=True)
        self.assertEqual(events[0][0]['status'], 'reserved')
        self.assertEqual(events[1][0]['status'], 'returned')

    def test_time_cap(self):
        config = b.settings(5)
        self.assertEqual(config['session_seconds'], int((5-config['pre_timeout_allowance_usd'])/config['pessimistic_hourly_rate']*3600))
        self.assertEqual(config['timeout'], config['session_seconds'])
        self.assertGreater(config['timeout'], b.CALL_SECONDS + b.SHUTDOWN_SECONDS)
        with self.assertRaises(ValueError):
            b.settings(config['pre_timeout_allowance_usd'])
        stop = config['timeout']-b.CALL_SECONDS-b.SHUTDOWN_SECONDS
        self.assertTrue(b.may_start(0, config))
        self.assertTrue(b.may_start(stop-1, config))
        self.assertFalse(b.may_start(stop, config))
        self.assertFalse(b.may_start(config['timeout']-1, config))
        self.assertEqual(b.settings(50)['session_seconds'], 21600)
        for cap in (.39, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                b.settings(cap)
        checkpoints = {'base': {'available': True}}
        expected = dict(binding('a'*40, 'development', checkpoints), backend_settings=config)
        receipt = dict(expected, approved_by='Chris Lahn', dollar_cap=5)
        events = []
        guard = LaunchGuard(receipt, expected, checkpoints, events.append, owner_approved=True)
        for _ in range(176):
            guard.call('base', 0, lambda: 'ok')
        self.assertEqual(guard.reserved, 5)
        self.assertEqual(len(guard.attempts), 176)
        guard.before_cell = lambda: b.may_start(stop, config)
        with self.assertRaisesRegex(ValueError, 'session time limit'):
            guard.call('base', 0, lambda: self.fail('late request'))
        self.assertEqual(len(guard.attempts), 176)
        with self.assertRaises(ValueError):
            LaunchGuard(dict(receipt, dollar_cap=.39), expected, checkpoints, events.append, owner_approved=True)

    def test_timeout_stops_and_analysis_unknown(self):
        from exploratory.step4_harness.runner import run_block
        from exploratory.step4_harness.analysis import report
        checkpoints = {'base': {'available': True}, 'neutral': {'available': True}}
        expected = binding('a'*40, 'development', checkpoints)
        receipt = dict(expected, approved_by='Chris Lahn', dollar_cap=3)
        guard = LaunchGuard(receipt, expected, checkpoints, lambda rows: None, owner_approved=True)
        calls = []
        def backend(*args):
            calls.append(args)
            if len(calls) == 1:
                raise b.CallTimeout('partial')
            raise RuntimeError('other failure stops stage')
        rows = run_block('development', checkpoints, guard, backend, lambda row: None, 0,
                         execution_verifier=lambda commit: None)
        self.assertEqual(len(calls), 1)
        self.assertEqual([r['terminal_status'] for r in rows], ['call_timeout'])
        self.assertEqual(rows[0]['attempts'][0]['raw'], 'partial')
        self.assertEqual(rows[0]['protocol_bounds'], [0, 1])
        unit = report(rows)['units'][0]
        self.assertEqual(unit['status'], 'call_timeout')
        for metric in unit['metrics'].values():
            self.assertEqual(metric['unknown'], 1)
            self.assertEqual(metric['planned'], 1)

    def test_render_origins_identically(self):
        seen = []
        runtime = NS(prompt_ids=lambda tokenizer, messages, flag: seen.append(deepcopy(messages)) or [1])
        scripted = [{'role': 'assistant', 'content': '{"tool":"read_record","args":{"record_id":"SOURCE"}}'},
                    {'role': 'tool', 'content': {'ok': True}}]
        generated = json.loads(json.dumps(scripted))
        b.render(runtime, None, 'system', scripted)
        b.render(runtime, None, 'system', generated)
        self.assertEqual(seen[0], seen[1])

    def test_tool_dropping_template_keeps_source_evidence(self):
        from exploratory.step4_cases.drafts import load
        from exploratory.step4_harness.runner import episode
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return '\n'.join(m['content'] for m in messages if m['role'] != 'tool')
        tokenizer = Tokenizer()
        runtime = NS(prompt_ids=lambda tok, messages, flag:
                     tok.apply_chat_template(messages, add_generation_prompt=flag))
        self.assertNotIn('DROPPED', b.render(runtime, tokenizer, 'system',
                         [dict(role='tool', content='DROPPED')]))
        for case in load():
            replies = iter(['{"tool":"read_record","args":{"record_id":"SOURCE"}}',
                            '{"tool":null,"args":{}}'])
            row = episode(case, 'action', lambda *x: next(replies))
            text = b.render(runtime, tokenizer, case['visible']['system'],
                            row['attempts'][-1]['history'])
            source = next(m['content'] for m in case['visible']['prefix']
                          if m['role'] == 'tool' and m['content']['record_id'] == 'SOURCE')
            observation = json.dumps({'last_tool_result': source}, ensure_ascii=False)
            self.assertEqual(text.count(observation), 2)
            for value in source['record'].values():
                if isinstance(value, str):
                    self.assertIn(value, text)

    def test_partial_is_durable_on_timeout(self):
        ticks = iter([0, 0, 601])
        aborted = []
        params = NS(clone=lambda: NS())
        engine = NS(get_tokenizer=lambda: None, get_default_sampling_params=lambda: params,
                    add_request=lambda *a, **kw: None,
                    step=lambda: [NS(request_id='0', outputs=[NS(text='partial')], finished=False)],
                    abort_request=aborted.append)
        runtime = NS(prompt_ids=lambda *args: [1])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'fresh'
            journal = b.Journal(root)
            backend = b.Backend(engine, runtime, {}, journal, None, lambda: next(ticks))
            with self.assertRaises(b.CallTimeout) as caught:
                backend('base', 's', [], 4096)
            self.assertEqual(caught.exception.raw, 'partial')
            self.assertEqual(aborted, [['0']])
            events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['raw'], 'partial')
            self.assertTrue(events[-1]['no_resend'])
            with self.assertRaises(FileExistsError):
                b.Journal(root)

    def test_detach_and_once_claim(self):
        calls = []
        class Ledger:
            def __init__(self):
                self.used = {}
            def put(self, *args, **kwargs):
                calls.append('claim')
                if args[0] in self.used:
                    return False
                self.used[args[0]] = args[1]
                return True
        ledger = Ledger()
        app = NS(run=lambda **kw: calls.append(kw) or nullcontext(), app_id='app')
        worker = NS(spawn=lambda *args: calls.append('spawn') or NS(object_id='call'))
        receipt = dict(binding('a'*40, 'development', {'base': {'available': True}}),
                       archive_sha256='b'*64, dollar_cap=5, backend_settings=b.settings(5),
                       approved_by='Chris Lahn', approval_id='development-1')
        with tempfile.TemporaryDirectory() as temp:
            b.submit(app, worker, ledger, receipt, 'id', Path(temp)/'receipt')
            with self.assertRaises(ValueError):
                b.submit(app, worker, ledger, receipt, 'id2', Path(temp)/'receipt2')
            variants = [dict(receipt, dollar_cap=5.0),
                        dict(receipt, backend_settings=dict(reversed(list(receipt['backend_settings'].items())))),
                        dict(receipt, backend_settings={
                            k: float(v) if type(v) in (int, float) else v
                            for k, v in receipt['backend_settings'].items()})]
            for index, variant in enumerate(variants):
                with self.subTest(index=index):
                    self.assertEqual(b.execution_fingerprint(receipt), b.execution_fingerprint(variant))
                    with self.assertRaisesRegex(ValueError, 'receipt already claimed'):
                        b.submit(app, worker, ledger, variant, 'duplicate', Path(temp)/f'duplicate{index}')
            entry = ledger.used[b.claim_key(receipt)]
            self.assertEqual(entry, dict(run_id='id', reserved=5,
                                        execution_fingerprint=b.execution_fingerprint(receipt)))
            self.assertNotEqual(b.claim_key(receipt), b.claim_key(dict(receipt, approval_id='development-2')))
            for invalid_id in ('', ' ', None, 5):
                with self.assertRaisesRegex(ValueError, 'nonempty approval_id'):
                    b.claim_key(dict(receipt, approval_id=invalid_id))
            with self.assertRaisesRegex(ValueError, 'unexpected receipt fields'):
                b.submit(app, worker, ledger, dict(receipt, note='new note'), 'id3', Path(temp)/'receipt3')
            self.assertEqual(calls.count('spawn'), 1)
            self.assertEqual(b.claim_key(receipt), b.claim_key(dict(receipt, monthly_headroom_usd=50)))
            with self.assertRaises(ValueError):
                b.claim_key({k: v for k, v in receipt.items() if k != 'approval_id'})
        self.assertEqual(calls[:3], [{'detach': True}, 'claim', 'spawn'])


class TimeoutKnownActTests(unittest.TestCase):
    def test_known_act_survives_call_timeout(self):
        from exploratory.step4_harness.analysis import observed
        row = dict(terminal_status='call_timeout', primary=True, routine=False,
                   format_closed_valid=False, protocol_bounds=[0, 1])
        self.assertIs(observed(row, 'primary'), True)
        self.assertIsNone(observed(row, 'routine'))
        self.assertIsNone(observed(row, 'protocol'))


class JournalTests(unittest.TestCase):
    def test_commit_count_and_generation_order(self):
        for partials in (1, 100):
            with self.subTest(partials=partials), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'journal'
                durable = []
                def commit():
                    durable.append([json.loads(line) for line in
                                    (root/'events.jsonl').read_text().splitlines()])
                journal = b.Journal(root, commit)
                params = NS(clone=lambda: NS())
                step = [0]
                def add(*args, **kwargs):
                    self.assertEqual(durable[-1][-1]['event'], 'before_generation')
                    step[0] = 0
                def advance():
                    step[0] += 1
                    return [NS(request_id=str(backend.sequence-1),
                               outputs=[NS(text='x'*step[0])],
                               finished=step[0] == partials)]
                engine = NS(get_tokenizer=lambda: None,
                            get_default_sampling_params=lambda: params,
                            add_request=add, step=advance)
                backend = b.Backend(engine, NS(prompt_ids=lambda *a: [1]), {}, journal, None)
                for _ in range(3):
                    backend('base', 'system', [], 4096)
                    self.assertEqual(durable[-1][-1]['event'], 'returned')
                journal(dict(event='cell'))
                self.assertEqual(len(durable), 7)
                for event in durable[-1]:
                    self.assertIn('wall_time', event)
                    self.assertIsInstance(event['monotonic_seconds'], float)
                for name in ('attempt_ledger', 'launch', 'failure', 'stage_end', 'generation_stopped'):
                    journal(dict(event=name))
                    self.assertEqual(durable[-1][-1]['event'], name)

    def test_stop_publishes_latest_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'journal'
            snapshots = []
            journal = b.Journal(root, lambda: snapshots.append(
                (root/'events.jsonl').read_text()))
            journal(dict(event='before_generation'))
            journal(dict(event='partial', raw='first'))
            journal(dict(event='partial', raw='latest'))
            self.assertEqual(len(snapshots), 1)
            journal(dict(event='generation_stopped', raw='latest', no_resend=True))
            self.assertEqual(json.loads(snapshots[-1].splitlines()[-1])['raw'], 'latest')
            self.assertEqual(len(snapshots), 2)
