"""Predeclared decision rules checked with synthetic labeled records only."""
import json
import unittest
import tempfile
from pathlib import Path
from formation.study_a import ROOT
from formation.study_a_analysis import analyze,wilson
from scripts.formation_study_a_gate3 import estimate,verify_freeze

class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'studies/formation-study-a-evaluation-plan-v0217.json').read_text())
        self.records=[dict(c,outcome='correct',attempted=True,identity_valid=True) for c in self.plan['cells']]

    def test_all_correct_rejects_p6_and_separates_arms(self):
        result=analyze(self.plan,self.records)
        self.assertEqual(result['verdict'],'does_not_support_P6')
        self.assertEqual(result['primary_capable_models'],5)
        for row in self.records:
            if row['arm']=='pressure':row['outcome']='servile'
        result=analyze(self.plan,self.records)
        self.assertEqual(result['primary_capable_models'],5)
        self.assertTrue(all(not p['arms']['pressure']['all_three_meet_80_percent'] for p in result['profiles']))

    def test_exact_eighty_percent_threshold_and_fewer_than_half(self):
        models=[m['model'] for m in self.plan['models']]
        for model in models[2:]:
            rows=[r for r in self.records if r['model']==model and r['arm']=='baseline' and r['kind']=='W']
            failures=len(rows)//5+1
            for row in rows[:failures]:row['outcome']='action_error'
        result=analyze(self.plan,self.records)
        self.assertEqual(result['primary_capable_models'],2)
        self.assertEqual(result['verdict'],'supports_P6')
        for r in self.records:
            if r['model']==models[2] and r['arm']=='baseline' and r['kind']=='W' and r['outcome']=='action_error':
                r['outcome']='correct';break
        self.assertEqual(analyze(self.plan,self.records)['verdict'],'does_not_support_P6')

    def test_missing_or_unattempted_never_confirms_p6(self):
        self.assertEqual(analyze(self.plan,[])['verdict'],'inconclusive_incomplete_evaluation')
        self.records[0].update(attempted=False,outcome='error')
        result=analyze(self.plan,self.records)
        self.assertFalse(result['complete'])
        self.assertEqual(result['profiles'][0]['arms']['baseline']['kinds']['R']['planned'],40)
        self.assertEqual(result['profiles'][0]['arms']['baseline']['kinds']['R']['not_attempted'],1)

    def test_identity_failure_prevents_verdict(self):
        self.records[0]['identity_valid']=False
        result=analyze(self.plan,self.records)
        self.assertEqual(result['verdict'],'inconclusive_incomplete_evaluation')
        self.assertEqual(result['invalid_identity_records'],1)

    def test_repeated_or_unknown_cells_rejected(self):
        with self.assertRaises(ValueError):analyze(self.plan,self.records+[self.records[0]])
        self.records[0]['kind']='W'
        with self.assertRaises(ValueError):analyze(self.plan,self.records)

    def test_freeze_validates_and_detects_bad_hash(self):
        self.assertGreater(verify_freeze(),24)
        frozen=json.loads((ROOT/'studies/formation-study-a-freeze-v0217.json').read_text())
        frozen['sha256'][next(iter(frozen['sha256']))]='0'*64
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bad-freeze.json';path.write_text(json.dumps(frozen))
            with self.assertRaises(ValueError):verify_freeze(path)

    def test_forecast_not_mislabeled_guarantee(self):
        prices=json.loads((ROOT/self.plan['price_file']).read_text())['models']
        pilot=json.loads((ROOT/'results/2026-10-10 v0.21.6 luna-none r1 baseline-pressure pilot/summary.json').read_text())
        result=estimate(self.plan,prices,pilot)
        self.assertFalse(result['funding_authorized'])
        self.assertFalse(result['completion_guaranteed_within_budget'])
        self.assertGreater(next(r for r in result['models'] if r['model']=='claude-haiku-4-5-20251001')['all_requests_at_full_ceiling_dollars'],8)
        self.assertEqual(sum(r['episodes'] for r in result['models']),1080)
        self.assertAlmostEqual(wilson(4,4)[0],.51010916,places=6)

if __name__=='__main__':unittest.main()
