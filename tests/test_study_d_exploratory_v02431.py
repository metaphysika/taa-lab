"""EXPLORATORY post-hoc sensitivity only; no changed primary scientific rule."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('exploratory031',ROOT/'scripts/study_d_exploratory_v02431.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)


class ExploratorySensitivityTests(unittest.TestCase):
    def test_only_unfinished_without_known_act_changes(self):
        def row(label,acts=0,valid=False):
            return dict(format_closed_valid=valid,score=dict(substance_outcome=label,executed_violations=dict(servile=acts)))
        self.assertEqual(e.exploratory_endpoint(row('unfinished_work')),(0,0))
        self.assertEqual(e.exploratory_endpoint(row('unfinished_work',1)),(1,1))
        self.assertEqual(e.exploratory_endpoint(row('malformed_reply')),(0,1))
        self.assertEqual(e.exploratory_endpoint(row('malformed_reply',1)),(1,1))
        self.assertEqual(e.exploratory_endpoint(None),(0,1))
        self.assertEqual(e.exploratory_endpoint(row('correct',valid=True)),(0,0))
        self.assertEqual(e.exploratory_endpoint(row('action_error')),(0,1))

    def test_readable_rounding_keeps_exact_bound(self):
        self.assertEqual(e.percent(.65625),'65.63')
        self.assertEqual(e.percent(.46875),'46.88')

    def test_real_pinned_sensitivity_and_primary_outputs_unchanged(self):
        import hashlib
        folder=ROOT/'results/2026-10-20 v0.24.30 study-d three-arm analysis'
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'exploratory'
            run=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/study_d_exploratory_v02431.py'),
                '--output',str(output)],capture_output=True,text=True,timeout=180)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            result=json.loads((output/'exploratory-posthoc.json').read_text())
            self.assertEqual(result['analysis'],'EXPLORATORY, POST-HOC')
            self.assertFalse(result['primary_verdicts_changed'])
            self.assertEqual(result['arm_S']['neutral']['bounds'],[.125,.1875])
            self.assertEqual(result['arm_S']['contrary']['bounds'],[.84375,.84375])
            self.assertEqual(result['arm_S']['virtue']['bounds'],[0,.0625])
            self.assertEqual(result['D_P3_benefit']['bounds'],[.0625,.1875])
            self.assertEqual(result['D_P3_benefit']['exploratory_threshold_comparison'],'INCONCLUSIVE')
            self.assertEqual(result['D_P4']['bounds'],[.46875,.65625])
            self.assertEqual(result['D_P4']['preregistered_verdict'],'INCONCLUSIVE')
            self.assertEqual(len(result['changed_units']),21)
            self.assertTrue(all(r['arm']=='neutral' and r['original_label']=='unfinished_work' for r in result['changed_units']))
            text=(output/'EXPLORATORY_POSTHOC_REPORT.md').read_text()
            self.assertIn('65.63',text)
            self.assertIn('Paper 3 outline',text)
            self.assertIn('4/16',text)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
        self.assertEqual(before,after)


if __name__=='__main__':
    unittest.main()
