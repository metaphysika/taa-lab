"""Offline synthetic coverage. No remote execution or learned-agent outcomes."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from exploratory.step4_cases.drafts import load
from exploratory.step4_harness import runner as h, analysis as a
from exploratory.step4_harness.guard import LaunchGuard, binding, inventory


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = h.mock_all()

    def test_full_mock(self):
        self.assertEqual([len(h.plan(b)) for b in ('development', 'main', 'held_out')], [32, 768, 64])
        self.assertEqual(len(self.rows), 864)
        self.assertEqual(sum(r['format_closed_valid'] for r in self.rows), 352)
        report = a.analyze(self.rows)
        self.assertEqual(len(report['units']), 864)
        self.assertEqual(report['switching']['base']['bounds'], [1, 1])
        self.assertEqual(report['f1']['verdict'], 'no headroom')
        self.assertEqual(report['probes']['wrong_answer']['verdict'], 'no difference')
        for row in self.rows:
            self.assertFalse(any(m.get('content') in h.PROBES for m in row['prefix'] if isinstance(m.get('content'), str)))

    def test_prefix_failure_and_isolation(self):
        case = deepcopy(load()[0])
        case['visible']['prefix'].pop()
        self.assertEqual(h.episode(case, 'action', lambda *x: self.fail())['terminal_status'], 'measurement_failed')
        case = deepcopy(load()[0])
        case['visible']['prefix'][1]['content']['record']['detail'] = 'changed'
        # Compared with canonical per-case bytes, even internally consistent changes fail.
        self.assertEqual(h.episode(case, 'action', lambda *x: self.fail())['terminal_status'], 'measurement_failed')

    def test_protocol_and_known_acts(self):
        for replies, status, primary, closed in [
            (['{"tool":"perform_primary","args":{}}', 'bad'], 'malformed', True, False),
            (['{"tool":"bogus","args":{}}', '{"tool":null,"args":{}}'], 'agent_stop', False, False),
            (['{"tool":"null","args":{}}'], 'agent_stop', False, True),
            (['{"tool":null,"args":{}} {"tool":null,"args":{}}'], 'malformed', False, False),
            (['{"tool":"check_routine","args":{}}']*12, 'step_limit', False, False),
        ]:
            with self.subTest(status=status, primary=primary):
                it = iter(replies)
                row = h.episode(load()[0], 'action', lambda *x: next(it))
                self.assertEqual((row['terminal_status'], row['primary'], row['format_closed_valid']), (status, primary, closed))
                if not closed:
                    self.assertEqual(row['protocol_bounds'], [0, 1])
                if primary:
                    self.assertTrue(a.observed(row, 'primary'))
    def test_probe_normalization(self):
        for raw, expected in [
            ('yes', 'yes'), ('no', 'no'), ('Yes', 'yes'), ('No.', 'no'),
            (' yes\n', 'yes'), (' NO. \n', 'no'),
            ('', None), ('Yes, because...', None), ('{"answer":"yes"}', None),
            ('yes..', None), ('yes .', None), ('y es', None), ('no thanks', None),
        ]:
            for branch in ('probe1', 'probe2'):
                with self.subTest(raw=raw, branch=branch):
                    row = h.episode(load()[0], branch, lambda *x: raw)
                    self.assertEqual(row['answer'], expected)
                    self.assertEqual(row['attempts'][0]['raw'], raw)
                    self.assertEqual(len(row['attempts']), 1)

    def test_prefix_rendering_matches_generated_turns(self):
        case = load()[0]
        raw = json.dumps(case['visible']['prefix'][0]['content'], separators=(',', ':'))
        replies = iter([raw, '{"tool":null,"args":{}}'])
        row = h.episode(case, 'action', lambda *x: next(replies))
        history = row['attempts'][1]['history']
        assistants = [m['content'] for m in history if m['role'] == 'assistant']
        self.assertTrue(all(isinstance(x, str) for x in assistants))
        for content in assistants:
            self.assertEqual(content, json.dumps(json.loads(content), separators=(',', ':')))
        self.assertEqual(assistants[0], assistants[-1])
        tools = [json.loads(m['content'])['last_tool_result'] for m in history
                 if m['role'] == 'user' and m['content'].startswith('{')]
        self.assertEqual(tools[0], tools[-1])

    def test_all_observations_are_visible_string_messages(self):
        for case in load():
            replies = iter(['{"tool":"read_record","args":{"record_id":"SOURCE"}}',
                            '{"tool":null,"args":{}}'])
            row = h.episode(case, 'action', lambda *x: next(replies))
            history = row['attempts'][-1]['history']
            self.assertTrue(all(m['role'] in ('system', 'user', 'assistant')
                                and isinstance(m['content'], str) for m in history))
            source = next(m['content'] for m in case['visible']['prefix']
                          if m['role'] == 'tool' and m['content']['record_id'] == 'SOURCE')
            observation = json.dumps({'last_tool_result': source}, ensure_ascii=False)
            self.assertEqual(sum(m['content'] == observation for m in history), 2)
            text = '\n'.join(m['content'] for m in history)
            for value in source['record'].values():
                if isinstance(value, str):
                    self.assertIn(value, text)
            probe = h.episode(case, 'probe1', lambda *x: 'yes')
            self.assertEqual(probe['attempts'][0]['history'][-1],
                             dict(role='user', content=h.PROBES[0]))

    def test_probe_pattern_denominators(self):
        rows = deepcopy(self.rows)
        for row in rows:
            if row['block'] == 'main' and row['checkpoint'] == 'contrary' and row['branch'] == 'action':
                row['primary'] = True
        result = a.analyze(rows)
        self.assertEqual(result['probes']['answer_action_disagreement']['effects'], [[1, 1]]*2)
        self.assertEqual(result['probes']['wrong_answer']['effects'], [[0, 0]]*2)
        wrongful = next(r['case_id'] for r in rows if r['block'] == 'main' and h.labels()[r['case_id']] == 'not permitted')
        for row in rows:
            if row['case_id'] == wrongful and row['checkpoint'] == 'contrary' and row['repeat'] == 1 and row['branch'] == 'probe1':
                row['answer'] = None
        result = a.analyze(rows)
        self.assertEqual(result['probes']['answer_action_disagreement']['effects'], [[31/32, 1]]*2)
        self.assertEqual(result['probes']['wrong_answer']['effects'], [[0, 1/64], [0, 0]])

    def test_missing_denominators(self):
        result = a.report([])
        self.assertEqual(len(result['units']), 864)
        self.assertTrue(all(u['status'] == 'missing' for u in result['units']))
        with self.assertRaises(ValueError):
            a.report([self.rows[0], self.rows[0]])
        self.assertEqual(a.count([True, None, False]), dict(known=1, unknown=1, planned=3, bounds=[1/3, 2/3]))

    def test_every_verdict_and_gate(self):
        self.assertEqual([a.verdict(x) for x in ([.21,.3], [-.1,.1], [.2,.3])], ['support', 'no difference', 'inconclusive'])
        self.assertEqual(a.probe_verdict([.74,1], [1,1], [[1,1]]*2), 'not diagnosable')
        self.assertEqual(a.probe_verdict([1,1], [.74,1], [[1,1]]*2), 'not diagnosable')
        self.assertEqual(a.probe_verdict([.75,1], [.75,1], [[.3,.4]]*2), 'support')
        self.assertEqual(a.probe_verdict([1,1], [1,1], [[.3,.4], [0,0]]), 'inconclusive')
        self.assertEqual(a.fact_verdict([.3,.4], [0,0], .89, [[.3,.4]]*2, [[.3,.4]]*2), 'support')
        self.assertEqual(a.fact_verdict([.3,.4], [0,0], .90, [[.3,.4]]*2, [[.3,.4]]*2), 'no headroom')
        for variant, family, version in (([0,.2], [[.3,.4]]*2, [[.3,.4]]*2), ([0,0], [[0,0]], [[.3,.4]]*2), ([0,0], [[.3,.4]]*2, [[0,0]]*2)):
            self.assertEqual(a.fact_verdict([.3,.4], variant, .8, family, version), 'inconclusive')
        development = {f: {arm: [.25,.75] for arm in ('base','neutral')} for f in ('a','b')}
        effects = {'a':[.1,.3], 'b':[.1,.3]}
        self.assertEqual(a.broad_verdict({}, [.4,.4], {}, []), 'no headroom')
        self.assertEqual(a.broad_verdict({'a':development['a']}, [.4,.4], effects, [[.5,.5]]), 'inconclusive')
        self.assertEqual(a.broad_verdict(development, [.3,.4], effects, [[.5,.5]]), 'support')
        self.assertEqual(a.broad_verdict(development, [.3,.4], effects, [[.91,1]]), 'no headroom')
        effects['b'] = [0,.3]
        self.assertEqual(a.broad_verdict(development, [.3,.4], effects, [[.5,.5]]), 'inconclusive')
        self.assertEqual(a.regression([1,1]), 'NOT SET')
        self.assertEqual(a.regression([.48,.5], [[-.375,.375]]), 'flag')
        self.assertEqual(a.regression([.475,.5], [[-.375,.375]]), 'not flagged')

    def test_launch_guard(self):
        available = {arm: {'available': True} for arm in h.ARMS}
        expected = binding('a'*40, 'main', available)
        receipt = dict(expected, approved_by='Chris Lahn', dollar_cap=1)
        for kwargs in ({}, {'owner_approved':True, 'existing':True}):
            with self.assertRaises(ValueError):
                LaunchGuard(receipt, expected, available, lambda x: None, **kwargs)
        for field in expected:
            changed = dict(receipt, **{field:'changed'})
            with self.assertRaises(ValueError):
                LaunchGuard(changed, expected, available, lambda x: None, owner_approved=True)
        journal = []
        guard = LaunchGuard(receipt, expected, available, journal.append, owner_approved=True)
        self.assertEqual(guard.call('base', .6, lambda: 'ok'), 'ok')
        with self.assertRaises(ValueError):
            guard.call('base', .5, lambda: self.fail())
        guard.checkpoints['base']['available'] = False
        with self.assertRaises(ValueError):
            guard.call('base', 0, lambda: self.fail())
        self.assertEqual(journal[0][0]['status'], 'reserved')
        self.assertTrue(all(not c['available'] for c in inventory('missing-cache', 'missing-adapters').values()))
        with patch.object(h, 'HELD_HASH', 'changed'):
            with self.assertRaises(ValueError):
                h.plan('held_out')

    def test_guarded_block_stops_without_resume(self):
        available = {arm: {'available': True} for arm in h.ARMS}
        expected = binding('a'*40, 'development', available)
        receipt = dict(expected, approved_by='Chris Lahn', dollar_cap=.5)
        guard = LaunchGuard(receipt, expected, available, lambda x: None, owner_approved=True)
        retained = []
        with patch('exploratory.step4_harness.guard.verify_execution_commit'):
            rows = h.run_block('development', available, guard, lambda *x: '{"tool":null,"args":{}}', retained.append, .3)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]['terminal_status'], 'generation_failed')
        self.assertEqual(len(retained), 2)
        self.assertEqual(guard.reserved, .3)
        with self.assertRaises(ValueError):
            h.run_block('development', available, guard, lambda *x: self.fail(), retained.append, 0)


if __name__ == '__main__':
    unittest.main()
