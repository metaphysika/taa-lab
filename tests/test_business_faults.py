"""Claude PR31 ruling: observe non-atomic writes; never waive audit failures."""
from copy import deepcopy
import unittest
from comparators.business import Backend
from comparators.business_faults import FaultAdapter,NOT_APPLICABLE,NotApplicableByDesign
from tests.trace_support.bundle import world
from tests.trace_support.state_observations import Observer


class BusinessFaultTests(unittest.TestCase):
    def proposal(self,arm):
        b=Backend(arm);s=b.start(world(),{'records':{'RET1':{'received':True}}})
        s,p=b.propose(s,'A','issue_refund',dict(claim='CL1',amount=120,to='K1_card',basis='return'))
        return b,s,p['execution_intent']

    def audit(self,before,after,result):
        return Observer(before).audit('fault',before,after,result,agent=True,execute={'actor':'A','token':next(iter(before['intents']))})

    def test_pre_effect_failure_has_no_writes_or_receipt(self):
        for arm in ('floor','static'):
            b,s,t=self.proposal(arm);after,r=b.execute(s,'A',t,'after_validate')
            self.assertEqual(after,s)
            self.assertEqual(r['execute_result'],'failed')
            self.assertFalse([x for x in self.audit(s,after,r) if x['status']!='pass'])

    def test_effect_write_survives_failure_and_common_audit_exposes_missing_receipt(self):
        for arm in ('floor','static'):
            b,s,t=self.proposal(arm);after,r=b.execute(s,'A',t,'during_effect_commit')
            self.assertEqual(after['records']['REF1'][-1]['fields']['amount'],120)
            self.assertEqual(after['receipts'],s['receipts'])
            self.assertEqual(after['business_operations'],s['business_operations'])
            bad=[x for x in self.audit(s,after,r) if x['status']!='pass']
            self.assertEqual([x['assertion'] for x in bad],['fault.record_effects_match_receipts'])
            self.assertNotIn('REF1',s['records'])

    def test_before_receipt_keeps_effect_and_business_operation_without_rollback(self):
        for arm in ('floor','static'):
            b,s,t=self.proposal(arm);after,r=b.execute(s,'A',t,'during_receipt_write')
            self.assertIn('REF1',after['records']);self.assertFalse(after['receipts'])
            self.assertEqual(len(after['business_operations']),len(s['business_operations'])+1)
            self.assertEqual(after['log'],s['log'])
            self.assertEqual([x['assertion'] for x in self.audit(s,after,r) if x['status']!='pass'],['fault.record_effects_match_receipts'])

    def test_failure_before_log_keeps_actual_receipt_and_effect(self):
        for arm in ('floor','static'):
            b,s,t=self.proposal(arm);after,r=b.execute(s,'A',t,'before_log_write')
            self.assertIn('REF1',after['records']);self.assertEqual(len(after['receipts']),1)
            self.assertEqual(after['log'],s['log']);self.assertEqual(r['execute_result'],'failed')
            self.assertFalse([x for x in self.audit(s,after,r) if x['status']!='pass'])

    def test_absent_boundaries_are_not_executed_and_have_specific_reasons(self):
        self.assertEqual(set(NOT_APPLICABLE),{'after_stage','during_token_consumption','during_duty_update','during_revision_advance'})
        for arm in ('floor','static'):
            for point,reason in NOT_APPLICABLE.items():
                b,s,t=self.proposal(arm);prior=deepcopy(s)
                with self.assertRaisesRegex(NotApplicableByDesign,reason.split(':')[0]):b.execute(s,'A',t,point)
                self.assertEqual(s,prior)

    def test_unknown_boundary_is_rejected_without_mutation(self):
        with self.assertRaises(ValueError):FaultAdapter('imaginary_boundary')

    def test_plain_duty_operation_fault_occurs_after_its_actual_business_write(self):
        from tests.trace_support.state_observations import executed
        for arm in ('floor','static'):
            b=Backend(arm);s=b.start(world())
            s,p=b.propose(s,'A','offer_duty',dict(duty='D_resolve(CL1)',to='F'))
            after,r=b.execute(s,'A',p['execution_intent'],'during_effect_commit')
            self.assertEqual(len(after['business_operations']),len(s['business_operations'])+1)
            self.assertEqual(after['business_operations'][-1]['tool'],'offer_duty')
            self.assertFalse(after['receipts'])
            self.assertTrue(executed(s,after))
