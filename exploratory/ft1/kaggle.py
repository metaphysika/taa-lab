"""Local Kaggle FT1 staging only. No Kaggle executable or network import."""
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from . import data, ft1r_data, mounts, plan, plan_ft1r


def verify_data(folder, layout=None):
    if layout not in (None, data.FT1R_LAYOUT):
        raise ValueError('training data layout mismatch')
    folder=Path(folder)
    raw=(folder/'manifest.json').read_bytes()
    manifest=json.loads(raw)
    if manifest.get('tokenizer_verified') is not True:
        raise ValueError('real Gemma tokenizer data manifest required')
    data.matching(manifest['token_table'])
    expected={f'arm-{a}.jsonl' for a in data.ARMS}|set(data.PROBE_FILES.values())
    if manifest.get('layout') != layout:
        raise ValueError('training data layout mismatch')
    if layout == data.FT1R_LAYOUT:
        if not re.fullmatch('[a-f0-9]{64}', manifest.get('tokenizer_sha256', '')):
            raise ValueError('FT1-R tokenizer hash required')
        quote_gate = manifest.get('quote_gate', {})
        if quote_gate.get('passed') is not True or not ft1r_data.meets_quote_minimums(
                quote_gate.get('targets', {})):
            raise ValueError('FT1-R quoted-line data gate required')
        expected = {f'arm-{a}.jsonl' for a in ft1r_data.ARMS} | {ft1r_data.PROBE_FILE}
    if set(manifest['sha256'])!=expected: raise ValueError('incomplete data inventory')
    for name,digest in manifest['sha256'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('data binding mismatch')
    return hashlib.sha256(raw).hexdigest()


def configuration(arm,seed,repo_commit,data_manifest_sha256):
    if ((arm,seed) not in plan.MODELS[1:] and (arm,seed) != plan.SUPPLEMENTARY_MODEL
            and (arm,seed) not in plan_ft1r.TRAINING_ORDER): raise ValueError('unplanned arm/seed')
    if not re.fullmatch('[a-f0-9]{40}',repo_commit): raise ValueError('exact commit required')
    if not re.fullmatch('[a-f0-9]{64}',data_manifest_sha256): raise ValueError('data hash required')
    config = dict(mode='ft1',plan_only=True,approved=False,arm=arm,seed=seed,repo_commit=repo_commit,
                data_manifest_sha256=data_manifest_sha256,model='gemma-3-12b-it',
                recipe=plan.core.RECIPE,layout='ft0b',max_skipped_updates=25,
                loss_log_fields=['action_sum','action_count','reason_sum','reason_count'],
                data_order_sha256=hashlib.sha256(data.dump(plan.order(seed)).encode()).hexdigest())

    if (arm, seed) in plan_ft1r.TRAINING_ORDER:
        config['data_layout'] = data.FT1R_LAYOUT
    return config


def stage(folder,arm,seed,repo_commit,data_folder,qualification=False,
          model_source=None,repo_dataset=None,data_dataset=None,owner=None,receipt_dataset=None,
          first_gate_file=None,first_gate_dataset=None,first_training_folder=None,first_training_dataset=None,
          second_gate_file=None,second_gate_dataset=None,second_training_folder=None,second_training_dataset=None):
    if not all((model_source,repo_dataset,data_dataset,owner,receipt_dataset)):
        raise ValueError('versioned model source, repo/data datasets and owner are required')
    plan.core.validate_model_source(model_source,'gemma-3-12b-it')
    if not re.fullmatch('[a-z0-9_-]+',owner) or any(
            not re.fullmatch('[a-z0-9_-]+/[a-z0-9_-]+',v) for v in (repo_dataset,data_dataset,receipt_dataset)):
        raise ValueError('invalid Kaggle owner/dataset handles')
    cell = arm, seed
    is_ft1r = cell in plan_ft1r.TRAINING_ORDER
    layout = data.FT1R_LAYOUT if is_ft1r else None
    config=configuration(arm,seed,repo_commit,verify_data(data_folder, layout) if is_ft1r else verify_data(data_folder))
    if is_ft1r and qualification:
        raise ValueError('FT1-R has no qualification phase')
    datasets = [repo_dataset,data_dataset,'metaphysika/k2-wheels',receipt_dataset]
    required = plan_ft1r.required_gates(cell) if is_ft1r else ()
    if required:
        config.update(plan_ft1r.require_first_gate(cell, first_gate_file, first_training_folder,
                                                  config['data_manifest_sha256'],
                                                  second_gate_file=second_gate_file,
                                                  second_training_folder=second_training_folder))
    for stage_name, inputs in (
            ('first', (first_gate_file, first_training_folder, first_gate_dataset, first_training_dataset)),
            ('second', (second_gate_file, second_training_folder, second_gate_dataset, second_training_dataset))):
        if stage_name in required:
            if any(not re.fullmatch('[a-z0-9_-]+/[a-z0-9_-]+', handle or '') for handle in inputs[2:]):
                raise ValueError(f'versioned {stage_name} gate and training datasets required')
            datasets.extend(inputs[2:])
        elif any(value is not None for value in inputs):
            raise ValueError(f'unexpected {stage_name} gate input')
    manifest=json.loads((Path(data_folder)/'manifest.json').read_bytes())
    config['arm_data_sha256']=manifest['sha256'][f'arm-{arm}.jsonl']
    config['acquisition_file']=ft1r_data.PROBE_FILE if is_ft1r else data.PROBE_FILES[arm]
    config['acquisition_sha256']=manifest['sha256'][config['acquisition_file']]
    config['mounts']=dict(repo_commit_marker='COMMIT.txt',data_manifest_sha256=config['data_manifest_sha256'],
                          model='/kaggle/input/models/'+model_source)
    config['model_source']=model_source
    config['receipt_dataset']=receipt_dataset
    config['receipt_slug']=mounts.receipt_slug(receipt_dataset)  # searched for at run time, never a fixed path
    config['execution']='plan only; separate exact-commit owner approval required'
    config['phase']='qualify' if qualification else 'train'
    if qualification and arm!='3': raise ValueError('qualification uses arm 3')
    config['optimizer_steps']=10 if qualification else 250
    config['source_sha256'] = source_inventory(repo_commit, include_sealed=False) if is_ft1r else source_inventory(repo_commit)
    folder=data.safe_output(folder); folder.mkdir(parents=True)
    # Executable later, but PLAN_ONLY and a separate phase receipt both gate training.
    source=('import sys, os, json, hashlib\nfrom pathlib import Path\n'
            'PLAN_ONLY = True\n'
            'CONFIG = '+repr(config)+'\n'
            'OUTPUT = "/kaggle/working/ft1-'+arm+'-'+str(seed)+'-'+config['phase']+'"\n'
            'if PLAN_ONLY:\n    print(CONFIG)\n'
            'else:\n'
            '    os.environ["CUDA_VISIBLE_DEVICES"] = "0"\n'
            '    repos = [p.parent for p in Path("/kaggle/input").rglob("COMMIT.txt") if p.read_text().strip()==CONFIG["repo_commit"]]\n'
            '    datasets = [p.parent for p in Path("/kaggle/input").rglob("manifest.json") if hashlib.sha256(p.read_bytes()).hexdigest()==CONFIG["data_manifest_sha256"]]\n'
            '    if len(repos)!=1 or len(datasets)!=1: raise ValueError("missing or ambiguous hash-bound mounts")\n'
            '    sys.path.insert(0, str(repos[0]))\n'
            '    from exploratory.ft1.runner import run\n'
            '    from exploratory.ft1.mounts import find_receipt\n'
            '    receipt = json.loads(find_receipt("/kaggle/input", CONFIG["receipt_slug"]).read_text())\n'
            '    run(CONFIG, CONFIG["mounts"]["model"], datasets[0], OUTPUT, receipt)\n')
    if required:
        source = source.replace('    run(CONFIG, CONFIG["mounts"]["model"], datasets[0], OUTPUT, receipt)\n',
            '    from exploratory.ft1.plan_ft1r import FirstGateDecisionRequired\n'
            '    prerequisites = {}\n'
            f'    for stage in {required!r}:\n'
            '        gates = [p for p in Path("/kaggle/input").rglob("gate.json") if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == CONFIG[stage + "_gate_sha256"]]\n'
            '        training = [p.parent for p in Path("/kaggle/input").rglob("manifest.json") if hashlib.sha256(p.read_bytes()).hexdigest() == CONFIG[stage + "_training_manifest_sha256"]]\n'
            '        if len(gates) != 1 or len(training) != 1: raise FirstGateDecisionRequired(f"Missing or ambiguous {stage} gate or adapter. Stop for Chris.")\n'
            '        prerequisites[stage + "_gate_file"] = gates[0]\n'
            '        prerequisites[stage + "_training_folder"] = training[0]\n'
            '    run(CONFIG, CONFIG["mounts"]["model"], datasets[0], OUTPUT, receipt, **prerequisites)\n')
    notebook=dict(nbformat=4,nbformat_minor=5,metadata={'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
                  cells=[dict(cell_type='code',execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    (folder/'ft1_plan.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    (folder/'ft1-binding.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (folder/'kernel-metadata.json').write_text(json.dumps(dict(id=f'{owner}/ft1-{arm}-{seed}-'+config['phase'],title=f'ft1-{arm}-{seed}-'+config['phase'],
         code_file='ft1_plan.ipynb',language='python',kernel_type='notebook',is_private=True,
         enable_gpu=True,enable_internet=False,dataset_sources=datasets,model_sources=[model_source]),indent=2),encoding='utf-8')
    return config


def source_inventory(commit, *, include_sealed=True):
    root=Path(__file__).resolve().parents[2]
    if include_sealed:
        names=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'exploratory/ft1'],cwd=root,text=True).splitlines()
    else:
        modules = ('__init__', 'data', 'data_diagnostics', 'evaluate_runner', 'evaluate_stage',
                   'evaluation', 'ft1r_data', 'kaggle', 'memory', 'mounts', 'plan', 'plan_ft1r',
                   'qualification', 'runner', 'scoring', 'selection', 'training')
        names = [f'exploratory/ft1/{name}.py' for name in modules]
        names.append('exploratory/ft1/selection_expected.json')
    names=[n for n in names if n.endswith(('.py','selection_expected.json'))]+['exploratory/k2_kaggle/'+n for n in ('core.py','ft0.py','ft0b.py')]
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
    if seed not in (*plan.SEEDS, *plan_ft1r.SEEDS): raise ValueError('unplanned seed')
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
    p.add_argument('--first-gate-file'); p.add_argument('--first-gate-dataset')
    p.add_argument('--first-training-folder'); p.add_argument('--first-training-dataset')
    p.add_argument('--second-gate-file'); p.add_argument('--second-gate-dataset')
    p.add_argument('--second-training-folder'); p.add_argument('--second-training-dataset')
    a=p.parse_args()
    args = vars(a)
    args.pop('plan')
    args.pop('mode')
    args['folder'] = args.pop('output')
    args['data_folder'] = args.pop('data')
    print(json.dumps(stage(**args), indent=2))
