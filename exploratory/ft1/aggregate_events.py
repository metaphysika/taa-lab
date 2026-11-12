"""Offline JSONL aggregation command; private inputs stay local."""
import json
from pathlib import Path
from .aggregation import aggregate,analyze
from .data import safe_output

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--cases',required=True); p.add_argument('--events',required=True)
    p.add_argument('--eligibility',required=True); p.add_argument('--output',required=True)
    a=p.parse_args()
    cases=json.loads(Path(a.cases).read_text(encoding='utf-8'))['cases']
    events=[json.loads(line) for line in Path(a.events).read_text(encoding='utf-8').splitlines()]
    gates=json.loads(Path(a.eligibility).read_text(encoding='utf-8'))
    eligibility={(g['arm'],g['training_seed']):g for g in gates}
    summaries,descriptive=aggregate(cases,events,eligibility)
    result=dict(predictions=analyze(summaries),
                models=[dict(arm=arm,training_seed=seed,counts=s['counts'],
                             denominators=dict(pairs=24,servile_W=s['servile_w_denominator'],U=24,knowledge=48),
                             pair_correct_min=sum(p['minimum'] for p in s['pair_bounds']),
                             pair_correct_max=sum(p['maximum'] for p in s['pair_bounds']),
                             knowledge=s['knowledge'],secondary_bounds=s['secondary_bounds'],missing_episodes=s['missing_episodes'],
                             mechanical_turn_rate=s['mechanical_turn_rate'])
                        for (arm,seed),s in descriptive.items()])
    safe_output(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    # Do not print private case data or per-case summaries.

if __name__=='__main__': main()
