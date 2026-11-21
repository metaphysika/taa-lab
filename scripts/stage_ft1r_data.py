"""Stage a private, CPU-only FT1-R data job from a clean exact commit."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

if __package__:
    from . import ft1r_data_job as job
else:
    import ft1r_data_job as job


ROOT = Path(__file__).resolve().parents[1]
STAGE_ROOT = Path('C:/t/ft1r-data')
CPU_IMAGE = ('gcr.io/kaggle-images/python@sha256:'
             '0717e81990be591f8c5f98f033d29ab23e9ffde057e5b3a6bd4371f93969e962')
# The data/report modules and the transitive imports reached through k2_kaggle.core.
# Step 4 fixtures and its execution backends are unused by this job.
SOURCE_FILES = (
    'scripts/ft1r_data_report.py',
    'exploratory/ft1/__init__.py', 'exploratory/ft1/data.py',
    'exploratory/ft1/data_diagnostics.py', 'exploratory/ft1/ft1r_data.py',
    'exploratory/ft1/selection.py', 'exploratory/k2_kaggle/core.py',
    'exploratory/step4_harness/__init__.py', 'exploratory/step4_harness/crossing.py',
    'exploratory/step4_harness/crossing_analysis.py', 'exploratory/step4_harness/k1.py',
    'exploratory/step4_harness/k1_analysis.py', 'exploratory/step4_harness/l1.py',
    'exploratory/step4_harness/l1_analysis.py', 'exploratory/step4_harness/runner.py',
    'exploratory/measurement_v02456/policy.py', 'exploratory/step4_cases/drafts.py',
    'formation/__init__.py', 'formation/study_a.py', 'formation/study_b_parser_v0234.py',
    'formation/study_b_replay_v0234.py', 'formation/study_b_v0227.py',
    'formation/study_d_base_gate_v0248.py', 'agents/__init__.py', 'agents/gemini_client.py',
    'taa/__init__.py', 'taa/consequence.py', 'taa/determinations.py', 'taa/gate.py',
    'taa/premises.py', 'taa/preview.py', 'taa/records.py',
)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')


def source_artifact(commit):
    if any(Path(name).name == 'sealed.py' for name in SOURCE_FILES):
        raise ValueError('sealed source forbidden')
    return job.json_bytes({'repo_commit': commit, 'files': {
        name: git('show', f'{commit}:{name}') for name in SOURCE_FILES
    }})


def stage(commit, owner):
    if not re.fullmatch('[0-9a-f]{40}', commit) or git('rev-parse', 'HEAD').strip() != commit:
        raise ValueError('checkout must be at the full requested commit SHA')
    if git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('checkout must be clean')
    if not re.fullmatch('[a-z0-9_-]+', owner):
        raise ValueError('invalid Kaggle owner')
    output = STAGE_ROOT / commit
    if output.exists():
        raise ValueError(f'bundle already exists: {output}')

    source = source_artifact(commit)
    receipt = dict(phase=job.PHASE, repo_commit=commit, source_sha256=job.sha256(source), approved=False)
    binding = dict(phase=job.PHASE, repo_commit=commit, source_sha256=receipt['source_sha256'],
                   source_dataset=f'{owner}/ft1r-source-{commit[:12]}',
                   receipt_dataset=f'{owner}/ft1r-data-approval-{commit[:12]}')
    code = (git('show', f'{commit}:scripts/ft1r_data_job.py') +
            f'\n\nPLAN_ONLY = True\nBINDING = {binding!r}\n'
            'if PLAN_ONLY:\n    print(BINDING)\nelse:\n    run(BINDING)\n')
    notebook = dict(nbformat=4, nbformat_minor=5, metadata={
        'kernelspec': dict(display_name='Python 3', language='python', name='python3')},
        cells=[dict(id='ft1r-data', cell_type='code', execution_count=None, metadata={},
                    outputs=[], source=code.splitlines(keepends=True))])
    kernel = dict(id=f'{owner}/ft1r-data-{commit[:12]}', title=f'ft1r-data-{commit[:12]}',
                  code_file='ft1r_data.ipynb', language='python', kernel_type='notebook',
                  is_private=True, enable_gpu=False, enable_internet=False, docker_image=CPU_IMAGE,
                  dataset_sources=[binding['source_dataset'], binding['receipt_dataset']],
                  model_sources=[job.MODEL_SOURCE])
    files = {
        'kernel/ft1r_data.ipynb': job.json_bytes(notebook),
        'kernel/kernel-metadata.json': job.json_bytes(kernel),
        f'source/{job.SOURCE_FILE}': source,
        'receipt/receipt.json': job.json_bytes(receipt),
    }
    for directory in ('source', 'receipt'):
        handle = binding[f'{directory}_dataset']
        files[f'{directory}/dataset-metadata.json'] = job.json_bytes({
            'id': handle, 'title': handle.split('/')[1], 'licenses': [{'name': 'other'}],
        })
    STAGE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=STAGE_ROOT) as work:
        pending = Path(work) / 'bundle'
        for name, raw in files.items():
            path = pending / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        pending.rename(output)
    print(output)
    for name in sorted(files):
        print(f'{job.sha256((output / name).read_bytes())}  {name}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('commit', help='Full SHA of the current clean checkout')
    parser.add_argument('--owner', default='metaphysika', help='Kaggle owner for the staged handles')
    args = parser.parse_args()
    try:
        stage(args.commit, args.owner)
    except (ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'{exc}\n')
