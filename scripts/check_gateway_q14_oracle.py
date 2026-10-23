import argparse,json,sys,itertools
from pathlib import Path
from copy import deepcopy
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.trace_support import reference_runner as runner,production_backend as core
from tests.trace_support.bundle import world
from conventional_gateway import backend as sql
from comparators.business import Backend
from comparators.duty_oracle import Oracle
from worlds.refunds.token_bindings import prepare
p=argparse.ArgumentParser();p.add_argument('--arms',nargs='+',default=['production','conventional','floor','static']);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
source=ROOT/'tests/regression_scenarios/q14.yaml';rows=yaml.safe_load(source.read_text());results=[]
for arm in a.arms:
 b=core if arm=='production' else sql if arm=='conventional' else Backend(arm)
 for trace in rows:
  case=dict(id=trace['id'],trace=trace,parameters={},source=str(source));program,bindings=prepare(case)
  s=b.start(world(),trace.get('setup',{}),defer_first_step=True);o=Oracle(s);proposals={};checked=0
  before_correction=None;error=None
  try:
   for step,group in itertools.groupby(program['trace']['steps'],key=lambda x:x['step']):
    entries=list(group)
    for at in range(s['step']+1,step):
     s=b.enter_step(s,at)[0];o.clock(at);o.reconcile(s)
    o.clock(step);events=[e for entry in entries for e in entry.get('events',[])]
    def observed(index,before,after,result):o.external(events[index],after)
    s=b.enter_step(s,step,events,event_observer=observed)[0];o.reconcile(s)
    def check(entry):
     global checked
     for expected in entry.get('expect',{}).get('duties',[]):
      assert runner.contains(o.board()[expected['id']],expected),(expected,o.board()[expected['id']])
      checked+=1
    for entry in entries:
     if 'propose' not in entry and 'execute' not in entry:check(entry)
    for entry in entries:
     if 'propose' not in entry:continue
     v=entry['propose'];s,r=b.propose(s,v['actor'],v['tool'],v['args']);bindings.record(entry,r.get('execution_intent',r.get('token')))
     if bindings.last is not None:proposals[bindings.last]=v
     o.proposal(v['actor'],v['tool'],v['args'],s);o.reconcile(s);check(entry)
    for entry in entries:
     if 'execute' not in entry:continue
     x=entry['execute'];token=bindings.execution(x);prior=deepcopy(s);s,r=b.execute(s,x['actor'],token,x.get('inject_fault'))
     committed=len(s['receipts'])>len(prior['receipts']) or 'business_operations' in s and len(s['business_operations'])>len(prior['business_operations'])
     if committed:
      v=proposals[token];frozen=deepcopy(s);o.committed(x['actor'],v['tool'],v['args'],s);assert s==frozen
     else:o.reconcile(s)
     check(entry)
    if step==3:before_correction=deepcopy(o.board()['D_resolve(CL7)'])
   d=o.board()['D_resolve(CL7)']
   if trace['id']=='R-Q14-repeated-default':assert d['coverage']==100
   if trace['id'] in ('R-Q14-support-rises','R-Q14-support-falls'):
    assert d['discharge_coverage']==before_correction['discharge_coverage']
    assert d['coverage_proof']!=d['discharge_coverage']
   if trace['id']=='R-Q14-same-coverage-no-reopening':assert not any(h.startswith('reopened@') for h in d['history'])
  except Exception as e:error=dict(type=type(e).__name__,message=str(e))
  results.append(dict(arm=arm,trace=trace['id'],duty_assertions=checked,error=error))
  print(json.dumps(results[-1]),flush=True)
a.report.write_text(json.dumps(dict(results=results,errors=sum(bool(r['error']) for r in results)),indent=2)+'\n');raise SystemExit(any(r['error'] for r in results))
