"""Stage private, internet-off Test 1b notebooks and receipts locally."""
import argparse
import hashlib
from pathlib import Path
import re

from exploratory.test1 import stage as test1_stage

from .design import PASS_COUNTS, conditions
from .runner import MODEL_SOURCE, approval_words, run_settings

SOURCE_PATHS = tuple(f'exploratory/test1b/{name}.py' for name in (
    '__init__', 'analysis', 'design', 'reply', 'runner', 'stage',
))
NOTEBOOK = """import hashlib, json, os, sys
from pathlib import Path

PLAN_ONLY = True
CONFIG = BINDING_VALUE
if PLAN_ONLY:
    print(CONFIG)
else:
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    root = Path('/kaggle/input')
    source_slug = CONFIG['source_dataset'].split('/')[-1]
    matches = [p.parent for p in root.rglob('COMMIT.txt') if source_slug in p.parts
               and p.read_text().strip() == CONFIG['repo_commit']]
    if len(matches) != 1:
        raise ValueError('exact Test 1b source mount required')
    repo = matches[0]
    for name, digest in CONFIG['source_sha256'].items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != digest:
            raise ValueError('source bytes differ from the staged commit: ' + name)
    sys.path.insert(0, str(repo))
    from exploratory.ft1.mounts import find_receipt
    from exploratory.test1b.runner import run
    receipt_path = find_receipt(root, CONFIG['receipt_dataset'].split('/')[-1])
    receipt = json.loads(receipt_path.read_bytes())
    trial = receipt_path.with_name('trial-report.json').read_bytes() if CONFIG['phase'] == 'main' else None
    run(CONFIG, receipt, '/kaggle/working/test1b-' + CONFIG['phase'], trial)
"""


def inventory(commit):
    repo_bytes = test1_stage.inventory(commit)
    repo_bytes.update({name: test1_stage.git('show', f'{commit}:{name}') for name in SOURCE_PATHS})
    return repo_bytes


def stage(output, commit, owner):
    if (not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch('[a-z0-9_-]+', owner)
            or test1_stage.git('rev-parse', commit + '^{commit}').decode().strip() != commit):
        raise ValueError('exact tracked commit and Kaggle owner required')
    output = Path(output).resolve()
    if 'results' in {part.lower() for part in output.parts}:
        raise ValueError('use a staging directory outside results')
    repo_bytes = inventory(commit)
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in repo_bytes.items()}
    source_slug = 'test1b-source-' + commit[:12]
    source = f'{owner}/{source_slug}'
    dataset = output / source_slug
    repo = dataset / 'taa-lab'
    repo.mkdir(parents=True)
    (repo / 'COMMIT.txt').write_text(commit + '\n', encoding='utf-8')
    for name, raw in repo_bytes.items():
        destination = repo / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    write_json = test1_stage.write_json
    write_json(dataset / 'dataset-metadata.json', dict(
        id=source, title=source_slug, licenses=[dict(name='other')], isPrivate=True,
    ))
    for phase in PASS_COUNTS:
        slug = 'test1b-' + phase
        receipt_slug = f'{slug}-receipt-{commit[:12]}'
        receipt_dataset = f'{owner}/{receipt_slug}'
        binding = dict(phase=phase, repo_commit=commit, source_dataset=source,
                       receipt_dataset=receipt_dataset, source_sha256=hashes, **run_settings(phase))
        job = output / slug
        receipt = output / receipt_slug
        job.mkdir()
        receipt.mkdir()
        notebook = dict(nbformat=4, nbformat_minor=5, metadata=dict(
            kernelspec=dict(display_name='Python 3', language='python', name='python3')),
            cells=[dict(id='test1b-plan', cell_type='code', execution_count=None, metadata={}, outputs=[],
                        source=NOTEBOOK.replace('BINDING_VALUE', repr(binding)).splitlines(keepends=True))],
        )
        write_json(job / 'test1b.ipynb', notebook)
        write_json(job / 'kernel-metadata.json', dict(
            id=f'{owner}/{slug}', title=slug, code_file='test1b.ipynb', language='python',
            kernel_type='notebook', is_private=True, enable_gpu=True, enable_internet=False,
            dataset_sources=[source, receipt_dataset, 'metaphysika/k2-wheels'], model_sources=[MODEL_SOURCE],
        ))
        write_json(job / 'binding.json', binding)
        write_json(job / 'review-roster.json', list(conditions(phase, repo_bytes[test1_stage.CASES_PATH])))
        write_json(receipt / 'receipt.json', dict(
            approved=False, approval_words=None, required_approval_words=approval_words(binding),
            trial_report_sha256=None, binding=binding,
        ))
        write_json(receipt / 'dataset-metadata.json', dict(
            id=receipt_dataset, title=receipt_slug, licenses=[dict(name='other')], isPrivate=True,
        ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--owner', required=True)
    args = parser.parse_args()
    stage(args.output, args.commit, args.owner)
