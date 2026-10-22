"""Sol-authored C4 controls; no cross-arm scoring or frozen-fixture edits."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from comparators import harness as poec
from tests.trace_support import production_backend, reference_runner
from taa_gateway_reference import refunds as reference
from worlds.refunds.catalog import catalog, inputs_only
from worlds.refunds.token_bindings import prepare

class Capture:
    def __init__(self, backend):
        self.backend, self.executions = backend, []
    def __getattr__(self, key):
        return getattr(self.backend, key)
    def execute(self, before, actor, token, fault):
        after, result = self.backend.execute(before, actor, token, fault)
        self.executions.append((token, deepcopy(before), deepcopy(after)))
        return after, result

def diagnostic(program):
    """Extra non-source proposal issues a distinct unused certificate."""
    result = deepcopy(program)
    entries = result['trace']['steps']
    index = next(i for i, e in enumerate(entries) if 'propose' in e)
    probe = deepcopy(entries[index])
    probe.pop('expect', None)
    probe.pop('proposal_origin', None)
    probe['propose']['args']['customer'] = 'K1'
    entries.insert(index, probe)
    return result

class TokenBindingTests(unittest.TestCase):
    def source(self):
        return next(c for c in catalog() if c['id'] == 'T02')

    def test_origin_is_trace_and_entry_index_not_clock_step(self):
        source = self.source()
        prepared, bindings = prepare(source)
        index = next(i for i, e in enumerate(source['trace']['steps']) if 'propose' in e)
        self.assertEqual(bindings.labels['T1'], ('T02', index))
        self.assertEqual(prepared['trace']['steps'][index]['proposal_origin'], ['T02', index])
        self.assertNotIn('proposal_origin', source['trace']['steps'][index])
        stripped = inputs_only(prepared)
        self.assertEqual(stripped['trace']['steps'][index]['proposal_origin'], ['T02', index])
        self.assertFalse(any('expect' in e for e in stripped['trace']['steps']))

    def test_refusal_never_falls_back_to_extra_native_token(self):
        source, bindings = prepare(self.source())
        entry = next(e for e in source['trace']['steps'] if 'propose' in e)
        bindings.record({}, 'T1')
        self.assertIsNone(bindings.resolve('T1'))
        bindings.record(entry, None)
        self.assertIsNone(bindings.execution({'token': 'T1'}))
        self.assertIsNone(bindings.execution({'token_from': 'last_proposal'}))
        self.assertIsNone(bindings.resolve('unknown'))
        self.assertEqual(bindings.expectation('token', 'T1'), 'unissued:T1')
        self.assertEqual(bindings.expectation('disposition', 'PERMIT'), 'PERMIT')
        for native in ('EC9', 'T42', 'H7'):
            _, arm = prepare(self.source())
            arm.record(entry, native)
            self.assertEqual(arm.execution({'token': 'T1'}), native)
        with self.assertRaisesRegex(ValueError, 'origin executed twice'):
            bindings.record(entry, 'later')

    def test_extra_diagnostic_preserves_reference_and_production_references(self):
        for backend in (reference, production_backend):
            with self.subTest(backend=backend.__name__):
                source, bindings = prepare(self.source())
                capture = Capture(backend)
                rows = reference_runner.run(diagnostic(source), backend=capture, token_bindings=bindings)
                self.assertEqual([r for r in rows if r['status'] != 'pass'], [])
                first, second = capture.executions
                self.assertEqual(first[0], 'T2')
                self.assertEqual(second[0], 'T3')
                self.assertEqual(first[2]['tokens']['T2']['status'], 'consumed')
                self.assertNotEqual(first[2]['tokens']['T1']['status'], 'consumed')
                self.assertEqual(bindings.labels['T1'], ('T02', 1))

    def test_tracegrant_preserves_references_after_extra_certificate(self):
        from agents.refunds.correct import Correct
        original = Correct.program
        with patch.object(Correct, 'program', lambda controller, case: diagnostic(original(controller, case))):
            result = poec.episode(self.source(), 'correct')
        proposals = [r for r in result['observations'] if r['kind'] == 'proposal']
        self.assertEqual(proposals[0]['result']['certificate']['id'], 'EC1')
        self.assertEqual(proposals[1]['result']['certificate']['id'], 'EC2')
        self.assertEqual([r['certificate']['id'] for r in result['receipts']], ['EC2', 'EC3'])

    def test_invalid_dynamic_reference_is_rejected(self):
        _, bindings = prepare(self.source())
        for entry in ({'token_from': 'other'}, {'token_from': 'last_proposal', 'token': 'T1'}):
            with self.assertRaisesRegex(ValueError, 'invalid dynamic'):
                bindings.execution(entry)

    def test_refused_source_is_attempt_without_token_despite_unused_diagnostic(self):
        for backend in (reference, production_backend):
            with self.subTest(backend=backend.__name__):
                case = self.source()
                case['trace']['setup']['records']['RET1']['received'] = False
                source, bindings = prepare(case)
                first = next(i for i, e in enumerate(source['trace']['steps']) if 'propose' in e)
                # No false assertion/report side effect: support alone refuses.
                source['trace']['steps'][first]['propose']['args'].pop('asserts', None)
                source['trace']['steps'].insert(first, {'step': 2, 'propose': {'actor': 'A',
                    'tool': 'message_party', 'args': {'claim': 'CL1', 'to': 'K1',
                        'template': 'refund_held', 'missing': 'receipt'}}})
                capture = Capture(backend)
                rows = reference_runner.run(source, backend=capture, token_bindings=bindings)
                self.assertTrue(any(r['status'] == 'discrepancy' for r in rows))
                self.assertIsNone(capture.executions[0][0])
                self.assertIn('T1', capture.executions[0][1]['tokens'])
                self.assertNotIn('REF1', capture.executions[0][2]['records'])
                self.assertEqual(capture.executions[0][2]['tokens']['T1']['status'], 'live')

    def test_missing_token_does_not_crash_revision_assertion(self):
        actual = reference_runner.observe('same_revision_as', 'unissued:T1', {'tokens': {}, 'revision': 1},
                                           {}, {'proposal': None})
        self.assertEqual(actual, 'missing token')
