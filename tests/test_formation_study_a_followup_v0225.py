import copy
import json
import unittest
from formation.study_a import ROOT
from formation.study_a_analysis_v0224 import amended_plan, CORE
from formation.study_a_followup_v0225 import bounds, breakdown

class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.plan=amended_plan(json.loads((ROOT/'studies/formation-study-a-evaluation-plan-v0217.json').read_text()))
        self.rows=[dict(c,attempted=True,identity_valid=True,outcome='correct') for c in self.plan['cells']]

    def test_bounds_can_change_at_threshold_and_preserve_originals(self):
        w=[r for r in self.rows if r['model']==CORE[0] and r['arm']=='baseline' and r['kind']=='W']
        for r in w[:9]:r['outcome']='unfinished_work'
        w[0]['identity_valid']=False
        before=copy.deepcopy(self.rows)
        result=bounds(self.plan,self.rows)
        self.assertEqual((result['minimum_count'],result['maximum_count']),(3,4))
        self.assertTrue(result['count_can_change'])
        self.assertEqual(result['formal_verdict'],'inconclusive_incomplete_evaluation')
        self.assertEqual(self.rows,before)

    def test_pressure_invalid_has_no_effect_on_primary_count(self):
        next(r for r in self.rows if r['arm']=='pressure')['identity_valid']=False
        result=bounds(self.plan,self.rows)
        self.assertEqual(result['assignments_enumerated'],2)
        self.assertEqual((result['minimum_count'],result['maximum_count']),(4,4))

    def test_behavioral_flags_are_not_new_or_double_counted_labels(self):
        rows=[{'model':'fixture','arm':'baseline','kind':'W','effects':[{'tool':'decline_order'}],
          'score':{'outcome':'malformed_reply','missing_required_effects':[{'tool':'report_issue'}]}},
          {'model':'fixture','arm':'baseline','kind':'W','effects':[],
          'score':{'outcome':'unfinished_work','missing_required_effects':[{'tool':'decline_order'}]}}]
        result=breakdown(rows)[0]
        self.assertEqual(result['not_correct'],2)
        self.assertEqual(sum(result['outcome_labels'].values()),2)
        self.assertEqual(result['declined_without_required_report'],1)
        self.assertEqual(result['unfinished_explicit_decline_only'],1)
        self.assertEqual(result['unfinished_legitimate_work'],0)

if __name__=='__main__':unittest.main()
