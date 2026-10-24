#!/usr/bin/env python3
"""All active frozen/regression sources on the three normative implementations."""
from pathlib import Path
import argparse,json,sys,yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.trace_support import reference_runner as runner,production_backend as core,regressions
from tests.trace_support.bundle import cases,verify_bundle
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as sql
from worlds.refunds.token_bindings import prepare
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);a=p.parse_args()
verify_bundle();report={'scope':'All active sources, historical superseded fixtures retained but not asserted as current policy','backends':{}}
def extra(name):
 path=ROOT/'tests/regression_scenarios'/(name+'.yaml')
 return [dict(id=t['id'],trace=t,parameters={},source=str(path)) for t in yaml.safe_load(path.read_text())]
def summary(rows,n):return dict(scenarios=n,source=sum(r.get('origin')=='source' for r in rows),audits=sum(r.get('origin')=='state-audit' for r in rows),checks=len(rows),discrepancies=sum(r['status']=='discrepancy' for r in rows),incomplete=sum(r['status']=='incomplete' for r in rows))
for name,b in [('reference',reference),('core',core),('conventional',sql)]:
 groups={};report['backends'][name]=groups
 for suite,inputs in [('frozen',cases()),*[(s,extra(s)) for s in ('h1','q14_null_allocation','q14','q14_overlap','q15','q16','comparison_review_v02','q17','q17_1')]]:
  rows=[]
  for c in inputs:
   program,bindings=prepare(c);rows+=runner.run(program,backend=b,token_bindings=bindings)
  groups[suite]=dict(counts=summary(rows,len(inputs)),assertions=rows)
  print(json.dumps(dict(backend=name,suite=suite,**groups[suite]['counts'])),flush=True)
  a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
  if any(r['status']!='pass' for r in rows):raise SystemExit('acceptance disagreement; stop before scoring')
 rr=regressions.run_suite(runner,backend=b);rows=rr['assertions'];groups['permanent']=dict(counts=summary(rows,rr['scenarios']),**rr)
 assert all(r['status']=='pass' for r in rows)
 a.report.write_text(json.dumps(report,indent=2)+'\n')
report['gate_pass']=True;a.report.write_text(json.dumps(report,indent=2)+'\n')
