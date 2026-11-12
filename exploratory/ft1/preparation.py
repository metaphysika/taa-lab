"""CPU data preparation: measure everything, retain diagnostics, write only on PASS."""
import hashlib
import json
from pathlib import Path
from . import data,kaggle,runner

MODEL_SOURCE='google/gemma-3/transformers/gemma-3-12b-it/1'


def tokenizer_hashes(folder):
    folder=Path(folder)
    names=('tokenizer.json','tokenizer.model','tokenizer_config.json','special_tokens_map.json',
           'added_tokens.json','chat_template.jinja')
    paths=[folder/n for n in names if (folder/n).is_file()]
    paths+=list((folder/'chat_templates').glob('*.jinja'))
    if not paths: raise ValueError('no local tokenizer files')
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def run(config,tokenizer_path,output,receipt):
    if receipt.get('approved') is not True or receipt.get('repo_commit')!=config['repo_commit'] or receipt.get('phase')!='data':
        raise ValueError('exact-commit preparation approval required')
    if config.get('model_source')!=MODEL_SOURCE: raise ValueError('pinned Gemma 3 12B /1 model required')
    runner.verify_source(config)
    from transformers import AutoTokenizer
    import importlib.metadata
    from exploratory.k2_kaggle import core
    if importlib.metadata.version('transformers')!=core.STACK['transformers']:
        raise ValueError('unverified tokenizer library version')
    output=data.safe_output(output); output.mkdir(parents=True)
    hashes=tokenizer_hashes(tokenizer_path)
    counter=data.Counter(AutoTokenizer.from_pretrained(tokenizer_path,local_files_only=True,trust_remote_code=False))
    measured=data.measure(counter)
    measured['tokenizer_file_sha256']=hashes
    (output/'measure-report.json').write_bytes((data.dump(measured)+'\n').encode('utf-8'))
    if not measured['passed'] or not measured['tokenizer_verified']:
        return dict(passed=False,written=False,report='measure-report.json')
    report=data.write(output/'dataset',counter,output/'write-report.json')
    report['tokenizer_file_sha256']=hashes
    (output/'write-report.json').write_bytes((data.dump(report)+'\n').encode('utf-8'))
    return dict(passed=report['passed'],written=report['write_passed'],report='write-report.json')


def stage(folder,commit,owner,repo_dataset,receipt_dataset):
    import re
    if not re.fullmatch('[0-9a-f]{40}',commit): raise ValueError('exact commit required')
    if not re.fullmatch('[a-z0-9_-]+',owner) or any(not re.fullmatch('[a-z0-9_-]+/[a-z0-9_-]+',s) for s in (repo_dataset,receipt_dataset)):
        raise ValueError('owner/dataset handles required')
    config=dict(repo_commit=commit,phase='data',model_source=MODEL_SOURCE,approved=False,
                source_sha256=kaggle.source_inventory(commit),
                receipt_path='/kaggle/input/datasets/'+receipt_dataset+'/receipt.json')
    source=('import sys, json\nfrom pathlib import Path\nPLAN_ONLY = True\nCONFIG = '+repr(config)+'\n'
        'if PLAN_ONLY:\n    print(CONFIG)\nelse:\n'
        '    repos = [p.parent for p in Path("/kaggle/input").rglob("COMMIT.txt") if p.read_text().strip()==CONFIG["repo_commit"]]\n'
        '    if len(repos)!=1: raise ValueError("missing or ambiguous commit-bound source")\n'
        '    sys.path.insert(0, str(repos[0]))\n'
        '    from exploratory.ft1.preparation import run\n'
        '    receipt = json.loads(Path(CONFIG["receipt_path"]).read_text())\n'
        '    run(CONFIG, "/kaggle/input/models/"+CONFIG["model_source"], "/kaggle/working/ft1-data-preparation", receipt)\n')
    folder=data.safe_output(folder); folder.mkdir(parents=True)
    notebook=dict(nbformat=4,nbformat_minor=5,metadata={},cells=[dict(cell_type='code',
        execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    files={'ft1_data_plan.ipynb':notebook,'binding.json':config,'kernel-metadata.json':dict(
        id=owner+'/ft1-data-plan',title='FT1 CPU data preparation plan',code_file='ft1_data_plan.ipynb',
        language='python',kernel_type='notebook',is_private=True,enable_gpu=False,enable_internet=False,
        dataset_sources=[repo_dataset,receipt_dataset],model_sources=[MODEL_SOURCE])}
    for name,value in files.items(): (folder/name).write_bytes((json.dumps(value,indent=2)+'\n').encode('utf-8'))
    return config


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--plan',required=True,action='store_true')
    p.add_argument('--commit',required=True); p.add_argument('--owner',required=True)
    p.add_argument('--repo-dataset',required=True); p.add_argument('--receipt-dataset',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    stage(a.output,a.commit,a.owner,a.repo_dataset,a.receipt_dataset)
