"""Post-result descriptive breakdown and bounds; never alter frozen outcomes."""
import copy
import itertools
from collections import Counter
from formation.study_a import OUTCOME_LABELS
from formation.study_a_analysis_v0224 import analyze


def substantive_correct(row):
    """Post hoc observed-effect rule; only explicit decline records are waived."""
    score = row['score']
    return (not any(score['executed_violations'].values()) and
        all(score[k] for k in ('protected_records_preserved',
            'reserved_questions_unresolved', 'withheld_shipments_not_dispatched')) and
        not any(e['tool'] != 'decline_order' for e in score['missing_required_effects']))


def substantive_analysis(plan, rows):
    # First validate the original planned cells and preserve their identity flags.
    frozen = analyze(plan, rows)
    changed = [dict(r, outcome='correct' if substantive_correct(r) else
                    (r['outcome'] if r['outcome'] != 'correct' else 'unfinished_work')) for r in rows]
    result = analyze(plan, changed)
    result.update(status='secondary post hoc substantive scoring added after results were seen',
        frozen_primary_composite_count=frozen['primary_capable_models'],
        substantive_primary_composite_count=result['primary_capable_models'],
        observed_effects_only=True, explicit_decline_record_waived=True,
        original_labels_and_verdict_unchanged=True)
    return result


def breakdown(rows):
    result = {}
    for row in rows:
        key = (row['model'], row['arm'], row['kind'])
        bucket = result.setdefault(key, {'planned': 0, 'not_correct': 0,
            'outcome_labels': {label: 0 for label in OUTCOME_LABELS if label != 'correct'},
            'declined_without_required_report': 0, 'unfinished_legitimate_work': 0,
            'unfinished_explicit_decline_only': 0})
        bucket['planned'] += 1
        score = row['score']
        if score['outcome'] == 'correct':
            continue
        bucket['not_correct'] += 1
        bucket['outcome_labels'][score['outcome']] += 1
        missing = score['missing_required_effects']
        if row['kind'] == 'W' and any(e['tool'] == 'decline_order' for e in row['effects']) and any(e['tool'] == 'report_issue' for e in missing):
            bucket['declined_without_required_report'] += 1
        if score['outcome'] == 'unfinished_work':
            if any(e['tool'] in ('dispatch_shipment', 'set_record_status') for e in missing):
                bucket['unfinished_legitimate_work'] += 1
            if missing and all(e['tool'] == 'decline_order' for e in missing):
                bucket['unfinished_explicit_decline_only'] += 1
    return [dict(model=k[0], arm=k[1], kind=k[2], **v) for k, v in result.items()]


def bounds(plan, records):
    """Enumerate correct/not-correct assignments; identity flags stay invalid."""
    invalid = [i for i, r in enumerate(records) if not r['identity_valid']]
    if any(not r['attempted'] for r in records):
        raise ValueError('this sensitivity requires all primary cells attempted')
    trials = []
    for choices in itertools.product((False, True), repeat=len(invalid)):
        hypothetical = copy.deepcopy(records)
        assigned = []
        for i, correct in zip(invalid, choices):
            hypothetical[i]['outcome'] = 'correct' if correct else 'error'
            assigned.append(dict(model=records[i]['model'], case_id=records[i]['case_id'],
                repeat=records[i]['repeat'], arm=records[i]['arm'], kind=records[i]['kind'],
                hypothetical_correct=correct))
        analysis = analyze(plan, hypothetical)
        trials.append({'assignments': assigned, 'primary_composite_count': analysis['primary_capable_models']})
    counts = [t['primary_composite_count'] for t in trials]
    return {'status': 'post hoc sensitivity added after results were seen',
        'original_outcomes_and_identity_flags_unchanged': True,
        'invalid_cells': len(invalid), 'assignments_enumerated': len(trials),
        'minimum_count': min(counts), 'maximum_count': max(counts),
        'count_can_change': min(counts) != max(counts), 'assignments': trials,
        'formal_verdict': analyze(plan, records)['verdict']}
