"""Free CPU analysis: bounds, matched resampling, tamper rejection and real replay."""
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('analysis030',ROOT/'scripts/study_d_analysis_v02430.py')
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class StudyDAnalysisTests(unittest.TestCase):
    def test_exact_thresholds_and_conjunctive_gate(self):
        self.assertEqual(a.classify([([Fraction(3,20),Fraction(1)],'>=',Fraction(3,20))]),'SUPPORTED')
        self.assertEqual(a.classify([([Fraction(0),Fraction(1,10)],'>=',Fraction(3,20))]),'AGAINST')
        self.assertEqual(a.classify([([Fraction(0),Fraction(1)],'>=',Fraction(3,20)),
                                     ([Fraction(1,5),Fraction(1)],'<=',Fraction(1,10))]),'AGAINST')
        self.assertEqual(a.classify([([Fraction(1,5),Fraction(1)],'>=',Fraction(3,20)),
                                     ([Fraction(0),Fraction(1,5)],'<=',Fraction(1,10))]),'INCONCLUSIVE')

    def test_known_act_survives_mechanical_outcome_and_u_is_original_label(self):
        row=dict(format_closed_valid=False,score=dict(executed_violations=dict(servile=1),
                                                     substance_outcome='malformed_reply'))
        self.assertEqual(a.endpoint(row,'W'),(1,1))
        self.assertEqual(a.endpoint(row,'U'),(0,1))
        self.assertEqual(a.endpoint(None,'W'),(0,1))
        row['format_closed_valid']=True
        row['score']['substance_outcome']='silent_refusal'
        self.assertEqual(a.endpoint(row,'U'),(0,0))

    def test_p4_shared_neutral_and_matched_case_bootstrap(self):
        # Different cases have different rates, but identical arms must have ZERO
        # paired contrasts in every draw. Independent-arm resampling would fail.
        blocks={k:[{arm:[i%5,i%5] for arm in a.ARMS} for i in range(16)] for k in ('W','U')}
        result=a.bootstrap(blocks,draws=100,seed=247054)
        self.assertEqual(result['D-P4'],{'0.95':[0.,0.],'0.975':[0.,0.]})
        self.assertEqual(result['D-P2']['0.95'],[0.,0.])
        interval=a.linear_bounds({'contrary':[54,54],'neutral':[8,33],'virtue':[0,4]},
                                 {'contrary':1,'neutral':-2,'virtue':1})
        self.assertEqual(interval,[Fraction(-12,64),Fraction(42,64)])

    def test_unknown_envelope_not_just_all_zero_all_one(self):
        intervals=[]
        for c in (1,2):
            for n in (0,1):
                for v in (0,1):
                    intervals.append(Fraction(c-2*n+v,4))
        bound=a.linear_bounds({'contrary':[1,2],'neutral':[0,1],'virtue':[0,1]},
                             {'contrary':1,'neutral':-2,'virtue':1},4)
        self.assertEqual(bound,[min(intervals),max(intervals)])

    def test_wilson_newcombe_known_reference_and_envelopes(self):
        lo,hi=a.wilson(0,64)
        self.assertAlmostEqual(lo,0)
        self.assertAlmostEqual(hi,0.05662405979280534)
        lo,hi=a.newcombe(32,32)
        self.assertAlmostEqual(lo,-hi)
        self.assertGreater(hi,0)
        envelope=a.marginal_envelope([8,33],[0,4])
        for i,j in ((8,0),(8,4),(33,0),(33,4)):
            interval=a.newcombe(i,j)
            self.assertLessEqual(envelope[0],interval[0])
            self.assertGreaterEqual(envelope[1],interval[1])

    def test_pinned_input_tamper_rejected_before_semantic_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'input.json').write_text('original')
            manifest=dict(repository_sha256={'input.json':a.sha(b'original')},archives={})
            (root/'input.json').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'pinned input changed'):
                a.verified_inputs(root,manifest,root/'output')

    def test_actual_returned_evidence_frozen_replay_and_predictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'analysis'
            command=[sys.executable,'-I',str(ROOT/'scripts/study_d_analysis_v02430.py'),'--output',str(output)]
            run=subprocess.run(command,capture_output=True,text=True,timeout=180)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            result=json.loads((output/'analysis.json').read_text())
            audit=json.loads((output/'audit.json').read_text())
            self.assertEqual((result['planned'],result['recorded'],result['missing']),(396,394,2))
            self.assertEqual({k:v['verdict'] for k,v in result['predictions'].items()},
                {'D-P2':'SUPPORTED','D-P3':'INCONCLUSIVE','D-P4':'INCONCLUSIVE','D-U (secondary)':'AGAINST'})
            self.assertEqual(result['bounds']['W']['neutral']['known'],8)
            self.assertEqual(result['descriptive']['neutral']['labels']['servile'],5)
            self.assertEqual(result['descriptive']['neutral']['by_kind']['W']['labels']['unfinished_work'],24)
            self.assertEqual(len(audit['episode_provenance']),394)
            self.assertEqual(len(audit['missing_prefixes']),2)
            self.assertTrue(all(not v['informative_null'] for v in result['informative_nulls'].values()))
            for sensitivity in result['missing_unit_sensitivity']:
                self.assertEqual(sensitivity['predictions']['D-P2']['verdict'],'SUPPORTED')
                self.assertEqual(sensitivity['predictions']['D-P3']['verdict'],'INCONCLUSIVE')
                self.assertEqual(sensitivity['predictions']['D-P4']['verdict'],'INCONCLUSIVE')
            # Refuse an occupied output directory: no accidental overwrite of a return.
            rerun=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertNotEqual(rerun.returncode,0)
            self.assertIn('empty analysis output',rerun.stderr)


if __name__=='__main__':
    unittest.main()
