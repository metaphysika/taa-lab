"""Offline JSONL aggregation command; private inputs stay local."""
import json
from pathlib import Path
from .aggregation import aggregate,analyze,analyze_rejection_sensitivity
from .data import safe_output
from .plan import SUPPLEMENTARY_MODEL, SUPPLEMENTARY_LABEL

def gate_rows(gates):
    eligibility = {}
    for gate in gates:
        if 'seed' in gate and 'training_seed' in gate and gate['seed'] != gate['training_seed']:
            raise ValueError('conflicting gate seed fields')
        key = (gate['arm'],gate.get('training_seed',gate.get('seed')))
        if key in eligibility and eligibility[key] != gate:
            raise ValueError('conflicting duplicate model gate')
        eligibility[key] = gate
    return eligibility


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--cases',required=True); p.add_argument('--events',required=True)
    p.add_argument('--eligibility',required=True); p.add_argument('--output',required=True)
    a=p.parse_args()
    cases=json.loads(Path(a.cases).read_text(encoding='utf-8'))['cases']
    events=[json.loads(line) for line in Path(a.events).read_text(encoding='utf-8').splitlines()]
    gates=json.loads(Path(a.eligibility).read_text(encoding='utf-8'))
    eligibility=gate_rows(gates)
    summaries,descriptive=aggregate(cases,events,eligibility)
    stopped=any(s.get('decision_required') for cell,s in descriptive.items() if cell != SUPPLEMENTARY_MODEL)
    result=dict(status='gate_decision_required' if stopped else 'complete',
                predictions=None if stopped else analyze(summaries),rejection_sensitivity=None if stopped else analyze_rejection_sensitivity(summaries),
                models=[dict(arm=arm,training_seed=seed,counts=s['counts'],
                             mechanical_unknowns=s['mechanical_unknowns'],gate_status=s['gate_status'],
                             decision_required=s.get('decision_required'),
                             denominators=dict(pairs=24,servile_W=s['servile_w_denominator'],U=24,knowledge=48),
                             pair_correct_min=sum(p['minimum'] for p in s['pair_bounds']),
                             pair_correct_max=sum(p['maximum'] for p in s['pair_bounds']),
                             knowledge=s['knowledge'],secondary_bounds=s['secondary_bounds'],missing_episodes=s['missing_episodes'],
                             mechanical_turn_rate=s['mechanical_turn_rate'])
                        for (arm,seed),s in descriptive.items()])
    if SUPPLEMENTARY_MODEL in descriptive:
        replacement = descriptive[SUPPLEMENTARY_MODEL]
        decision_required = replacement.get('decision_required')
        included = any(s['training_seed'] == SUPPLEMENTARY_MODEL[1] for s in summaries.get('1', []))
        reading = 'not established'
        if included and not stopped:
            p2_arms = {arm: summaries[arm] for arm in ('base', '1', '2') if arm in summaries}
            reading = analyze(p2_arms, include_supplementary=True)['P2']
        result['supplementary_P2'] = dict(label=SUPPLEMENTARY_LABEL, verdict=reading,
                                          replacement_included=included, decision_required=decision_required)
    safe_output(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    # Do not print private case data or per-case summaries.

if __name__=='__main__': main()
