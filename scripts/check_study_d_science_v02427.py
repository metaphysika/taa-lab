"""Free virtue-only operational revision contract. No Modal or scientific calls."""
import ast
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02427 as h
from formation import study_d_gemma_stages_v02426 as old


def check():
    h.verify_assets(ROOT/'studies/formation-study-d-gemma-stages-v02427')
    for name in ('ENGINE','TRAIN','LORA','PACKAGES'):assert getattr(h,name)==getattr(old,name),name
    assert (ROOT/'scripts/study_d_gemma_stages_runtime_v02427.py').read_bytes()==(ROOT/'scripts/study_d_gemma_stages_runtime_v02426.py').read_bytes()
    assert list(h.STAGES)==['virtue'] and h.STAGES['virtue']['software']==9600 and h.STAGES['virtue']['timeout']==9800
    assert h.CAP==36 and h.PRIOR==19.67 and h.CREDIT==10.39
    assert abs(h.reservation('virtue')-9.194555555555556)<1e-12
    app=(ROOT/'scripts/study_d_gemma_stages_app_v02427.py').read_text()
    assert "modal.Volume.from_name('taa-study-d-gemma-v02426-evidence').read_only()" in app
    assert app.index('composite=repair.repair_composite')<app.index('h.require_previous')<app.index("ledger.put(stage+'/once'")<app.index('worker.spawn')
    assert "source_ledger.get('pair/closed')" in app and 'source_ledger.put' not in app
    old_tree=ast.parse((ROOT/'formation/study_d_gemma_stages_v02426.py').read_text())
    new_tree=ast.parse((ROOT/'formation/study_d_gemma_stages_v02427.py').read_text())
    functions=lambda t:{n.name:ast.dump(n) for n in t.body if isinstance(n,ast.FunctionDef)}
    before,after=functions(old_tree),functions(new_tree)
    for name in ('planned_bounds','acquisition_decisions','graph_kv','verify_reused_adapter','neutral_union'):
        assert before[name]==after[name],name
    print('PASS: virtue only; unchanged runtime/science; CPU repaired composite verified before reservation; read-only source')


if __name__=='__main__':check()
