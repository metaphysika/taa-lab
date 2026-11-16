"""Offline synthetic checks; never open the private battery."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import evaluate_runner as runner, evaluate_stage
from exploratory.step4_harness import crossing
from exploratory.ft1.runner import DeadlineExceeded

NULL = '{"tool":null,"args":{}}'


class EvaluationTests(unittest.TestCase):
    def config(self):
        return dict(arm='base',seed=None,phase='evaluate',part=0,part_count=2,gate_sha256='d'*64,model_source='local',repo_commit='a'*40,
            adapter_sha256=None,training_manifest_sha256=None,data_manifest_sha256='b'*64,sealed_sha256='c'*64)

    def test_receipt(self):
        config = self.config()
        receipt = dict(config,approved=True)
        runner.validate(config,receipt)
        for key in ('repo_commit','arm','seed','phase','part','adapter_sha256','training_manifest_sha256','data_manifest_sha256','sealed_sha256','gate_sha256','part_count','model_source'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                runner.validate(config,dict(receipt,**{key:'different'}))
        with self.assertRaises(ValueError):
            runner.validate(dict(config,adapter_sha256='a'*64),dict(receipt,adapter_sha256='a'*64))

    def test_order_gate_and_base(self):
        config = self.config()
        records = [dict(messages=[dict(role='user',content='synthetic'),dict(role='assistant',content=NULL)]) for _ in range(40)]
        events = []
        cases = [dict(id=f'synthetic-{i}',pair_id=f'pair-{i//2}',kind='W' if i%2==0 else 'U',difficulty_group=str(i//12)) for i in range(48)]
        def episode(case,generate,count,retain,format_only=False):
            raw = generate('system',[],1024)
            retain(dict(event='turn',raw=raw))
        with patch.object(runner.evaluation,'episode',side_effect=episode):
            gate = runner.protocol(config,records,lambda *a:'malformed',len,events.append,lambda:None,[])
        self.assertFalse(gate['acquired'])
        self.assertEqual([e['event'] for e in events[:40]],['acquisition_turn']*40)
        with patch.object(runner.evaluation,'run_cell') as cells:
            result = runner.test_cells(config,cases,gate,lambda *a:NULL,len,events.append,lambda:None)
            self.assertEqual(cells.call_count,48)
            self.assertEqual(result['status'],'complete')
        config = dict(config,arm='3',seed=247056,adapter_sha256='e'*64,training_manifest_sha256='f'*64)
        gate.update({k:config[k] for k in ('arm','seed','adapter_sha256','training_manifest_sha256')})
        with patch.object(runner.evaluation,'run_cell') as cells:
            result = runner.test_cells(config,cases,gate,lambda *a:NULL,len,events.append,lambda:None)
            cells.assert_not_called()
            self.assertEqual(result['status'],'ineligible')
        gate['acquired']=gate['trained']=True
        runner.validate_gate(config,gate)
        for key in ('arm','seed','adapter_sha256','training_manifest_sha256','repo_commit','data_manifest_sha256','model_source'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                runner.validate_gate(config,dict(gate,**{key:'wrong'}))

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
            path = Path(tmp)/'one.json'; path.write_text('synthetic')
            self.assertEqual(runner.find_hash(tmp,runner.sha(path)),path)
            with self.assertRaises(ValueError): runner.find_hash(tmp,'0'*64)
            (Path(tmp)/'two.json').write_text('synthetic')
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


    def test_run_base_without_adapter_and_deadline_metadata(self):
        config = dict(self.config(),phase='gate',part=None,part_count=None,gate_sha256=None,sealed_sha256=None)
        receipt = dict(config,approved=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'acquisition-shared.json').write_text('[]')
            with patch.object(runner,'verify_source'),patch.object(runner.kaggle,'verify_data',return_value=config['data_manifest_sha256']),patch.object(runner,'prepare',return_value=(lambda *a:NULL,len)) as prepare,patch.object(runner,'protocol',return_value=dict(acquired=False,trained=True)):
                runner.run(config,'local',root,None,root/'out',receipt)
                self.assertIsNone(prepare.call_args.args[1])
                self.assertTrue((root/'out'/'gate.json').exists())
            with patch.object(runner,'verify_source'),patch.object(runner.kaggle,'verify_data',return_value=config['data_manifest_sha256']),patch.object(runner,'prepare',side_effect=DeadlineExceeded('stop')):
                with self.assertRaises(DeadlineExceeded):
                    runner.run(config,'local',root,None,root/'partial',receipt)
                meta = json.loads((root/'partial'/'metadata.json').read_text())
                self.assertEqual(meta['result']['status'],'incomplete')
                self.assertTrue((root/'partial'/'manifest.json').is_file())

    def test_stager_is_plan_only(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(evaluate_stage.kaggle,'verify_data',return_value='b'*64),patch.object(evaluate_stage.kaggle,'source_inventory',return_value={}):
            folder = Path(tmp)/'stage'
            evaluate_stage.stage(folder,'base',None,runner.kaggle.subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),tmp,'c'*64,0,
                'google/gemma-3/transformers/gemma-3-12b-it/1','owner/repo','owner/data','owner/sealed','owner/receipt','owner',gate_sha256='d'*64,gate_dataset='owner/gate')
            notebook = json.loads((folder/'ft1_evaluate.ipynb').read_text())
            source = ''.join(notebook['cells'][0]['source'])
            self.assertIn('PLAN_ONLY = True',source)
            compile(source,'notebook','exec')
            metadata = json.loads((folder/'kernel-metadata.json').read_text())
            self.assertFalse(metadata['enable_internet'])
            self.assertTrue(metadata['enable_gpu'])
            self.assertIn('kernelspec',notebook['metadata'])


    def test_small_json_single_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'small.json').write_text('{}')
            (root/'large.safetensors').write_bytes(b'x')
            (root/'oversized.json').write_bytes(b'x')
            stat = Path.stat
            def fake_stat(path, *args, **kwargs):
                from types import SimpleNamespace
                if path.name == 'oversized.json': return SimpleNamespace(st_size=6*1024**2)
                if path.name == 'large.safetensors': return SimpleNamespace(st_size=24*1024**3)
                return stat(path,*args,**kwargs)
            with patch.object(Path,'stat',fake_stat),patch.object(runner,'sha',return_value='a'*64) as sha:
                result = runner.find_hashes(root,dict(one='a'*64,two='a'*64))
                self.assertEqual(sha.call_args_list[0].args[0],root/'small.json')
                self.assertEqual(sha.call_count,1)
                self.assertEqual(result['one'],result['two'])

    def test_parts_and_duplicate_gates(self):
        from exploratory.ft1.aggregate_events import gate_rows
        cases = [dict(id=str(i),pair_id=str(i//2),difficulty_group=str(i//12)) for i in range(48)]
        parts = [runner.part_indices(cases,p,2) for p in range(2)]
        self.assertFalse(parts[0] & parts[1])
        self.assertEqual(parts[0] | parts[1],set(range(48)))
        for indices in parts:
            self.assertEqual(len(indices),24)
            self.assertEqual({group:sum(cases[i]['difficulty_group']==group for i in indices) for group in ('0','1','2','3')},dict.fromkeys(('0','1','2','3'),6))
            self.assertTrue(all((i^1) in indices for i in indices))
        row = dict(arm='base',seed=None,acquired=False)
        self.assertEqual(len(gate_rows([row,row])),1)
        with self.assertRaises(ValueError): gate_rows([row,dict(row,acquired=True)])



    def test_gate_stager_needs_no_sealed_input(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(evaluate_stage.kaggle,'verify_data',return_value='b'*64),patch.object(evaluate_stage.kaggle,'source_inventory',return_value={}):
            folder = Path(tmp)/'gate-stage'
            config = evaluate_stage.stage(folder,'base',None,runner.kaggle.subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),tmp,None,0,
                'google/gemma-3/transformers/gemma-3-12b-it/1','owner/repo','owner/data',None,'owner/receipt','owner',phase='gate',attention='eager',prefill_mode='chunked',prefill_chunk_size=256,prompt_ceiling=14000)
            runner.validate(config,dict(config,approved=True))
            import jsonschema
            schema = json.loads(Path('docs/process/FT1_EVAL_SETTINGS_RECEIPT_v02494.schema.json').read_text())
            jsonschema.validate(dict(config, approved=True), schema)
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(dict(config, approved=False), schema)
            self.assertEqual({k:config[k] for k in ('attention','prefill_mode','prefill_chunk_size','prompt_ceiling')},dict(attention='eager',prefill_mode='chunked',prefill_chunk_size=256,prompt_ceiling=14000))
            self.assertIsNone(config['sealed_sha256'])
            self.assertIsNone(config['gate_sha256'])
            notebook = json.loads((folder/'ft1_evaluate.ipynb').read_text())
            compile(''.join(notebook['cells'][0]['source']),'gate-notebook','exec')
            metadata = json.loads((folder/'kernel-metadata.json').read_text())
            self.assertEqual(len(metadata['dataset_sources']),4)

    def test_test_input_gate_binding_before_model_load(self):
        config = self.config()
        gate = dict(config,acquired=False,trained=False)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sealed = root/'cases.json'; sealed.write_text('{"cases":[]}')
            gate_file = root/'gate.json'; gate_file.write_text(json.dumps(gate))
            config.update(sealed_sha256=runner.sha(sealed),gate_sha256=runner.sha(gate_file))
            with patch.object(runner,'verify_source'),patch.object(runner.kaggle,'verify_data',return_value=config['data_manifest_sha256']),patch.object(runner,'prepare') as prepare:
                with self.assertRaises(ValueError):
                    runner.run(config,'local',root,sealed,root/'out',dict(config,approved=True),gate_file=sealed)
                prepare.assert_not_called()
                gate['seed']=247056
                gate_file.write_text(json.dumps(gate)); config['gate_sha256']=runner.sha(gate_file)
                with self.assertRaises(ValueError):
                    runner.run(config,'local',root,sealed,root/'out',dict(config,approved=True),gate_file=gate_file)
                prepare.assert_not_called()

    def test_balance_refusal_and_gate_null_fields(self):
        cases = [dict(id=str(i),pair_id=str(i//2),kind='W' if i%2==0 else 'U',difficulty_group=str(i//12)) for i in range(48)]
        indices = runner.part_indices(cases,0,2)
        events = []
        runner.check_part_balance(cases,indices,events.append)
        cases[0]['difficulty_group']='1'
        with self.assertRaises(ValueError): runner.check_part_balance(cases,indices,events.append)
        self.assertEqual(set(events[-1]),{'event','counts'})
        cases[0]['difficulty_group']='0'
        with self.assertRaises(ValueError): runner.check_part_balance(cases,(indices-{0})|{2},events.append)
        config = dict(self.config(),phase='gate',part=None,part_count=None,sealed_sha256=None,gate_sha256=None)
        receipt = dict(config,approved=True)
        runner.validate(config,receipt)
        for key in ('part','part_count','gate_sha256','sealed_sha256'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                runner.validate(dict(config,**{key:1}),dict(receipt,**{key:1}))
            missing = dict(receipt); missing.pop(key)
            with self.assertRaises(ValueError): runner.validate(config,missing)

    def test_broken_link_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root/'good.json'; path.write_text('{}')
            stat = Path.stat
            def broken_stat(path,*args,**kwargs):
                if path.name == 'broken.json': raise FileNotFoundError('synthetic broken link')
                return stat(path,*args,**kwargs)
            with patch.object(runner.os,'walk',return_value=[(tmp,[],['broken.json','good.json'])]),patch.object(Path,'stat',broken_stat):
                self.assertEqual(runner.find_hash(root,runner.sha(path)),path)






class SettingsTests(unittest.TestCase):
    def test_settings(self):
        config = dict(EvaluationTests().config(), attention='eager', prefill_mode='chunked', prefill_chunk_size=256, prompt_ceiling=14000)
        runner.validate(config, dict(config, approved=True))
        gate = dict(config, acquired=True, trained=True)
        runner.validate_gate(config, gate)
        for key in ('attention','prefill_mode','prefill_chunk_size','prompt_ceiling'):
            missing = dict(config, approved=True); missing.pop(key)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'evaluation settings mismatch' if key != 'prompt_ceiling' else 'separate exact evaluation approval required'): runner.validate(config, missing)
            missing = dict(gate); missing.pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError): runner.validate_gate(config, missing)

    def test_prepare_attention_readback(self):
        from types import SimpleNamespace
        model = SimpleNamespace(config=SimpleNamespace(_attn_implementation='eager'))
        events = []
        with patch.object(runner,'load_base',return_value=(model,None,None)) as load, patch.object(runner,'generation_functions'):
            runner.prepare('unused',None,events.append,lambda:None,attention='eager')
        self.assertEqual(load.call_args.kwargs,dict(attention='eager'))
        self.assertFalse(events[0]['mismatch'])
        self.assertEqual(events[0]['stage'], 'base')
        model.config._attn_implementation='sdpa'
        with patch.object(runner,'load_base',return_value=(model,None,None)), patch.object(runner,'generation_functions'):
            with self.assertRaisesRegex(ValueError, 'attention readback mismatch'):
                runner.prepare('unused',None,events.append,lambda:None,attention='eager')
        self.assertTrue(events[-1]['mismatch'])

    def test_text_attention_is_authoritative(self):
        from types import SimpleNamespace as NS
        model = NS(config=NS(_attn_implementation='eager', text_config=NS(_attn_implementation='sdpa')))
        with self.assertRaisesRegex(ValueError, 'attention readback mismatch'):
            runner.attention_readback(model, 'eager', lambda e: None, 'base')

    def test_adapter_readback_called(self):
        from types import SimpleNamespace as NS
        import sys
        base, adapter = NS(config=NS()), NS(config=NS())
        peft = NS(PeftConfig=NS(from_pretrained=lambda *a, **k: NS()),
                  PeftModel=NS(from_pretrained=lambda *a, **k: adapter))
        with patch.dict(sys.modules, peft=peft), patch.object(runner, 'load_base', return_value=(base,None,'local')), patch.object(runner, 'generation_functions'), patch.object(runner, 'attention_readback') as readback:
            runner.prepare('local','adapter',lambda e: None,lambda: None,attention='eager')
        self.assertEqual([c.args[3] for c in readback.call_args_list], ['base','adapter'])
        self.assertIs(readback.call_args_list[-1].args[0], adapter)

    def test_agent_safe_targets_do_not_import_sealed(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, 'scripts/agent_safe_imports.py', '-m', 'tests.ft1_safe_import_guard'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_gate_retains_observed_attention(self):
        config = dict(EvaluationTests().config(), phase='gate', part=None, part_count=None,
                      sealed_sha256=None, gate_sha256=None)
        def prepare(*args, **kwargs):
            args[2](dict(event='attention_readback', stage='base', observed='sdpa'))
            return lambda *a: NULL, len
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'acquisition-shared.json').write_text('[]')
            with patch.object(runner,'verify_source'), patch.object(runner.kaggle,'verify_data',return_value=config['data_manifest_sha256']), patch.object(runner,'prepare',side_effect=prepare), patch.object(runner,'protocol',return_value=dict(acquired=False,trained=True)):
                runner.run(config,'local',root,None,root/'out',dict(config,approved=True))
            self.assertEqual(json.loads((root/'out'/'gate.json').read_text())['attention'], 'sdpa')
