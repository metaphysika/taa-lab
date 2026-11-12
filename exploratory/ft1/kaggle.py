"""Local Kaggle FT1 staging only. No Kaggle executable or network import."""
import hashlib
import json
import re
from pathlib import Path
from . import data, plan


def verify_data(folder):
    folder=Path(folder)
    raw=(folder/'manifest.json').read_bytes()
    manifest=json.loads(raw)
    if manifest.get('tokenizer_verified') is not True:
        raise ValueError('real Gemma tokenizer data manifest required')
    data.matching(manifest['token_table'])
    expected={f'arm-{a}.jsonl' for a in data.ARMS}|{'acquisition.json'}
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


def stage(folder,arm,seed,repo_commit,data_folder):
    config=configuration(arm,seed,repo_commit,verify_data(data_folder))
    manifest=json.loads((Path(data_folder)/'manifest.json').read_bytes())
    config['arm_data_sha256']=manifest['sha256'][f'arm-{arm}.jsonl']
    config['mounts']=dict(repo='/kaggle/input/taa-ft1-repo',data='/kaggle/input/taa-ft1-data',model='LOCAL_GEMMA_MODEL_MOUNT')
    config['execution']='plan only; separate exact-commit owner approval required'
    folder=data.safe_output(folder); folder.mkdir(parents=True)
    # The staged notebook deliberately has no executable training cell.
    # Owner-approved future runner calls prepare()/train() after separate binding.
    source='import sys\nsys.path.insert(0, "/kaggle/input/taa-ft1-repo")\nfrom exploratory.ft1.kaggle import configuration\nCONFIG = '+repr(config)+'\nprint(CONFIG)\n'
    notebook=dict(nbformat=4,nbformat_minor=5,metadata={},
                  cells=[dict(cell_type='code',execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    (folder/'ft1_plan.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    (folder/'ft1-binding.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (folder/'kernel-metadata.json').write_text(json.dumps(dict(title=f"FT1 {arm} seed {seed} plan",
         code_file='ft1_plan.ipynb',language='python',kernel_type='notebook',is_private=True,
         enable_gpu=True,enable_internet=False,dataset_sources=[],model_sources=[]),indent=2),encoding='utf-8')
    return config


def prepare(model_path,seed,retain):
    """Future injected local-only model preparation; never called by plan CLI."""
    import torch,transformers,peft
    from exploratory.k2_kaggle import core,ft0b
    core.check_stack(); ft0b.check_internals()
    if seed not in plan.SEEDS: raise ValueError('unplanned seed')
    if torch.cuda.device_count()!=1: raise ValueError('one visible GPU required')
    transformers.set_seed(seed)  # BEFORE LoRA initialization.
    tokenizer=transformers.AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=False)
    model=core.load_model('gemma-3-12b-it',transformers,model_path,
       quantization_config=transformers.BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
         bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16),device_map={'':0})
    model=peft.prepare_model_for_kbit_training(model)
    model=peft.get_peft_model(model,peft.LoraConfig(r=8,lora_alpha=16,lora_dropout=0,bias='none',
          task_type='CAUSAL_LM',target_modules=core.lora_targets('gemma-3-12b-it',[n for n,_ in model.named_modules()])))
    model.config.use_cache=False
    retain(dict(event='ft1_prepared',seed=seed,recipe=core.RECIPE,layout='ft0b'))
    return model,tokenizer


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--plan',action='store_true',required=True)
    p.add_argument('--mode',choices=['ft1'],default='ft1')
    p.add_argument('--arm',required=True); p.add_argument('--seed',type=int,required=True)
    p.add_argument('--repo-commit',required=True); p.add_argument('--data',required=True); p.add_argument('--output',required=True)
    a=p.parse_args()
    print(json.dumps(stage(a.output,a.arm,a.seed,a.repo_commit,a.data),indent=2))
