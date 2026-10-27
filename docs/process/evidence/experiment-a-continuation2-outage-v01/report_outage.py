"""Read-only inventory of retained rows and accounting; no episode reconstruction."""
import json,base64
from pathlib import Path
from collections import Counter
from decimal import Decimal
P=Path(__file__).parent
sources=[Path('/workspace/taa-experiment-a-evidence/pilot-b871cee5-20261026/pilot'),Path('/workspace/taa-experiment-a-evidence/continuation1-480835a8-20261027/pilot'),P/'pilot']
def frames(p):return [json.loads(f.read_bytes()) for f in sorted(p.glob('[0-9]*.json'))]
before=json.loads((P/'outage-before.json').read_text());validation=json.loads((P/'outage-verification.json').read_text())
allframes=[f for p in sources for f in frames(p)]
rows=[f['value'] for f in allframes if f['kind']=='episode_summary']
native={p:Counter() for p in ('anthropic','google')};dollars={p:Decimal(0) for p in native};request=None
for f in allframes:
 if f['kind']=='request':request=f['value']
 elif f['kind']=='native_reply':
  v=json.loads(base64.b64decode(f['value']['base64']));u=v.get('usage',v.get('usageMetadata'))
  for k,n in u.items():
   if type(n)is int:native[request['provider']][k]+=n
   elif isinstance(n,dict):
    for kk,nn in n.items():
     if type(nn)is int:native[request['provider']][k+'.'+kk]+=nn
 elif f['kind']=='usage':dollars[f['value']['provider']]+=Decimal(f['value']['charged'])
counts=Counter((r['spec']['provider'],r['spec']['arm'],'D' if r['spec']['program'].startswith('T') else 'P') for r in rows)
report=['# Experiment A continuation 2: executor outage','',
 '[Descriptive] Chris authorized a status check and append-only closure on 2026-10-27. No experiment CLI, continuation or provider request was started. Existing process is not alive. Evidence is intact as retained; the interrupted episode has no episode_end/score row. Missing scores were not reconstructed. This is a guard stop, never resumed.','',
 '[Descriptive] Last pre-closure evidence file: `pilot/episode-0090/000040.json`, written **2026-10-27T15:48:41.317104Z** (10:48:41.317104 a.m. America/Chicago). Last recorded request: **index 90, T09/taa/Anthropic, repeat 3, turn 4, attempt 1**. The child subsequently records the host step for turn 5, but no turn-5 provider request exists.','',
 '[Descriptive] Before closure: 36 completed C2 child chains verified; the interrupted child and root had valid canonical hash-linked prefixes without checkpoints. Appended an executor_outage closure to that child, an explicit recovery observation and executor_outage closure to the root. All 94 chains now verify (3 roots, 91 children). All pre-existing files, bytes and timestamps remain unchanged. No synthetic episode_end, oracle assessment, scientific score or summary was inserted.','',
 '[Descriptive] Whole pilot: **88 complete episodes**, two earlier recorded guard stops (indices 22 and 53), and interrupted index 90 now closed as executor_outage without a score row; **91 touched indices**, **305 untouched**. C2 alone: 36 complete and one interrupted. The index-90 score is unavailable in this status report; do not silently classify it as model_done or derive a point estimate from this inventory. Earlier results and stopped rows remain unchanged.','',
 '| Provider | Arm | D complete | P complete |','|---|---|---:|---:|']
for p in native:
 for arm in ('model_alone','conventional','taa'):report.append(f'| {p} | {arm} | {counts[p,arm,"D"]} | {counts[p,arm,"P"]} |')
report+=['','[Descriptive] Every native settlement and retained reserve in all three roots was checked using the committed read-only accounting auditor. It exactly reconciles to published/local experiment-state **40f2c28cf127a8d75aaea14083d74b3ea3a9f524**, last advanced 2026-10-27T15:48:37Z. All 232 C2 reservations, requests, replies and settlements are present; no C2 reservation is open. Earlier failed neutral-check reserve remains part of the historical baseline.','',
 '| Anthropic cumulative | Google cumulative | Step cumulative |','|---:|---:|---:|',
 f'| ${before["accounting"]["provider_totals"]["anthropic"]} | ${before["accounting"]["provider_totals"]["google"]} | ${before["accounting"]["step_total"]} |','',
 '[Descriptive] Whole-pilot request/reply count: 558. Native-usage-backed charges at frozen prices (not an independent provider invoice): '+', '.join(p+' $'+str(v) for p,v in dollars.items())+'. Native token totals below preserve provider field meanings: Anthropic output includes thinking; Google prompt includes cache. Do not add nested detail fields to their parent totals.','',
 '| Provider | Native usage field | Tokens |','|---|---|---:|']
for p,ns in native.items():
 for k,n in sorted(ns.items()):report.append(f'| {p} | {k} | {n} |')
report+=['','[Descriptive] Every confirmation observation, delay and same-commit re-push from all roots is preserved in state-confirmations.json and the raw journals, including the stranded-settlement publication before C2 request 1. No confirmation or re-push occurred during this status check.','',
 '[Descriptive] **Active lease and every marker are unchanged**, including continuation-000002.once. The approved detached code checkout was not modified. H stays sealed; no H material, verdict, bootstrap, rescore, replacement or resume. The executor failure cause and exact process death time are not established by retained evidence.','',
 '| Root | Frames | Checkpoint |','|---|---:|---|']
for source in sources:
 cp=next(c for c in validation['chains'] if c['directory']==str(source));report.append(f'| `{source}` | {cp["count"]} | `{cp["head"]}` |')
report+=['','[Descriptive] Reproduction: close_outage.py records the owner-authorized closure procedure (one time only, refuses an already closed root); outage-before.json pins every pre-existing evidence file and tracked state file; outage-verification.json contains all 94 ending checkpoints and the accounting result. report_outage.py reads retained records only. Older describe.py/render.py are unexecuted pre-outage helpers, not this report’s source and not a completed-pilot analysis.','',
 '[Descriptive] Publication: retained files and raw archive are scanned with the PR #38 credential patterns, exact configured-secret comparisons, archive-member and decoded-native checks. See secret-scan.json and project-publication-scan.json for actual results. Results-only PR #41 remains draft/unmerged for Claude and Astra review.']
(P/'REPORT.md').write_text('\n'.join(report)+'\n')
(P/'retained-native-usage.json').write_text(json.dumps(dict(claim='[Descriptive] Retained native fields only; no scientific outcome reconstruction.',native_tokens={p:dict(n) for p,n in native.items()},usage_backed_dollars={p:str(v) for p,v in dollars.items()},completed_episode_inventory=[dict(provider=p,arm=a,case_set=s,complete=n) for (p,a,s),n in sorted(counts.items())]),indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(complete=len(rows),requests=sum(f['kind']=='request' for f in allframes),usage_backed_dollars={p:str(v) for p,v in dollars.items()})))
