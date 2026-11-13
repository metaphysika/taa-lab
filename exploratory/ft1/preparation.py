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
    import importlib.metadata
    from exploratory.k2_kaggle import core
    output=data.safe_output(output); output.mkdir(parents=True)
    versions={}
    for name in ('transformers','tokenizers','python'):
        if name=='python':
            import platform
            versions[name]=platform.python_version()
        else:
            try: versions[name]=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: versions[name]=None
    def save(name,report):
        report['versions']=versions
        (output/name).write_bytes((data.dump(report)+'\n').encode('utf-8'))
    if versions['transformers']!=core.STACK['transformers']:
        failure=dict(passed=False,written=False,versions=versions,expected_transformers=core.STACK['transformers'],
                     setup_failure='transformers version mismatch',record_count=0)
        save('measure-report.json',failure)
        data.print_measure_summary(failure)
        return dict(failure,report='measure-report.json')
    from transformers import AutoTokenizer
    tokenizer_path=core.resolve_model_path(tokenizer_path)
    hashes=tokenizer_hashes(tokenizer_path)
    counter=data.Counter(AutoTokenizer.from_pretrained(tokenizer_path,local_files_only=True,trust_remote_code=False))
    measured=data.measure(counter)
    if measured['passed']:
        from .selection import verify_expected
        try: verify_expected(measured)
        except ValueError as exc:
            measured['passed']=False
            measured['aggregate_failures'].append(str(exc))
    measured['tokenizer_file_sha256']=hashes
    save('measure-report.json',measured)
    data.print_measure_summary(measured)
    if not measured['passed'] or not measured['tokenizer_verified']:
        return dict(passed=False,written=False,report='measure-report.json',versions=versions)
    from .data_diagnostics import DataBuildError
    try:
        report=data.write(output/'dataset',counter,output/'write-report.json')
    except DataBuildError:
        # The writer already retains its complete diagnostic report.
        report=json.loads((output/'write-report.json').read_bytes())
        report['tokenizer_file_sha256']=hashes
        save('write-report.json',report)
        return dict(passed=False,written=False,report='write-report.json',versions=versions)
    report['tokenizer_file_sha256']=hashes
    save('write-report.json',report)
    return dict(passed=report['passed'],written=report['write_passed'],report='write-report.json',versions=versions)


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
    notebook=dict(nbformat=4,nbformat_minor=5,metadata={'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},cells=[dict(cell_type='code',
        execution_count=None,metadata={},outputs=[],source=source.splitlines(True))])
    files={'ft1_data_plan.ipynb':notebook,'binding.json':config,'kernel-metadata.json':dict(
        id=owner+'/ft1-data-plan',title='ft1-data-plan',code_file='ft1_data_plan.ipynb',
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
