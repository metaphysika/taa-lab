"""Free v02425 inherited-asset, schema and unchanged science/serving contract."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02425 as h
from formation import study_d_gemma_stages_v02424 as old


def check():
    assets=ROOT/'studies/formation-study-d-gemma-stages-v02425'
    h.verify_assets(assets)
    for p in (ROOT/'studies/formation-study-d-gemma-stages-v02420').iterdir():
        if p.is_file():assert p.read_bytes()==(assets/p.name).read_bytes(),'inherited asset changed: '+p.name
    assert h.ENGINE==old.ENGINE and h.TRAIN==old.TRAIN and h.LORA==old.LORA and h.PACKAGES==old.PACKAGES
    before=ast.parse((ROOT/'scripts/study_d_gemma_stages_runtime_v02424.py').read_text())
    source=(ROOT/'scripts/study_d_gemma_stages_runtime_v02425.py').read_text();after=ast.parse(source)
    functions=lambda t:{n.name:n for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    previous,current=functions(before),functions(after)
    for name,node in previous.items():
        if name!='arm_worker':assert ast.dump(node)==ast.dump(current[name]),'runtime implementation changed: '+name
    worker=current['arm_worker'];branches=[n for n in ast.walk(worker) if isinstance(n,ast.If) and ast.unparse(n.test)=="stage == 'pair'"]
    assert len(branches)==1
    reuse=branches[0]
    assert 'verify_reused_adapter' in ast.unparse(reuse)
    assert 'train_child' not in '\n'.join(ast.unparse(n) for n in reuse.body)
    assert 'train_child' in '\n'.join(ast.unparse(n) for n in reuse.orelse)
    assert ast.unparse(worker).index('verify_reused_adapter')<ast.unparse(worker).index('session = Serving')
    old_worker=previous['arm_worker']
    # Actual frozen generation, acquisition, scheduling, parser/scorer and gate code,
    # moved into a callable production post-training path, rather than reimplemented.
    old_episode=next(n for n in ast.walk(old_worker) if isinstance(n,ast.FunctionDef) and n.name=='episode')
    post=current['post_training_arm']
    new_episode=next(n for n in ast.walk(post) if isinstance(n,ast.FunctionDef) and n.name=='episode')
    assert ast.dump(old_episode)==ast.dump(new_episode)
    old_checks=next(n for n in ast.walk(old_worker) if isinstance(n,ast.FunctionDef) and n.name=='checks')
    new_checks=next(n for n in ast.walk(post) if isinstance(n,ast.FunctionDef) and n.name=='checks')
    assert ast.dump(old_checks)==ast.dump(new_checks)
    old_else=next(n for n in ast.walk(old_worker) if isinstance(n,ast.If) and ast.unparse(n.test)=="stage == 'smoke'" and any(isinstance(x,ast.FunctionDef) and x.name=='checks' for x in n.orelse)).orelse
    body=post.body
    first=next(i for i,n in enumerate(body) if isinstance(n,ast.FunctionDef) and n.name=='checks')
    assert [ast.dump(n) for n in old_else]==[ast.dump(n) for n in body[first:-1]],'post-training scientific path differs'
    for n in ast.walk(after):
        if isinstance(n,ast.Call):assert not any(s in ast.unparse(n.func) for s in ('merge_and_unload','merge_adapter','merge_and_check'))
    spec=importlib.util.spec_from_file_location('seed_check',ROOT/'scripts/check_study_d_sampler_v02422.py')
    seeds=importlib.util.module_from_spec(spec);spec.loader.exec_module(seeds);assert seeds.seed_check(source)==1
    app=(ROOT/'scripts/study_d_gemma_stages_app_v02425.py').read_text()
    assert "modal.Volume.from_name(h.SOURCE_PRIVATE).read_only()" in app
    assert app.index("save('adapter-provenance/'")<app.index("ledger.put(stage+'/once'")<app.index('calls={arm:worker.spawn')
    assert "'VLLM_USE_FLASHINFER_SAMPLER':'0'" in app
    assert set(h.STAGES)=={'pair','virtue'} and h.CAP==36 and h.PRIOR==10.93
    print('PASS: ALL inherited assets/schema, served science path, read-only reuse/pre-load proof, no pair retraining, frozen config/seeds')


if __name__=='__main__':check()
