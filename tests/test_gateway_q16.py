"""Q16/H1 source-derived capacity and supersession acceptance; no expected model outputs."""
from copy import deepcopy
from itertools import groupby
from pathlib import Path
import unittest
import yaml
from tests.trace_support import reference_runner as runner, production_backend as production, regressions
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as conventional
from tests.trace_support.bundle import world
from worlds.refunds.token_bindings import prepare
from comparators.duty_oracle import Oracle
from comparators.business import Backend as BusinessBackend


def programs():
    path=Path(__file__).parent/'regression_scenarios/q16.yaml'
    return [dict(id=t['id'],trace=t,parameters={},source=str(path)) for t in yaml.safe_load(path.read_text())]


def replay_oracle(case,b):
    program,bindings=prepare(case)
    s=b.start(world(),program['trace'].get('setup',{}),defer_first_step=True)
    o=Oracle(s)
    for step,group in groupby(program['trace']['steps'],key=lambda entry:entry['step']):
        entries=list(group)
        for at in range(s['step']+1,step):
            s=b.enter_step(s,at)[0];o.clock(at);o.reconcile(s)
        o.clock(step)
        events=[ev for entry in entries for ev in entry.get('events',[])]
        def observe(index,before,after,result):
            o.external(events[index],after)
        s=b.enter_step(s,step,events,event_observer=observe)[0];o.reconcile(s)
        def compare(entry):
            for expected in entry.get('expect',{}).get('duties',[]):
                assert runner.contains(o.board()[expected['id']],expected),(case['id'],expected,o.board()[expected['id']])
        for entry in entries:
            if 'propose' not in entry and 'execute' not in entry:compare(entry)
        proposals={}
        for entry in entries:
            if 'propose' not in entry:continue
            p=entry['propose'];s,result=b.propose(s,p['actor'],p['tool'],p['args'])
            bindings.record(entry,result.get('execution_intent',result.get('token')))
            proposals[bindings.last]=p
            o.proposal(p['actor'],p['tool'],p['args'],s);o.reconcile(s);compare(entry)
        for entry in entries:
            if 'execute' not in entry:continue
            x=entry['execute'];token=bindings.execution(x)
            s,result=b.execute(s,x['actor'],token,x.get('inject_fault'))
            if result.get('execute_result')=='committed':
                p=proposals.get(token)
                if p is None:
                    raise AssertionError('test scenario execution lacks its originating proposal')
                before=deepcopy(s);o.committed(x['actor'],p['tool'],p['args'],s)
                assert s==before,'external oracle changed actual records'
            else:o.reconcile(s)
            compare(entry)
    return s,o


class Q16Tests(unittest.TestCase):
    def test_all_source_scenarios_through_common_runner_and_state_audits(self):
        for backend in (reference,production,conventional):
            for case in programs():
                with self.subTest(backend=backend.__name__,trace=case['id']):
                    program,bindings=prepare(case)
                    rows=runner.run(program,backend=backend,token_bindings=bindings)
                    self.assertFalse([row for row in rows if row['status']!='pass'])

    def test_common_oracle_rederives_capacity_from_actual_inputs_on_both_hosts(self):
        for name,backend in [('production',production),('conventional',conventional),
                             ('floor',BusinessBackend('floor')),('static',BusinessBackend('static'))]:
            for case in programs():
                with self.subTest(backend=name,trace=case['id']):replay_oracle(case,backend)

    def test_supersessions_preserve_both_historical_sources_and_explicit_lineage(self):
        old=regressions.cases(include_superseded=True)
        active=regressions.cases()
        changes={c['historical_id']:c['id'] for c in active if 'historical_id' in c}
        self.assertEqual(changes,{'R-Q11-authorized-standing':'R-Q16-authorized-without-capacity',
                                 'R-Q12-parallel-L':'R-Q16-parallel-L'})
        self.assertEqual(len(old),32);self.assertEqual(len(active),32)
        self.assertTrue(set(changes)<=set(c['id'] for c in old))
        self.assertFalse(set(changes)&set(c['id'] for c in active))
        for c in old:
            if c['id'] not in changes:
                self.assertEqual(next(a for a in active if a['id']==c['id']),c)
