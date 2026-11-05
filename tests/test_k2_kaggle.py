import json
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.k2_kaggle import core
from exploratory.step4_harness import crossing

class K2Tests(unittest.TestCase):
    def test_plan(self):
        self.assertEqual(len(core.plan(1)),96)
        self.assertEqual(len(core.plan(2)),528)
        for step in (1,2):
            cells=core.plan(step,5)
            self.assertEqual(len({tuple(c.values()) for c in cells}),len(cells))
            for arm in core.ARMS:
                self.assertEqual(len([c for c in cells if c['checkpoint']==arm]),len(cells)//3)
    def test_hashes_and_scorer(self):
        core.validate_assets()
        self.assertIs(core.SCORER,crossing.replay)
        self.assertIs(core.k1.c.replay,core.SCORER)
    def test_missing_cells_remain_unknown(self):
        summary=core.sanity_summary([])
        self.assertEqual(len(summary),6)
        for group in summary.values():
            self.assertEqual(group,dict(planned=16,classes={'unknown':16}))
    def test_gate_and_fake_run(self):
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ValueError): core.run(2,core.fake_model,lambda x:None,dry_run=False)
            for step in (1,2):
                rows=[]
                core.run(step,core.fake_model,rows.append)
                self.assertEqual(sum(r['event']=='cell' for r in rows),len(core.plan(step)))
    def test_notebooks_cpu(self):
        import tempfile
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            for name in ('k2_train.ipynb','k2_eval.ipynb'):
                nb=json.loads((Path(core.__file__).parent/name).read_text())
                with tempfile.TemporaryDirectory() as tmp:
                    namespace={}
                    for cell in nb['cells']:
                        if cell['cell_type']!='code':continue
                        code=''.join(cell['source'])
                        code=code.replace("Path('/kaggle/input/taa-k2-repo/taa-lab')",'Path('+repr(str(core.ROOT))+')')
                        code=code.replace("Path('/kaggle/working/k2-output')",'Path('+repr(tmp)+') / "output"')
                        exec(compile(code,name,'exec'),namespace)
                    self.assertTrue((Path(tmp)/'output/manifest.json').is_file())
    def test_issuer_rewrites(self):
        case=next(c for c in core.c.cases() if c['kind']=='W')
        for issuer in core.ISSUERS:
            rewritten=core.issuer_case(case,issuer)
            self.assertEqual(rewritten['answer_key'],case['answer_key'])
            if issuer not in ('manager','driver'):
                self.assertNotIn('contract driver',json.dumps(rewritten))
