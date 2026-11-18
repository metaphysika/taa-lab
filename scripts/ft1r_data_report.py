"""Measure FT1-R with an existing local Gemma tokenizer, without loading a model."""
import argparse
import hashlib
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exploratory.ft1 import data, data_diagnostics, ft1r_data
from exploratory.k2_kaggle import core


def is_real_tokenizer(tokenizer):
    try:
        from transformers import PreTrainedTokenizerBase
    except ImportError:
        return False
    return isinstance(tokenizer, PreTrainedTokenizerBase)


def tokenizer_fingerprint(folder):
    # Hash relative names and content hashes for local tokenizer and template assets.
    names = ('config.json', 'tokenizer.json', 'tokenizer.model', 'tokenizer_config.json',
             'special_tokens_map.json', 'added_tokens.json', 'chat_template.jinja')
    files = [folder / name for name in names]
    files.extend((folder / 'chat_templates').glob('*.jinja'))
    inventory = {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(files) if path.is_file()}
    if not {'tokenizer.json', 'tokenizer.model'}.intersection(inventory):
        raise ValueError('local Gemma tokenizer assets required')
    return core.digest(inventory)


def report_for(tokenizer, report_path, output_path=None, *, tokenizer_sha256=None,
               expected_tokenizer_sha256=None):
    report_path = data.safe_output(report_path)
    output_path = data.safe_output(output_path) if output_path else None
    if output_path and report_path.is_relative_to(output_path):
        raise ValueError('report and dataset require separate paths')
    counter = data.Counter(tokenizer)
    report = dict(layout=data.FT1R_LAYOUT, versions=data_diagnostics.runtime_versions(),
                  passed=False, tokenizer_verified=is_real_tokenizer(tokenizer),
                  tokenizer_sha256=tokenizer_sha256,
                  limits=dict(trained=640, total=1024,
                              history_overflow='Replace records whose history pushes them above 1,024 tokens.',
                              tool_result='Training uses "recorded". At test the tool result is a JSON world update, inherited from FT1.'))
    try:
        core.end_token(tokenizer)
        rows, manifest, training = ft1r_data.generate_training(counter)
        report['training'] = training
        probes = ft1r_data.probes(counter)
        report['probes'] = dict(count=len(probes), fit=ft1r_data.fit(probes))
        report['passed'] = training['passed']
    except ValueError as exc:
        report['refusal'] = str(exc)

    if output_path and not report['tokenizer_verified']:
        report['passed'] = False
        report.setdefault('refusal', 'real tokenizer verification required')

    if output_path and (not re.fullmatch('[a-f0-9]{64}', expected_tokenizer_sha256 or '')
                        or tokenizer_sha256 != expected_tokenizer_sha256):
        report['passed'] = False
        report.setdefault('refusal', 'expected Gemma 3 12B tokenizer SHA-256 must match local files')

    if output_path and report['passed']:
        manifest['tokenizer_verified'] = report['tokenizer_verified']
        manifest['tokenizer_sha256'] = tokenizer_sha256
        payloads = {f'arm-{arm}.jsonl': ''.join(data.dump(row)+'\n' for row in records).encode('utf-8')
                    for arm, records in rows.items()}
        payloads[ft1r_data.PROBE_FILE] = data.dump(probes).encode('utf-8')
        manifest['sha256'] = {name: hashlib.sha256(content).hexdigest() for name, content in payloads.items()}
        output_path.mkdir(parents=True)
        for name, content in payloads.items():
            (output_path/name).write_bytes(content)
        manifest_bytes = (data.dump(manifest)+'\n').encode('utf-8')
        (output_path/'manifest.json').write_bytes(manifest_bytes)
        report['file_sha256'] = dict(manifest['sha256'], **{'manifest.json': hashlib.sha256(manifest_bytes).hexdigest()})

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes((data.dump(report)+'\n').encode('utf-8'))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expected-tokenizer-sha256',
                        help='Expected Gemma 3 12B tokenizer asset fingerprint, required for export')
    args = parser.parse_args()
    tokenizer_dir = args.tokenizer.resolve()
    if not tokenizer_dir.is_dir():
        parser.error('--tokenizer must name an existing local directory')
    fingerprint = tokenizer_fingerprint(tokenizer_dir)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True, trust_remote_code=False)
    if tokenizer_fingerprint(tokenizer_dir) != fingerprint:
        parser.error('local tokenizer files changed during loading')
    report = report_for(tokenizer, args.report, args.output, tokenizer_sha256=fingerprint,
                        expected_tokenizer_sha256=args.expected_tokenizer_sha256)
    print(data.dump(dict(passed=report['passed'], report=str(args.report))))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
