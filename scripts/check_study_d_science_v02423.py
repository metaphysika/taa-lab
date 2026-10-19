"""Free offline CI contract for the selected science serving path; no GPU imports."""
import ast
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02423 as h
from formation import study_d_gemma_stages_v02420 as old


def check(source=None):
    source=source or (ROOT/'scripts/study_d_gemma_stages_runtime_v02423.py').read_text()
    tree=ast.parse(source)
    serving=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Serving')
    init=next(n for n in serving.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    text=ast.unparse(init)
    assert text.index('guard.configure()')<text.index('from vllm import LLM')
    assert 'EngineArgs(**h.ENGINE)' in text
    assert text.index('guard.check_log(native)')<text.index('self.engine.add_lora')
    assert 'h.graph_kv' in text and 'torch.cuda.mem_get_info()' in text
    assert 'cudagraph_specialize_lora' in text and 'cudagraph_capture_sizes' in text
    assert 'LoRARequest' in text and 'self.engine.add_lora(self.adapter)' in text
    assert 'reset_prefix_cache' not in source  # Retain KV prefixes throughout each arm worker.
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            assert not any(v in name for v in ('merge_and_unload','merge_adapter','merge_and_check')),'merged weights forbidden'
            if isinstance(node.func,ast.Name) and node.func.id=='EngineArgs':
                assert ast.unparse(node)=='EngineArgs(**h.ENGINE)','unreviewed serving config'
            if isinstance(node.func,ast.Attribute) and node.func.attr=='Popen':
                assert any(k.arg=='env' and ast.unparse(k.value)=='child_env' for k in node.keywords),'unguarded child env'
    assert "child_env=module('sampler_guard','sampler_guard.py').child_env(os.environ)" in source
    assert h.ENGINE==dict(old.ENGINE,enforce_eager=False,enable_prefix_caching=True,
        compilation_config=dict(cudagraph_specialize_lora=True,cudagraph_capture_sizes=[1,2],max_cudagraph_capture_size=2))
    assert h.ENGINE['model']==h.MODEL and h.ENGINE['revision']==h.REVISION and h.ENGINE['enable_lora'] is True
    assert h.LORA==old.LORA and h.TRAIN==old.TRAIN and h.PACKAGES==old.PACKAGES
    # Preserve request seeds, histories, scheduling, score/parser calls and acquisition gating.
    legacy=ast.parse((ROOT/'scripts/study_d_gemma_stages_runtime_v02420.py').read_text())
    def functions(t):
        return {n.name:n for n in t.body if isinstance(n,ast.FunctionDef)}
    old_f,new_f=functions(legacy),functions(tree)
    for name in ('end_of_turn_id','training_example','dataset','data_summary','expected_lora_architecture','lora_coverage','trainable_coverage','training_process','arm_worker'):
        assert ast.dump(old_f[name])==ast.dump(new_f[name]),'scientific function changed: '+name
    old_s=next(n for n in legacy.body if isinstance(n,ast.ClassDef) and n.name=='Serving')
    for name in ('generate','run','guard','event'):
        a=next(n for n in old_s.body if isinstance(n,ast.FunctionDef) and n.name==name)
        b=next(n for n in serving.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(a)==ast.dump(b),'scientific serving path changed: '+name
    import importlib.util
    spec=importlib.util.spec_from_file_location('seed_contract',ROOT/'scripts/check_study_d_sampler_v02422.py')
    seed_contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(seed_contract)
    assert seed_contract.seed_check(source)==1
    app=(ROOT/'scripts/study_d_gemma_stages_app_v02423.py').read_text()
    assert "'VLLM_USE_FLASHINFER_SAMPLER':'0'" in app
    assert set(h.STAGES)=={'pair','virtue'}
    print('PASS: exact live LoRA/graphs/retained-prefix science path, sampler guard, seeds and frozen scientific functions')


if __name__=='__main__':check()
