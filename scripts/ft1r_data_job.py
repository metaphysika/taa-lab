"""Receipt-gated FT1-R Kaggle data job. Staging embeds this code in the notebook."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile


PHASE = 'ft1r-data'
MODEL_SOURCE = 'google/gemma-3/transformers/gemma-3-12b-it/1'
SOURCE_FILE = 'ft1r-source.json'

# Retained FT1 preparation measure-report.json (kernel v4, 2026-11-13).
VERSIONS = {'python': '3.13.18', 'transformers': '5.20.2', 'tokenizers': '0.23.3'}
TOKENIZER_FILES = {
    'tokenizer.json': '7d4046bf0505a327dd5a0abbb427ecd4fc82f99c2ceaa170bc61ecde12809b0c',
    'tokenizer.model': '1299c11d7cf632ef3b4e11937501358ada021bbdf7c47638d13c0ee982f2e79c',
    'tokenizer_config.json': '10a27b015a8c561aee8fb959b949e63b6c11b67965c0eccf519e6375439f092e',
    'special_tokens_map.json': '2f7b0adf4fb469770bb1490e3e35df87b1dc578246c5e7e6fc76ecf33213a397',
    'added_tokens.json': '50b2f405ba56a26d4913fd772089992252d7f942123cc0a034d96424221ba946',
}
TOKENIZER_SHA256 = '1698598f704cbd60313f2d49725456a2084449a73919d2264cca33d2c85a8552'


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')


def read_mount(root, handle, name):
    owner, slug = handle.split('/')
    folders = [root / slug, root / 'datasets' / owner / slug]
    matches = [path for folder in folders for path in folder.rglob(name) if path.is_file()]
    if len(matches) != 1:
        raise ValueError(f'missing or ambiguous mounted {name} for {handle}')
    return matches[0].read_bytes()


def verify_receipt(binding, receipt):
    if (binding.get('phase') != PHASE or not isinstance(receipt, dict)
            or receipt.get('approved') is not True
            or receipt.get('phase') != PHASE
            or receipt.get('repo_commit') != binding['repo_commit']
            or receipt.get('source_sha256') != binding['source_sha256']):
        raise ValueError('exact-commit ft1r-data approval receipt required')


def unpack_source(binding, raw, root):
    if sha256(raw) != binding['source_sha256']:
        raise ValueError('mounted source artifact SHA-256 mismatch')
    artifact = json.loads(raw)
    if artifact['repo_commit'] != binding['repo_commit']:
        raise ValueError('mounted source commit mismatch')
    for name, content in artifact['files'].items():
        path = PurePosixPath(name)
        if (not re.fullmatch(r'[a-zA-Z0-9_./-]+', name) or path.is_absolute()
                or '..' in path.parts or path.name == 'sealed.py'):
            raise ValueError(f'invalid source artifact path: {name}')
        target = root.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode('utf-8'))


def measure(input_root, tokenizer_dir, output):
    from exploratory.ft1.data_diagnostics import runtime_versions
    from exploratory.k2_kaggle import core
    from scripts.ft1r_data_report import report_for

    versions = runtime_versions()
    if versions != VERSIONS:
        raise ValueError(f'runtime version mismatch: expected {VERSIONS}, found {versions}')
    model_mount = core.resolve_model_path(input_root / 'models' / MODEL_SOURCE, root=input_root)
    tokenizer_dir.mkdir()
    hashes = {}
    for name, expected in TOKENIZER_FILES.items():
        raw = (model_mount / name).read_bytes()
        hashes[name] = sha256(raw)
        if hashes[name] != expected:
            raise ValueError(f'mounted tokenizer SHA-256 mismatch: {name}')
        (tokenizer_dir / name).write_bytes(raw)
    fingerprint = core.digest(hashes)
    if fingerprint != TOKENIZER_SHA256:
        raise ValueError('mounted tokenizer fingerprint mismatch')

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True, trust_remote_code=False)
    return report_for(tokenizer, output / 'report.json', output / 'dataset',
                      tokenizer_sha256=fingerprint, expected_tokenizer_sha256=TOKENIZER_SHA256,
                      tokenizer_file_sha256=hashes)


def run(binding, input_root=Path('/kaggle/input'), output=Path('/kaggle/working/ft1r-data')):
    receipt = json.loads(read_mount(input_root, binding['receipt_dataset'], 'receipt.json'))
    verify_receipt(binding, receipt)
    source = read_mount(input_root, binding['source_dataset'], SOURCE_FILE)
    if output.exists() or output.is_symlink():
        raise ValueError('FT1-R output already exists')
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        repo = scratch / 'source'
        unpack_source(binding, source, repo)
        # Extracted source is available only for this fresh notebook kernel.
        if {'exploratory', 'formation', 'scripts', 'taa', 'agents'}.intersection(sys.modules):
            raise ValueError('FT1-R data job requires a fresh kernel')
        original_path = sys.path[:]
        sys.path.insert(0, str(repo))
        try:
            with tempfile.TemporaryDirectory(dir=output.parent) as work:
                pending = Path(work) / PHASE
                pending.mkdir()
                report = measure(input_root, scratch / 'tokenizer', pending)
                if report['passed'] is not True and (pending / 'dataset').exists():
                    raise ValueError('refusing to publish a dataset after a failed data gate')
                manifest = {p.relative_to(pending).as_posix(): sha256(p.read_bytes())
                            for p in sorted(pending.rglob('*')) if p.is_file()}
                (pending / 'output-manifest.json').write_bytes(json_bytes({
                    'phase': PHASE, 'repo_commit': binding['repo_commit'],
                    'source_sha256': binding['source_sha256'], 'passed': report['passed'],
                    'sha256': manifest,
                }))
                pending.rename(output)
        finally:
            sys.path[:] = original_path
    print(json.dumps({'passed': report['passed'], 'output': str(output)}))
    return report
