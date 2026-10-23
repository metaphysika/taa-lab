"""Sol-authored from Claude's Q14-NULL-ALLOCATION ruling; review pending.

Permanent acceptance. Expected values are specified by the ruling, never by a
backend. Actual arm records are preserved, including explicit null vs omission.
"""
from copy import deepcopy
import unittest

from taa_gateway_reference import refunds as reference
from tests.trace_support import production_backend as production
from conventional_gateway import backend as conventional
from comparators.business import Backend
from comparators.duty_oracle import Oracle
from tests.trace_support.bundle import world


class NullAllocationTests(unittest.TestCase):
    def setup_world(self):
        return {'records': {'RET1': {'received': True}, 'CL8': {'kind': 'claim',
            'claimant': 'K1', 'order': 'ORD1', 'amount': 120, 'basis': 'return'}}}

    def backends(self):
        return [('production', production), ('conventional', conventional), ('floor', Backend('floor'))]

    def committed_payment_and_notice(self, b):
        s = b.start(world(), self.setup_world())
        o = Oracle(s);o.clock(1);o.reconcile(s)
        for tool, args in [('issue_refund', {'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return'}),
                           ('message_party', {'claim': 'CL1', 'to': 'K1', 'template': 'refund_issued', 'amount': 120, 'cites': 'REF1'})]:
            s, r = b.propose(s, 'A', tool, args)
            s, r = b.execute(s, 'A', r.get('execution_intent', r.get('token')))
            self.assertEqual(r['execute_result'], 'committed')
            before = deepcopy(s)
            o.committed('A', tool, args, s)
            self.assertEqual(s, before, 'oracle must never normalize actual arm records')
        return s, o

    def test_original_committed_control_passes_all_three_without_rewriting_records(self):
        for name, b in self.backends():
            with self.subTest(backend=name):
                s, o = self.committed_payment_and_notice(b)
                self.assertEqual(o.board()['D_refund(CL1,120)']['resolution'], 'discharged')
                self.assertEqual(o.board()['D_resolve(CL1)']['resolution'], 'discharged')
                self.assertEqual(o.board()['D_refund(CL8,120)']['resolution'], 'unresolved')
                f = s['records']['REF1'][-1]['fields']
                self.assertEqual('allocated_to' in f, name == 'production')
                if name == 'production':self.assertIsNone(f['allocated_to'])

    def test_mirror_correction_to_another_claims_duty_reopens_and_stays_blocked(self):
        for name, b in self.backends():
            with self.subTest(backend=name):
                s, o = self.committed_payment_and_notice(b)
                event = {'type': 'record_correction', 'record': 'REF1', 'by': 'payment_processor',
                         'new': {'allocated_to': 'D_refund(CL8,120)'}}
                s = b.enter_step(s, 2, [event])[0]
                before = deepcopy(s)
                o.clock(2);o.external(event, s);o.reconcile(s, 'REF1@v2')
                self.assertEqual(s, before)
                self.assertEqual(o.board()['D_refund(CL1,120)']['resolution'], 'unresolved')
                self.assertEqual(o.board()['D_resolve(CL1)']['resolution'], 'unresolved')
                self.assertEqual(o.board()['D_refund(CL8,120)']['resolution'], 'unresolved')
                self.assertEqual(s['records']['REF1'][-1]['fields']['allocated_to'], 'D_refund(CL8,120)')

    def settlement_state(self, allocation='ABSENT'):
        s = reference.start(world(), self.setup_world())
        f = dict(kind='refund', claim='CL1', claimant='K1', order='ORD1', amount=120,
                 currency='USD', settled=True, to='K1_card')
        if allocation != 'ABSENT':f['allocated_to'] = allocation
        reference.put(s, 'REFX', f, 'payment_processor')
        return s

    def test_record_allocation_absent_null_claim_and_own_duty_are_equivalent(self):
        for allocation in ('ABSENT', None, 'CL1', 'D_refund(CL1,120)'):
            with self.subTest(allocation=allocation):
                s = self.settlement_state(allocation)
                reference.reconcile(s)
                self.assertEqual(s['duties']['D_refund(CL1,120)']['resolution'], 'discharged')
                self.assertEqual(s['duties']['D_refund(CL8,120)']['resolution'], 'unresolved')

    def test_record_and_internal_allocations_bound_to_other_duty_stay_blocked(self):
        for allocation in ('CL8', 'D_refund(CL8,120)', 'claim of K2', False, 0, [], {}):
            with self.subTest(record_allocation=allocation):
                s = self.settlement_state(allocation);reference.reconcile(s)
                self.assertEqual(s['duties']['D_refund(CL1,120)']['resolution'], 'unresolved')
        s = self.settlement_state();s['allocations']['REFX'] = 'D_refund(CL8,120)'
        reference.reconcile(s)
        self.assertEqual(s['duties']['D_refund(CL1,120)']['resolution'], 'unresolved')

    def test_null_internal_allocation_is_unallocated(self):
        s = self.settlement_state();s['allocations']['REFX'] = None
        reference.reconcile(s)
        self.assertEqual(s['duties']['D_refund(CL1,120)']['resolution'], 'discharged')

    def test_same_claim_notice_can_reuse_a_settlement_bound_to_its_refund_duty(self):
        s = self.settlement_state('D_refund(CL1,120)')
        reference.reconcile(s)
        args = dict(claim='CL1', to='K1', template='refund_issued', amount=120, cites='REFX')
        s, proposal = reference.propose(s, 'A', 'message_party', args)
        self.assertEqual(proposal['disposition'], 'PERMIT')
        s, execution = reference.execute(s, 'A', proposal['token'])
        self.assertEqual(execution['execute_result'], 'committed')
        self.assertTrue(s['receipts'])
        self.assertEqual(s['duties']['D_resolve(CL1)']['resolution'], 'discharged')
        wrong = dict(claim='CL1', to='K1', template='refund_issued', amount=120, cites='REFX')
        self.assertEqual(reference.constraints(s, 'A', 'message_party', wrong)['disposition'], 'PERMIT')

    def test_generic_reference_null_allocation_matches_absence_but_other_duty_blocks(self):
        from tests.test_gateway_reference import policy, grant, ARGS
        from taa_gateway_reference.model import initial, transition, Event
        for binding in ('ABSENT', None, 'C', 'different-duty'):
            with self.subTest(binding=binding):
                spec = policy(duties=True);s = initial(spec)
                for event in [Event('configuration', 'configuration', {'entitlements': {'C': {'claimant': 'customer',
                    'currency': 'USD', 'order_id': 'O', 'amount_minor': 1000}}}),
                    Event('grant', 'lead', grant()), Event('record', 'carrier', {'id': 'return', 'kind': 'return', 'fields': {'received': True}}),
                    Event('record', 'claims', {'id': 'C', 'kind': 'claim', 'fields': dict(ARGS, owed=True)})]:
                    s = transition(s, event, spec).state
                did = next(iter(s['duties']))
                if binding != 'ABSENT':s['allocations']['PAYMENT'] = did if binding == 'C' else binding
                s = transition(s, Event('record', 'payments', {'id': 'P', 'kind': 'settlement', 'fields': dict(ARGS,
                    settled=True, transaction_id='PAYMENT', allocation_id='PAYMENT')}), spec).state
                self.assertEqual(s['duties'][did]['resolution'], 'unresolved' if binding == 'different-duty' else 'discharged')
