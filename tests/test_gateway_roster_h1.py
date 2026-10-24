"""H1 component expectations authored from Claude's authenticated host-event ruling.

Isolated worlds only. No model output supplies an expectation; review is pending.
"""
from copy import deepcopy
import unittest

from taa_gateway_reference import refunds as reference
from tests.trace_support import production_backend as production
from conventional_gateway import backend as conventional
from comparators.business import Backend
from comparators.observed_world import view
from comparators.duty_oracle import Oracle
from tests.trace_support.bundle import world, verify_bundle

SETUP = {'host_events': ['roster_change']}


def change(**kw):
    return dict(type='roster_change', by='company', party='F',
                remove_jurisdictions=['refund_authority', 'claim_decisions'], **kw)


class RosterH1Tests(unittest.TestCase):
    def backends(self):
        return [('reference', reference), ('production', production), ('conventional', conventional),
                ('floor', Backend('floor')), ('static', Backend('static')), ('tracegrant', Backend('tracegrant', 'T02'))]

    def start(self, backend, setup=SETUP):
        return backend.start(world(), deepcopy(setup))

    def event(self, backend, state, event):
        return backend.enter_step(state, state['step'], [event])[0]

    def test_changed_roster_is_versioned_with_history_and_no_permission(self):
        for name, backend in self.backends():
            with self.subTest(backend=name):
                s = self.start(backend)
                initial = view(s)
                after = self.event(backend, s, change())
                actual = view(after)
                self.assertEqual(len(actual['records']['F']), 2)
                self.assertEqual(actual['records']['F'][0], initial['records']['F'][0])
                self.assertNotIn('claim_decisions', actual['records']['F'][-1]['fields']['jurisdictions'])
                self.assertGreater(after['revision'], s['revision'])
                self.assertEqual(actual['grants'], initial['grants'])
                self.assertEqual(after['world'], s['world'])

    def test_non_root_sender_is_logged_with_no_write_or_revision(self):
        for name, backend in self.backends():
            with self.subTest(backend=name):
                s = self.start(backend)
                e = change();e['by'] = 'L'
                after = self.event(backend, s, e)
                self.assertEqual(after['revision'], s['revision'])
                self.assertEqual(view(after)['records'], view(s)['records'])
                self.assertGreater(len(after['log']), len(s['log']))

    def test_noop_changes_are_log_only_and_root_can_restore_capacity_facts(self):
        for name, backend in self.backends():
            with self.subTest(backend=name):
                s = self.event(backend, self.start(backend), change())
                noop = self.event(backend, s, change())
                self.assertEqual(noop['revision'], s['revision'])
                self.assertEqual(view(noop)['records'], view(s)['records'])
                self.assertGreater(len(noop['log']), len(s['log']))
                restore = dict(type='roster_change', by='company', party='F',
                    add_jurisdictions=['refund_authority', 'claim_decisions'])
                restored = self.event(backend, noop, restore)
                self.assertEqual(len(view(restored)['records']['F']), 3)
                self.assertIn('claim_decisions', view(restored)['records']['F'][-1]['fields']['jurisdictions'])

    def test_event_entries_are_processed_in_order(self):
        for name, backend in self.backends():
            with self.subTest(backend=name):
                s = self.start(backend)
                add = dict(type='roster_change', by='company', party='R',
                    add_jurisdictions=['misconduct_reports'], add_may_receive=['misconduct_reports'])
                remove = dict(type='roster_change', by='company', party='R',
                    remove_jurisdictions=['misconduct_reports'], remove_may_receive=['misconduct_reports'])
                # R is an explicitly declared party in this isolated world.
                w = world();w['parties']['R'] = {'role': 'reviewer'}
                s = backend.start(w, deepcopy(SETUP))
                after = backend.enter_step(s, 1, [add, remove])[0]
                rows = view(after)['records']['R']
                self.assertEqual(len(rows), 3)
                self.assertIn('misconduct_reports', rows[1]['fields']['jurisdictions'])
                self.assertNotIn('misconduct_reports', rows[2]['fields']['jurisdictions'])
                self.assertEqual(rows[0], view(s)['records']['R'][0])

    def test_relevant_change_voids_outstanding_tokens_but_noop_does_not(self):
        args = {'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return'}
        for name, backend in self.backends()[:3]:
            with self.subTest(backend=name):
                s = self.start(backend, dict(SETUP, records={'RET1': {'received': True}}))
                s = backend.enter_step(s, 1)[0]
                s, result = backend.propose(s, 'A', 'issue_refund', args)
                token = result['token']
                self.assertEqual(s['tokens'][token]['status'], 'live')
                e = dict(type='roster_change', by='company', party='R',
                    add_jurisdictions=['misconduct_reports'], add_may_receive=['misconduct_reports'])
                after = self.event(backend, s, e)
                self.assertEqual(after['tokens'][token]['status'], 'void')
                after, proposal = backend.propose(after, 'A', 'issue_refund', args)
                after2 = self.event(backend, after, e)
                self.assertEqual(after2['revision'], after['revision'])
                self.assertEqual(after2['tokens'][proposal['token']]['status'], 'live')

    def test_frozen_world_does_not_admit_roster_events(self):
        verify_bundle()
        for name, backend in self.backends():
            with self.subTest(backend=name):
                s = self.start(backend, {})
                with self.assertRaises((ValueError, production.UnsupportedCapability)):
                    self.event(backend, s, change())

    def test_common_oracle_reads_actual_roster_versions_not_native_statuses(self):
        for name, backend in self.backends():
            with self.subTest(backend=name):
                s = self.start(backend)
                o = Oracle(s)
                after = self.event(backend, s, change())
                o.external(change(), after)
                self.assertEqual(len(o.s['records']['F']), 2)
                self.assertNotIn('claim_decisions', o.s['records']['F'][-1]['fields']['jurisdictions'])
                self.assertEqual(o.s['records']['F'][0], view(s)['records']['F'][0])

    def test_malformed_and_unknown_target_are_log_only(self):
        for name, backend in self.backends():
            for delta in ({'party': ['F']}, {'party': 'UNKNOWN'}, {'add_jurisdictions': 'root'},
                          {'add_may_receive': ['']}, {'extra_right': 'grant'}):
                with self.subTest(backend=name, delta=delta):
                    s = self.start(backend)
                    e = dict(change(), **delta)
                    after = self.event(backend, s, e)
                    self.assertEqual(after['revision'], s['revision'])
                    self.assertEqual(view(after)['records'], view(s)['records'])
                    self.assertGreater(len(after['log']), len(s['log']))

    def test_membership_noop_and_duplicate_add_do_not_reorder_or_duplicate(self):
        for name, backend in self.backends():
            with self.subTest(backend=name):
                s = self.start(backend)
                e = dict(type='roster_change', by='company', party='F',
                    remove_jurisdictions=['refund_authority'],
                    add_jurisdictions=['refund_authority', 'refund_authority'])
                noop = self.event(backend, s, e)
                self.assertEqual(noop['revision'], s['revision'])
                self.assertEqual(view(noop)['records'], view(s)['records'])
                e = dict(type='roster_change', by='company', party='R',
                    add_jurisdictions=['misconduct_reports', 'misconduct_reports'])
                after = self.event(backend, s, e)
                members = view(after)['records']['R'][-1]['fields']['jurisdictions']
                self.assertEqual(members.count('misconduct_reports'), 1)

    def test_core_requires_authentic_current_service_envelope_and_single_write_path(self):
        from taa_gateway.records import Write
        s = self.start(production)
        c = production._context(s)
        payload = {'party': 'F', 'remove_jurisdictions': ['claim_decisions']}
        authentic = c.auth.issue(c.sessions['company'], 'gateway_roster', 1, 'roster_change', payload)
        forged = deepcopy(authentic);forged['content']['party'] = 'A'
        before = c.store.snapshot()
        with self.assertRaises(ValueError):
            c.roster.receive(forged)
        self.assertEqual(c.store.snapshot(), before)
        for recipient, step in (('gateway', 1), ('gateway_roster', 0), ('gateway_roster', 2)):
            envelope = c.auth.issue(c.sessions['company'], recipient, step, 'roster_change', payload)
            with self.assertRaises(ValueError):
                c.roster.receive(envelope)
            self.assertEqual(c.store.snapshot(), before)
        row = c.store.read('party:F')
        with self.assertRaises(ValueError):
            c.store.publish(c.sources['warehouse'], 'external_record', [Write('party:F', 'party', row['fields'])])
        self.assertEqual(c.store.snapshot(), before)
        c.roster.receive(authentic)
        self.assertEqual(len(c.store.snapshot()['records']['party:F']), 2)
        logged = [e for e in c.log.events() if e['type'] == 'roster_change_accepted']
        self.assertEqual(logged[-1]['payload']['envelope'], authentic)

    def test_conventional_roster_authentication_checks_the_envelope(self):
        from unittest.mock import patch
        from conventional_gateway.world import World
        host = World(world(), deepcopy(SETUP))
        before = host.store.snapshot()
        envelope = host._envelope('L', 'roster', 'roster', change())
        envelope['sender'] = 'company'
        with patch.object(host, '_envelope', return_value=envelope):
            with self.assertRaises((PermissionError, ValueError)):
                host.event(change())
        self.assertEqual(host.store.snapshot(), before)

    def test_h1_preserves_the_declared_no_invalidation_ablations(self):
        from comparators.cross_arm import Core
        args = {'claim': 'CL1', 'amount': 120, 'to': 'K1_card', 'basis': 'return'}
        event = dict(type='roster_change', by='company', party='R', add_may_receive=['misconduct_reports'])
        for mode in ('without_invalidation', 'without_invalidation_reassessment_diagnostic'):
            b = Core(mode)
            s = self.start(b, dict(SETUP, records={'RET1': {'received': True}}))
            s, result = b.propose(s, 'A', 'issue_refund', args)
            after = self.event(b, s, event)
            self.assertGreater(after['revision'], s['revision'])
            self.assertEqual(after['tokens'][result['token']]['status'], 'live')

    def test_isolated_traces_use_the_common_runner_and_full_state_audits(self):
        from pathlib import Path
        import yaml
        from tests.trace_support import reference_runner as runner
        path = Path(__file__).parent / 'regression_scenarios/h1.yaml'
        cases = [dict(id=t['id'], trace=t, parameters={}, source=str(path)) for t in yaml.safe_load(path.read_text())]
        for name, backend in self.backends()[:3]:
            for case in cases:
                with self.subTest(backend=name, case=case['id']):
                    rows = runner.run(case, backend=backend)
                    self.assertTrue(any(r['origin'] == 'state-audit' for r in rows))
                    self.assertFalse([r for r in rows if r['status'] != 'pass'])

    def test_core_rechecks_envelope_step_inside_the_write_transaction(self):
        from unittest.mock import patch
        s = self.start(production)
        c = production._context(s)
        e = c.auth.issue(c.sessions['company'], 'gateway_roster', 1, 'roster_change',
                         {'party': 'F', 'remove_jurisdictions': ['claim_decisions']})
        original = c.store.gateway_mutation
        def intervening_clock(session, tool, callback):
            c.store.publish(c.gateway, 'advance_clock', step=2)
            return original(session, tool, callback)
        with patch.object(c.store, 'gateway_mutation', side_effect=intervening_clock):
            with self.assertRaises(ValueError):
                c.roster.receive(e)
        self.assertEqual(len(c.store.snapshot()['records']['party:F']), 1)
        self.assertIn('claim_decisions', c.store.read('party:F')['fields']['jurisdictions'])


if __name__ == '__main__':
    unittest.main()
