"""Local Kaggle FT1 staging only. No Kaggle executable or network import."""
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from . import data, plan


def verify_data(folder):
    folder=Path(folder)
    raw=(folder/'manifest.json').read_bytes()
    manifest=json.loads(raw)
    if manifest.get('tokenizer_verified') is not True:
        raise ValueError('real Gemma tokenizer data manifest required')
    data.matching(manifest['token_table'])
    expected={f'arm-{a}.jsonl' for a in data.ARMS}|set(data.PROBE_FILES.values())
    if set(manifest['sha256'])!=expected: raise ValueError('incomplete data inventory')
    for name,digest in manifest['sha256'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('data binding mismatch')
    return hashlib.sha256(raw).hexdigest()


def configuration(arm,seed,repo_commit,data_manifest_sha256):
    if (arm,seed) not in plan.MODELS[1:]: raise ValueError('unplanned arm/seed')
    if not re.fullmatch('[a-f0-9]{40}',repo_commit): raise ValueError('exact commit required')
    if not re.fullmatch('[a-f0-9]{64}',data_manifest_sha256): raise ValueError('data hash required')
    return dict(mode='ft1',plan_only=True,approved=False,arm=arm,seed=seed,repo_commit=repo_commit,
                data_manifest_sha256=data_manifest_sha256,model='gemma-3-12b-it',
                recipe=plan.core.RECIPE,layout='ft0b',max_skipped_updates=25,
                loss_log_fields=['action_sum','action_count','reason_sum','reason_count'],
                data_order_sha256=hashlib.sha256(data.dump(plan.order(seed)).encode()).hexdigest())


def stage(folder,arm,seed,repo_commit,data_folder,qualification=False,
          model_source=None,repo_dataset=None,data_dataset=None,owner=None,receipt_dataset=None):
    if not all((model_source,repo_dataset,data_dataset,owner,receipt_dataset)):
        raise ValueError('versioned model source, repo/data datasets and owner are required')
    plan.core.validate_model_source(model_source,'gemma-3-12b-it')
    if not re.fullmatch('[a-z0-9_-]+',owner) or any(
            not re.fullmatch('[a-z0-9_-]+/[a-z0-9_-]+',v) for v in (repo_dataset,data_dataset,receipt_dataset)):
        raise ValueError('invalid Kaggle owner/dataset handles')
    config=configuration(arm,seed,repo_commit,verify_data(data_folder))
    manifest=json.loads((Path(data_folder)/'manifest.json').read_bytes())
    config['arm_data_sha256']=manifest['sha256'][f'arm-{arm}.jsonl']
    config['acquisition_file']=data.PROBE_FILES[arm]
    config['acquisition_sha256']=manifest['sha256'][data.PROBE_FILES[arm]]
    config['mounts']=dict(repo_commit_marker='COMMIT.txt',data_manifest_sha256=config['data_manifest_sha256'],
                          model='/kaggle/input/models/'+model_source)
    config['model_source']=model_source
    config['receipt_path']='/kaggle/input/datasets/'+receipt_dataset+'/receipt.json'
    config['execution']='plan only; separate exact-commit owner approval required'
    config['phase']='qualify' if qualification else 'train'
    if qualification and arm!='3': raise ValueError('qualification uses arm 3')
    config['optimizer_steps']=10 if qualification else 250
    config['source_sha256']=source_inventory(repo_commit)
    folder=data.safe_output(folder); folder.mkdir(parents=True)
    # Executable later, but PLAN_ONLY and a separate phase receipt both gate training.
    source=('import sys, os, json, hashlib\nfrom pathlib import Path\n'
            'PLAN_ONLY = True\n'
            'CONFIG = '+repr(config)+'\n'
            'OUTPUT = "/kaggle/working/ft1-'+arm+'-'+str(seed)+'-'+config['phase']+'"\n'
            'APPROVAL_RECEIPT = CONFIG["receipt_path"]\n'
            'if PLAN_ONLY:\n    print(CONFIG)\n'
            'else:\n'
            '    os.environ["CUDA_VISIBLE_DEVICES"] = "0"\n'
            '    repos = [p.parent for p in Path("/kaggle/input").rglob("COMMIT.txt") if p.read_text().strip()==CONFIG["repo_commit"]]\n'
            '    datasets = [p.parent for p in Path("/kaggle/input").rglob("manifest.json") if hashlib.sha256(p.read_bytes()).hexdigest()==CONFIG["data_manifest_sha256"]]\n'
            '    if len(repos)!=1 or len(datasets)!=1: raise ValueError("missing or ambiguous hash-bound mounts")\n'
            '    sys.path.insert(0, str(repos[0]))\n'
            '    from exploratory.ft1.runner import run\n'
            '    receipt = json.loads(Path(APPROVAL_RECEIPT).read_text())\n'
            '    run(CONFIG, CONFIG["mounts"]["model"], datasets[0], OUTPUT, receipt)\n')
    notebook=dict(nbformat=4,nbformat_minor=5,metadata={},
                  cells=[dict(cell_type='code',execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    (folder/'ft1_plan.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    (folder/'ft1-binding.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (folder/'kernel-metadata.json').write_text(json.dumps(dict(id=f'{owner}/ft1-{arm}-{seed}-'+config['phase'],title=f"FT1 {arm} seed {seed} plan",
         code_file='ft1_plan.ipynb',language='python',kernel_type='notebook',is_private=True,
         enable_gpu=True,enable_internet=False,dataset_sources=[repo_dataset,data_dataset,'metaphysika/k2-wheels',receipt_dataset],model_sources=[model_source]),indent=2),encoding='utf-8')
    return config


def source_inventory(commit):
    root=Path(__file__).resolve().parents[2]
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'exploratory/ft1'],cwd=root,text=True).splitlines()
    names=[n for n in names if n.endswith('.py')]+['exploratory/k2_kaggle/'+n for n in ('core.py','ft0.py','ft0b.py')]
    return {name:hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=root)).hexdigest() for name in names}


def prepare(model_path,seed,retain,check=lambda:None):
    """Future injected local-only model preparation; never called by plan CLI."""
    from exploratory.k2_kaggle import core,ft0b
    started=time.monotonic()
    check()
    retain(dict(event='local_wheels',sha256=core.install_wheels()))
    packages=core.check_stack(); ft0b.check_internals()
    import torch,transformers,peft
    model_path=core.resolve_model_path(model_path)
    if seed not in plan.SEEDS: raise ValueError('unplanned seed')
    if torch.cuda.device_count()!=1: raise ValueError('one visible GPU required')
    transformers.set_seed(seed)  # BEFORE LoRA initialization.
    tokenizer=transformers.AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
    check()
    model=core.load_model('gemma-3-12b-it',transformers,model_path,
       quantization_config=transformers.BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
         bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16),device_map={'':0})
    check()
    model=peft.prepare_model_for_kbit_training(model)
    model=peft.get_peft_model(model,peft.LoraConfig(r=8,lora_alpha=16,lora_dropout=0,bias='none',
          task_type='CAUSAL_LM',target_modules=core.lora_targets('gemma-3-12b-it',[n for n,_ in model.named_modules()])))
    check()
    model.config.use_cache=False
    retain(dict(event='ft1_prepared',seed=seed,recipe=core.RECIPE,layout='ft0b',packages=packages,
                gpu=torch.cuda.get_device_name(0),visible_gpus=torch.cuda.device_count(),
                setup_seconds=time.monotonic()-started,loaded_class=type(model.get_base_model()).__name__))
    return model,tokenizer


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--plan',action='store_true',required=True)
    p.add_argument('--mode',choices=['ft1'],default='ft1')
    p.add_argument('--qualification',action='store_true'); p.add_argument('--arm',required=True); p.add_argument('--seed',type=int,required=True)
    p.add_argument('--model-source',required=True); p.add_argument('--repo-dataset',required=True)
    p.add_argument('--receipt-dataset',required=True); p.add_argument('--data-dataset',required=True); p.add_argument('--owner',required=True)
    p.add_argument('--repo-commit',required=True); p.add_argument('--data',required=True); p.add_argument('--output',required=True)
    a=p.parse_args()
    print(json.dumps(stage(a.output,a.arm,a.seed,a.repo_commit,a.data,a.qualification,a.model_source,a.repo_dataset,a.data_dataset,a.owner,a.receipt_dataset),indent=2))
