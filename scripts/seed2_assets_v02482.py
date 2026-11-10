"""Offline generation of seed 2 order and source index; never contacts a backend."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_stages_v02482 as h
from formation.seed2_order_v02482 import encode


def canonical(path):
    return path.read_bytes().replace(b'\r\n',b'\n')


def build():
    folder=ROOT/'studies/formation-study-d-gemma-stages-v02482'
    folder.mkdir(exist_ok=True)
    old=ROOT/'studies/formation-study-d-gemma-stages-v02424'
    # Copy only recipe/probe assets used by the new runtime, with canonical Git LF bytes.
    names=('bundle.json','plan.json','ci-pinned-config.json','ci-served-token-fixture.json',
           'contrary-2000-train.jsonl','neutral-2000-train.jsonl','virtue-2000-train.jsonl',
           'neutral-acquisition.json','ordered-acquisition.json','observed-stop-v02416.json','vllm-logging.json')
    for name in names:(folder/name).write_bytes(canonical(old/name))
    (folder/'training-order.json').write_bytes(encode(h.SHUFFLE_SEED,h.TRAIN_SEED))
    def write(name,value):
        (folder/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    write('stages.json',dict(version=h.VERSION,approved=False,training=h.TRAIN,lora=h.LORA,
        engine=h.ENGINE,stages=h.STAGES,training_cap_usd=8,evaluation_cap_usd=5))
    frozen=[str(p.relative_to(ROOT)).replace('\\','/') for p in old.iterdir() if p.is_file()]
    frozen+=['formation/study_d_gemma_stages_v02424.py','scripts/study_d_gemma_stages_runtime_v02424.py']
    preservation={name:hashlib.sha256(subprocess.check_output(['git','show','40c77e66:'+name],cwd=ROOT)).hexdigest() for name in frozen}
    write('seed1-preservation.json',preservation)
    app=ast.parse((ROOT/'scripts/study_d_gemma_stages_app_v02482.py').read_text())
    copies=ast.literal_eval(next(n.value for n in ast.walk(app) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='copies' for t in n.targets)))
    sources=set(copies.values())|{'scripts/formation_study_d_gemma_stages_v02482.py',
        'scripts/study_d_gemma_stages_app_v02482.py','scripts/study_d_gemma_stages_entry_v02482.py',
        'scripts/study_d_gemma_submission_v02416.py','scripts/seed2_assets_v02482.py','formation/seed2_order_v02482.py'}
    digest=lambda p:hashlib.sha256(canonical(p)).hexdigest()
    # Hash only the active roster. Other copied archival files are never interpreted.
    active=set(names)|{'training-order.json','stages.json','seed1-preservation.json'}
    write('integrity.json',dict(version=h.VERSION,sha256={n:digest(folder/n) for n in sorted(active)},
        code_sha256={n:digest(ROOT/n) for n in sorted(sources)},
        remote_code_sha256={dest:digest(ROOT/source) for dest,source in copies.items()}))


if __name__=='__main__':build()
