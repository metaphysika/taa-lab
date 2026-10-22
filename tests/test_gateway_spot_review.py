"""Sol-authored from Astra's 2026-10-21 spot check; expectations reviewed by Claude."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from taa_gateway_reference import refunds
from tests.trace_support import reference_runner as runner
from tests.trace_support.bundle import cases as frozen_cases, world, verify_bundle
from tests.trace_support.regressions import cases, mutated, run_suite
from tests.trace_support.state_observations import Observer, state_delta


class SpotReviewRegressions(unittest.TestCase):
    def test_regression_scenarios_and_negative_controls(self):
        report = run_suite(runner)
        self.assertEqual(report['scenarios'], 32)
        self.assertEqual([r for r in report['assertions'] if r['status'] != 'pass'], [])
        self.assertEqual(len(report['negative_controls']), 3)
        for result in report['negative_controls']:
            self.assertTrue(any(r['status'] == 'discrepancy' for r in result['raw_observations']))
            self.assertFalse(any(r['status'] == 'incomplete' for r in result['raw_observations']))
        verify_bundle()

    def test_offer_expiry_precedes_same_step_authority_loss(self):
        # Q12 says LIVE windows survive loss. At expiry there is no live window;
        # phase 1 expiry precedes the phase 2 loss response, so a new one opens.
        from tests.trace_support import production_backend
        for backend in (refunds, production_backend):
            with self.subTest(backend=backend.__name__):
                state = backend.start(world())
                state, _ = backend.enter_step(state, 2)
                state, decision = backend.propose(state, "A", "offer_duty", {"duty": "D_resolve(CL1)", "to": "F"})
                state, _ = backend.execute(state, "A", decision["token"])
                state, _ = backend.enter_step(state, 7, [{"type": "grant_revocation", "grant": "G1", "by": "F"}])
                duty = state["duties"]["D_resolve(CL1)"]
                self.assertEqual(duty["owner"], "A")
                self.assertEqual(duty["offered_to"], "F")
                self.assertEqual(duty.get("offer_due", duty.get("offer_deadline_step")), 12)

    def test_hidden_extra_refund_and_refusal_write_fail_state_observations(self):
        for tid, method, mutation in [('T39', 'execute', 'extra_settled_refund'),
                                      ('T34', 'propose', 'refused_refund_without_description')]:
            with self.subTest(tid=tid):
                c = next(c for c in frozen_cases() if c['id'] == tid)
                with patch.object(runner.model, method, mutated(getattr(runner.model, method), mutation)):
                    bad = [r for r in runner.run(c) if r['status'] == 'discrepancy']
                self.assertTrue(any(r['origin'] == 'state-audit' for r in bad))
                self.assertTrue(any(r['origin'] == 'source' and
                                    (r['assertion'].endswith('.committed') or r['assertion'].endswith('.action_executed')) for r in bad))

    def test_retained_version_compares_content_at_publication(self):
        c = next(c for c in frozen_cases() if c['id'] == 'T38')
        with patch.object(runner.model, 'apply_event', mutated(runner.model.apply_event, 'rewrite_REF1_v1')):
            bad = [r for r in runner.run(c) if r['status'] == 'discrepancy']
        self.assertTrue(any(r['assertion'].endswith('.record_versions_retained') for r in bad))
        self.assertTrue(any(r['assertion'].endswith('.immutable_record_versions') for r in bad))

    def test_both_deadlines_survive_repeat_and_only_redispatch_advances_route(self):
        c = next(c for c in cases() if c['id'] == 'R-B2')
        actual = []
        enter = runner.model.enter_step
        def inspect(*args, **kwargs):
            state, result = enter(*args, **kwargs)
            actual.append(deepcopy(state))
            return state, result
        with patch.object(runner.model, 'enter_step', side_effect=inspect):
            self.assertTrue(all(r['status'] == 'pass' for r in runner.run(c)))
        before = next(s for s in actual if s['step'] == 4)['duties']['D_report(ORDR1)']
        after = actual[-1]['duties']['D_report(ORDR1)']
        self.assertEqual((before['due'], before['route_due']), (7, 7))
        self.assertEqual((after['due'], after['route_due'], after['recipient']), (7, 12, 'F'))

    def test_packed_and_split_event_inputs_produce_identical_phase_state(self):
        observed = {}
        enter = runner.model.enter_step
        for cid in ('R-B4-packed', 'R-B4-split'):
            def capture(*args, **kwargs):
                s, r = enter(*args, **kwargs)
                if s['step'] == 2:
                    observed[cid] = deepcopy(s)
                return s, r
            with patch.object(runner.model, 'enter_step', side_effect=capture):
                runner.run(next(c for c in cases() if c['id'] == cid))
        self.assertEqual(observed['R-B4-packed'], observed['R-B4-split'])
        self.assertNotIn('D_refund(CL1,120)', observed['R-B4-split']['duties'])

    def test_first_step_events_also_precede_initial_duty_engine(self):
        c = deepcopy(next(c for c in cases() if c['id'] == 'R-B4-split'))
        c['trace']['setup'] = {'records': {'RET1': {'received': True}}}
        for entry in c['trace']['steps']:
            entry['step'] -= 1
        # At step 1 the seeded true receipt is corrected true -> false before
        # any duty reconciliation; D_resolve is new, but no refund duty is new.
        for entry in c['trace']['steps'][:2]:
            entry['expect']['duties_created'] = [{'id': 'D_resolve(CL1)', 'resolution': 'unresolved'}]
        self.assertTrue(all(r['status'] == 'pass' for r in runner.run(c)))

    def test_t33_two_event_entries_are_one_phase_and_still_pass(self):
        c = next(c for c in frozen_cases() if c['id'] == 'T33')
        self.assertEqual(len([e for e in c['trace']['steps'] if e['step'] == 4 and 'events' in e]), 2)
        rows = runner.run(c)
        self.assertFalse([r for r in rows if r['status'] != 'pass'])
        # Structural assertion: the driver enters step 4 only once, with both events.
        enter = runner.model.enter_step
        steps = []
        def entering(state, step, events=(), **kwargs):
            steps.append((step, len(events)))
            return enter(state, step, events, **kwargs)
        with patch.object(runner.model, 'enter_step', side_effect=entering):
            runner.run(c)
        self.assertEqual([x for x in steps if x[0] == 4], [(4, 2)])

    def test_reviewer_token_count_comes_from_state(self):
        apply = runner.model.apply_event
        def issuing(*args, **kwargs):
            s, result = apply(*args, **kwargs)
            if args[1].get('type') == 'resolution' and args[1].get('question') == 'goodwill_approval':
                s['tokens']['HIDDEN'] = {'actor': 'F', 'tool': 'read_record', 'args': {},
                                         'revision': s['revision'], 'expires': 99, 'status': 'live', 'grant': 'G1'}
            return s, result
        with patch.object(runner.model, 'apply_event', side_effect=issuing):
            rows = runner.run(next(c for c in frozen_cases() if c['id'] == 'T17'))
        self.assertTrue(any(r['status'] == 'discrepancy' and r['origin'] == 'source' and
                            r['assertion'].endswith('.tokens_issued_by_reviewer') for r in rows))

    def test_reported_resolution_write_cannot_replace_a_real_record(self):
        apply = runner.model.apply_event
        def missing(*args, **kwargs):
            s, result = apply(*args, **kwargs)
            if args[1].get('type') == 'resolution' and args[1].get('question') == 'goodwill_approval':
                s['records'] = {rid: versions for rid, versions in s['records'].items() if versions[-1]['kind'] != 'resolution'}
            return s, result
        with patch.object(runner.model, 'apply_event', side_effect=missing):
            rows = runner.run(next(c for c in frozen_cases() if c['id'] == 'T17'))
        self.assertTrue(any(r['status'] == 'discrepancy' and r['origin'] == 'source' and
                            r['assertion'].endswith('.records_written') for r in rows))

    def test_consumption_and_receipt_are_observed_not_declared(self):
        execute = runner.model.execute
        for damage in ('restore_token', 'drop_receipt'):
            def broken(*args, **kwargs):
                s, result = execute(*args, **kwargs)
                if result.get('execute_result') == 'committed':
                    if damage == 'restore_token':
                        s['tokens'][args[2]]['status'] = 'live'
                    else:
                        s['receipts'].pop()
                return s, result
            with patch.object(runner.model, 'execute', side_effect=broken):
                rows = runner.run(next(c for c in frozen_cases() if c['id'] == 'T02'))
            self.assertTrue(any(r['status'] == 'discrepancy' and r['origin'] == 'source' and
                                r['assertion'].endswith('.token_state' if damage == 'restore_token' else '.receipt') for r in rows))

    def test_repeated_partial_denial_notices_do_not_create_extra_coverage(self):
        # Sol-authored component control, using T09 inputs. A 100 payment and
        # two notices of the same 100 denial cover 200 of 250, not 300.
        c = deepcopy(next(c for c in frozen_cases() if c['id'] == 'T09'))
        c['trace'].pop('final', None)
        c['trace']['steps'] = [e for e in c['trace']['steps'] if e['step'] <= 6]
        for step, token in ((7, 'T3'), (8, 'T4')):
            c['trace']['steps'].extend([
                {'step': step, 'propose': {'actor': 'A', 'tool': 'message_party',
                 'args': {'to': 'K2', 'template': 'refund_denied', 'claim': 'CL3', 'amount': 100, 'basis': 'DEL2'}},
                 'expect': {'disposition': 'PERMIT', 'token': token}},
                {'step': step, 'execute': {'actor': 'A', 'token': token},
                 'expect': {'duties': [{'id': 'D_resolve(CL3)', 'resolution': 'unresolved'}]}}])
        c['trace']['steps'].append({'step': 9, 'propose': {'actor': 'A', 'tool': 'close_case', 'args': {'case': 'CL3'}},
                                   'expect': {'disposition': 'REFUSE'}})
        self.assertTrue(all(r['status'] == 'pass' for r in runner.run(c)))

    def test_observer_requires_description_contract_and_audits_every_collection(self):
        s = refunds.start(world())
        for collection in ('records', 'receipts', 'tokens', 'duties', 'notices', 'reports', 'allocations'):
            after = deepcopy(s)
            if isinstance(after[collection], dict):
                after[collection]['HIDDEN'] = {'unexpected': True}
            else:
                after[collection].append({'unexpected': True})
            self.assertIn(collection, state_delta(s, after))
        rows = Observer(s).audit('missing', s, s, {})
        self.assertTrue(any(r['status'] == 'incomplete' for r in rows))


if __name__ == '__main__':
    unittest.main()
