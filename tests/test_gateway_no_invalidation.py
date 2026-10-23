"""Sol-authored C2 component expectations from Claude's committed ruling.

These are controlled engineering cases, not edited frozen outcomes or H3 scores.
"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from taa_gateway.executor import FAULTS, Runtime
from taa_gateway.records import Write
from taa_gateway.refunds import RefundWorld, native_id
from tests.trace_support.bundle import world
from tests.trace_support.production_backend import KEY

PRIMARY = 'without_invalidation'
DIAGNOSTIC = 'without_invalidation_reassessment_diagnostic'


class NoInvalidationTests(unittest.TestCase):
    def context(self, mode, **setup):
        setup = {'records': {'RET1': {'received': True}}, **setup}
        c = RefundWorld(world(), KEY, setup=setup, ablation=mode)
        c.store.publish(c.gateway, 'advance_clock', step=1)
        c.engine.reconcile()
        return c

    def proposal(self, c, amount=120):
        args = {'claim': 'CL1', 'amount': amount, 'to': 'K1_card', 'basis': 'return'}
        return c.runtime.propose(c.sessions['A'], {'tool': 'issue_refund', 'arguments': args})

    def correct(self, c):
        rid = native_id('RET1', 'return_receipt')
        fields = deepcopy(c.store.snapshot()['records'][rid][-1]['fields'])
        fields['received'] = False
        c.store.publish(c.sources['warehouse'], 'external_record', [Write(rid, 'return_receipt', fields)])
        c.engine.reconcile()

    def revoke(self, c):
        rid = native_id('G1', 'grant')
        fields = deepcopy(c.store.snapshot()['records'][rid][-1]['fields'])
        fields['status'] = 'revoked'
        c.store.publish(c.gateway, 'grant_change', [Write(rid, 'grant', fields)])
        c.engine.reconcile()

    def refund_rows(self, c):
        return [versions[-1]['fields'] for versions in c.store.snapshot()['records'].values()
                if versions[-1]['kind'] == 'refund']

    def test_support_correction_primary_commits_diagnostic_and_default_refuse(self):
        for mode in (None, PRIMARY, DIAGNOSTIC):
            with self.subTest(mode=mode):
                c = self.context(mode)
                token = self.proposal(c)['token']
                certificate = deepcopy(c.store.snapshot()['tokens'][token]['certificate'])
                self.correct(c)
                before = c.store.snapshot()
                self.assertGreater(before['revision'], certificate['state_revision'])
                self.assertEqual(before['tokens'][token]['certificate'], certificate)
                self.assertEqual(before['tokens'][token]['status'], 'void' if mode is None else 'live')
                # New proposals still go through the full, unchanged rules.
                self.assertNotEqual(self.proposal(c)['disposition'], 'PERMIT')
                result = c.runtime.execute(c.sessions['A'], token)
                expected = 'committed' if mode == PRIMARY else 'refused_stale_revision' if mode is None else 'refused_revalidation'
                self.assertEqual(result['execute_result'], expected)
                self.assertEqual(len(self.refund_rows(c)), int(mode == PRIMARY))
                if mode == PRIMARY:
                    after = c.store.snapshot()
                    self.assertEqual(after['tokens'][token]['certificate'], certificate)
                    self.assertEqual(after['receipts'][-1]['pre_transaction_revision'], before['revision'])
                    self.assertEqual(result['validation_compares'], 'fixed_token_conditions_only')

    def test_grant_revocation_does_not_void_either_variant(self):
        for mode in (PRIMARY, DIAGNOSTIC):
            with self.subTest(mode=mode):
                c = self.context(mode)
                token = self.proposal(c)['token']
                self.revoke(c)
                self.assertEqual(c.store.snapshot()['tokens'][token]['status'], 'live')
                result = c.runtime.execute(c.sessions['A'], token)
                self.assertEqual(result['execute_result'], 'committed' if mode == PRIMARY else 'refused_revalidation')
                self.assertEqual(len(self.refund_rows(c)), int(mode == PRIMARY))

    def test_benign_record_insertion_allows_both_variants_but_default_invalidates(self):
        for mode in (None, PRIMARY, DIAGNOSTIC):
            with self.subTest(mode=mode):
                c = self.context(mode)
                token = self.proposal(c)['token']
                revision = c.store.revision
                c.store.publish(c.gateway, 'seed', [Write(native_id('NOTE1', 'agent_note'), 'agent_note', {'text': 'not evidence'})])
                self.assertGreater(c.store.revision, revision)
                with patch.object(c.pipeline, 'assess_snapshot', wraps=c.pipeline.assess_snapshot) as check:
                    result = c.runtime.execute(c.sessions['A'], token)
                self.assertEqual(result['execute_result'], 'refused_stale_revision' if mode is None else 'committed')
                self.assertEqual(check.call_count, int(mode == DIAGNOSTIC))
                if mode == DIAGNOSTIC:
                    self.assertEqual(result['validation_compares'], 'fixed_token_conditions_and_reassessment')

    def test_actor_exact_arguments_tool_and_single_use_are_retained(self):
        for mode in (PRIMARY, DIAGNOSTIC):
            with self.subTest(mode=mode):
                c = self.context(mode)
                token = self.proposal(c)['token']
                before = c.store.snapshot()
                for actor, options, expected in (
                    ('B', {}, 'refused_wrong_actor'),
                    ('A', {'arguments': {'claim': 'CL1', 'amount': 119, 'to': 'K1_card', 'basis': 'return'}}, 'refused_argument_mismatch'),
                    ('A', {'tool': 'message_party'}, 'refused_argument_mismatch')):
                    result = c.runtime.execute(c.sessions[actor], token, **options)
                    self.assertEqual(result['execute_result'], expected)
                    self.assertEqual(c.store.snapshot(), before)
                self.assertEqual(c.runtime.execute(c.sessions['A'], token)['execute_result'], 'committed')
                consumed = c.store.snapshot()
                self.assertEqual(c.runtime.execute(c.sessions['A'], token)['execute_result'], 'refused_token_consumed')
                self.assertEqual(c.store.snapshot(), consumed)
                self.assertEqual(len(self.refund_rows(c)), 1)

    def test_intrinsic_expiry_advances_revision_without_voiding_other_tokens(self):
        for mode in (PRIMARY, DIAGNOSTIC):
            with self.subTest(mode=mode):
                c = self.context(mode)
                first = self.proposal(c, 80)['token']
                c.store.publish(c.gateway, 'advance_clock', step=3)
                second = self.proposal(c, 70)['token']
                revision = c.store.revision
                c.store.publish(c.gateway, 'advance_clock', step=11)
                state = c.store.snapshot()
                self.assertGreater(state['revision'], revision)
                self.assertEqual(state['tokens'][first]['status'], 'void')
                self.assertEqual(state['tokens'][first]['void_reason'], 'expired')
                self.assertEqual(state['tokens'][second]['status'], 'live')
                self.assertEqual(c.runtime.execute(c.sessions['A'], first)['execute_result'], 'refused_token_expired')
                self.assertEqual(c.runtime.execute(c.sessions['A'], second)['execute_result'], 'committed')

    def test_primary_removes_residual_staging_and_cumulative_invalidation(self):
        c = self.context(PRIMARY)
        first, second = self.proposal(c, 80)['token'], self.proposal(c, 70)['token']
        original = deepcopy(c.store.snapshot()['tokens'][second])
        self.assertEqual(c.runtime.execute(c.sessions['A'], first)['execute_result'], 'committed')
        self.assertEqual(c.store.snapshot()['tokens'][second]['status'], 'live')
        self.assertEqual(c.runtime.execute(c.sessions['A'], second)['execute_result'], 'committed')
        state = c.store.snapshot()
        self.assertEqual(sum(r['amount'] for r in self.refund_rows(c)), 150)
        self.assertIn(native_id('REF1', 'refund'), state['records'])
        self.assertIn(native_id('REF2', 'refund'), state['records'])
        self.assertEqual(state['tokens'][second]['plan_hash'], original['plan_hash'])
        self.assertEqual(state['tokens'][second]['certificate'], original['certificate'])
        self.assertEqual(len(state['receipts']), 2)
        self.assertTrue(all(state['tokens'][token]['status'] == 'consumed' for token in (first, second)))

    def test_diagnostic_reassessment_blocks_stale_cumulative_permission(self):
        c = self.context(DIAGNOSTIC)
        first, second = self.proposal(c, 80)['token'], self.proposal(c, 70)['token']
        self.assertEqual(c.runtime.execute(c.sessions['A'], first)['execute_result'], 'committed')
        self.assertEqual(c.store.snapshot()['tokens'][second]['status'], 'live')
        self.assertEqual(c.runtime.execute(c.sessions['A'], second)['execute_result'], 'refused_revalidation')
        self.assertEqual(sum(r['amount'] for r in self.refund_rows(c)), 80)

    def test_all_seven_real_faults_roll_back_both_variants(self):
        for mode in (PRIMARY, DIAGNOSTIC):
            for fault in FAULTS:
                with self.subTest(mode=mode, fault=fault):
                    c = self.context(mode)
                    token = self.proposal(c)['token']
                    before = c.store.snapshot()
                    result = c.runtime.execute(c.sessions['A'], token, fault=fault)
                    self.assertEqual(result['execute_result'], 'failed')
                    self.assertEqual(c.store.snapshot(), before)
                    last = c.log.events()[-1]
                    self.assertEqual(last['type'], 'execution_rolled_back')
                    partial = last['payload']['partial_state']
                    if fault == 'during_effect_commit':
                        self.assertIn(native_id('REF1', 'refund'), partial['records'])
                    if fault == 'during_receipt_write':
                        self.assertEqual(len(partial['receipts']), 1)

    def test_duty_engine_and_unowned_reporting_are_retained(self):
        for mode in (PRIMARY, DIAGNOSTIC):
            with self.subTest(mode=mode):
                c = self.context(mode)
                token = self.proposal(c)['token']
                self.revoke(c)
                c.store.publish(c.gateway, 'advance_clock', step=6)
                c.engine.reconcile()
                state = c.store.snapshot()
                self.assertEqual(state['tokens'][token]['status'], 'live')
                duty = state['duty_records']['D_resolve(CL1)'][-1]['fields']
                self.assertIsNone(duty['owner'])
                self.assertEqual(duty['resolution'], 'unresolved')
                self.assertIn('D_unowned_report(CL1)', state['duty_records'])
                self.assertTrue(state['reports'])

    def test_trusted_modes_survive_explicit_checkpoint_restore(self):
        for mode in (PRIMARY, DIAGNOSTIC):
            with self.subTest(mode=mode):
                c = self.context(mode)
                token = self.proposal(c)['token']
                self.correct(c)
                restored = RefundWorld(world(), KEY, native=c.store.snapshot(), events=c.log.events(), ablation=mode)
                self.assertFalse(restored.store.invalidates_tokens_on_revision)
                result = restored.runtime.execute(restored.sessions['A'], token)
                self.assertEqual(result['execute_result'], 'committed' if mode == PRIMARY else 'refused_revalidation')

    def test_modes_are_constructor_choices_not_setup_fields(self):
        c = self.context(None, ablation=PRIMARY)
        self.assertTrue(c.store.invalidates_tokens_on_revision)
        for mode in (None, 'without_admissibility'):
            self.assertTrue(self.context(mode).store.invalidates_tokens_on_revision)
        with self.assertRaises(AttributeError):
            c.store.invalidates_tokens_on_revision = False
        with self.assertRaisesRegex(ValueError, 'requires the explicit no-invalidation'):
            Runtime(c.store, c.auth, c.gateway, c.pipeline, c.tools, reassess_on_execute=False)
        with self.assertRaisesRegex(ValueError, 'must be a boolean'):
            Runtime(c.store, c.auth, c.gateway, c.pipeline, c.tools, reassess_on_execute='false')
