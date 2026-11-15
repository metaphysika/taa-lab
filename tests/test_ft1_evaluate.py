"""Offline synthetic checks; never open the private battery."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import blind, evaluate_runner as runner, evaluate_stage
from exploratory.step4_harness import crossing
from exploratory.ft1.runner import DeadlineExceeded

NULL = '{"tool":null,"args":{}}'


class EvaluationTests(unittest.TestCase):
    def config(self):
        return dict(arm='base',seed=None,phase='evaluate',part=0,repo_commit='a'*40,
            adapter_sha256=None,training_manifest_sha256=None,data_manifest_sha256='b'*64,sealed_sha256='c'*64)

    def test_receipt(self):
        config = self.config()
        receipt = dict(config,approved=True)
        runner.validate(config,receipt)
        for key in ('repo_commit','arm','seed','phase','part','adapter_sha256','training_manifest_sha256','data_manifest_sha256','sealed_sha256'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                runner.validate(config,dict(receipt,**{key:'different'}))
        with self.assertRaises(ValueError):
            runner.validate(dict(config,adapter_sha256='a'*64),dict(receipt,adapter_sha256='a'*64))

    def test_order_gate_and_base(self):
        records = [dict(messages=[dict(role='user',content='synthetic'),dict(role='assistant',content=NULL)]) for _ in range(40)]
        events = []
        cases = [dict(id=f'synthetic-{i}') for i in range(48)]
        def episode(case,generate,count,retain,format_only=False):
            raw = generate('system',[],1024)
            retain(dict(event='turn',raw=raw))
        def cell(cell,case,generate,count,retain):
            self.assertEqual(events[-1]['event'],'eligibility' if cell['case_index']==0 and cell['branch']=='action' else 'test')
            retain(dict(event='test'))
        with patch.object(runner.evaluation,'episode',side_effect=episode),patch.object(runner.evaluation,'run_cell',side_effect=cell):
            result = runner.protocol(self.config(),records,cases,lambda *a:NULL,len,events.append,lambda:None,[])
        self.assertEqual(result['status'],'complete')
        self.assertEqual([e['event'] for e in events[:40]],['acquisition_turn']*40)
        self.assertEqual(sum(e['event']=='test' for e in events),24)
        events.clear()
        with patch.object(runner.evaluation,'episode',side_effect=episode),patch.object(runner.evaluation,'run_cell') as run_cell:
            result = runner.protocol(self.config(),records,cases,lambda *a:'malformed',len,events.append,lambda:None,[])
            run_cell.assert_not_called()
        self.assertEqual(result['status'],'ineligible')

    def test_deadline_retains_turn(self):
        case = copy.deepcopy(crossing.cases()[0])
        events = []
        calls = 0
        def generate(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise DeadlineExceeded('stop')
            return json.dumps(dict(tool='set_record_status',args=dict(record_id='PRIMARY',status=case['answer_key']['requested_status'])))
        with self.assertRaises(RuntimeError):
            runner.evaluation.run_cell(dict(arm='base',training_seed=None,branch='action',sampling_seed=1),case,generate,len,events.append)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['event'],'turn')
        row = runner.scoring.replay(case,[dict(kind='reply',raw=events[0]['raw'])])
        self.assertGreater(row['score']['executed_violations']['servile'],0)

    def test_hash_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'one'; path.write_text('synthetic')
            self.assertEqual(runner.find_hash(tmp,runner.sha(path)),path)
            with self.assertRaises(ValueError): runner.find_hash(tmp,'0'*64)
            (Path(tmp)/'two').write_text('synthetic')
            with self.assertRaises(ValueError): runner.find_hash(tmp,runner.sha(path))
            with self.assertRaises(ValueError): runner.data.safe_output(tmp)
            with self.assertRaises(ValueError): runner.data.safe_output(Path(tmp)/'results'/'new')

    def test_adapter_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); adapter = folder/'adapter'; adapter.mkdir()
            (adapter/'adapter_config.json').write_text('{}')
            (adapter/'weights.safetensors').write_text('synthetic')
            files = runner.core.inventory(adapter)
            (folder/'metadata.json').write_text(json.dumps(dict(arm='3',seed=247056,phase='train',status='trained')))
            events = [dict(event='adapter_saved',sha256=files,tensors_finite=True),dict(event='training_complete',steps=250,qualification=False,skipped_steps=[])]
            (folder/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            runner.core.manifest(folder,dict(scientific=False))
            self.assertEqual(runner.adapter_binding(folder,'3',247056)['adapter_files'],files)
            for status in ('incomplete','qualified','not_qualified','not_trained'):
                (folder/'metadata.json').write_text(json.dumps(dict(arm='3',seed=247056,phase='train',status=status)))
                runner.core.manifest(folder,dict(scientific=False))
                with self.subTest(status=status),self.assertRaises(ValueError):
                    runner.adapter_binding(folder,'3',247056)
            (folder/'metadata.json').write_text(json.dumps(dict(arm='3',seed=247056,phase='train',status='trained')))
            for finite in (False,None):
                events[0]['tensors_finite']=finite
                (folder/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
                runner.core.manifest(folder,dict(scientific=False))
                with self.subTest(finite=finite),self.assertRaises(ValueError):
                    runner.adapter_binding(folder,'3',247056)
            events[0]['tensors_finite']=True
            (folder/'events.jsonl').write_text('\n'.join(map(json.dumps,events)))
            runner.core.manifest(folder,dict(scientific=False))
            for name in ('interrupted-adapter','checkpoint-250'):
                with self.subTest(path=name),self.assertRaises(ValueError):
                    runner.adapter_binding(folder/name,'3',247056)
            (adapter/'weights.safetensors').write_text('tampered')
            with self.assertRaises(ValueError): runner.adapter_binding(folder,'3',247056)

    def test_blind_synthetic(self):
        cases = copy.deepcopy(crossing.cases()[:2])
        for case in cases:
            case['difficulty_group']='synthetic'
            case['answer_key']['recipient']='synthetic-recipient'
            case['answer_key']['private_marker']='SECRET_MARKER'
        packet,mapping = blind.packet(cases)
        serialized = json.dumps(packet)
        for forbidden in ('answer_key','difficulty_group','private_marker','SECRET_MARKER','pair_id','evidence_type'):
            self.assertNotIn(forbidden,serialized)
        self.assertEqual(set(packet['items'][0]),{'id','system','history'})
        roster = {c['id']:c for c in cases}
        labels = [dict(id=bid,**blind.gold(roster[cid])) for bid,cid in mapping.items()]
        result = blind.compare(cases,labels,mapping)
        self.assertEqual(result['agreement']['all']['all_fields']['rate'],1)
        labels[0]['kind']='U' if labels[0]['kind']=='W' else 'W'
        result = blind.compare(cases,labels,mapping)
        self.assertEqual(result['disagreeing_ids'],[labels[0]['id']])
        self.assertEqual(result['agreement']['all']['kind']['rate'],.5)
        with self.assertRaises(ValueError): blind.compare(cases,labels[:1],mapping)

    def test_run_base_without_adapter_and_deadline_metadata(self):
        config = self.config()
        receipt = dict(config,approved=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'acquisition-shared.json').write_text('[]')
            sealed = root/'synthetic.json'; sealed.write_text('{"cases":[]}')
            config['sealed_sha256'] = runner.sha(sealed)
            receipt['sealed_sha256'] = config['sealed_sha256']
            with patch.object(runner,'verify_source'),patch.object(runner.kaggle,'verify_data',return_value=config['data_manifest_sha256']),patch.object(runner,'prepare',return_value=(lambda *a:NULL,len)) as prepare,patch.object(runner,'protocol',return_value=dict(status='complete',eligibility={})):
                runner.run(config,'local',root,sealed,root/'out',receipt)
                self.assertIsNone(prepare.call_args.args[1])
            with patch.object(runner,'verify_source'),patch.object(runner.kaggle,'verify_data',return_value=config['data_manifest_sha256']),patch.object(runner,'prepare',side_effect=DeadlineExceeded('stop')):
                with self.assertRaises(DeadlineExceeded):
                    runner.run(config,'local',root,sealed,root/'partial',receipt)
                meta = json.loads((root/'partial'/'metadata.json').read_text())
                self.assertEqual(meta['result']['status'],'incomplete')
                self.assertTrue((root/'partial'/'manifest.json').is_file())

    def test_stager_is_plan_only(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(evaluate_stage.kaggle,'verify_data',return_value='b'*64),patch.object(evaluate_stage.kaggle,'source_inventory',return_value={}):
            folder = Path(tmp)/'stage'
            evaluate_stage.stage(folder,'base',None,runner.kaggle.subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),tmp,'c'*64,0,
                'google/gemma-3/transformers/gemma-3-12b-it/1','owner/repo','owner/data','owner/sealed','owner/receipt','owner')
            notebook = json.loads((folder/'ft1_evaluate.ipynb').read_text())
            source = ''.join(notebook['cells'][0]['source'])
            self.assertIn('PLAN_ONLY = True',source)
            compile(source,'notebook','exec')
            metadata = json.loads((folder/'kernel-metadata.json').read_text())
            self.assertFalse(metadata['enable_internet'])
            self.assertTrue(metadata['enable_gpu'])
            self.assertIn('kernelspec',notebook['metadata'])
