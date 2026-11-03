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
        self.assertEqual([len(plan(s)) for s in b.STAGES], [32, 384, 384, 64])

    def test_cap_and_resume(self):
        checkpoints = {'base': {'available': True}}
        expected = binding('a'*40, 'development', checkpoints)
        receipt = dict(expected, approved_by='Chris Lahn', dollar_cap=b.CALL_RESERVE)
        events = []
        guard = LaunchGuard(receipt, expected, checkpoints, events.append, owner_approved=True)
        self.assertEqual(guard.call('base', b.CALL_RESERVE, lambda: 'first'), 'first')
        with self.assertRaises(ValueError):
            guard.call('base', b.CALL_RESERVE, lambda: self.fail('cap bypass'))
        with self.assertRaises(ValueError):
            LaunchGuard(receipt, expected, checkpoints, events.append, owner_approved=True, existing=True)
        self.assertEqual(events[0][0]['status'], 'reserved')
        self.assertEqual(events[1][0]['status'], 'returned')

    def test_render_origins_identically(self):
        seen = []
        runtime = NS(prompt_ids=lambda tokenizer, messages, flag: seen.append(deepcopy(messages)) or [1])
        scripted = [{'role': 'assistant', 'content': '{"tool":"read_record","args":{"record_id":"SOURCE"}}'},
                    {'role': 'tool', 'content': {'ok': True}}]
        generated = json.loads(json.dumps(scripted))
        b.render(runtime, None, 'system', scripted)
        b.render(runtime, None, 'system', generated)
        self.assertEqual(seen[0], seen[1])

    def test_partial_is_durable_on_timeout(self):
        ticks = iter([0, 0, 121])
        params = NS(clone=lambda: NS())
        engine = NS(get_tokenizer=lambda: None, get_default_sampling_params=lambda: params,
                    add_request=lambda *a, **kw: None,
                    step=lambda: [NS(request_id='0', outputs=[NS(text='partial')], finished=False)],
                    abort_request=lambda ids: None)
        runtime = NS(prompt_ids=lambda *args: [1])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'fresh'
            journal = b.Journal(root)
            backend = b.Backend(engine, runtime, {}, journal, None, lambda: next(ticks))
            with self.assertRaises(TimeoutError):
                backend('base', 's', [], 4096)
            events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['raw'], 'partial')
            self.assertTrue(events[-1]['no_resend'])
            with self.assertRaises(FileExistsError):
                b.Journal(root)

    def test_detach_and_once_claim(self):
        calls = []
        class Ledger:
            used = False
            def put(self, *args, **kwargs):
                calls.append('claim')
                if self.used:
                    return False
                self.used = True
                return True
        ledger = Ledger()
        app = NS(run=lambda **kw: calls.append(kw) or nullcontext(), app_id='app')
        worker = NS(spawn=lambda *args: calls.append('spawn') or NS(object_id='call'))
        with tempfile.TemporaryDirectory() as temp:
            b.submit(app, worker, ledger, {}, 'id', Path(temp)/'receipt')
            with self.assertRaises(ValueError):
                b.submit(app, worker, ledger, {}, 'id2', Path(temp)/'receipt2')
        self.assertEqual(calls[:3], [{'detach': True}, 'claim', 'spawn'])
