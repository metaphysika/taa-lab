"""Build private, internet-off Kaggle bundles locally. This module has no upload path."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from exploratory.ft1.kaggle import source_inventory

from .design import PAIR_COUNTS, conditions
from .runner import MODEL_SOURCE, SETTINGS, TIME_LIMIT_SECONDS, approval_words

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    'agents/__init__.py', 'agents/gemini_client.py', 'taa', 'formation/__init__.py',
    'formation/study_a.py', 'formation/study_b_v0227.py', 'formation/study_b_parser_v0234.py',
    'formation/study_b_replay_v0234.py', 'formation/study_d_base_gate_v0248.py',
    'exploratory/step4_harness/__init__.py', 'exploratory/step4_harness/runner.py',
    'exploratory/step4_harness/crossing.py', 'exploratory/step4_harness/crossing_analysis.py',
    'exploratory/step4_harness/k1.py', 'exploratory/step4_harness/k1_analysis.py',
    'exploratory/step4_harness/l1.py', 'exploratory/step4_harness/l1_analysis.py',
    'exploratory/step4_cases/drafts.py', 'exploratory/measurement_v02456/policy.py', 'exploratory/test1',
)
CASES_PATH = 'exploratory/test1/cases.json'
NOTEBOOK = """import hashlib, json, os, sys
from pathlib import Path

PLAN_ONLY = True
CONFIG = BINDING_VALUE
if PLAN_ONLY:
    print(CONFIG)
else:
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    root = Path('/kaggle/input')
    matches = [p.parent for p in root.rglob('COMMIT.txt')
               if CONFIG['source_dataset'].split('/')[-1] in p.parts
               and p.read_text().strip() == CONFIG['repo_commit']]
    if len(matches) != 1:
        raise ValueError('exact Test 1 source mount required')
    repo = matches[0]
    for name, digest in CONFIG['source_sha256'].items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != digest:
            raise ValueError('source bytes differ from the staged commit: ' + name)
    sys.path.insert(0, str(repo))
    from exploratory.ft1.mounts import find_receipt
    from exploratory.test1.runner import run
    receipt_path = find_receipt(root, CONFIG['receipt_dataset'].split('/')[-1])
    receipt = json.loads(receipt_path.read_bytes())
    practice = None
    if CONFIG['phase'] == 'main':
        raw = receipt_path.with_name('practice-report.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt.get('practice_report_sha256'):
            raise ValueError('practice report does not match the main approval receipt')
        practice = json.loads(raw)
    run(CONFIG, receipt, '/kaggle/working/test1-' + CONFIG['phase'], practice)
"""


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def inventory(commit):
    # FT1 provides a source inventory that explicitly excludes sealed modules.
    bound = source_inventory(commit, include_sealed=False)
    names = git('ls-tree', '-r', '--name-only', commit, '--', *SOURCE_PATHS).decode().splitlines()
    paths = set(bound) | {name for name in names if name.endswith('.py')} | {CASES_PATH, 'LICENSE'}
    return {name: git('show', f'{commit}:{name}') for name in sorted(paths)}


def binding(phase, commit, source, receipt, repo_bytes):
    return dict(
        phase=phase, repo_commit=commit, source_dataset=source, receipt_dataset=receipt,
        settings=SETTINGS, model_source=MODEL_SOURCE, time_limit_seconds=TIME_LIMIT_SECONDS[phase],
        source_sha256={name: hashlib.sha256(raw).hexdigest() for name, raw in repo_bytes.items()},
    )


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def stage(output, commit, owner):
    if (not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch('[a-z0-9_-]+', owner)
            or git('rev-parse', commit + '^{commit}').decode().strip() != commit):
        raise ValueError('exact tracked commit and Kaggle owner required')
    output = Path(output).resolve()
    if 'results' in {part.lower() for part in output.parts}:
        raise ValueError('use a staging directory outside results')
    repo_bytes = inventory(commit)
    output.mkdir(parents=True)
    source_slug = 'test1-source-' + commit[:12]
    source = f'{owner}/{source_slug}'
    dataset = output / source_slug
    repo = dataset / 'taa-lab'
    repo.mkdir(parents=True)
    (repo / 'COMMIT.txt').write_text(commit + '\n', encoding='utf-8')
    for name, raw in repo_bytes.items():
        destination = repo / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    write_json(dataset / 'dataset-metadata.json', dict(
        id=source, title=source_slug, licenses=[dict(name='other')], isPrivate=True,
    ))
    for phase in PAIR_COUNTS:
        slug = 'test1-' + phase
        receipt_slug = f'{slug}-receipt-{commit[:12]}'
        receipt_dataset = f'{owner}/{receipt_slug}'
        config = binding(phase, commit, source, receipt_dataset, repo_bytes)
        job = output / slug
        receipt_folder = output / receipt_slug
        job.mkdir()
        receipt_folder.mkdir()
        notebook = dict(nbformat=4, nbformat_minor=5, metadata=dict(
            kernelspec=dict(display_name='Python 3', language='python', name='python3')),
            cells=[dict(id='test1-plan', cell_type='code', execution_count=None, metadata={}, outputs=[],
                        source=NOTEBOOK.replace('BINDING_VALUE', repr(config)).splitlines(keepends=True))],
        )
        write_json(job / 'test1.ipynb', notebook)
        write_json(job / 'kernel-metadata.json', dict(
            id=f'{owner}/{slug}', title=slug, code_file='test1.ipynb', language='python',
            kernel_type='notebook', is_private=True, enable_gpu=True, enable_internet=False,
            dataset_sources=[source, receipt_dataset, 'metaphysika/k2-wheels'], model_sources=[MODEL_SOURCE],
        ))
        write_json(job / 'binding.json', config)
        roster = list(conditions(phase, repo_bytes[CASES_PATH]))
        write_json(job / 'review-roster.json', roster)
        write_json(receipt_folder / 'receipt.json', dict(
            approved=False, approval_words=None, required_approval_words=approval_words(config),
            practice_report_sha256=None, binding=config,
        ))
        write_json(receipt_folder / 'dataset-metadata.json', dict(
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
