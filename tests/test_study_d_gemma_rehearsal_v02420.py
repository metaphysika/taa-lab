"""Architecture-conditioned coverage regressions; no Torch, models or backend required."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from formation import study_d_gemma_stages_v02420 as h
spec=importlib.util.spec_from_file_location('runtime20',Path(__file__).resolve().parents[1]/'scripts/study_d_gemma_stages_runtime_v02420.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def config(real=False):
    return dict(num_hidden_layers=60 if real else 2,
        layer_types=(['sliding_attention']*5+['full_attention'])*10 if real else ['sliding_attention','full_attention'],
        attention_k_eq_v=True,hidden_size=5376 if real else 32,intermediate_size=21504 if real else 64,
        num_attention_heads=32 if real else 4,num_key_value_heads=16 if real else 2,
        num_global_key_value_heads=4 if real else 2,head_dim=256 if real else 8,global_head_dim=512 if real else 8)


def fake_model(cfg=None):
    cfg=cfg or config();expected=r.expected_lora_architecture(cfg,h.LORA);names=[]
    for layer,entry in expected['per_layer'].items():
        for target,shape in entry['linear_shapes'].items():
            prefix='self_attn' if target in ('q_proj','k_proj','v_proj','o_proj') else 'mlp'
            names.append(('model.language_model.layers.'+layer+'.'+prefix+'.'+target,
                SimpleNamespace(in_features=shape[0],out_features=shape[1])))
    model=SimpleNamespace(config=SimpleNamespace(text_config=SimpleNamespace(**cfg)),named_modules=lambda:iter(names))
    return model,names


class RehearsalTests(unittest.TestCase):
    def test_transformers_loading_info_sets_and_nested_collections(self):
        info=dict(missing_keys=set(),unexpected_keys={'vision_tower.z','audio_tower.a'},mismatched_keys=frozenset(),error_msgs=(),nested=({3,1},))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'training-load.json';r.write(p,dict(loading_info=r.loading_info_json(info)))
            o=json.loads(p.read_text())['loading_info'];self.assertEqual(o['unexpected_keys'],['audio_tower.a','vision_tower.z'])
            self.assertEqual(o['nested'],[[1,3]]);self.assertEqual(o['missing_keys'],[])
    def test_strict_encoder_rejects_unknown_bad_key_and_nonfinite_before_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';p.write_text('original')
            for value in (object(),Path('x'),{1:'x'},float('nan'),float('inf')):
                with self.assertRaises(TypeError):r.write(p,value)
                self.assertEqual(p.read_text(),'original')
    def test_real_pinned_architecture_expected_counts_and_parameters(self):
        actual=json.loads((Path(__file__).resolve().parents[1]/'studies/formation-study-d-gemma-software-attempt-v02418/received-evidence-001/extracted/gemma-v02418-smoke-return-001/cpu/tokenizer.json').read_text())['model_and_generation_config']['config.json']['text_config']
        expected=r.expected_lora_architecture(actual,h.LORA)
        self.assertEqual((expected['layers'],expected['sliding_layers'],expected['full_attention_layers']),(60,50,10))
        self.assertEqual(expected['matched_module_count'],410)
        self.assertEqual(expected['target_module_counts'],dict(q_proj=60,k_proj=60,v_proj=50,o_proj=60,gate_proj=60,up_proj=60,down_proj=60))
        self.assertEqual(expected['expected_trainable_parameters'],61214720)
        model,_=fake_model(actual);self.assertEqual(r.lora_coverage(model,h.LORA)['status'],'PASS')
    def test_exact_v02419_pattern_now_passes_without_adding_v_proj(self):
        model,_=fake_model();o=r.lora_coverage(model,h.LORA)
        self.assertEqual(o['matched_module_count'],13)
        self.assertEqual(o['expected_trainable_parameters'],7808)
        self.assertEqual(o['observed_per_layer']['0']['v_proj'],1)
        self.assertEqual(o['observed_per_layer']['1']['v_proj'],0)
    def test_any_wrong_presence_missing_target_or_shape_fails(self):
        for bad in ('extra_full_v','missing_sliding_v','missing_full_q','wrong_shape','duplicate'):
            with self.subTest(bad=bad):
                model,names=fake_model()
                if bad=='extra_full_v':names.append(('model.language_model.layers.1.self_attn.v_proj',SimpleNamespace(in_features=32,out_features=16)))
                elif bad=='missing_sliding_v':names[:]=[n for n in names if not n[0].endswith('v_proj')]
                elif bad=='missing_full_q':names[:]=[n for n in names if '.1.self_attn.q_proj' not in n[0]]
                elif bad=='wrong_shape':names[0][1].out_features=999
                else:names.append(names[0])
                with self.assertRaises(RuntimeError):r.lora_coverage(model,h.LORA)
    def test_failure_reports_preserve_observed_per_layer_counts(self):
        model,names=fake_model()
        names.append(('model.language_model.layers.1.self_attn.v_proj',SimpleNamespace(in_features=32,out_features=16)))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'coverage.json'
            with self.assertRaises(RuntimeError):r.lora_coverage(model,h.LORA,path)
            o=json.loads(path.read_text())
            self.assertEqual(o['status'],'STOP_FOR_REVIEW')
            self.assertEqual(o['observed_per_layer']['1']['v_proj'],1)
            self.assertEqual(o['per_layer']['1']['coverage']['v_proj'],0)
            self.assertTrue(o['coverage_errors'])
    def test_unknown_layer_type_or_false_shared_kv_fails(self):
        for change in (dict(layer_types=['sliding_attention','other']),dict(attention_k_eq_v=False),dict(num_hidden_layers=3)):
            c=config();c.update(change)
            with self.assertRaises(RuntimeError):r.expected_lora_architecture(c,h.LORA)
    def test_observed_trainable_count_must_match_each_layer(self):
        model,_=fake_model();coverage=r.lora_coverage(model,h.LORA)
        params=[]
        for layer,row in coverage['per_layer'].items():
            n=row['expected_trainable_parameters']
            params.append(('base_model.model.language_model.layers.'+layer+'.lora_A',SimpleNamespace(requires_grad=True,numel=lambda n=n:n)))
        model.named_parameters=lambda:iter(params);model.parameters=lambda:(v for _,v in params)
        self.assertEqual(r.trainable_coverage(model,coverage)['trainable_parameters'],7808)
        params[0][1].numel=lambda:1
        with self.assertRaises(RuntimeError):r.trainable_coverage(model,coverage)
    def test_new_cap_stage_reservations_and_frozen_science_unchanged(self):
        from formation import study_d_gemma_stages_v02419 as old
        self.assertEqual(h.CAP,30)
        for field in ('STAGES','TRAIN','LORA','ENGINE','PACKAGES','SMOKE_STEPS','SMOKE_CASES'):
            self.assertEqual(getattr(h,field),getattr(old,field))
        self.assertAlmostEqual(sum(h.reservation(s) for s in h.STAGES),20.18175)
        self.assertEqual(h.budget('cpu',9,21,True,'owner')['cumulative_ceiling_usd'],30)
        with self.assertRaises(ValueError):h.budget('cpu',10,20,True,'over cap and free credit')
        with self.assertRaises(ValueError):h.budget('cpu',h.PRIOR,1,True,'insufficient free credit for remaining plan')
    def test_rehearsal_uses_actual_entry_and_reports_coverage(self):
        import inspect
        cpu=inspect.getsource(r.cpu_rehearsal);train=inspect.getsource(r.training_process)
        self.assertIn("__file__,'train'",cpu);self.assertIn('model.save_pretrained(checkpoint',cpu)
        self.assertIn('local_files_only',train);self.assertIn('max_steps=2 if rehearsal',train)
        self.assertLess(train.index('training-load.json'),train.index('get_peft_model(model'))
        self.assertIn('verify_adapter_reload(model',train);self.assertIn('trainable_coverage(model,coverage,',train)
    def test_ci_frozen_tensor_data_preserves_loss_masks(self):
        fixture=Path(__file__).resolve().parents[1]/'studies/formation-study-d-gemma-stages-v02420/ci-served-token-fixture.json'
        for arm in ('contrary','virtue','neutral'):
            rows=r.ci_tensor_data(arm,fixture);self.assertEqual(len(rows),18)
            self.assertEqual(rows[0],rows[3])
            self.assertEqual(rows[0]['labels'][-1],106)
        with tempfile.TemporaryDirectory() as d:
            obj=json.loads(fixture.read_text());obj['arms']['contrary'][0]['labels'][0]=123
            path=Path(d)/'broken.json';path.write_text(json.dumps(obj))
            with self.assertRaises(RuntimeError):r.ci_tensor_data('contrary',path)
    def test_ci_cannot_substitute_for_modal_pass(self):
        import inspect
        text=inspect.getsource(r.training_process)
        self.assertIn("p.get('stage')!='ci_cpu_rehearsal'",text)
        self.assertNotIn('ci_cpu_rehearsal',h.STAGES)
        self.assertIn('ci_formatted_data',text)
        self.assertEqual(r.tiny_config_values(dict(text_config=config(),vision_config={},audio_config={}))['text_config']['num_hidden_layers'],2)
    def test_missing_rehearsal_proof_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cpu';p.mkdir();(p/'receipt.json').write_text('{}')
            with self.assertRaises(ValueError):h.require_cpu(d,dict(commit='a'*40,asset_sha256='b'*64))
