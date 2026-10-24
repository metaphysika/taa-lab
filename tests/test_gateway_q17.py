"""Q17 ruling-derived cases; frozen expectations are not modified."""
from dataclasses import replace
from pathlib import Path
import unittest,yaml
from tests import test_gateway_pipeline as fixture
from tests.trace_support import production_backend as core
from tests.trace_support.bundle import world
from comparators.duty_oracle import Oracle
from comparators import commit_oracle
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as conventional

class ScopeDimensionTests(unittest.TestCase):
    def test_inapplicable_dimension_skips_but_unknown_customer_stays_hold(self):
        f=fixture.PipelineTests();f.setUp();f.delivered()
        f.grant['resource_scope']={'template':['refund_denied']};f.put(f.grant['id'],'grant',f.grant)
        self.assertEqual(f.propose()['disposition'],'PERMIT')
        f.grant['resource_scope']={'customer':['customer-one']};f.put(f.grant['id'],'grant',f.grant)
        f.tools[0]=replace(f.tools[0],scope=lambda args,view:{'customer':None});f.pipeline=f.build()
        self.assertEqual(f.propose()['disposition'],'HOLD')

    def test_known_absent_dimension_refuses_instead_of_hold(self):
        f=fixture.PipelineTests();f.setUp();f.delivered()
        f.grant['resource_scope']={'template':['refund_denied']};f.put(f.grant['id'],'grant',f.grant)
        f.tools[0]=replace(f.tools[0],scope=lambda args,view:{'template':None},scope_absent_is_violation=('template',),scope_dimensions=('template',));f.pipeline=f.build()
        r=f.propose();self.assertEqual(r['disposition'],'REFUSE')
        self.assertIn('absent scope value',str(r['checks']))

    def test_external_oracle_and_committed_act_assessment_use_q17_reference(self):
        path=Path(__file__).parent/'regression_scenarios/q17.yaml'
        for t in [t for p in (path,path.with_name('q17_1.yaml')) for t in yaml.safe_load(p.read_text())]:
            with self.subTest(case=t['id']):
                s=core.start(world(),t['setup']);o=Oracle(s);o.reconcile(s)
                p=t['steps'][0]['propose'];r=commit_oracle.evaluate(commit_oracle.snapshot(o,s),p['actor'],p['tool'],p['args'])
                self.assertEqual(r['disposition'],t['steps'][0]['expect']['disposition'])
                if t['steps'][0]['expect']['disposition']=='REFUSE':
                    for name, backend in (('core',core),('reference',reference),('conventional',conventional)):
                        with self.subTest(backend=name):
                            state=backend.start(world(),t['setup'])
                            _, decision=backend.propose(state,p['actor'],p['tool'],p['args'])
                            self.assertEqual(decision['rule'],'AU1')
                            self.assertEqual(decision['failed_stage'],'authority')
                o.proposal(p['actor'],p['tool'],p['args'],s)
                self.assertFalse([d for d in o.board().values() if d['kind']=='report'])
