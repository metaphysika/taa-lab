"""Score an order-crossing journal with the pre-registered crossing_analysis rules.

Usage: python scripts/step4_crossing_score.py <events.jsonl> <receipt.json>
"""
import json, sys, collections
sys.path.insert(0, '.')
from exploratory.step4_harness import crossing as c, crossing_analysis as a
ev = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8')]
receipt = json.load(open(sys.argv[2]))
rows = [e['row'] for e in ev if e.get('event') == 'cell']
cases = {x['id']: x for x in c.cases()}
counts = a.tally(receipt['crossing_cells'], cases, rows)
for k in sorted(counts): print(k, dict(counts[k]))
print(json.dumps(a.verdicts(counts), indent=1))
print('terminal', collections.Counter(r['terminal_status'] for r in rows))
print('labels', collections.Counter((r['checkpoint'], r['crossing_arm'], cases[r['case_id']]['kind'], r['score']['substance_outcome']) for r in rows if 'score' in r))
ran = {(r['case_id'], r['checkpoint'], r['crossing_arm']) for r in rows}
print('unrun', [ (x['case_id'], x['checkpoint'], x['crossing_arm']) for x in receipt['crossing_cells'] if (x['case_id'], x['checkpoint'], x['crossing_arm']) not in ran])
