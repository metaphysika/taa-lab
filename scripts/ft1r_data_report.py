"""Measure FT1-R with an existing local Gemma tokenizer, without loading a model."""
import argparse
import hashlib
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


def report_for(tokenizer, report_path, output_path=None):
    report_path = data.safe_output(report_path)
    output_path = data.safe_output(output_path) if output_path else None
    if output_path and report_path.is_relative_to(output_path):
        raise ValueError('report and dataset require separate paths')
    counter = data.Counter(tokenizer)
    report = dict(layout=data.FT1R_LAYOUT, versions=data_diagnostics.runtime_versions(),
                  passed=False, tokenizer_verified=False,
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
        report['tokenizer_verified'] = is_real_tokenizer(tokenizer)
    except ValueError as exc:
        report['refusal'] = str(exc)

    if output_path and not report['tokenizer_verified']:
        report['passed'] = False
        report.setdefault('refusal', 'real tokenizer verification required')

    if output_path and report['passed']:
        manifest['tokenizer_verified'] = report['tokenizer_verified']
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
    args = parser.parse_args()
    tokenizer_dir = args.tokenizer.resolve()
    if not tokenizer_dir.is_dir():
        parser.error('--tokenizer must name an existing local directory')
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True, trust_remote_code=False)
    report = report_for(tokenizer, args.report, args.output)
    print(data.dump(dict(passed=report['passed'], report=str(args.report))))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
