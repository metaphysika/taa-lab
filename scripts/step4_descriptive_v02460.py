"""CPU-only post-hoc readings. Writes only the named generated document."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exploratory.measurement_v02456.policy import parse_action, first_json_span
from exploratory.step4_harness.runner import labels
ROOT = Path(__file__).resolve().parents[1]

def events(path):
    data = path.read_bytes()
    if path.suffix == '.gz':
        data = gzip.decompress(data)
    return [json.loads(x) for x in data.splitlines()]

def answer(raw):
    lines = raw.strip().splitlines() if isinstance(raw, str) else []
    value = lines[0].strip().lower().removesuffix('.') if lines else None
    return value if value in ('yes', 'no') else None

def actions(raw):
    result = []
    while raw:
        try:
            span = first_json_span(raw)
            result.append(parse_action(span, multiple='first'))
            raw = raw[raw.index(span)+len(span):]
        except (ValueError, TypeError):
            break
    return result

def generate():
    paths = [next(ROOT.glob('results/*main base-neutral/events.jsonl')),
             next(ROOT.glob('results/*main contrary-virtue/events.jsonl.gz'))]
    groups = defaultdict(list); lengths = defaultdict(list); rows = []; all_events = []
    sources = []
    for path in paths:
        ev = events(path); all_events.extend(ev)
        sources.append(f"- `{path.relative_to(ROOT).as_posix()}` SHA256 `{hashlib.sha256(path.read_bytes()).hexdigest()}`")
        rows.extend(e['row'] for e in ev if e['event'] == 'cell')
    labs = labels()
    for row in rows:
        for attempt in row['attempts']:
            raw = attempt.get('raw')
            if not isinstance(raw, str):
                raw = ''
            groups[row['checkpoint'], labs[row['case_id']], row['branch']].append(raw)
            lengths[row['checkpoint']].append(raw)
    out = ['# Step 4 descriptive readings v0.24.60', '',
        '**POST HOC, DESCRIPTIVE ONLY. This is not a rescoring. Frozen verdicts stand: F1 no headroom; probes not diagnosable. These reply counts never enter the frozen analysis.**', '',
        'Reproduce: `python scripts/step4_descriptive_v02460.py`. All retained main-block replies, including timeout partials when present, are included. Missing branches are not replies. Counts below describe syntax and first choices, not completed episodes or correctness.', '', *sources, '',
        '| Checkpoint | Label | Variant | Replies | Frozen readable counts | Frozen unreadable | First-action counts | First-action unreadable | First-line yes/no | First-line unreadable | Later primary/stop conflict |',
        '|---|---|---|---:|---|---:|---|---:|---|---:|---:|']
    for (arm,label,branch), raws in sorted(groups.items()):
        frozen=Counter(); first=Counter(); lines=Counter(); conflicts=0
        for raw in raws:
            try:
                if branch == 'action':
                    value = str(parse_action(raw, multiple='malformed')['tool'])
                else:
                    value = raw.strip().lower().removesuffix('.')
                    if value not in ('yes','no'): raise ValueError()
                frozen[value]+=1
            except (ValueError,TypeError): frozen['UNREADABLE']+=1
            found=actions(raw)
            if found:
                first[str(found[0]['tool'])]+=1
                # A later primary conflicts with an initial routine/report/stop;
                # later work conflicts with an initial stop. Descriptive, no intent inferred.
                conflicts += int(any((a['tool']=='perform_primary' and found[0]['tool']!='perform_primary') or
                    (found[0]['tool'] is None and a['tool'] is not None) for a in found[1:]))
            else: first['UNREADABLE']+=1
            lines[answer(raw) or 'UNREADABLE']+=1
        def counts(c): return ', '.join(f'{k}:{v}' for k,v in sorted(c.items()) if k!='UNREADABLE') or 'none'
        out.append(f'| {arm} | {label} | {branch} | {len(raws)} | {counts(frozen)} | {frozen["UNREADABLE"]} | {counts(first)} | {first["UNREADABLE"]} | {counts(lines)} | {lines["UNREADABLE"]} | {conflicts} |')
    out += ['', 'A first-action reading describes only that action. Later content can contradict it. The conflict column counts replies with a later primary after a different first action, or later work after a first stop; it is a conservative operational conflict indicator, not an exhaustive semantic contradiction judgment. All extra text remains in the sources. First-action readings of probes and first-line readings of actions are shown for completeness, not as valid outcomes for those branches.', '', '## Reply length, format and recurring phrases', '']
    for arm,raws in sorted(lengths.items()):
        action_raws=[raw for (a,l,b),rs in groups.items() if a==arm and b=='action' for raw in rs]
        rejected=sum(1 for raw in action_raws if _bad(raw))
        phrases={p:sum(p.lower() in raw.lower() for raw in raws) for p in ('I cannot promise','report_issue','perform_primary','check_routine')}
        out += [f'{arm}: {len(raws)} replies, mean {statistics.mean(map(len,raws)):.1f} characters, maximum {max(map(len,raws))}; frozen action parser unreadable {rejected}/{len(action_raws)}. Recurring phrase/substring counts (case insensitive, one count per reply): {phrases}. At a rough assumed four characters/token, {sum(len(x)>4096 for x in raws)} replies exceed the 1,024-token character proxy. Exact past token counts are unavailable in the retained journal; all {len(raws)} are unknown for an exact 1,024-token cutoff. This proxy does not establish actual truncation counts.', '']
    out += ['## Timing inputs for the crossing estimate', '']
    cv=events(paths[1]); cr=[r for r in rows if r['checkpoint']=='contrary']; ar=[r for r in cr if r['branch']=='action']
    before={e['request']:e for e in cv if e['event']=='before_generation'}
    durations=[e['monotonic_seconds']-before[e['request']]['monotonic_seconds'] for e in cv if e['event']=='returned' and before[e['request']]['checkpoint']=='contrary']
    phases=[e['elapsed'] for e in cv if e['event']=='phase_end']
    out += [f'Measured contrary: {len(cr)} branches, {sum(len(r["attempts"]) for r in cr)} requests; action-only {len(ar)} episodes / {sum(len(r["attempts"]) for r in ar)} requests (derived {sum(len(r["attempts"]) for r in ar)/len(ar):.3f} requests/episode). Mean generation interval {statistics.mean(durations):.3f} seconds/request across {len(durations)} returned requests; excludes journal time between requests. Inventory and engine phase elapsed sum {sum(phases):.3f} seconds. These main-block measurements are a format-fragile proxy for a different battery, not a guarantee.', '']
    return '\n'.join(out)

def _bad(raw):
    try: parse_action(raw,multiple='malformed'); return False
    except (ValueError,TypeError): return True

if __name__=='__main__':
    (ROOT/'docs/process/STEP4_DESCRIPTIVE_POSTHOC_v02460.md').write_text(generate(),encoding='utf8')
