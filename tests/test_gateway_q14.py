"""Sol-authored from Claude's Q14 clarification; expectations reviewed by Claude.

Normative-source attribution; this implementation/test delta awaits PR review.
Frozen outcomes are not synthesized from either implementation.
"""
from copy import deepcopy
from pathlib import Path
import json
import unittest
import yaml
from tests.trace_support.bundle import world
from tests.trace_support import production_backend as native
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as sql
from conventional_gateway.world import World
from comparators.business import Backend
from comparators.observed_world import payment_commit_order
from comparators.duty_oracle import Oracle

DUTY='D_resolve(CL7)'
ISSUED=dict(claim='CL7',to='K2',template='refund_issued',amount=250,cites='REF1')
DENIED=dict(claim='CL7',to='K2',template='refund_denied',amount=150,basis='DEL2')
FAULTS=('after_validate','after_stage','during_effect_commit','during_token_consumption',
        'during_duty_update','during_receipt_write','during_revision_advance')


def setup():
    return deepcopy(yaml.safe_load((Path(__file__).parent/'regression_scenarios/q14.yaml').read_text())[0]['setup'])


def act(backend,state,args,fault=None):
    state,p=backend.propose(state,'A','message_party',args)
    return backend.execute(state,'A',p.get('execution_intent',p.get('token')),fault)


class Q14Tests(unittest.TestCase):
    def test_sql_projection_rolls_back_at_all_seven_real_faults_and_is_cleared(self):
        for point in FAULTS:
            with self.subTest(fault=point):
                h=World(world(),setup());h.clock(1);h.reconcile()
                p=h.propose('A','message_party',ISSUED);self.assertEqual(h.execute('A',p['token'])['execute_result'],'committed')
                p=h.propose('A','message_party',DENIED);before=h.store.snapshot()
                self.assertEqual(h.execute('A',p['token'],point)['execute_result'],'failed')
                self.assertEqual(h.store.snapshot(),before)
                self.assertIsNone(h.store._pending_receipt)
                self.assertEqual(h.store.current('duties')[DUTY]['coverage'],250)
                self.assertEqual(h.store.current('duties')[DUTY]['resolution'],'unresolved')
                self.assertEqual(h.store.events()[-1]['payload']['reason'],point)

    def test_native_projection_rolls_back_at_all_seven_real_faults(self):
        state=native.start(world(),setup());state,_=act(native,state,ISSUED)
        for point in FAULTS:
            with self.subTest(fault=point):
                c=native._context(state)
                p=c.runtime.propose(c.sessions['A'],dict(tool='message_party',arguments=DENIED))
                before=c.store.snapshot()
                self.assertEqual(c.runtime.execute(c.sessions['A'],p['token'],fault=point)['execute_result'],'failed')
                self.assertEqual(c.store.snapshot(),before)
                self.assertEqual(c.engine.ledger(c.store.snapshot())[DUTY]['content']['coverage'],250)
                self.assertEqual(c.log.events()[-1]['type'],'execution_rolled_back')
                self.assertEqual(c.log.events()[-1]['payload']['fault'],point)

    def test_real_business_partial_notice_without_receipt_never_discharges(self):
        for arm in ('floor','static'):
            with self.subTest(arm=arm):
                b=Backend(arm);s=b.start(world(),setup());s,_=act(b,s,ISSUED)
                s,r=act(b,s,DENIED,'during_receipt_write')
                self.assertEqual(r['execute_result'],'failed')
                self.assertEqual(len(s['notices']),2);self.assertEqual(len(s['receipts']),1)
                # A fresh oracle ignores all native resolution/ownership data.
                o=Oracle(s);o.clock(s['step']);o.reconcile(s)
                self.assertEqual(o.board()[DUTY]['coverage'],250)
                self.assertEqual(o.board()[DUTY]['resolution'],'unresolved')

    def test_committed_malformed_portion_has_receipt_but_covers_nothing(self):
        for arm in ('floor','static'):
            with self.subTest(arm=arm):
                b=Backend(arm);s=b.start(world(),setup())
                s,r=act(b,s,dict(ISSUED,amount=100,portion={'from':False,'to':100}))
                self.assertEqual(r['execute_result'],'committed');self.assertEqual(len(s['receipts']),1)
                o=Oracle(s);o.clock(s['step']);o.reconcile(s)
                self.assertEqual(o.board()[DUTY]['coverage'],0)
                self.assertEqual(o.board()[DUTY]['resolution'],'unresolved')

    def test_proposal_alone_contributes_nothing(self):
        b=sql;s=b.start(world(),setup());s,p=b.propose(s,'A','message_party',ISSUED)
        self.assertEqual(p['disposition'],'PERMIT');self.assertFalse(s['receipts']);self.assertFalse(s['notices'])
        o=Oracle(s);o.clock(s['step']);o.reconcile(s)
        self.assertEqual(o.board()[DUTY]['coverage'],0)

    def test_business_first_commit_sequence_survives_correction_and_sorted_serialization(self):
        b=Backend('floor');config=setup();config['records'].pop('REF1');s=b.start(world(),config)
        for step,rid,amount in [(2,'REFZ',100),(3,'REFA',150)]:
            event=dict(type='record_insert',record=rid,by='payment_processor',fields=dict(kind='chargeback',claim='CL7',claimant='K2',order='ORD2',amount=amount,currency='USD',to='K2_card',settled=True))
            s=b.enter_step(s,step,[event])[0]
        s=b.enter_step(s,4,[dict(type='record_correction',record='REFZ',by='payment_processor',new={'settled':False})])[0]
        serialized=json.loads(json.dumps(s,sort_keys=True))
        self.assertEqual(list(serialized['records']).index('REFA')<list(serialized['records']).index('REFZ'),True)
        self.assertEqual(payment_commit_order(serialized),['REFZ','REFA'])
        self.assertEqual([r['commit_sequence'] for r in serialized['records']['REFZ']],[1,3])
        self.assertEqual(serialized['records']['REFA'][0]['commit_sequence'],2)

    def test_business_missing_write_provenance_is_reported_not_inferred(self):
        b=Backend('floor');s=b.start(world(),setup())
        malformed=deepcopy(s)
        del malformed['records']['REF1'][0]['commit_sequence']
        with self.assertRaisesRegex(ValueError,'write provenance'):
            payment_commit_order(malformed)
        self.assertIn('commit_sequence',s['records']['REF1'][0])

    def test_corrected_coverage_reopens_at_due_boundary_and_preserves_original_proof(self):
        for name,b in [('reference',reference),('production',native),('conventional',sql)]:
            for supported in (200,300):
                for offset in (-1,0,1):
                    with self.subTest(backend=name,supported=supported,due_offset=offset):
                        state=b.start(world(),setup())
                        state,_=act(b,state,ISSUED)
                        state,_=act(b,state,DENIED)
                        old=deepcopy(state['duties'][DUTY]['discharge_coverage'])
                        notices=deepcopy(state['notices'])
                        self.assertEqual(state['duties'][DUTY]['resolution'],'discharged')
                        due=state['duties'][DUTY]['due']
                        event=dict(type='record_correction',record='DEL2',by='carrier',new={'failed_value':supported})
                        state=b.enter_step(state,due+offset,[event])[0]
                        duty=state['duties'][DUTY]
                        self.assertEqual(duty['coverage'],350)
                        self.assertEqual(duty['resolution'],'unresolved')
                        self.assertEqual(duty['overdue'],offset>=0)
                        self.assertEqual(duty['discharge_coverage'],old)
                        self.assertNotEqual(duty['coverage_proof'],old)
                        self.assertEqual(state['notices'],notices)
                        self.assertEqual(state['records']['DEL2'][0]['fields']['failed_value'],250)
                        state,decision=b.propose(state,'A','close_case',{'case':'CL7'})
                        self.assertEqual(decision['disposition'],'REFUSE')

    def test_current_proof_records_an_invalidated_cited_payment_and_its_new_version(self):
        for name,b in [('reference',reference),('production',native),('conventional',sql)]:
            with self.subTest(backend=name):
                state=b.start(world(),setup())
                state,_=act(b,state,ISSUED);state,_=act(b,state,DENIED)
                original=deepcopy(state['duties'][DUTY]['discharge_coverage'])
                event=dict(type='record_correction',record='REF1',by='payment_processor',new={'settled':False})
                state=b.enter_step(state,2,[event])[0]
                duty=state['duties'][DUTY];proof=duty['coverage_proof']
                self.assertEqual(duty['resolution'],'unresolved')
                self.assertEqual(duty['coverage'],150)
                self.assertEqual(duty['discharge_coverage'],original)
                if 'versions' in proof:
                    self.assertEqual(proof['versions']['REF1'],2)
                else:
                    self.assertIn('records',proof)
                    versions={r['record_id'].split(':')[-1]:r['record_version'] for r in proof['records']}
                    self.assertEqual(versions['REF1'],2)
                self.assertEqual([rid.split(':')[-1] for rid in proof['financial_order']],['REF1'])

    def test_invalid_non_null_allocation_values_block_without_normalizing_records(self):
        for name,b in [('reference',reference),('production',native),('conventional',sql)]:
            for value in (False,0,[],{}):
                with self.subTest(backend=name,value=value):
                    state=b.start(world(),setup())
                    event=dict(type='record_correction',record='REF1',by='payment_processor',new={'allocated_to':value})
                    state=b.enter_step(state,2,[event])[0]
                    self.assertEqual(state['records']['REF1'][-1]['fields']['allocated_to'],value)
                    self.assertEqual(state['duties']['D_refund(CL7,250)']['resolution'],'unresolved')
