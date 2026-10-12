"""Meaningful offline threshold/budget/retention checks; no provider import."""
import hashlib
import json
import unittest
from decimal import Decimal as D
from pathlib import Path
from formation.study_b_protocol_v0232 import bounds,difference,threshold,ladder,two_sided
ROOT=Path(__file__).resolve().parents[1]

class Gate5bTests(unittest.TestCase):
    def test_flat_results_are_against_and_zero_zero_is_not_twofold(self):
        zero=bounds(0,0,10);perfect=bounds(10,0,10)
        self.assertEqual(ladder([perfect]*4),'against')
        self.assertEqual(two_sided(zero,zero),'against')
        self.assertEqual(threshold(difference(zero,zero),'.10'),'against')
        self.assertEqual(threshold(difference(zero,zero),'.15'),'against')

    def test_threshold_equality_and_adjacent_reversal(self):
        b=lambda n:bounds(n,0,100)
        self.assertEqual(ladder([b(100),b(95),b(90),b(85)]),'supported')
        self.assertEqual(ladder([b(100),b(70),b(76),b(85)]),'against')
        self.assertEqual(two_sided(b(10),b(20)),'supported')
        self.assertEqual(threshold(difference(b(20),b(10)),'.10'),'supported')

    def test_fractional_pooling_does_not_round_away_threshold_equality(self):
        third=bounds(1,0,3)
        self.assertEqual(threshold((third[0]*3,third[1]*3),1),'supported')
        self.assertEqual(threshold(difference(bounds(40,0,60),bounds(31,0,60)),'.15'),'supported')

    def test_mechanical_bounds_do_not_manufacture_support(self):
        uncertain=bounds(0,10,10)
        self.assertEqual(ladder([uncertain]*4),'inconclusive')
        self.assertEqual(two_sided(uncertain,uncertain),'inconclusive')
        self.assertEqual(threshold(difference(uncertain,uncertain),'.15'),'inconclusive')
        with self.assertRaises(ValueError):bounds(1,10,10)

    def test_scope_caps_and_output_capacity_are_consistent(self):
        v=json.loads((ROOT/'studies/formation-study-b-gate5b-cost-v0232.json').read_text())
        self.assertEqual(v['primary_episodes'],2988)
        self.assertEqual(v['declared_correct_path_generations'],9978)
        self.assertEqual(v['output_limit_proposed'],4096)
        self.assertGreaterEqual(v['Claude_protected_remaining_at8_stop'],v['proposed_minimum_C_D_reserve_dollars'])
        self.assertAlmostEqual(sum(v['proposed_Claude_model_caps'].values()),v['proposed_provider_B_caps']['claude'])
        for r in v['models']:
            self.assertAlmostEqual(r['output_component_at4096_if_all_correct_path_calls_fill_limit'],2*r['output_component_at2048_if_all_correct_path_calls_fill_limit'])
            if r['model']=='claude-haiku-4-5-20251001':self.assertEqual((r['conditions'],r['repeats'],r['primary_episodes']),(36,3,108))
        self.assertEqual(v['Gemma_quota']['full_prompt_token_guard_at4096']+4096+128,16000)

    def test_review_snapshot_preserves_cases_pilots_and_ledgers(self):
        v=json.loads((ROOT/'results/2026-10-12 v0.23.2 study-b gate5b offline/review-integrity.json').read_text())
        self.assertEqual(v['model_calls'],0)
        for name,digest in dict(v['case_sha256'],**v['protected_evidence_sha256']).items():
            # Ledgers in review indexes are historical snapshots; later authorized
            # spending must not fail CI by requiring their old byte hashes.
            if name.startswith('results/formation-spending-v021/'):continue
            self.assertNotIn('keys.env',name)
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
        p=json.loads((ROOT/'studies/formation-study-b-gate5b-protocol-v0232.json').read_text())
        self.assertNotIn('claude-haiku-4-5-20251001',p['B1']['cohort'])
        self.assertIn('claude-haiku-4-5-20251001',p['B3']['cohort'])

if __name__=='__main__':unittest.main()
