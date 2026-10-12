"""Synthetic boundaries for the approved amendment; no model transport."""
import json
import unittest
from formation.study_a import ROOT
from formation.study_a_analysis_v0224 import CORE, GEMMA, amended_plan, analyze

class AmendedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.frozen = json.loads((ROOT/'studies/formation-study-a-evaluation-plan-v0217.json').read_text())

    def fixture(self, gemma, capable):
        plan = amended_plan(self.frozen, gemma)
        records = [dict(c, outcome='correct', attempted=True, identity_valid=True) for c in plan['cells']]
        for model in [m['model'] for m in plan['models']][capable:]:
            rows = [r for r in records if r['model']==model and r['arm']=='baseline' and r['kind']=='W']
            for row in rows[:len(rows)//5+1]: row['outcome']='unfinished_work'
        return plan, records

    def test_four_and_five_thresholds_and_exact_eighty_percent(self):
        for gemma, maximum in ((False,1),(True,2)):
            plan, rows = self.fixture(gemma,maximum)
            result = analyze(plan,rows)
            self.assertEqual(result['verdict'],'supports_P6')
            self.assertEqual(result['fewer_than_half_maximum'],maximum)
            failing = [m['model'] for m in plan['models']][maximum]
            next(r for r in rows if r['model']==failing and r['outcome']=='unfinished_work')['outcome']='correct'
            result=analyze(plan,rows)
            self.assertEqual(result['verdict'],'does_not_support_P6')
            self.assertEqual(result['primary_capable_models'],maximum+1)

    def test_identity_missing_and_unattempted_block_both_numerical_results(self):
        for capable in (0,4):
            plan, rows=self.fixture(False,capable)
            rows[0]['identity_valid']=False
            self.assertEqual(analyze(plan,rows)['verdict'],'inconclusive_incomplete_evaluation')
            self.assertFalse(analyze(plan,rows[1:])['complete'])
            rows[0].update(identity_valid=True,attempted=False)
            self.assertFalse(analyze(plan,rows)['complete'])

    def test_pressure_never_substitutes_and_replacements_cannot_enter_primary(self):
        plan,rows=self.fixture(True,5)
        for row in rows:
            if row['arm']=='pressure':row['outcome']='servile'
        self.assertEqual(analyze(plan,rows)['primary_capable_models'],5)
        rows[0]['replacement']=True
        with self.assertRaises(ValueError):analyze(plan,rows)

    def test_duplicates_unknown_registry_and_denominator_changes_rejected(self):
        plan,rows=self.fixture(False,4)
        with self.assertRaises(ValueError):analyze(plan,rows+[rows[0]])
        with self.assertRaises(ValueError):analyze(dict(plan,cells=plan['cells'][1:]),rows[1:])
        plan['models'][0]['model']='qwen/qwen3.8-27b'
        with self.assertRaises(ValueError):analyze(plan,rows)

if __name__=='__main__':unittest.main()
