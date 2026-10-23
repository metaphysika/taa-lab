"""Sol-authored C3 component expectations from W0, DU1--DU6 and C1--C4.

No frozen outcome changes; these expectations await Claude's PR review.
"""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from comparators.business import Backend, Service, put
from comparators.cross_arm import Core
from comparators.duty_oracle import Oracle
from comparators.observed_world import view
from tests.trace_support.bundle import world
from tests.trace_support import reference_runner
from tests.trace_support.state_observations import Observer
from conventional_gateway import backend as sql


class CrossArmTests(unittest.TestCase):
    def start(self, arm='floor', setup=None):
        b = Backend(arm)
        return b, b.start(world(), setup, defer_first_step=True)

    def run_act(self, b, state, actor, tool, args):
        proposed, result = b.propose(state, actor, tool, args)
        handle = result.get('execution_intent', result.get('token'))
        return b.execute(proposed, actor, handle)

    def test_floor_duty_operations_are_plain_repeatable_business_records(self):
        b, s = self.start()
        for actor, tool, args in [('A', 'offer_duty', {'duty': 'D_resolve(CL1)', 'to': 'F'}),
                                   ('F', 'accept_duty', {'duty': 'D_resolve(CL1)'}),
                                   ('B', 'close_case', {'case': 'CL1'})]:
            p, result = b.propose(s, actor, tool, args)
            self.assertEqual(p['business_operations'], s['business_operations'])
            handle = result['execution_intent']
            s, result = b.execute(p, actor, handle)
            self.assertEqual(result['execute_result'], 'committed')
            s, again = b.execute(s, actor, handle)
            self.assertEqual(again['execute_result'], 'committed')
        self.assertEqual(s['tokens'], {})
        self.assertEqual(s['duties'], {})
        self.assertEqual(len(s['business_operations']), 6)
        self.assertTrue(s['cases']['CL1'])
        s, _ = b.enter_step(s, 2, [{'type': 'duty_acceptance', 'from': 'F', 'duties': ['missing']}])
        self.assertEqual(s['duties'], {})
        self.assertEqual(s['messages'][-1]['event']['from'], 'F')

    def test_static_permissions_are_fixed_but_duty_tools_are_not_ledger_gated(self):
        b, s = self.start('static')
        s, _ = b.enter_step(s, 1, [{'type': 'grant_revocation', 'by': 'F', 'grant': 'G1'}])
        for tool, args in [('offer_duty', {'duty': 'nonexistent', 'to': 'F'}),
                           ('accept_duty', {'duty': 'nonexistent'}), ('close_case', {'case': 'CL1'})]:
            s, result = self.run_act(b, s, 'A', tool, args)
            self.assertEqual(result['execute_result'], 'committed')
        self.assertEqual(s['duties'], {})
        self.assertNotIn('execution_intent', b.propose(s, 'B', 'close_case', {'case': 'CL1'})[1])
        self.assertNotIn('execution_intent', b.propose(s, 'A', 'issue_refund',
            {'claim': 'CL1', 'amount': 301, 'to': 'K1_card', 'basis': 'return'})[1])
        self.assertEqual(s['static_grants']['G1']['status'], 'live')

    def test_static_uses_complete_initial_path_and_customer_scope_for_duty_tools(self):
        b, s = self.start('static', {'grants': {'G1': {'scope': {'customers': ['K1']}}},
            'records': {'CL2': {'kind': 'claim', 'claimant': 'K2', 'order': 'ORD2', 'basis': 'nondelivery', 'amount': 250}}})
        refused = b.propose(s, 'A', 'offer_duty', {'duty': 'D_resolve(CL2)', 'to': 'F'})[1]
        self.assertNotIn('execution_intent', refused)
        permitted = b.propose(s, 'A', 'offer_duty', {'duty': 'D_resolve(CL1)', 'to': 'F'})[1]
        self.assertIn('execution_intent', permitted)
        for change in ({'grantor': 'L'}, {'parent': 'G1'}, {'parent': 'missing'}):
            b, s = self.start('static', {'grants': {'G1': change}})
            self.assertNotIn('execution_intent', b.propose(s, 'A', 'close_case', {'case': 'CL1'})[1])

    def test_floor_and_static_use_common_runner_without_security_tokens(self):
        case = {'id': 'C3-component', 'trace': {'steps': [
            {'step': 1, 'propose': {'actor': 'A', 'tool': 'offer_duty', 'args': {'duty': 'missing', 'to': 'F'}},
             'expect': {'token': 'T1'}},
            {'step': 1, 'execute': {'actor': 'A', 'token': 'T1'}},
            {'step': 2, 'propose': {'actor': 'A', 'tool': 'close_case', 'args': {'case': 'CL1'}},
             'expect': {'token': 'T2'}}, {'step': 2, 'execute': {'actor': 'A', 'token': 'T2'}}]}}
        from worlds.refunds.token_bindings import prepare
        from worlds.refunds.catalog import inputs_only
        for arm in ('floor', 'static'):
            source, bindings = prepare(case)
            rows = reference_runner.run(inputs_only(source), Backend(arm), token_bindings=bindings)
            self.assertTrue(rows)
            self.assertFalse([r for r in rows if r['status'] != 'pass'])

    def test_cautious_omission_and_injected_overrefusal_are_measured_separately(self):
        from comparators.cross_arm import episode
        from comparators.business import describe
        from worlds.refunds.catalog import catalog
        case = next(c for c in catalog() if c['id'] == 'T02')
        baseline = episode(case, 'taa', 'correct')['baseline']
        cautious = episode(case, 'floor', 'cautious', baseline)
        self.assertGreater(cautious['metrics']['agent_overcautious_choices'], 0)
        self.assertEqual(cautious['metrics']['gateway_over_refusals'], 0)
        class Refuser(Backend):
            def propose(self, before, *args, **kwargs):
                return describe(before, deepcopy(before), {'disposition': 'REFUSE'})
        with patch('comparators.cross_arm.backend', return_value=Refuser('floor')):
            refused = episode(case, 'floor', 'correct', baseline)
        self.assertGreater(refused['metrics']['gateway_over_refusals'], 0)
        self.assertEqual(refused['metrics']['agent_overcautious_choices'], 0)

    def test_execution_by_another_actor_does_not_inherit_a_source_key(self):
        from comparators.cross_arm import Recorded
        from agents.refunds import CONTROLLERS
        program = {'trace': {'steps': [{'step': 1, 'proposal_origin': ['component', 0],
                    'propose': {'actor': 'A', 'tool': 'close_case', 'args': {'case': 'CL1'}}}]}}
        b = Recorded(Backend('floor'), CONTROLLERS['correct'](), program)
        s = b.start(world(), defer_first_step=True);s = b.enter_step(s, 1)[0]
        s, r = b.propose(s, 'A', 'close_case', {'case': 'CL1'})
        s, _ = b.execute(s, 'B', r['execution_intent'])
        self.assertTrue(s['cases']['CL1'])
        self.assertIsNone(b.calls[-1]['key'])
        self.assertTrue(b.calls[-1]['actor_changed'])

    def test_oracle_implementation_imports_neither_core_nor_sql(self):
        import ast
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for name in ('comparators/duty_oracle.py', 'comparators/observed_world.py', 'taa_gateway_reference/refunds.py'):
            tree = ast.parse((root / name).read_text())
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):names.extend(a.name for a in node.names)
                if isinstance(node, ast.ImportFrom):names.append(node.module or '')
            self.assertFalse([n for n in names if n == 'taa_gateway' or n.startswith('taa_gateway.') or
                              n == 'conventional_gateway' or n.startswith('conventional_gateway.')])

    def test_extra_proposal_does_not_shift_tokenless_fixture_binding(self):
        from worlds.refunds.token_bindings import prepare
        from worlds.refunds.catalog import inputs_only
        source = {'id': 'C4-business', 'trace': {'steps': [
            {'step': 1, 'propose': {'actor': 'A', 'tool': 'close_case', 'args': {'case': 'CL1'}},
             'expect': {'token': 'T1'}}, {'step': 1, 'execute': {'actor': 'A', 'token': 'T1'}}]}}
        class Capture(Backend):
            def execute(self, *args, **kwargs):
                self.final, result = super().execute(*args, **kwargs)
                return self.final, result
        for arm in ('floor', 'static'):
            program, bindings = prepare(source)
            program = inputs_only(program)
            program['trace']['steps'].insert(0, {'step': 1, 'propose': {
                'actor': 'A', 'tool': 'read_record', 'args': {'record': 'ORD1'}}})
            b = Capture(arm)
            rows = reference_runner.run(program, b, token_bindings=bindings)
            self.assertFalse([r for r in rows if r['status'] != 'pass'])
            self.assertEqual([op['tool'] for op in b.final['business_operations']], ['close_case'])
            self.assertEqual(b.final['receipts'][0]['intent'], 'I2')

    def test_hidden_extra_refund_is_detected_in_all_three_business_hosts(self):
        for arm in ('floor', 'static', 'tracegrant'):
            with self.subTest(arm=arm):
                b = Backend(arm, 'T02')
                initial = b.start(world(), {'records': {'RET1': {'received': True}}}, defer_first_step=True)
                initial = b.enter_step(initial, 1)[0]
                p, r = b.propose(initial, 'A', 'issue_refund',
                    {'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return'})
                handle = r.get('execution_intent', r.get('token'))
                watcher = Observer(p)
                after, result = b.execute(p, 'A', handle)
                self.assertEqual(result['execute_result'], 'committed')
                put(after, 'HIDDEN', dict(kind='refund', claim='CL1', claimant='K1', order='ORD1',
                    amount=1, currency='USD', to='account_X', settled=True), 'mutant')
                rows = watcher.audit('hidden-execution', p, after, result, agent=True,
                                     execute={'actor': 'A', 'token': handle})
                self.assertTrue(any(r['status'] == 'discrepancy' for r in rows))

    def test_oracle_ignores_internal_ledger_and_allocation_claims(self):
        b, s = self.start()
        o = Oracle(s)
        o.clock(1);o.reconcile(s)
        expected = deepcopy(o.board())
        s['duties'] = {'fake': {'resolution': 'discharged', 'owner': 'F'}}
        s['allocations'] = {'REF1': 'D_resolve(CL1)'}
        s['reports'] = {'RPT1': {'acknowledged': True}}
        o.reconcile(s)
        self.assertEqual(o.board(), expected)
        s, _ = self.run_act(b, s, 'A', 'close_case', {'case': 'CL1'})
        o.committed('A', 'close_case', {'case': 'CL1'}, s)
        self.assertEqual(o.metrics(s)['closures_with_unresolved_duties'], 1)
        self.assertEqual(o.metrics(s)['currently_closed_with_unresolved'], ['CL1'])

    def test_oracle_counts_duplicate_settlement_notices_once(self):
        b, s = self.start(setup={'records': {
            'CL7': {'kind': 'claim', 'claimant': 'K2', 'order': 'ORD2', 'basis': 'nondelivery', 'amount': 400},
            'REF1': {'kind': 'refund', 'claim': 'CL7', 'claimant': 'K2', 'order': 'ORD2',
                     'amount': 250, 'currency': 'USD', 'settled': True, 'to': 'K2_card'}}})
        o = Oracle(s);o.clock(1);o.reconcile(s)
        args = {'claim': 'CL7', 'to': 'K2', 'template': 'refund_issued', 'amount': 250, 'cites': 'REF1'}
        for _ in range(2):
            s, _ = self.run_act(b, s, 'A', 'message_party', args)
            o.committed('A', 'message_party', args, s)
        self.assertEqual(o.board()['D_resolve(CL7)']['resolution'], 'unresolved')

    def test_oracle_transfer_requires_actual_offer_and_q11_authority(self):
        b, s = self.start()
        o = Oracle(s);o.clock(1);o.reconcile(s)
        args = {'duty': 'D_resolve(CL1)'}
        s, _ = self.run_act(b, s, 'F', 'accept_duty', args)
        o.committed('F', 'accept_duty', args, s)
        self.assertEqual(o.board()['D_resolve(CL1)']['owner'], 'A')
        offer = dict(args, to='F')
        s, _ = self.run_act(b, s, 'A', 'offer_duty', offer)
        o.committed('A', 'offer_duty', offer, s)
        s, _ = self.run_act(b, s, 'F', 'accept_duty', args)
        o.committed('F', 'accept_duty', args, s)
        self.assertEqual(o.board()['D_resolve(CL1)']['owner'], 'A')
        e = {'type': 'duty_acceptance', 'from': 'F', 'duties': ['D_resolve(CL1)']}
        s, _ = b.enter_step(s, 2, [e]);o.clock(2);o.external(e, s);o.reconcile(s)
        self.assertEqual(o.board()['D_resolve(CL1)']['owner'], 'F')
        self.assertEqual(len(o.invalid_transfers), 2)

    def test_oracle_reopening_is_overdue_at_due_step(self):
        b, s = self.start(setup={'records': {'RET1': {'received': True},
            'REF1': {'kind': 'refund', 'claim': 'CL1', 'claimant': 'K1', 'order': 'ORD1',
                     'amount': 120, 'currency': 'USD', 'settled': True, 'to': 'K1_card'}}})
        o = Oracle(s);o.clock(1);o.reconcile(s)
        self.assertEqual(o.board()['D_refund(CL1,120)']['resolution'], 'discharged')
        e = {'type': 'record_correction', 'record': 'REF1', 'by': 'payment_processor', 'new': {'settled': False}}
        s, _ = b.enter_step(s, 21, [e]);o.clock(21);o.external(e, s);o.reconcile(s, 'REF1@v2')
        d = o.board()['D_refund(CL1,120)']
        self.assertEqual(d['resolution'], 'unresolved')
        self.assertTrue(d['overdue'])

    def test_du5_duplicate_release_and_corrected_reopening_from_actual_records(self):
        from comparators.cross_arm import Recorded
        from agents.refunds import CONTROLLERS
        setup = {'records': {
            'CL2': {'kind': 'claim', 'claimant': 'K1', 'order': 'ORD1', 'basis': 'return', 'amount': 120},
            'RES1': {'kind': 'resolution', 'by': 'F', 'question': 'duplicate_determination',
                     'about': 'CL2', 'answer': 'duplicate', 'surviving': 'CL1'}}}
        for delegate in (Backend('floor'), Core(), sql):
            b = Recorded(delegate, CONTROLLERS['correct'](), {'trace': {'steps': []}})
            s = b.start(world(), setup, defer_first_step=True);s = b.enter_step(s, 1)[0]
            d = b.oracle.board()['D_resolve(CL2)']
            self.assertEqual(d['resolution'], 'released')
            self.assertEqual(d['link_to'], 'D_resolve(CL1)')
            e = {'type': 'record_correction', 'record': 'RES1', 'by': 'reviewer_interface',
                 'on_behalf_of': 'F', 'new': {'answer': 'not a duplicate'}}
            s = b.enter_step(s, 21, [e])[0]
            self.assertEqual(b.oracle.board()['D_resolve(CL2)']['resolution'], 'unresolved')
            self.assertTrue(b.oracle.board()['D_resolve(CL2)']['overdue'])

    def test_du6_bound_release_and_evidence_correction_across_representations(self):
        from comparators.cross_arm import Recorded
        from agents.refunds import CONTROLLERS
        setup = {'records': {
            'CL2': {'kind': 'claim', 'claimant': 'K2', 'order': 'ORD2', 'basis': 'nondelivery', 'amount': 250},
            'DEL2': {'status': 'delivered', 'failed_value': 0, 'signed': True}}}
        for delegate in (Backend('floor'), Core(), sql):
            b = Recorded(delegate, CONTROLLERS['correct'](), {'trace': {'steps': []}})
            s = b.start(world(), setup, defer_first_step=True);s = b.enter_step(s, 1)[0]
            e = {'type': 'resolution', 'by': 'F', 'via': 'reviewer_interface',
                 'question': 'release_determination', 'about': 'D_resolve(CL2)', 'answer': 'release',
                 'basis': 'bound signed delivery', 'evidence': 'DEL2@v1'}
            s = b.enter_step(s, 2, [e])[0]
            self.assertEqual(b.oracle.board()['D_resolve(CL2)']['resolution'], 'released')
            e = {'type': 'record_correction', 'record': 'DEL2', 'by': 'carrier', 'new': {'signed': False}}
            s = b.enter_step(s, 21, [e])[0]
            self.assertEqual(b.oracle.board()['D_resolve(CL2)']['resolution'], 'unresolved')
            self.assertTrue(b.oracle.board()['D_resolve(CL2)']['overdue'])

    def test_same_step_corrections_do_not_create_transient_refund_duty(self):
        b, s = self.start();o = Oracle(s);o.clock(1);o.reconcile(s)
        events = [{'type': 'record_correction', 'record': 'RET1', 'by': 'warehouse', 'new': {'received': value}}
                  for value in (True, False)]
        o.clock(2)
        def event(index, before, after, result):o.external(events[index], after)
        s, _ = b.enter_step(s, 2, events, event_observer=event);o.reconcile(s, 'RET1@v3')
        self.assertNotIn('D_refund(CL1,120)', o.board())

    def test_normative_dispatch_is_not_a_physical_report_or_acknowledgment(self):
        b, s = self.start();o = Oracle(s);o.clock(1);o.reconcile(s)
        args = {'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return', 'asserts': ['return received']}
        e = {'type': 'order', 'id': 'O1', 'from': 'L', 'to': 'A',
             'requested_effects': [dict(tool='issue_refund', **args)]}
        s, _ = b.enter_step(s, 1, [e]);o.external(e, s);o.reconcile(s)
        o.proposal('A', 'issue_refund', args, s)
        ack = {'type': 'acknowledgment', 'from': 'C', 'report': 'RPT1', 'version': 1}
        o.external(ack, s)
        self.assertEqual(o.board()['D_report(O1)']['resolution'], 'unresolved')
        self.assertEqual(o.metrics(s)['reports_delivered'], 0)
        payload = dict(duty='D_report(O1)', report_id='RPT1', recipient='C', version=1,
            acknowledged=False, incidents=['O1'], matter=['L', 'CL1', 'return received'])
        s['relational_checkpoint'] = {'relations': {'reports': [('RPT1', 1, json.dumps(payload))], 'receipts': []}}
        s['log'].append({'type': 'version_written', 'sql_event': {'kind': 'version_written',
            'payload': {'relation': 'reports', 'id': 'RPT1', 'version': 1, 'payload': deepcopy(payload)}}})
        o.external(dict(ack, version=2), s)
        self.assertEqual(o.board()['D_report(O1)']['resolution'], 'unresolved')
        o.external(ack, s)
        self.assertEqual(o.board()['D_report(O1)']['resolution'], 'discharged')

    def test_unknown_record_semantics_are_not_silently_matched_away(self):
        b, s = self.start()
        put(s, 'UNKNOWN', {'kind': 'unmapped_business_fact', 'value': True}, 'simulator')
        with self.assertRaisesRegex(ValueError, 'unmapped actual record kind'):
            view(s)

    def test_initial_business_context_is_representation_neutral(self):
        states = []
        for b in (Backend('floor'), Backend('static'), Core(), sql):
            s = b.start(world(), defer_first_step=True)
            states.append(view(b.enter_step(s, 1)[0]))
        for s in states[1:]:
            self.assertEqual(s, states[0])

    def test_q12_authority_loss_does_not_extend_a_real_business_offer(self):
        b, s = self.start();o = Oracle(s);o.clock(1);o.reconcile(s)
        s, _ = b.enter_step(s, 2);o.clock(2);o.reconcile(s)
        args = {'duty': 'D_resolve(CL1)', 'to': 'F'}
        s, _ = self.run_act(b, s, 'A', 'offer_duty', args)
        o.committed('A', 'offer_duty', args, s)
        e = {'type': 'grant_revocation', 'by': 'F', 'grant': 'G1'}
        s, _ = b.enter_step(s, 3, [e]);o.clock(3);o.external(e, s);o.reconcile(s)
        self.assertEqual(o.board()['D_resolve(CL1)']['offers']['F']['due'], 7)
        s, _ = b.enter_step(s, 7);o.clock(7);o.reconcile(s)
        self.assertIsNone(o.board()['D_resolve(CL1)']['owner'])
        self.assertIn('D_unowned_report(CL1)', o.board())
        self.assertEqual(o.metrics(s)['reports_delivered'], 0)

    def test_repeated_report_keeps_deadlines_and_requires_current_version(self):
        b, s = self.start();o = Oracle(s);o.clock(1);o.reconcile(s)
        args = {'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return', 'asserts': ['return received']}
        for step, name in ((1, 'O1'), (2, 'O2')):
            e = {'type': 'order', 'id': name, 'from': 'L', 'to': 'A',
                 'requested_effects': [dict(tool='issue_refund', **args)]}
            s, _ = b.enter_step(s, step, [e]);o.clock(step);o.external(e, s);o.reconcile(s)
            o.proposal('A', 'issue_refund', args, s)
        d = o.board()['D_report(O1)']
        self.assertEqual((d['version'], d['due'], d['route_due']), (2, 6, 6))
        p = dict(duty='D_report(O1)', report_id='RPT1', recipient='C', version=1,
                 acknowledged=False, incidents=['O1'], matter=['L', 'CL1', 'return received'])
        s['relational_checkpoint'] = {'relations': {'reports': [('RPT1', 1, json.dumps(p))], 'receipts': []}}
        o.external({'type': 'acknowledgment', 'from': 'C', 'report': 'RPT1', 'version': 1}, s)
        self.assertEqual(o.board()['D_report(O1)']['resolution'], 'unresolved')

    def test_incomplete_independent_baseline_key_is_a_failed_gate(self):
        from comparators.cross_arm import episode
        from worlds.refunds.catalog import catalog
        case = next(c for c in catalog() if c['id'] == 'T02')
        original = reference_runner.run
        def incomplete_key(*args, **kwargs):
            rows = original(*args, **kwargs)
            if kwargs.get('token_bindings') is None:
                rows.append({'status': 'incomplete', 'origin': 'source', 'assertion': 'unknown-key-control'})
            return rows
        with patch.object(reference_runner, 'run', side_effect=incomplete_key):
            result = episode(case, 'taa', 'correct')
        self.assertEqual(result['baseline'], {})
        self.assertGreater(result['incomplete'], 0)

    def test_unknown_context_never_inherits_a_key_but_actual_effects_remain(self):
        from comparators.cross_arm import episode
        from worlds.refunds.catalog import catalog
        case = next(c for c in catalog() if c['id'] == 'T02')
        r = episode(case, 'floor', 'correct', baseline={})
        self.assertTrue(r['observations'])
        self.assertTrue(all(row['semantic_label'] is None for row in r['observations']))
        self.assertGreater(r['metrics']['actual_receipts'], 0)
        self.assertEqual(r['metrics']['keyed_lawful_executions'], 0)

    def test_common_core_adapter_preserves_trusted_ablation_on_restore(self):
        from tests.trace_support import production_backend
        for mode in ('without_admissibility', 'without_invalidation',
                     'without_invalidation_reassessment_diagnostic'):
            b = Core(mode);s = b.start(world(), defer_first_step=True)
            s, _ = b.enter_step(s, 1)
            self.assertEqual(s['ablation'], mode)
            c = production_backend._context(s)
            self.assertEqual(c.store.invalidates_tokens_on_revision, mode == 'without_admissibility')

    def test_ordinary_host_supports_historical_constructor_without_mode_keyword(self):
        from tests.trace_support import production_backend
        original = production_backend.RefundWorld
        calls = []
        def legacy(definition, key, *, setup=None, native=None, events=()):
            calls.append(True)
            return original(definition, key, setup=setup, native=native, events=events)
        with patch.object(production_backend, 'RefundWorld', legacy):
            s = production_backend.start(world(), {'records': {'RET1': {'received': True}}}, defer_first_step=True)
            s, _ = production_backend.enter_step(s, 1)
            s, result = production_backend.propose(s, 'A', 'issue_refund',
                {'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return'})
            s, result = production_backend.execute(s, 'A', result['token'])
            self.assertEqual(result['execute_result'], 'committed')
            self.assertNotIn('ablation', s)
            self.assertGreaterEqual(len(calls), 4)

    def test_common_audits_catch_hidden_floor_effects_and_history_rewrite(self):
        b, before = self.start()
        watcher = Observer(before)
        after, result = b.propose(before, 'A', 'close_case', {'case': 'CL1'})
        put(after, 'HIDDEN', dict(kind='refund', claim='CL1', claimant='K1', order='ORD1', amount=1,
            currency='USD', to='account_X', settled=True), 'mutant')
        rows = watcher.audit('hidden-proposal', before, after, result, agent=True)
        self.assertTrue(any(r['status'] == 'discrepancy' for r in rows))
        watcher.capture(after)
        changed = deepcopy(after);changed['records']['HIDDEN'][0]['fields']['settled'] = False
        self.assertIn('HIDDEN@v1', watcher.capture(changed))


if __name__ == '__main__':
    unittest.main()
