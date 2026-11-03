"""CPU-only, local-files-only proposed wire-format alignment audit. No model imports."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = '842da3794eaa0b77d5f08bae87a17459d91ff475'
HASHES = {
    'tokenizer.json': 'cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f',
    'tokenizer_config.json': '9f4fec4b1dc6ecddf8f4a92e9caea5971c0e67d81309f3f9066a2bee8c362633',
    'chat_template.jinja': 'ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4',
}


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def messages(visible):
    """Proposed JSON-action transport; backend parity remains an execution gate."""
    result = [dict(role='system', content=visible['system']),
              dict(role='user', content=visible['task'] + '\nTools: ' + compact(visible['tools']))]
    for m in visible['prefix']:
        entry = dict(role=m['role'], content=compact(m['content']))
        if m['role'] == 'assistant':
            # The canonical template forward-scans tool replies only for tool calls.
            entry['tool_calls'] = [dict(type='function', function=dict(
                name=m['content']['tool'], arguments=m['content']['args']))]
        else:
            entry['name'] = 'read_record'
        result.append(entry)
    return result


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
    try:
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        from tokenizers import Tokenizer
    except ImportError as exc:
        report['reason'] = str(exc) + '; dependency downloads are outside task network authorization'
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return 2
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    env.filters['tojson'] = compact
    def fail(message):
        raise ValueError(message)
    env.globals['raise_exception'] = fail
    template = env.from_string((args.tokenizer_dir / 'chat_template.jinja').read_text(encoding='utf-8'))
    config = json.loads((args.tokenizer_dir / 'tokenizer_config.json').read_text(encoding='utf-8'))
    tokenizer = Tokenizer.from_file(str(args.tokenizer_dir / 'tokenizer.json'))
    cases = json.loads(source.read_bytes())
    encoded = {}
    rendered = {}
    for case in cases:
        text = template.render(**{**config, 'messages': messages(case['visible']),
                                  'add_generation_prompt': True, 'enable_thinking': False})
        for m in case['visible']['prefix']:
            if m['role'] == 'tool':
                for value in m['content']['record'].values():
                    if isinstance(value, str) and value not in text:
                        raise ValueError('Template dropped a record value: ' + case['id'])
        rendered[case['id']] = text
        encoded[case['id']] = tokenizer.encode(text, add_special_tokens=False)
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
                start = text.index(value)
                end = start + len(value)
                return all(all(start <= enc.offsets[t][0] and enc.offsets[t][1] <= end
                               for t in range(*s[side])) for s in spans)
            only_field = ta.replace(sa, '<CONTRAST>') == tb.replace(sb, '<CONTRAST>')
            aligned = len(ea.ids) == len(eb.ids) and all(s['a'] == s['b'] for s in spans)
            comparisons.append(dict(a=a['id'], b=b['id'], kind='fact' if decisive else 'parcel',
                                    counts=[len(ea.ids), len(eb.ids)], differing_spans=spans,
                                    aligned=aligned, only_expected_field=only_field,
                                    tokens_within_field=inside(ea, ta, sa, 'a') and inside(eb, tb, sb, 'b')))
    report.update(status='complete', index_convention='zero-based half-open spans; final token inclusive',
                  cases={k: dict(tokens=len(v.ids), decision_point=len(v.ids)-1,
                                 rendered_sha256=hashlib.sha256(rendered[k].encode()).hexdigest())
                         for k, v in encoded.items()}, comparisons=comparisons)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return int(any(not all(c[k] for k in ('aligned', 'only_expected_field', 'tokens_within_field'))
                   for c in comparisons))


if __name__ == '__main__':
    raise SystemExit(main())
