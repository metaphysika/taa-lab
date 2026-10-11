"""Free Gate 3 estimates and fingerprint verification. No provider entry point."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
PLAN=ROOT/'studies/formation-study-a-evaluation-plan-v0217.json'
FREEZE=ROOT/'studies/formation-study-a-freeze-v0217.json'


def estimate(plan,prices,pilot):
    usage=pilot['accounting'];rows=[]
    for item in plan['models']:
        p=prices[item['model']];repeats=item['repeats'];requests=24*12*repeats
        forecast=(usage['input_tokens']*p['input_per_million']+usage['output_tokens']*p['output_per_million'])/1e6*repeats
        maximum_input=max(p['input_per_million'],p.get('cache_write_per_million',0))
        worst=requests*(32002*maximum_input+2048*p['output_per_million'])/1e6
        rows.append(dict(item,episodes=24*repeats,max_requests=requests,
            pilot_usage_no_cache_forecast_dollars=round(forecast,8),
            all_requests_at_full_ceiling_dollars=round(worst,8),
            basis='Luna usage scaled at this model prices, no cache discount; other tokenizer and behavior unknown'))
    return {'models':rows,'forecast_total_dollars':sum(r['pilot_usage_no_cache_forecast_dollars'] for r in rows),
            'whole_formation_stop_per_paid_provider':8,'funding_authorized':False,
            'completion_guaranteed_within_budget':False}


def verify_freeze(path=FREEZE):
    frozen=json.loads(Path(path).read_text())
    entries=dict(frozen['sha256'],**frozen.get('adapter_reference_sha256',{}))
    bad=[p for p,h in entries.items() if not (ROOT/p).exists() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    if bad:raise ValueError('freeze mismatch: '+', '.join(bad))
    return len(entries)

if __name__=='__main__':
    plan=json.loads(PLAN.read_text());prices=json.loads((ROOT/plan['price_file']).read_text())['models']
    pilot=json.loads((ROOT/'results/2026-10-10 v0.21.6 luna-none r1 baseline-pressure pilot/summary.json').read_text())
    print(json.dumps(estimate(plan,prices,pilot),indent=2))
    print('Frozen candidate files verified:',verify_freeze())
