"""Post-results descriptions preserve scorer labels and matched denominators."""
import unittest
from formation import study_c_evaluation_v0242 as c
from formation.study_c_gemini_comparison_v0243 import comparison, readable, counts


class GeminiComparisonTests(unittest.TestCase):
    def test_mechanical_known_acts_do_not_become_servile_labels(self):
        rows=[{'score':dict(mechanical_outcome='action_error',substance_outcome='action_error',executed_violations={'servile':2})}]
        result=counts(rows,5)
        self.assertEqual(result['original_servile_labels'],0)
        self.assertEqual(result['observed_episodes_with_executed_servile_act'],1)
        self.assertEqual(result['scorer_executed_servile_count'],2)
        self.assertEqual(result['valid'],0);self.assertIsNone(result['original_servile_rate_valid'])

    def test_completed_sources_all_groups_and_original_B_rate(self):
        f=c.read(c.ROOT/c.FREEZE);am=c.read(c.ROOT/c.NATIVE_AMENDMENT);f=c.runtime_freeze(c.ROOT,f,am)
        cases={x['id']:x for x in c.read(c.ROOT/f['probe_files'])};cells=c.read(c.ROOT/f['schedule'])['cells']
        result=comparison(c.ROOT,f,cases,cells)
        self.assertEqual(result['C_all_W']['planned'],270)
        self.assertEqual(result['C_all_W']['original_servile_labels'],22)
        self.assertEqual(result['C_all_W']['observed_episodes_with_executed_servile_act'],24)
        self.assertEqual(result['C_all_W']['scorer_executed_servile_count'],47)
        self.assertEqual(result['B_all_W']['original_servile_labels'],11)
        self.assertEqual(result['B_all_W']['planned'],240)
        self.assertEqual(result['B_all_W']['scorer_executed_servile_count'],22)
        self.assertEqual(result['B_W_exact_source_cases_same_pressure']['planned'],90)
        self.assertEqual(result['C_shared_zero_W']['planned'],45)
        groups=result['by_history_length_theme_rung'];self.assertEqual(len(groups),54)
        self.assertEqual(sum(x['planned'] for x in groups),270)
        self.assertEqual(sum(x['original_servile_labels'] for x in groups),22)
        self.assertEqual(sum(x['scorer_executed_servile_count'] for x in groups),47)
        self.assertTrue(any(x['original_servile_labels']==0 for x in groups))
        self.assertEqual(len(result['items']),24)
        self.assertIn('not an established cause',readable(result))


if __name__=='__main__':unittest.main()
