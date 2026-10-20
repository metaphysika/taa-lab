"""Free v02426 static science, persistence and no-retraining contracts."""
import ast
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02426 as h
from formation import study_d_gemma_stages_v02425 as old


def check():
    assets=ROOT/'studies/formation-study-d-gemma-stages-v02426';h.verify_assets(assets)
    assert h.ENGINE==old.ENGINE and h.TRAIN==old.TRAIN and h.LORA==old.LORA and h.PACKAGES==old.PACKAGES
    trees=[ast.parse((ROOT/f'scripts/study_d_gemma_stages_runtime_{v}.py').read_text()) for v in ('v02425','v02426')]
    nodes=[{n.name:n for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))} for t in trees]
    for name in nodes[0]:
        if name not in ('Serving','arm_worker'):
            assert ast.dump(nodes[0][name])==ast.dump(nodes[1][name]),'scientific/training path changed: '+name
    methods=[{n.name:n for n in tree['Serving'].body if isinstance(n,ast.FunctionDef)} for tree in nodes]
    for name in methods[0]:
        if name not in ('event','guard'):assert ast.dump(methods[0][name])==ast.dump(methods[1][name]),'Serving changed: '+name
    event=methods[1]['event'];assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='commit' for n in ast.walk(event)), 'event must never commit (especially under serving lock)'
    assert 'os.fsync' in ast.unparse(event) and '.flush()' in ast.unparse(event)
    assert 'self.volume.check()' in ast.unparse(methods[1]['guard'])
    runtime=ast.unparse(nodes[1]['BatchedVolume']);assert 'self.lock' not in runtime and 'interval=30' in ast.unparse(nodes[1]['BatchedVolume']).replace(' ', '')
    worker=ast.unparse(nodes[1]['arm_worker']);branch=next(n for n in ast.walk(nodes[1]['arm_worker']) if isinstance(n,ast.If) and ast.unparse(n.test)=="stage == 'neutral-completion'" and 'training' in ast.unparse(n))
    assert 'train_child' not in '\n'.join(ast.unparse(n) for n in branch.body)
    assert 'verify_reused_adapter' in worker and 'BatchedVolume(volume)' in worker
    continuation=ast.unparse(nodes[1]['neutral_completion']);assert '247053 + index + turn - 1' in continuation
    assert "u['status'] == 'untouched'" in continuation and 'score_acquisition' not in continuation
    app=(ROOT/'scripts/study_d_gemma_stages_app_v02426.py').read_text()
    assert "'VLLM_USE_FLASHINFER_SAMPLER':'0'" in app and 'modal.Volume.from_name(h.SOURCE_PRIVATE).read_only()' in app
    assert app.index('h.verify_reused_adapter')<app.index("ledger.put(stage+'/once'")<app.index('calls={arm:worker.spawn')
    assert h.reservation('neutral-completion')<3.33 and h.CAP==36 and h.PRIOR==18.52
    print('PASS: frozen science/config/seeds/training; read-only reuse; no event commit; 30s timer; neutral untouched-only')


if __name__=='__main__':check()
