"""Sol-authored C1 component controls; not cross-arm scoring or H3 evidence."""
from copy import deepcopy
import unittest

from taa_gateway.refunds import RefundWorld, native_id
from taa_gateway.records import Write
from tests.trace_support import production_backend as backend
from tests.trace_support.bundle import world


class AdmissibilityAblationTests(unittest.TestCase):
    def context(self, ablation='without_admissibility', **setup):
        return RefundWorld(world(), backend.KEY, setup=setup, ablation=ablation)

    def propose(self, context, tool='issue_refund', args=None, actor='A'):
        return context.runtime.propose(context.sessions[actor], {'tool': tool, 'arguments': args or {
            'claim': 'CL1', 'amount': 120, 'to': 'account_X', 'basis': 'return'}})

    def test_only_prohibition_stage_removed_and_wrong_account_can_commit(self):
        for ablation, expected in ((None, 'PROHIBIT'), ('without_admissibility', 'PERMIT')):
            c = self.context(ablation, records={'RET1': {'received': True}})
            result = self.propose(c)
            self.assertEqual(result['disposition'], expected)
            if ablation:
                self.assertEqual([s['stage'] for s in result['stages']],
                                 ['authority', 'support', 'determination', 'duty'])
                self.assertFalse(any(r['stage'] == 'prohibition' for r in result['checks']))
                self.assertEqual(result['report_candidates'], [])
                committed = c.runtime.execute(c.sessions['A'], result['token'])
                self.assertEqual(committed['execute_result'], 'committed')
                self.assertEqual(committed['committed'][0]['to'], 'account_X')
                self.assertEqual(len(c.store.snapshot()['receipts']), 1)

    def test_support_authority_limits_and_closure_still_block(self):
        cases = [({}, 'A', 'issue_refund', None, 'SU1'),
                 ({'records': {'RET1': {'received': True}}}, 'B', 'issue_refund', None, 'AU1'),
                 ({'records': {'RET1': {'received': True}}}, 'A', 'issue_refund',
                  {'claim': 'CL1', 'amount': 400, 'to': 'K1_card', 'basis': 'return'}, 'per-refund-cap:'),
                 ({}, 'A', 'close_case', {'case': 'CL1'}, 'DU1')]
        for setup, actor, tool, args, rule in cases:
            with self.subTest(rule=rule):
                c = self.context(**setup)
                c.store.publish(c.gateway, 'advance_clock', step=1)
                c.engine.reconcile()
                result = self.propose(c, tool, args, actor)
                self.assertIn(result['disposition'], ('REFUSE', 'HOLD', 'ALTERNATIVE'))
                self.assertTrue(any(check['id'].startswith(rule) and check['disposition'] != 'PERMIT'
                                    for check in result['checks']))
                self.assertIsNone(result.get('token'))

    def test_revision_invalidation_and_atomic_rollback_remain(self):
        for mode in ('revision', 'fault'):
            with self.subTest(mode=mode):
                c = self.context(records={'RET1': {'received': True}})
                token = self.propose(c)['token']
                if mode == 'revision':
                    rid = native_id('RET1', 'return_receipt')
                    fields = deepcopy(c.store.snapshot()['records'][rid][-1]['fields'])
                    fields['received'] = False
                    c.store.publish(c.sources['warehouse'], 'external_record',
                                    [Write(rid, 'return_receipt', fields)])
                    self.assertEqual(c.store.snapshot()['tokens'][token]['status'], 'void')
                    self.assertEqual(c.runtime.execute(c.sessions['A'], token)['execute_result'], 'refused_stale_revision')
                else:
                    before = deepcopy(c.store.snapshot())
                    result = c.runtime.execute(c.sessions['A'], token, fault='during_receipt_write')
                    self.assertEqual(result['execute_result'], 'failed')
                    self.assertEqual(c.store.snapshot(), before)

    def test_no_prohibition_attribution_or_report_but_duty_engine_remains(self):
        # The same authentic order and current facts go to the unchanged backend.
        state = backend.start(world(), ablation='without_admissibility')
        state, _ = backend.enter_step(state, 2, [{'type': 'order', 'id': 'ORDR1', 'from': 'L', 'to': 'A',
            'requested_effects': [{'tool': 'issue_refund', 'claim': 'CL1', 'amount': 120,
                                   'asserts': ['return received']}]}])
        state, result = backend.propose(state, 'A', 'issue_refund', {
            'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return', 'asserts': ['return received']})
        self.assertNotEqual(result['disposition'], 'PROHIBIT')
        self.assertEqual(result['attributed_issuers'], [])
        self.assertEqual(state['reports'], {})
        self.assertIn('D_resolve(CL1)', state['duties'])
        self.assertFalse(any(d.startswith('D_report') for d in state['duties']))

    def test_configuration_is_explicit_not_a_setup_or_proposal_flag(self):
        c = RefundWorld(world(), backend.KEY, setup={
            'records': {'RET1': {'received': True}}, 'ablation': 'without_admissibility'})
        self.assertEqual(self.propose(c)['disposition'], 'PROHIBIT')
        with self.assertRaisesRegex(ValueError, 'unknown offline ablation'):
            self.context('anything-else')
