"""Local plan-only staging for a separately approved public-only fit-limit measurement."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
from . import data, kaggle, mounts
from exploratory.k2_kaggle import core


def stage(output, commit, owner, repo_dataset, receipt_dataset, model_source):
    if not re.fullmatch('[a-f0-9]{40}',commit):
        raise ValueError('exact commit required')
    core.validate_model_source(model_source,'gemma-3-12b-it')
    if not re.fullmatch('[a-z0-9_-]+',owner) or any(not re.fullmatch('[a-z0-9_-]+/[a-z0-9_-]+',d) for d in (repo_dataset,receipt_dataset)):
        raise ValueError('invalid owner or dataset')
    # Public phase excludes sealed source from its binding inventory.
    sources = {}
    root = Path(__file__).resolve().parents[2]
    allowed = ('data.py','evaluation.py','evaluate_runner.py','memory.py','fit_limit.py','throughput.py','scoring.py','plan.py','runner.py','kaggle.py','mounts.py','training.py','selection.py','local_tokenizer.py','selection_expected.json')
    for basename in allowed:
        name = 'exploratory/ft1/'+basename
        sources[name] = hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=root)).hexdigest()
    root = Path(__file__).resolve().parents[2]
    names = subprocess.check_output(['git','ls-tree','-r','--name-only',commit,
        'exploratory/step4_harness','exploratory/measurement_v02456','exploratory/k2_kaggle','formation'],cwd=root,text=True).splitlines()
    for name in names:
        if name.endswith('.py'):
            sources[name] = hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=root)).hexdigest()
    config = dict(phase='fit_limit',repo_commit=commit,model_source=model_source,
        data_manifest_sha256=None,source_sha256=sources,receipt_slug=mounts.receipt_slug(receipt_dataset))
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
    from exploratory.ft1.mounts import find_receipt
    from exploratory.ft1.fit_limit import run
    receipt = json.loads(find_receipt('/kaggle/input',CONFIG['receipt_slug']).read_bytes())
    run(CONFIG,'/kaggle/input/models/'+CONFIG['model_source'],'/kaggle/working/ft1-fit_limit',receipt)
'''.replace('CONFIG_VALUE',repr(config))
    folder = data.safe_output(output)
    folder.mkdir(parents=True)
    notebook = dict(nbformat=4,nbformat_minor=5,
        metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),
        cells=[dict(cell_type='code',execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    (folder/'ft1_fit_limit.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    (folder/'binding.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    metadata = dict(id=owner+'/ft1-fit_limit',title='ft1-fit_limit',code_file='ft1_fit_limit.ipynb',
        language='python',kernel_type='notebook',is_private=True,enable_gpu=True,enable_internet=False,
        dataset_sources=[repo_dataset,'metaphysika/k2-wheels',receipt_dataset],model_sources=[model_source])
    (folder/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan',action='store_true',required=True)
    for name in ('output','commit','owner','repo-dataset','receipt-dataset','model-source'):
        parser.add_argument('--'+name,required=True)
    args = vars(parser.parse_args()); args.pop('plan')
    print(json.dumps(stage(**args),indent=2))
