"""Offline cost projection from retained live episodes and native neutral usage.

No model transport, tokenizer service or scenario/controller rerun is invoked.
"""
from pathlib import Path
from decimal import Decimal as D
from collections import defaultdict
import csv,hashlib,json,zipfile
ROOT=Path('/workspace/taa-lab');OUT=Path(__file__).parent
source=ROOT/'studies/live-demo-03131469-review'
previous=ROOT/'docs/process/evidence/experiment-a-neutral-checks-v01'
guide=json.loads((previous/'guide-token-proxies.json').read_bytes())
actual_guide=(ROOT/'experiment_a/inputs/policy-guide.txt').read_bytes()
assert guide['guide_sha256']==hashlib.sha256(actual_guide).hexdigest()
assert guide['utf8_bytes']==len(actual_guide)==2536
rows=list(csv.DictReader((source/'per-episode.csv').open()))
turns=defaultdict(list);current=None
with zipfile.ZipFile(source/'full-evidence.zip') as z:
 for name in sorted(n for n in z.namelist() if n.startswith('original/evidence/') and len(n.split('/'))==3 and n.rsplit('/',1)[1][:1].isdigit() and n.endswith('.json')):
  frame=json.loads(z.read(name));value=frame['value']
  if frame['kind']=='request':current=(value['spec']['program'],value['spec']['arm'],value['spec']['repeat'])
  if frame['kind']=='usage':
   assert value['native'].get('completion_tokens_details',{}).get('reasoning_tokens',0)==0
   turns[current].append(value['native'])
projected=[]
for row in rows:
 native=turns[row['program'],row['arm'],1]
 assert sum(u['prompt_tokens'] for u in native)==int(row['input_tokens'])
 assert sum(u['completion_tokens'] for u in native)==int(row['output_tokens'])
 assert len(native)==int(row['turns'])
 first=native[0]['prompt_tokens'];assert all(u['prompt_tokens']>=first for u in native)
 projected.append(dict(episode=row['episode'],program=row['program'],arm=row['arm'],turns=len(native),input_tokens=int(row['input_tokens']),visible_output_tokens=int(row['output_tokens']),initial_prefix_tokens=first,per_turn_input=[u['prompt_tokens'] for u in native],per_turn_output=[u['completion_tokens'] for u in native]))
assert projected==json.loads((previous/'live-count-episodes.json').read_bytes())
assert (len(projected),sum(r['turns'] for r in projected),sum(r['input_tokens'] for r in projected),sum(r['visible_output_tokens'] for r in projected))==(30,275,540546,9336)
check=json.loads((OUT/'check-summary.json').read_bytes())
sonnet=check['native_usage']
sonnet_thinking=sum(u['output_tokens_details']['thinking_tokens'] for u in sonnet)
sonnet_total=sum(u['output_tokens'] for u in sonnet)
assert sonnet_thinking==0 and sonnet_total==74
sonnet_ratio=D(sonnet_thinking)/D(sonnet_total-sonnet_thinking)
google=next(r['native_usage'] for r in json.loads((previous/'check-summary.json').read_bytes())['rows'] if r['provider']=='google')
google_ratios=[D(u['thoughtsTokenCount'])/D(u['candidatesTokenCount']) for u in google]
google_pooled=D(sum(u['thoughtsTokenCount'] for u in google))/D(sum(u['candidatesTokenCount'] for u in google))
prices=json.loads((ROOT/'experiment_a/inputs/prices.json').read_bytes());scale=D(198)/30

def costs(provider,g,ratio=None,ceiling=False):
 rates=prices[provider]['rates'];rate=lambda n:D(rates[n+'_per_million'])
 totals={name:D(0) for name in ('disabled','no_hits','first_cold_then_prefix_hits')}
 for row in projected:
  t=row['turns'];prefix=D(row['initial_prefix_tokens']+g);inp=D(row['input_tokens']+g*t)
  output=D(t*(32768 if provider=='anthropic' else 65536)) if ceiling else D(row['visible_output_tokens'])*(1+ratio)
  out=output*rate('output')
  write=rate('cache_write_5m') if provider=='anthropic' else rate('input')
  totals['disabled']+=inp*rate('input')+out
  totals['no_hits']+=(inp-prefix*t)*rate('input')+prefix*t*write+out
  totals['first_cold_then_prefix_hits']+=(inp-prefix*t)*rate('input')+prefix*write+prefix*(t-1)*rate('cache_read')+out
 return {name:str(value*scale/1000000) for name,value in totals.items()}

result=dict(claim='[Interpretive] Conditional pilot-only costs from historical live usage and two neutral replies per provider; not affordability/completion guarantees.',source=dict(episodes=30,turns=275,input_tokens=540546,visible_output_tokens=9336,csv_sha256=hashlib.sha256((source/'per-episode.csv').read_bytes()).hexdigest(),archive_sha256=hashlib.sha256((source/'full-evidence.zip').read_bytes()).hexdigest(),reconstructed_rows_match_prior=True),pilot_episodes_per_provider=198,scale=str(scale),guide=guide,observed_ratios=dict(anthropic=dict(native_field='output_tokens_details.thinking_tokens',thinking=sonnet_thinking,total_output=sonnet_total,visible_output=sonnet_total-sonnet_thinking,per_reply=['0/50 = 0','0/24 = 0'],pooled=str(sonnet_ratio)),google=dict(per_reply=[str(v) for v in google_ratios],pooled=str(google_pooled),thinking=75,visible_output=24)),anthropic=dict(observed_ratio_guide533=costs('anthropic',533,sonnet_ratio),observed_ratio_guide536=costs('anthropic',536,sonnet_ratio),borrowed_google_ratio_sensitivity_not_observed_sonnet=costs('anthropic',536,google_pooled),output_ceiling_scenario=costs('anthropic',536,ceiling=True)),google=dict(low=costs('google',533,min(google_ratios)),central=costs('google',533,google_pooled),high=costs('google',536,max(google_ratios)),output_ceiling_scenario=costs('google',536,ceiling=True)),already_booked=check['after'],assumptions=['Each episode retains its actual input/output/turn count; scale30 to198 by6.6.','Add533–536 guide proxy tokens on EVERY turn. Offline o200k/cl100k counts are not native Sonnet/Gemini counts; no extra provider count request.','The30source episodes used Luna/floor/static/TAA on D; conventional/newP/provider behavior is not measured by this anchor.','Without hits Sonnet writes marked initial prefix on each turn at5m rates; Google misses cost ordinary input. Hit scenario assumes first turn cold then only that initial prefix hits in the SAME episode; growing history remains normal input. No cross-episode savings assumed.','Observed Sonnet thinking/visible ratio is0/74=0 in this short echo. It is not evidence future refund episodes have zero thinking; no signed/thinking continuity was exercised.','Google per-reply ratios2.125–3.625 and pooled3.125 come from its retained attempt1, not a new check. These ranges are proxy/sensitivity ranges, not statistical confidence intervals.','Neither provider check observed cache reads/writes. Cache-hit savings are hypothetical. Input/signature tokenization, cache eligibility/expiry, longer turns and retries can change costs.','Pilot-only forecasts exclude existing spend/checks. Output-ceiling scenarios hold historical turns/input fixed and would exceed caps, not complete pilots at those totals. Current provider/shared stops govern; no pilot is approved.'])
old=json.loads((previous/'live-count-projection.json').read_bytes())
assert all(result['google'][k]==old['google'][k] for k in ('low','central','high'))
(OUT/'live-count-episodes.json').write_text(json.dumps(projected,sort_keys=True,indent=2)+'\n')
(OUT/'live-count-projection.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('observed_ratios','anthropic','google')},indent=2))
