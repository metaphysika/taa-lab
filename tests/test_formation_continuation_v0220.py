"""Free fixtures for reviewed-timeout continuation; never contact a provider."""
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from formation.study_a import ROOT
from formation.evaluation_continuation_v0220 import ADAPTERS,review_source,run_continuation
from tests.test_formation_evaluation_v0218 import Response
SOURCE=ROOT/'results/2026-10-11 v0.21.9 haiku55-none r10 study-a evaluation'

class ContinuationTests(unittest.TestCase):
    def test_approval_required_before_any_credentials_or_transport(self):
        with patch('formation.evaluation_continuation_v0220.load_keys') as keys,patch('urllib.request.urlopen') as send:
            with self.assertRaises(ValueError):run_continuation(SOURCE,Path('/tmp/unapproved-continuation'))
            keys.assert_not_called();send.assert_not_called()

    def test_exact_unattempted_suffix_and_uncertain_reserve(self):
        review=review_source(SOURCE)
        self.assertEqual(len(review['pending_cells']),22)
        self.assertEqual(review['pending_cells'][0]['case_id'],'A_R02')
        self.assertEqual(review['retained_timeout_case'],'A_R01')
        self.assertEqual(review['retained_timeout_repeat'],10)
        self.assertAlmostEqual(review['remaining_cap_dollars'],0.52047815)
        self.assertNotIn(('A_R01',10),[(c['case_id'],c['repeat']) for c in review['pending_cells']])

    def test_pending_execution_evidence_blocks_continuation(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';shutil.copytree(SOURCE,source)
            (source/'A_R02-r10-checkpoint.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'pending cell has execution evidence'):review_source(source)

    def test_declared_suffix_runs_once_with_remaining_original_cap(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);root=folder/'root';source=folder/'source';shutil.copytree(SOURCE,source)
            plan=json.loads((ROOT/'studies/formation-study-a-evaluation-plan-v0217.json').read_text())
            relatives=set(ADAPTERS)|{'scripts/formation_study_a_evaluation.py','studies/formation-study-a-evaluation-plan-v0217.json','studies/formation-study-a-haiku55-evaluation-cost-plan-v0219.json','studies/formation-study-a-freeze-v0217.json',plan['price_file']}|{c['path'] for c in plan['cells']}
            for relative in relatives:
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/relative).read_bytes())
            review=review_source(source,root);fixtures=[]
            for path in ('studies/formation-study-a-fixtures-v0213.json','studies/formation-study-a-pressure-fixtures-v0215.json'):
                fixtures+=json.loads((ROOT/path).read_text())['fixtures']
            packets=[]
            for cell in review['pending_cells']:
                packets+=next(f['packets'] for f in fixtures if f['case_id']==cell['case_id'] and f['name']=='required_conduct')
            raws=iter(p['raw'] for p in packets);output=folder/'output'
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()}
            with patch('formation.evaluation_continuation_v0220.load_keys'),patch.dict('os.environ',{'ANTHROPIC_API_KEY':'declared-fixture-only'}),patch('urllib.request.urlopen',side_effect=lambda *a,**k:Response('claude-haiku-5-5','claude',next(raws))) as send:
                result=run_continuation(source,output,approved=True,reviewed_timeout=True,root=root)
                self.assertEqual(result['completed_cells'],22);self.assertEqual(send.call_count,len(packets))
                self.assertTrue(all(r['outcome']=='correct' for r in result['records']))
                run_continuation(source,output,approved=True,reviewed_timeout=True,root=root)
                self.assertEqual(send.call_count,len(packets))
            manifest=json.loads((output/'execution-manifest.json').read_text())
            self.assertAlmostEqual(manifest['budget']+review['source_estimated_dollars'],1)
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()})

if __name__=='__main__':unittest.main()
