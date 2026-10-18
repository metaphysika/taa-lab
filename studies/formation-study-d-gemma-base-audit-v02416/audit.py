import json,sys,hashlib,tempfile,pathlib,collections
dst=pathlib.Path(__file__).resolve().parent; root=dst.parents[1]; data=dst/'returned/gemma-base-v02416-gpu-return-001'; assets=root/'studies/formation-study-d-gemma-base-v02416'
plan=json.loads((assets/'plan.json').read_text());bundle=json.loads((assets/'bundle.json').read_text());tmp=tempfile.TemporaryDirectory()
for n,s in bundle.items():
 assert hashlib.sha256(s.encode()).hexdigest()==plan['bundle_sha256'][n]
 p=pathlib.Path(tmp.name)/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
sys.path.insert(0,tmp.name)
from formation.study_d_base_gate_v0248 import evaluate_episode,summarize
cases={p['case']['id']:p['case'] for p in plan['cases']};rows=[]
events=[json.loads(s) for s in (data/'gemma-base/events.jsonl').read_text().splitlines()];starts=[e for e in events if e['event']=='generation_start'];ends=[e for e in events if e['event']=='generation_return'];assert len(starts)==len(ends)==139
assert [e['request_id'] for e in starts]==[e['request_id'] for e in ends]
endmap={e['request_id']:e for e in ends}
for cell in plan['schedule']:
 case=cases[cell['case_id']];saved=json.loads((data/'gemma-base'/f"{case['id']}-r{cell['repeat']}.json").read_text())
 def generate(system,history,turn):
  key=f"{case['id']}/r{cell['repeat']}/t{turn}"; event=next(e for e in starts if e['request_id']==key)
  assert event['messages']==[dict(role='system',content=system)]+history
  ids=event['prompt_token_ids'];assert isinstance(ids,list) and all(type(i)==int for i in ids) and len(ids)+4096<=16384
  return endmap[key]['raw_text']
 row=evaluate_episode(case,generate);row['repeat']=cell['repeat'];assert row==saved,case['id'];rows.append(row)
s=summarize(rows,list(cases),{k:c['kind'] for k,c in cases.items()});r=json.loads((data/'gemma-base/report.json').read_text());assert r['summary']==s
cpu=json.loads((data/'cpu-check/receipt.json').read_text())
for n,h in cpu['evidence_sha256'].items():assert hashlib.sha256((data/n).read_bytes()).hexdigest()==h,n
assert cpu['status']=='PASS' and cpu['commit']=='881361e34c8a4299edbc718a7ab1900a837df6cc'
for stage in ['cpu','gpu']:
 a=json.loads((dst/f'gemma-base-v02416-{stage}-local-attempt.json').read_text());b=json.loads((dst/f'gemma-base-v02416-{stage}-local-attempt.submission.json').read_text());assert a['commit']==cpu['commit'];print(stage,b)
res=dict(status='PASS: offline consistency/replay audit; original format gate FAIL',episodes_replayed=len(rows),native_requests=139,source_commit=cpu['commit'],cpu_receipt_hashes_verified=True,summary=s,labels=dict(collections.Counter(x['score']['substance_outcome'] for x in rows)),load_seconds=r['load_seconds'],sampled_peak_bytes=r['memory']['sampled_peak_device_used_bytes'],generation_tokens_per_second=r['measured_tokens_per_second'],exceptions=[dict(case=x['case_id'] if 'case_id' in x else 'B-WU-cold-r2-pressure-U',repeat=x['repeat'],label=x['score']['substance_outcome']) for x in rows if not x['first_reply_parsed']],billing=dict(owner_remaining_credit_usd=25.70,owner_displayed_used_usd=4.30,prior_reported_total_usd=2.59,displayed_increment_usd=1.71,scope='owner reports $4.30 used/$25.70 left; not an itemized invoice',actual_invoice_export=None),training_performed=False,owner_exception='admitted post-results separately; FAIL unchanged; no cases removed')
(dst/'audit-results.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
