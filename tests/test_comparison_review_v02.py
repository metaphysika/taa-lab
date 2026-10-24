"""Owner-relayed Astra/Claude comparison blockers; no new comparison outcomes."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import yaml
from conventional_gateway import backend as sql
from taa_gateway_reference import refunds as reference
from tests.trace_support import production_backend as core,reference_runner as runner
from tests.trace_support.bundle import world
from worlds.refunds.token_bindings import prepare
from comparators.cross_arm import Recorded
from agents.refunds import CONTROLLERS
from comparators.tracegrant import TraceGrant,contract
from comparators.world import World
from comparators.business import Backend
from comparators import retained_actual
from comparators.harness import admit_active,SIMULATOR_KEY

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=ROOT/'tests/regression_scenarios/comparison_review_v02.yaml'
PROBE=ROOT/'tests/regression_scenarios/tracegrant_injected_drift_v02.json'


def cases():
    return [dict(id=t['id'],trace=t,parameters={},source=str(SCENARIOS)) for t in yaml.safe_load(SCENARIOS.read_text())]


def drift_probe():
    p=json.loads(PROBE.read_text());service=World(world(),p['setup']);gateway=TraceGrant(contract(p['contract']),certificate_key=SIMULATOR_KEY)
    admit_active(gateway,service)
    cert=gateway.decide('A','issue_refund',p['refund'])['certificate']
    assert gateway.dispatch(cert,'A','issue_refund',p['refund'],service)['dispatch']=='committed'
    cert=gateway.decide('A','message_party',p['notice'])['certificate'];before=service.snapshot();receipts=len(gateway.receipts)
    seen=[];original=service.apply
    def drift(tool,args,actor):
        actual=dict(args,**p['injection']);original(tool,actual,actor)
        seen.append(deepcopy(service.notices[-1]))
    with patch.object(service,'apply',side_effect=drift):
        result=gateway.dispatch(cert,'A','message_party',p['notice'],service)
    return dict(id=p['id'],label=p['label'],dispatch=result['dispatch'],result=result,
        new_receipts=len(gateway.receipts)-receipts,obligation_verified=gateway.states['notice']=='VERIFIED',
        injection_observed_customer=seen[-1]['customer'] if seen else None,
        world_rolled_back=service.snapshot()==before,expect=p['expect'])


class ComparisonReviewTests(unittest.TestCase):
    def test_parent_scope_refuses_on_reference_core_and_conventional(self):
        case=cases()[0]
        for name,backend in [('reference',reference),('core',core),('conventional',sql)]:
            with self.subTest(backend=name):
                program,bindings=prepare(case)
                rows=runner.run(program,backend=backend,token_bindings=bindings)
                self.assertFalse([r for r in rows if r['status']!='pass'])

    def test_same_duty_is_one_candidate_despite_two_actual_C_deliveries(self):
        case=cases()[1]
        for name,backend in [('core',core),('conventional',sql)]:
            with self.subTest(backend=name):
                program,bindings=prepare(case);observed=Recorded(backend,CONTROLLERS['correct'](),program)
                rows=runner.run(program,backend=observed,token_bindings=bindings)
                self.assertFalse([r for r in rows if r['status']!='pass'])
                physical=[r for r in observed.oracle.delivered if r['id']=='RPT1' and r['version']==1]
                self.assertEqual([r['to'] for r in physical],['C','F','C'])
                self.assertEqual(observed.oracle.board()['D_report(ORDR1)']['resolution'],'discharged')
                self.assertEqual(observed.oracle.metrics(observed.state)['reports_acknowledged'],1)

    def test_injected_drift_cannot_verify_the_notice_or_produce_a_receipt(self):
        probe=drift_probe()
        for key,expected in probe['expect'].items():self.assertEqual(probe[key],expected,key)
        self.assertTrue(probe['world_rolled_back'])

    def test_receiptless_closure_and_transfer_writes_are_explicitly_not_scored(self):
        for arm in ('floor','static'):
            for tool,args in [('close_case',{'case':'CL1'}),('offer_duty',{'duty':'D_resolve(CL1)','to':'F'}),('accept_duty',{'duty':'D_resolve(CL1)'})]:
                for boundary in ('during_effect_commit','during_receipt_write'):
                    with self.subTest(arm=arm,tool=tool,boundary=boundary):
                        b=Recorded(Backend(arm),CONTROLLERS['correct'](),{'trace':{'steps':[{'proposal_origin':['fault',0],'propose':{}}]}})
                        s=b.start(world(),{'records':{'RET1':{'received':True}}});s=b.enter_step(s,1)[0]
                        s,p=b.propose(s,'A',tool,args)
                        after,result=b.execute(s,'A',p['execution_intent'],boundary)
                        self.assertEqual(result['execute_result'],'failed')
                        self.assertEqual(after['receipts'],[])
                        row=b.calls[-1];self.assertFalse(row['committed'])
                        self.assertIn('not scored',row['receiptless_operation']['protocol_operation_scoring'])
                        self.assertIsNotNone(row['receiptless_operation']['reference_policy_assessment'])
                        self.assertFalse(b.oracle.closures);self.assertFalse(b.oracle.invalid_transfers)
                        if tool=='close_case':self.assertTrue(after['cases']['CL1'])
                        else:self.assertEqual(after['business_operations'][-1]['tool'],tool)
                        self.assertTrue(b.actual_transitions[-1]['actual_channels'])

    def test_retained_actual_changes_do_not_collapse_absence_false_or_rewrites(self):
        before={'step':1,'log':[],'records':{'R':[{'fact':True}]},'cases':{}}
        after=deepcopy(before);after['records']['R'][0]['fact']=False;after['cases']['C']=False
        delta=retained_actual.transition(before,after,'probe',{})
        self.assertEqual(delta['actual_channels']['records']['entries']['R']['before']['value'],[{'fact':True}])
        self.assertEqual(delta['actual_channels']['records']['entries']['R']['after']['value'],[{'fact':False}])
        self.assertEqual(delta['actual_channels']['cases']['entries']['C']['before'],{'present':False})
        self.assertEqual(delta['actual_channels']['cases']['entries']['C']['after'],{'present':True,'value':False})

    def test_conventional_template_restrictions_cover_parent_and_leaf(self):
        for gid in ('G0','G1'):
            with self.subTest(grant=gid):
                setup={'records':{'RET1':{'received':True},'REF1':dict(kind='refund',claim='CL1',claimant='K1',order='ORD1',amount=120,currency='USD',settled=True,to='K1_card')},
                    'grants':{gid:{'scope':{'customers':['K1','K2'],'template':['refund_denied']}}}}
                args=dict(claim='CL1',to='K1',amount=120,template='refund_issued',cites='REF1')
                for b in (reference,sql):
                    state=b.start(world(),setup);_,result=b.propose(state,'A','message_party',args)
                    self.assertEqual(result['disposition'],'REFUSE')

    def test_parent_actions_must_authorize_delegation_and_root_standing(self):
        args=dict(claim='CL1',amount=120,to='K1_card',basis='return')
        for actions,expected in [(['grant_refund_authority'],'PERMIT'),([], 'REFUSE'),(['grant_refund_authority','issue_refund'],'REFUSE')]:
            for name,b in [('reference',reference),('core',core),('conventional',sql)]:
                with self.subTest(actions=actions,backend=name):
                    state=b.start(world(),{'records':{'RET1':{'received':True}},'grants':{'G0':{'actions':actions}}})
                    _,result=b.propose(state,'A','issue_refund',args)
                    self.assertEqual(result['disposition'],expected)

    def test_ack_dedup_keeps_delivery_version_recipient_incident_and_eligibility_checks(self):
        case=deepcopy(cases()[1]);case['trace']['steps']=case['trace']['steps'][:-1]
        program,bindings=prepare(case);b=Recorded(core,CONTROLLERS['correct'](),program)
        runner.run(program,backend=b,token_bindings=bindings)
        base=deepcopy(b.oracle);base.clock(12)
        event=dict(type='acknowledgment',report='RPT1',version=1,**{'from':'C'})
        # Do not re-import delivery artifacts when deliberately omitting them.
        for defect in ('no_delivery','wrong_version','wrong_recipient','wrong_incidents','ineligible','two_duties'):
            with self.subTest(defect=defect):
                o=deepcopy(base);ev=deepcopy(event)
                if defect=='no_delivery':o.delivered=[]
                if defect=='wrong_version':ev['version']=2
                if defect=='wrong_recipient':ev['from']='R'
                if defect=='wrong_incidents':
                    for a in o.delivered:a['incidents']=[]
                if defect=='two_duties':
                    d=deepcopy(o.s['duties']['D_report(ORDR1)']);d['id']='D_duplicate';d['report_id']='RPT2';o.s['duties'][d['id']]=d
                with patch.object(o,'sync'),patch('comparators.duty_oracle.relation.report_choices',return_value=[] if defect=='ineligible' else ['C','F']):
                    o.external(ev,b.state)
                self.assertEqual(o.board()['D_report(ORDR1)']['resolution'],'unresolved')
