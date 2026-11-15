"""Plan-only evaluation notebook staging; no network operations."""
import json
import re
import hashlib
import subprocess
from pathlib import Path
from . import data, kaggle, mounts, plan
from .evaluate_runner import adapter_binding


def stage(output, arm, seed, commit, data_folder, sealed_sha256, part, model_source,
          repo_dataset, data_dataset, sealed_dataset, receipt_dataset, owner,
          training_folder=None, training_dataset=None):
    if (arm,seed) not in plan.MODELS or part not in range(4):
        raise ValueError('unplanned model or part')
    if not re.fullmatch('[a-f0-9]{40}',commit) or not re.fullmatch('[a-f0-9]{64}',sealed_sha256):
        raise ValueError('exact commit and sealed hash required')
    core = plan.core
    core.validate_model_source(model_source,'gemma-3-12b-it')
    datasets = [repo_dataset,data_dataset,sealed_dataset,receipt_dataset,'metaphysika/k2-wheels']
    if arm != 'base':
        if not training_dataset:
            raise ValueError('training dataset required')
        datasets.append(training_dataset)
        binding = adapter_binding(training_folder,arm,seed)
    else:
        if training_folder is not None or training_dataset is not None:
            raise ValueError('base has no adapter')
        binding = dict(adapter_sha256=None,training_manifest_sha256=None)
    if not re.fullmatch('[a-z0-9_-]+',owner) or any(not re.fullmatch('[a-z0-9_-]+/[a-z0-9_-]+',d) for d in datasets):
        raise ValueError('invalid dataset handle')
    config = dict(phase='evaluate',arm=arm,seed=seed,repo_commit=commit,part=part,
        data_manifest_sha256=kaggle.verify_data(data_folder),sealed_sha256=sealed_sha256,
        adapter_sha256=binding['adapter_sha256'],training_manifest_sha256=binding['training_manifest_sha256'],
        source_sha256=kaggle.source_inventory(commit),model_source=model_source,
        receipt_slug=mounts.receipt_slug(receipt_dataset))
    root = Path(__file__).resolve().parents[2]
    dependencies = subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'exploratory/step4_harness','exploratory/measurement_v02456','formation'],cwd=root,text=True).splitlines()
    for name in dependencies:
        if name.endswith('.py'):
            config['source_sha256'][name] = hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=root)).hexdigest()
    source = '''import os, sys, json
from pathlib import Path
PLAN_ONLY = True
CONFIG = CONFIG_VALUE
if PLAN_ONLY:
    print(CONFIG)
else:
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    repos = [p.parent for p in Path('/kaggle/input').rglob('COMMIT.txt') if p.read_text().strip() == CONFIG['repo_commit']]
    if len(repos) != 1: raise ValueError('missing or ambiguous repository')
    sys.path.insert(0,str(repos[0]))
    from exploratory.ft1.evaluate_runner import find_hash, run
    from exploratory.ft1.mounts import find_receipt
    data_folder = find_hash('/kaggle/input',CONFIG['data_manifest_sha256']).parent
    sealed = find_hash('/kaggle/input',CONFIG['sealed_sha256'])
    training = None if CONFIG['arm'] == 'base' else find_hash('/kaggle/input',CONFIG['training_manifest_sha256']).parent
    receipt = json.loads(find_receipt('/kaggle/input',CONFIG['receipt_slug']).read_bytes())
    run(CONFIG,'/kaggle/input/models/'+CONFIG['model_source'],data_folder,sealed,
        '/kaggle/working/ft1-evaluate-'+CONFIG['arm']+'-'+str(CONFIG['seed'])+'-'+str(CONFIG['part']),receipt,training)
'''.replace('CONFIG_VALUE',repr(config))
    folder = data.safe_output(output)
    folder.mkdir(parents=True)
    notebook = dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),
        cells=[dict(cell_type='code',execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    (folder/'ft1_evaluate.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    slug = f'ft1-eval-{arm}-{seed}-{part}'
    metadata = dict(id=owner+'/'+slug,title=slug,code_file='ft1_evaluate.ipynb',language='python',kernel_type='notebook',
        is_private=True,enable_gpu=True,enable_internet=False,dataset_sources=datasets,model_sources=[model_source])
    (folder/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    (folder/'binding.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan',action='store_true',required=True)
    for name in ('output','arm','commit','data-folder','sealed-sha256','model-source','repo-dataset','data-dataset','sealed-dataset','receipt-dataset','owner'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--part',type=int,required=True)
    parser.add_argument('--training-folder'); parser.add_argument('--training-dataset')
    args = vars(parser.parse_args()); args.pop('plan')
    print(json.dumps(stage(**args),indent=2))
