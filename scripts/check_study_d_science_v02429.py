"""Free frozen serving/worker acquisition/no-training contracts."""
import ast
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02429 as h
from formation import study_d_gemma_stages_v02428 as old


def function(source,name):
    return next(n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)


def check():
    h.verify_assets(ROOT/'studies/formation-study-d-gemma-stages-v02429')
    for name in ('ENGINE','TRAIN','LORA','PACKAGES'):assert getattr(h,name)==getattr(old,name),name
    new=(ROOT/'scripts/study_d_gemma_stages_runtime_v02429.py').read_text()
    prior=(ROOT/'scripts/study_d_gemma_stages_runtime_v02428.py').read_text()
    for name in ('Serving','BatchedVolume','training_example','dataset'):
        assert ast.dump(function(new,name))==ast.dump(function(prior,name)),name
    assert ast.dump(function((ROOT/'formation/study_d_gemma_stages_v02429.py').read_text(),'acquisition_decisions'))==ast.dump(function((ROOT/'formation/study_d_gemma_stages_v02428.py').read_text(),'acquisition_decisions'))
    worker=function(new,'arm_worker')
    calls=[n.func for n in ast.walk(worker) if isinstance(n,ast.Call)]
    assert not any(isinstance(n,ast.Name) and n.id in ('train_child','training_process') for n in calls)
    app=(ROOT/'scripts/study_d_gemma_stages_app_v02429.py').read_text()
    tree=ast.parse(app);controller=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='controller')
    assert not any(isinstance(n,(ast.While,ast.For,ast.AsyncFor)) for n in ast.walk(controller))
    assert 'call.get(' not in app and 'time.sleep(' not in app and 'acquisition_decisions(' not in app
    assert app.index('budget=admission.admit')<app.index("ledger.put(stage+'/once'")<app.index("save('reservation.json'")<app.index('worker.spawn')
    assert "private=modal.Volume.from_name(h.SOURCE_PRIVATE).read_only()" in app
    assert "taa-study-d-gemma-v02428-private-adapters').read_only()" in app
    assert (h.PRIOR,h.CREDIT,h.CAP)==(22.73,7.41,36)
    assert (h.STAGES['virtue']['software'],h.STAGES['virtue']['timeout'])==(4800,5000)
    assert "post_training_arm(session" in new
    print('PASS: identical scientific assets/settings/serving; serving-only worker; controller submits and returns; read-only adapter')


if __name__=='__main__':check()
