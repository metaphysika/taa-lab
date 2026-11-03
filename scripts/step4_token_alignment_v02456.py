"""CPU-only, local-files-only backend token alignment audit. No weights or model calls."""
import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REVISION = '842da3794eaa0b77d5f08bae87a17459d91ff475'
HASHES = {
    'tokenizer.json': 'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f',
    'tokenizer_config.json': '9f4fec4b1dc6ecddf8f4a92e9caea5971c0e67d81309f3f9066a2bee8c362633',
    'chat_template.jinja': 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4',
}


def messages(case):
    """Obtain the actual runner prefix, without inference."""
    from exploratory.step4_harness.runner import episode
    captured = []
    episode(case, 'action', lambda system, history, cap:
            captured.append((system, history)) or '{"tool":null,"args":{}}')
    system, history = captured[0]
    return [dict(role='system', content=system)] + history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / 'exploratory/step4_cases/cases.json'
    report = dict(status='blocked', revision=REVISION, wire_format='proposed; backend parity unverified',
                  case_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), tokenizer_hashes={})
    for name, expected in HASHES.items():
        actual = hashlib.sha256((args.tokenizer_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('Pinned tokenizer hash mismatch: ' + name)
        report['tokenizer_hashes'][name] = actual
    from transformers import AutoTokenizer
    import importlib.util
    import importlib.metadata
    import platform
    spec = importlib.util.spec_from_file_location('study_d_runtime', ROOT / 'scripts/study_d_gemma_runtime_v02416.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer_dir), local_files_only=True)
    report.update(wire_format='runner.episode 5818aad9 + modal_backend.render ef49d442 + runtime.prompt_ids',
                  earlier_report=dict(status='measured_contrasts_dropped', commit='7269d51cd95bf401cb1444a0e66a75d7379fd4a3', reason='All 32 contrasts omitted by tool-role rendering', report_path='docs/process/STEP4_TOKEN_ALIGNMENT_DROPPED_v02456.json', prior_blocked_commit='869b8bba'),
                  python=platform.python_version(),
                  packages={d.metadata['Name']: d.version for d in sorted(
                      importlib.metadata.distributions(), key=lambda d: d.metadata['Name'].lower())},
                  runtime_sha256=hashlib.sha256(Path(spec.origin).read_bytes()).hexdigest(),
                  template_sha256=hashlib.sha256(tokenizer.chat_template.encode()).hexdigest())
    cases = json.loads(source.read_bytes())
    encoded, rendered = {}, {}
    for case in cases:
        msgs = messages(case)
        from exploratory.step4_harness.modal_backend import render
        ids = render(runtime, tokenizer, msgs[0]['content'], msgs[1:])
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        if enc['input_ids'] != ids:
            raise ValueError('Offset encoding differs from backend token IDs')
        from types import SimpleNamespace
        encoded[case['id']] = SimpleNamespace(ids=ids, offsets=enc['offset_mapping'])
        rendered[case['id']] = text
    comparisons = []
    facts = [c for c in cases if c['id'].startswith('fact-')]
    for a in facts:
        for b in facts:
            if a['id'] >= b['id'] or a['pair'] != b['pair']:
                continue
            decisive = a['variant'] == b['variant'] and a['intended_label'] != b['intended_label']
            parcel = a['variant'] != b['variant'] and a['intended_label'] == b['intended_label']
            if not (decisive or parcel):
                continue
            va, vb = a['visible'], b['visible']
            key, index = ('evidence', 5) if decisive else ('detail', 1)
            sa, sb = [v['prefix'][index]['content']['record'][key] for v in (va, vb)]
            ta, tb = rendered[a['id']], rendered[b['id']]
            ea, eb = encoded[a['id']], encoded[b['id']]
            spans = []
            for tag, i, j, k, l in difflib.SequenceMatcher(a=ea.ids, b=eb.ids, autojunk=False).get_opcodes():
                if tag != 'equal':
                    spans.append(dict(a=[i, j], b=[k, l]))
            def inside(enc, text, value, side):
                if value not in text:
                    return False
                start = text.index(value)
                end = start + len(value)
                return all(all(start <= enc.offsets[t][0] and enc.offsets[t][1] <= end
                               for t in range(*s[side])) for s in spans)
            only_field = ta.replace(sa, '<CONTRAST>') == tb.replace(sb, '<CONTRAST>')
            aligned = len(ea.ids) == len(eb.ids) and all(s['a'] == s['b'] for s in spans)
            comparisons.append(dict(a=a['id'], b=b['id'], kind='fact' if decisive else 'parcel',
                                    counts=[len(ea.ids), len(eb.ids)], decision_points=[len(ea.ids)-1, len(eb.ids)-1], differing_spans=spans,
                                    aligned=aligned, expected_field_present=[sa in ta, sb in tb],
                                    contrast_visible=bool(spans), only_expected_field=only_field,
                                    tokens_within_field=inside(ea, ta, sa, 'a') and inside(eb, tb, sb, 'b')))
    report.update(status='complete', index_convention='zero-based half-open spans; final token inclusive',
                  cases={k: dict(tokens=len(v.ids), decision_point=len(v.ids)-1,
                                 rendered_sha256=hashlib.sha256(rendered[k].encode()).hexdigest())
                         for k, v in encoded.items()}, comparisons=comparisons)
    failed = [c for c in comparisons if not all(c[k] for k in
              ('aligned', 'contrast_visible', 'only_expected_field', 'tokens_within_field'))]
    report.update(status='measured_contrasts_dropped' if any(not c['contrast_visible'] for c in comparisons)
                  else ('measured_alignment_failed' if failed else 'measured_aligned'),
                  failed_contrasts=[dict(a=c['a'], b=c['b'], kind=c['kind']) for c in failed],
                  summary=dict(fact_contrasts=sum(c['kind'] == 'fact' for c in comparisons),
                               parcel_contrasts=sum(c['kind'] == 'parcel' for c in comparisons),
                               positionally_misaligned=sum(not c['aligned'] for c in comparisons),
                               contrasts_missing_from_render=sum(not all(c['expected_field_present']) for c in comparisons),
                               usable_alignment=not failed,
                               reason='User-wrapped observations preserve evidence; positional alignment is measured independently.'))
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return int(any(not all(c[k] for k in ('aligned', 'contrast_visible', 'only_expected_field', 'tokens_within_field'))
                   for c in comparisons))


if __name__ == '__main__':
    raise SystemExit(main())
