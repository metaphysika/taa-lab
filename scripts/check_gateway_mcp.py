#!/usr/bin/env python3
"""Scripted JSON-RPC client, frozen sources and permanent regression acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.trace_support import mcp_backend,reference_runner as runner,regressions
from tests.trace_support.bundle import cases,verify_bundle
from worlds.refunds.token_bindings import prepare
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
verify_bundle();report={'scope':'Offline authenticated-session MCP transport acceptance; no model client.','suites':{}}
def counts(rows,scenarios):
 return dict(scenarios=scenarios,source_assertions=sum(r.get('origin')=='source' for r in rows),state_audits=sum(r.get('origin')=='state-audit' for r in rows),checks=len(rows),discrepancies=sum(r['status']=='discrepancy' for r in rows),incomplete=sum(r['status']=='incomplete' for r in rows))
def run(name,programs):
 rows=[]
 for case in programs:
  program,bindings=prepare(case);rows.extend(runner.run(program,backend=mcp_backend,token_bindings=bindings))
 result={'counts':counts(rows,len(programs)),'checks':rows};report['suites'][name]=result
 print(json.dumps(dict(suite=name,**result['counts'])),flush=True)
run('frozen-v022',cases())
# Retain the established hidden-state negative controls and state-delta guard.
r=regressions.run_suite(runner,backend=mcp_backend)
report['suites']['permanent-regressions']={'counts':counts(r['assertions'],r['scenarios']),'checks':r['assertions'],'negative_controls':r['negative_controls']}
print(json.dumps(dict(suite='permanent-regressions',**report['suites']['permanent-regressions']['counts'])),flush=True)
for name in ('h1','q14_null_allocation','q14','q14_overlap','q15','q16'):
 path=ROOT/'tests/regression_scenarios'/(name+'.yaml')
 programs=[dict(id=t['id'],trace=t,parameters={},source=str(path)) for t in yaml.safe_load(path.read_text())]
 run(name,programs)
report['source_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT/'taa_gateway/mcp_server.py',ROOT/'tests/trace_support/mcp_backend.py',*sorted((ROOT/'tests/regression_scenarios').glob('*.yaml'))]}
report['gate_pass']=all(s['counts']['discrepancies']==s['counts']['incomplete']==0 for s in report['suites'].values())
a.report.parent.mkdir(parents=True,exist_ok=True)
if a.report.exists():raise ValueError('preserve existing report; choose a new output')
a.report.write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(not report['gate_pass'])
