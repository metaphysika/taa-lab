"""Q15/H1 expectations from Claude's approved text; full delta audits retained."""
from copy import deepcopy
from pathlib import Path
import itertools
import unittest
import yaml
from tests.trace_support import reference_runner as runner,production_backend as production
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as conventional
from tests.trace_support.bundle import world
from worlds.refunds.token_bindings import prepare
from comparators.duty_oracle import Oracle
from comparators.observed_world import report_artifacts


def programs():
    path=Path(__file__).parent/'regression_scenarios/q15.yaml'
    return [dict(id=t['id'],trace=t,parameters={},source=str(path)) for t in yaml.safe_load(path.read_text())]


def replay(case,b,oracle=False):
    s=b.start(world(),case['trace'].get('setup',{}),defer_first_step=True)
    o=Oracle(s) if oracle else None
    snapshots=[]
    for step,entries in itertools.groupby(case['trace']['steps'],key=lambda e:e['step']):
        entries=list(entries)
        for at in range(s['step']+1,step):
            s=b.enter_step(s,at)[0]
            if o:o.clock(at);o.reconcile(s)
        events=[e for entry in entries for e in entry.get('events',[])]
        if o:o.clock(step)
        def observed(index,before,after,result):
            if o:o.external(events[index],after)
        s=b.enter_step(s,step,events,event_observer=observed)[0]
        if o:o.reconcile(s)
        for entry in entries:
            if 'propose' in entry:
                p=entry['propose'];s=b.propose(s,p['actor'],p['tool'],p['args'])[0]
                if o:o.proposal(p['actor'],p['tool'],p['args'],s);o.reconcile(s)
            if o:
                for expected in entry.get('expect',{}).get('duties',[]):
                    assert runner.contains(o.board()[expected['id']],expected),(case['id'],expected,o.board()[expected['id']])
        snapshots.append(deepcopy(s))
    return s,o,snapshots


class Q15Tests(unittest.TestCase):
    def test_all_scenarios_use_common_runner_state_audits(self):
        for b in (reference,production,conventional):
            for case in programs():
                with self.subTest(backend=b.__name__,trace=case['id']):
                    program,bindings=prepare(case)
                    checks=runner.run(program,backend=b,token_bindings=bindings)
                    self.assertFalse([r for r in checks if r['status']!='pass'])

    def test_external_oracle_uses_actual_inputs_and_ordered_acks_on_both_hosts(self):
        for b in (production,conventional):
            for case in programs():
                with self.subTest(backend=b.__name__,trace=case['id']):
                    replay(case,b,oracle=True)

    def test_conflict_plus_deadline_dispatches_once_even_after_same_step_reconciliation(self):
        case=next(c for c in programs() if c['id']=='R-Q15-deadline-and-conflict')
        for b in (production,conventional):
            with self.subTest(backend=b.__name__):
                s,_,history=replay(case,b)
                self.assertEqual([x['to'] for x in report_artifacts(s)],['C','F'])
                again=b.enter_step(s,7)[0]
                self.assertEqual(report_artifacts(again),report_artifacts(s))
                self.assertEqual(again['duties']['D_report(ORDR1)']['route_due'],12)

    def test_same_recipient_same_version_redispatch_is_a_distinct_actual_delivery(self):
        for id,recipients in [('R-Q15-ack-before-conflict',['C','F','F']),('R-Q15-least-recent',['C','F','C','F'])]:
            case=next(c for c in programs() if c['id']==id)
            for b in (production,conventional):
                with self.subTest(backend=b.__name__,trace=id):
                    s,o,_=replay(case,b,oracle=True)
                    sends=report_artifacts(s)
                    self.assertEqual([x['to'] for x in sends],recipients)
                    self.assertEqual([x['delivery'] for x in sends],list(range(1,len(sends)+1)))
                    self.assertEqual(o.metrics(s)['reports_delivered'],len(recipients))
