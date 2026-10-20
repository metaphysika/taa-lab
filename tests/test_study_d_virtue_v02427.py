"""Actual returned-evidence CPU provenance/admission regression. No provider calls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'studies/formation-study-d-gemma-stages-v02427'


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class VirtueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        with zipfile.ZipFile(ROOT/'results/gemma-v02426-neutral-return-001.zip') as z:
            z.extractall(cls.root)
        cls.source=cls.root/'gemma-v02426-neutral-return-001'
        cls.repair=load('repair027','scripts/study_d_gemma_provenance_v02427.py')
        cls.h=load('virtue027','formation/study_d_gemma_stages_v02427.py')
        cls.binding=json.loads((ASSETS/'continuation-source-v02425.json').read_text())
        cls.source_record=cls.source/'source-composite-v02426.json'
        shutil.copyfile(cls.source/'pair/report.json',cls.source_record)
        cls.original=json.loads(cls.source_record.read_text())

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_actual_repaired_composite_and_every_non_missing_unit(self):
        result=self.repair.repair_composite(self.source,self.original,self.binding)
        self.assertEqual(result,json.loads((ASSETS/'composite-pair-v02427.json').read_text()))
        self.assertEqual(self.repair.validate_union(result['arms']['neutral']['episode_provenance']),dict(status='PASS',completed=130,missing=2))
        for unit in result['arms']['neutral']['episode_provenance']:
            if unit.get('missing'):continue
            self.assertEqual(self.repair.sha(self.source/unit['path']),unit['output_sha256'])
        new=[u for u in result['arms']['neutral']['episode_provenance'] if u['producer']=='v02426']
        self.assertEqual(len(new),34)
        self.assertTrue(all(u['status']=='completed' and u['issued_request_ids'] for u in new))
        # The old published record must stay byte-identical.
        self.assertEqual(self.repair.sha(self.source_record),json.loads((ASSETS/'completion-source-v02426.json').read_text())['source_composite_sha256'])
        self.assertEqual(result['arms']['neutral']['bounds'],self.original['arms']['neutral']['bounds'])

    def test_regression_old_untouched_provenance_rejected(self):
        with self.assertRaisesRegex(ValueError,'provenance'):
            self.repair.validate_union(self.original['arms']['neutral']['episode_provenance'])
        result=self.repair.repair_composite(self.source,self.original,self.binding)
        for field,value in [('path',None),('output_sha256',''),('issued_request_ids',[])]:
            broken=copy.deepcopy(result['arms']['neutral']['episode_provenance'])
            next(u for u in broken if u['producer']=='v02426')[field]=value
            with self.assertRaises(ValueError):self.repair.validate_union(broken)

    def test_actual_require_previous_accepts_reviewed_composite_only(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for p in self.source.iterdir():
                if p.name in ('pair','source-composite-v02426.json'):continue
                (root/p.name).symlink_to(p,target_is_directory=p.is_dir())
            shutil.copyfile(self.source_record,root/'source-composite-v02426.json')
            (root/'pair').mkdir();shutil.copyfile(ASSETS/'composite-pair-v02427.json',root/'pair/report.json')
            (root/'assets').symlink_to(ASSETS,target_is_directory=True)
            shutil.copyfile(ROOT/'scripts/study_d_gemma_provenance_v02427.py',root/'provenance.py')
            digest=self.h.sha(root/'pair/report.json')
            payload=dict(stage='virtue',commit='a'*40,actual_total_usd=19.67,previous_report_sha256=digest)
            ledger={'pair/closed':dict(status='COMPLETE',report_sha256=digest)}
            with patch.object(self.h,'__file__',str(root/'policy.py')):
                self.h.require_previous(root,payload,ledger)
                with self.assertRaises(ValueError):self.h.require_previous(root,dict(payload,previous_report_sha256='0'*64),ledger)
                with self.assertRaises(ValueError):self.h.require_previous(root,payload,{})
                (root/'pair/report.json').write_bytes(self.source_record.read_bytes())
                with self.assertRaises(ValueError):self.h.require_previous(root,payload,ledger)

    def test_static_sources_budget_and_all_inherited_assets(self):
        load('static027','scripts/check_study_d_science_v02427.py').check()
        load('launch027','scripts/formation_study_d_gemma_stages_v02427.py').check_sources()
        self.assertAlmostEqual(self.h.reservation('virtue'),9.194555555555556)
        b=self.h.budget('virtue',19.67,10.39,True,'owner/no card')
        self.assertAlmostEqual(b['projected_cumulative_reserved_usd'],28.864555555555556)
        for actual,credit in [(19.66,10.39),(19.67,9.19),(27,10.39)]:
            with self.assertRaises(ValueError):self.h.budget('virtue',actual,credit,True,'owner')
        self.assertEqual(list(self.h.STAGES),['virtue'])


@unittest.skipUnless(importlib.util.find_spec('modal') and __import__('sys').version_info[:2]==(3,12),'pinned offline SDK')
class VirtueSerializationTests(unittest.TestCase):
    def test_no_hydration_or_backend(self):
        import modal
        from modal._serialization import serialize
        module=load('app027','scripts/study_d_gemma_stages_app_v02427.py')
        with patch.object(modal.client._Client,'from_env',side_effect=AssertionError('backend forbidden')):
            app,worker,controller=module.define('virtue')
            for f in (worker,controller):self.assertGreater(len(serialize(f._raw_f_)),100)
