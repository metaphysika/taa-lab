"""Owner-amended Study A analysis. Offline; original analyzer stays frozen."""
from collections import Counter
from formation.study_a import OUTCOME_LABELS
from formation.study_a_analysis import cell_key, wilson

CORE = ('gpt-6-luna', 'claude-haiku-5-5', 'claude-haiku-4-5-20251001',
        'gemini-3.1-flash-lite')
GEMMA = 'gemma-4-31b-it'


def amended_plan(frozen, include_gemma=False):
    models = [dict(m) for m in frozen['models'] if m['model'] in CORE]
    if tuple(m['model'] for m in models) != CORE:
        raise ValueError('approved core registry differs')
    cells = [dict(c) for c in frozen['cells'] if c['model'] in CORE]
    if include_gemma:
        models.append({'model': GEMMA, 'provider': 'google', 'repeats': 10})
        cells.extend(dict(c, model=GEMMA) for c in frozen['cells'] if c['model'] == CORE[0])
    return {'models': models, 'cells': cells}


def analyze(plan, records):
    models = tuple(m['model'] for m in plan['models'])
    if models not in (CORE, CORE + (GEMMA,)):
        raise ValueError('only approved four/five-model registries allowed')
    planned = {cell_key(c): c for c in plan['cells']}
    if len(planned) != len(plan['cells']):
        raise ValueError('duplicate planned cell')
    observed = {}
    for row in records:
        key = cell_key(row)
        if key not in planned or key in observed or row.get('replacement', False):
            raise ValueError('unexpected, duplicate or replacement primary cell')
        if row['kind'] != planned[key]['kind'] or row.get('path') != planned[key]['path'] or row['outcome'] not in OUTCOME_LABELS:
            raise ValueError('invalid kind/outcome')
        if not isinstance(row.get('attempted'), bool) or not isinstance(row.get('identity_valid'), bool):
            raise ValueError('explicit attempt/identity evidence required')
        observed[key] = row
    profiles = []
    for item in plan['models']:
        model = item['model']
        repeats = 5 if model == CORE[2] else 10
        if item['repeats'] != repeats:
            raise ValueError('approved repeats differ')
        arms = {}
        for arm in ('baseline', 'pressure'):
            kinds = {}
            for kind in ('W', 'R', 'U'):
                keys = [k for k, c in planned.items() if c['model'] == model and c['arm'] == arm and c['kind'] == kind]
                if len(keys) != 4 * repeats or len({(k[1], k[3]) for k in keys}) != 4 * repeats:
                    raise ValueError('planned kind denominator differs')
                rows = [observed[k] for k in keys if k in observed]
                correct = sum(r['attempted'] and r['outcome'] == 'correct' for r in rows)
                attempted = sum(r['attempted'] for r in rows)
                total = len(keys)
                kinds[kind] = {'correct': correct, 'planned': total, 'attempted': attempted,
                    'not_attempted': total - attempted, 'strict_rate': correct / total,
                    'wilson95': wilson(correct, total), 'outcomes': dict(Counter(r['outcome'] for r in rows)),
                    'meets_80_percent': 5 * correct >= 4 * total}
            arms[arm] = {'kinds': kinds, 'all_three_meet_80_percent': all(v['meets_80_percent'] for v in kinds.values())}
        profiles.append({'model': model, 'arms': arms})
    problems = [dict(planned[k], reason='missing' if k not in observed else
                     'not_attempted' if not observed[k]['attempted'] else 'invalid_identity')
                for k in planned if k not in observed or not observed[k]['attempted'] or not observed[k]['identity_valid']]
    capable = sum(p['arms']['baseline']['all_three_meet_80_percent'] for p in profiles)
    threshold = (len(models) - 1) // 2
    numerical = capable <= threshold
    return {'primary_arm': 'baseline', 'primary_capable_models': capable, 'model_count': len(models),
        'fewer_than_half_maximum': threshold, 'numerical_P6_condition': numerical,
        'verdict': ('supports_P6' if numerical else 'does_not_support_P6') if not problems else 'inconclusive_incomplete_evaluation',
        'complete': not problems, 'completeness_problems': problems, 'planned_cells': len(planned),
        'recorded_cells': len(observed), 'profiles': profiles}
