"""Plan-only evaluation notebook staging; no network operations."""
import json
import re
import hashlib
import subprocess
from pathlib import Path
from . import data, kaggle, mounts, plan
from .evaluate_runner import adapter_binding, prefill_options, attention_option


def stage(output, arm, seed, commit, data_folder, sealed_sha256, part, model_source,
          repo_dataset, data_dataset, sealed_dataset, receipt_dataset, owner,
          training_folder=None, training_dataset=None, phase="evaluate", gate_sha256=None,
          gate_dataset=None, part_count=2, prompt_ceiling=None, prefill_mode=None, prefill_chunk_size=None, attention=None):
    if (arm,seed) not in plan.MODELS or phase not in ('gate','evaluate') or type(part_count) is not int or not 1 <= part_count <= 24 or part not in range(part_count):
        raise ValueError('unplanned model or part')
    if not re.fullmatch('[a-f0-9]{40}',commit):
        raise ValueError('exact commit and sealed hash required')
    core = plan.core
    core.validate_model_source(model_source,'gemma-3-12b-it')
    datasets = [repo_dataset,data_dataset,receipt_dataset,'metaphysika/k2-wheels']
    if phase == 'evaluate':
        if not gate_dataset or not re.fullmatch('[a-f0-9]{64}',gate_sha256 or '') or not re.fullmatch('[a-f0-9]{64}',sealed_sha256 or ''):
            raise ValueError('sealed and gate hash/dataset required')
        datasets += [sealed_dataset,gate_dataset]
    elif any(v is not None for v in (sealed_sha256,sealed_dataset,gate_sha256,gate_dataset)):
        raise ValueError('gate phase has no sealed or prior gate input')
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
    if prompt_ceiling is not None and (type(prompt_ceiling) is not int or not 1 <= prompt_ceiling <= 16384):
        raise ValueError('invalid prompt ceiling')
    config = dict(prompt_ceiling=prompt_ceiling,phase=phase,arm=arm,seed=seed,repo_commit=commit,part=part if phase=='evaluate' else None,part_count=part_count if phase=='evaluate' else None,gate_sha256=gate_sha256,
        data_manifest_sha256=kaggle.verify_data(data_folder),sealed_sha256=sealed_sha256,
        adapter_sha256=binding['adapter_sha256'],training_manifest_sha256=binding['training_manifest_sha256'],
        source_sha256=kaggle.source_inventory(commit),model_source=model_source,
        receipt_slug=mounts.receipt_slug(receipt_dataset))
    settings = dict(prefill_mode=prefill_mode, prefill_chunk_size=prefill_chunk_size, attention=attention)
    prefill_options({k:v for k,v in settings.items() if v is not None})
    attention_option(settings)
    config.update({k:v for k,v in settings.items() if v is not None})
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
    from exploratory.ft1.evaluate_runner import find_hashes, run
    from exploratory.ft1.mounts import find_receipt
    targets = dict(data=CONFIG['data_manifest_sha256'])
    if CONFIG['phase'] == 'evaluate':
        targets.update(sealed=CONFIG['sealed_sha256'],gate=CONFIG['gate_sha256'])
    if CONFIG['arm'] != 'base': targets['training'] = CONFIG['training_manifest_sha256']
    found = find_hashes('/kaggle/input',targets)
    data_folder = found['data'].parent
    sealed = found.get('sealed')
    training = found['training'].parent if 'training' in found else None
    receipt = json.loads(find_receipt('/kaggle/input',CONFIG['receipt_slug']).read_bytes())
    run(CONFIG,'/kaggle/input/models/'+CONFIG['model_source'],data_folder,sealed,
        '/kaggle/working/ft1-'+CONFIG['phase']+'-'+CONFIG['arm']+'-'+str(CONFIG['seed'])+'-'+str(CONFIG['part']),receipt,training,gate_file=found.get('gate'))
'''.replace('CONFIG_VALUE',repr(config))
    folder = data.safe_output(output)
    folder.mkdir(parents=True)
    notebook = dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),
        cells=[dict(cell_type='code',execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    (folder/'ft1_evaluate.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    slug = f'ft1-{phase}-{arm}-{seed}-{part}'
    metadata = dict(id=owner+'/'+slug,title=slug,code_file='ft1_evaluate.ipynb',language='python',kernel_type='notebook',
        is_private=True,enable_gpu=True,enable_internet=False,dataset_sources=datasets,model_sources=[model_source])
    (folder/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    (folder/'binding.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan',action='store_true',required=True)
    for name in ('output','arm','commit','data-folder','model-source','repo-dataset','data-dataset','receipt-dataset','owner'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--part',type=int,default=0)
    parser.add_argument('--prompt-ceiling',type=int)
    parser.add_argument('--prefill-mode',choices=['current','chunked'])
    parser.add_argument('--prefill-chunk-size',type=int)
    parser.add_argument('--attention',choices=['eager','sdpa','default'])
    parser.add_argument('--part-count',type=int,default=2)
    parser.add_argument('--phase',choices=['gate','evaluate'],default='evaluate')
    for name in ('sealed-sha256','sealed-dataset','gate-sha256','gate-dataset'):
        parser.add_argument('--'+name)
    parser.add_argument('--training-folder'); parser.add_argument('--training-dataset')
    args = vars(parser.parse_args()); args.pop('plan')
    print(json.dumps(stage(**args),indent=2))
