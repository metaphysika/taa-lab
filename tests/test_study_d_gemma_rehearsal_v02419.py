"""Offline regressions. Real pinned tiny-model rehearsal is separately approved Modal work."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from formation import study_d_gemma_stages_v02419 as h
spec=importlib.util.spec_from_file_location('runtime19',Path(__file__).resolve().parents[1]/'scripts/study_d_gemma_stages_runtime_v02419.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class RehearsalTests(unittest.TestCase):
    def test_transformers_loading_info_sets_and_nested_collections(self):
        info=dict(missing_keys=set(),unexpected_keys={'vision_tower.z','audio_tower.a'},mismatched_keys=frozenset(),error_msgs=(),nested=({3,1},))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'training-load.json';r.write(p,dict(loading_info=r.loading_info_json(info)))
            o=json.loads(p.read_text())['loading_info']
            self.assertEqual(o['unexpected_keys'],['audio_tower.a','vision_tower.z'])
            self.assertEqual(o['nested'],[[1,3]])
            self.assertEqual(o['missing_keys'],[])
    def test_strict_encoder_rejects_unknown_bad_key_and_nonfinite_before_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';p.write_text('original')
            for value in (object(),Path('x'),{1:'x'},float('nan'),float('inf')):
                with self.assertRaises(TypeError):r.write(p,value)
                self.assertEqual(p.read_text(),'original')
    def test_lora_requires_all_seven_in_every_layer(self):
        targets=('q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj')
        names=[('model.language_model.layers.'+str(i)+'.'+('self_attn.' if t.endswith('proj') and t in targets[:4] else 'mlp.')+t,None) for i in range(2) for t in targets]
        model=SimpleNamespace(config=SimpleNamespace(text_config=SimpleNamespace(num_hidden_layers=2)),named_modules=lambda:iter(names))
        self.assertEqual(len(r.lora_coverage(model,h.LORA)['matched_modules']),14)
        names.pop()
        with self.assertRaises(RuntimeError):r.lora_coverage(model,h.LORA)
    def test_new_namespace_budget_and_no_reduction_of_science(self):
        self.assertEqual(h.CAP,25)
        self.assertEqual(h.SMOKE_STEPS,8)
        self.assertEqual(h.TRAIN['examples'],2000)
        self.assertEqual(h.ENGINE['max_num_seqs'],2)
        self.assertAlmostEqual(h.reservation('cpu'),.22852777777777777)
        self.assertGreater(sum(h.reservation(s) for s in ('cpu','smoke','pair','virtue')),20)
    def test_rehearsal_uses_real_training_entry_and_local_random_checkpoint(self):
        import inspect
        cpu=inspect.getsource(r.cpu_rehearsal);train=inspect.getsource(r.training_process)
        self.assertIn("__file__,'train'",cpu)
        self.assertIn('model.save_pretrained(checkpoint',cpu)
        self.assertIn('local_files_only',train)
        self.assertIn("max_steps=2 if rehearsal",train)
        self.assertLess(train.index("training-load.json"),train.index('get_peft_model(model'))
        self.assertIn('verify_adapter_reload(model',train)
        self.assertIn("lora_coverage(model,h.LORA)",train)
    def test_missing_rehearsal_proof_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cpu';p.mkdir();(p/'receipt.json').write_text('{}')
            with self.assertRaises(ValueError):h.require_cpu(d,dict(commit='a'*40,asset_sha256='b'*64))
