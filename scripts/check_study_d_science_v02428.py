"""Free exact science/runtime and CPU-controller resource contracts."""
import ast
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02428 as h
from formation import study_d_gemma_stages_v02427 as old


def check():
    h.verify_assets(ROOT/'studies/formation-study-d-gemma-stages-v02428')
    for name in ('ENGINE','TRAIN','LORA','PACKAGES','STAGES'):assert getattr(h,name)==getattr(old,name),name
    assert (ROOT/'scripts/study_d_gemma_stages_runtime_v02428.py').read_bytes()==(ROOT/'scripts/study_d_gemma_stages_runtime_v02427.py').read_bytes()
    assert (h.CONTROLLER_CPU,h.CONTROLLER_MEMORY_MB,h.PRIOR,h.CREDIT,h.CAP)==(1.0,2048,19.67,10.38,36)
    app=(ROOT/'scripts/study_d_gemma_stages_app_v02428.py').read_text()
    assert 'cpu=(h.CONTROLLER_CPU,h.CONTROLLER_CPU),memory=(h.CONTROLLER_MEMORY_MB,h.CONTROLLER_MEMORY_MB)' in app
    assert app.index('budget=admission.admit')<app.index("ledger.put(stage+'/once'")<app.index('worker.spawn')
    assert 'folder.exists()' not in app and "save('../pair" not in app
    tree=ast.parse((ROOT/'formation/study_d_gemma_stages_v02428.py').read_text())
    previous=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require_previous')
    assert not any(isinstance(n,ast.Attribute) and n.attr=='repair_composite' for n in ast.walk(previous))
    provenance=(ROOT/'scripts/study_d_gemma_provenance_v02428.py').read_text()
    assert '.open() as journal:' in provenance and 'starts.add(key)' in provenance
    assert "starts[key]=e" not in provenance and "returns[key]=e" not in provenance
    print('PASS: exact science/runtime/worker guard; 1 CPU/2048MB controller; streaming single repair; explicit root path')


if __name__=='__main__':check()
