"""Explicit local retained-evidence check; fails if evidence is unavailable."""
import unittest
from exploratory.measurement_v02456.policy import protocol_bounds

class RetainedReplayTests(unittest.TestCase):
    def test_attempt4_replies_offline(self):
        import copy
        import json
        import os
        from pathlib import Path
        from exploratory.measurement_v02456.policy import replay
        root=Path(os.environ.get('TAA_ATTEMPT4', r'C:\Users\lahn0\T3\briefs\step4_attempt4\extracted\results\attempt-4'))
        self.assertTrue(root.is_dir(), 'retained evidence required for this explicit local test; set TAA_ATTEMPT4')
        assets=Path(__file__).resolve().parents[2]/'studies/formation-study-d-gemma-stages-v02429/transfer-cases.json'
        cases={q['case']['id']:q['case'] for q in json.loads(assets.read_text())}
        count=0
        totals={m:[0,0,0] for m in ("first","malformed")}
        for path in root.glob('*-*-*.json'):
            old=json.loads(path.read_text()); saved=copy.deepcopy(old)
            for mode in ('first','malformed'):
                row=replay(cases[old['case_id']],old['packets'],mode)
                self.assertIn(row['terminal_status'],('agent_stop','fixture_exhausted','step_limit','malformed_reply','malformed_action'))
                self.assertEqual(old,saved)
                totals[mode][0]+=not row['format_closed_valid']
                totals[mode][1]+=row['score']['executed_violations']['servile']>0
                totals[mode][2]+=protocol_bounds(row,cases[old['case_id']]['kind'])==(0,1)
            count+=1
        self.assertEqual(count,132)

        self.assertEqual(totals["malformed"], [13,18,13])
        self.assertEqual(totals["first"], [13,20,13])


if __name__ == "__main__": unittest.main()
