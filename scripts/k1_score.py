"""Score a K1 journal with the pre-registered k1_analysis counting rules.

Usage: python scripts/k1_score.py <events.jsonl> <receipt.json> <value-grades.jsonl>

Prints counts, prediction quantities and contrary-minus-neutral bounds. Thresholds and
verdicts are applied by hand from the notebook decision rules, not here.
"""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exploratory.step4_harness import k1, k1_analysis as a

ev = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8')]
receipt = json.load(open(sys.argv[2], encoding='utf-8'))
grades = {(g['case_id'], g['checkpoint'], g['repeat']): g
          for g in map(json.loads, open(sys.argv[3], encoding='utf-8'))}
rows = []
for e in ev:
    if e.get('event') != 'cell':
        continue
    row = dict(e['row'])
    if row['k1_arm'] == 'values':
        g = grades[(row['case_id'], row['checkpoint'], row['repeat'])]
        for field in ('value_grade', 'grading_failure'):
            if field in g:
                row[field] = g[field]
    rows.append(row)
cases = {x['id']: x for x in k1.c.cases()}
result = a.tally(receipt['k1_cells'], cases, rows)
for key in sorted(result['counts'], key=str):
    print('counts', key, dict(result['counts'][key]))
for key in sorted(result['prediction_quantities']):
    print('quantity', key, dict(result['prediction_quantities'][key]))
print('bounds', json.dumps(result['contrary_minus_neutral_bounds'], sort_keys=True))
print('wording_agreement', dict(result['wording_agreement']))
print('terminal', dict(collections.Counter((r['k1_arm'], r['terminal_status']) for r in rows)))
ran = {(r['k1_arm'], r['case_id'], r['checkpoint']) for r in rows}
unrun = [(x['k1_arm'], x['case_id'], x['checkpoint']) for x in receipt['k1_cells']
         if (x['k1_arm'], x['case_id'], x['checkpoint']) not in ran]
print('unrun', len(unrun), collections.Counter((x[0], x[2]) for x in unrun))
