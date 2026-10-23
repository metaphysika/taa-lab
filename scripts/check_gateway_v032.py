#!/usr/bin/env python3
"""Approved v0.3.2 regressions, with pinned-source sensitivity and real audits."""
import argparse
from pathlib import Path
import sys,json,yaml,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--implementation-root',type=Path,default=ROOT)
p.add_argument('--expect-baseline',action='store_true')
p.add_argument('--suite',choices=['q14','q15','q16'],default='q15')
p.add_argument('--report',type=Path,required=True)
a=p.parse_args();implementation=a.implementation_root.resolve();sys.path.insert(0,str(implementation))
import taa_gateway,taa_gateway_reference,conventional_gateway
sys.path.insert(0,str(ROOT))
from tests.trace_support import reference_runner as runner,production_backend as production
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as conventional
from worlds.refunds.token_bindings import prepare
for package in (taa_gateway,taa_gateway_reference,conventional_gateway):
 assert Path(package.__file__).resolve().is_relative_to(implementation)
path=ROOT/'tests/regression_scenarios'/(a.suite+'.yaml')
cases=[dict(id=t['id'],trace=t,parameters={},source=str(path)) for t in yaml.safe_load(path.read_text())]
report=dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),suite=a.suite,implementation_root=str(implementation),baseline=a.expect_baseline,backends={});ok=True
for name,b in [('reference',reference),('production',production),('conventional',conventional)]:
 rows=[];errors=[];failed=[]
 for case in cases:
  program,bindings=prepare(case)
  try:
   checks=runner.run(program,backend=b,token_bindings=bindings);rows.extend(checks)
   if any(r['status']!='pass' for r in checks):failed.append(case['id'])
  except Exception as e:errors.append(dict(trace=case['id'],type=type(e).__name__,message=str(e)));failed.append(case['id'])
 counts=dict(scenarios=len(cases),source_assertions=sum(r['origin']=='source' for r in rows),state_audits=sum(r['origin']=='state-audit' for r in rows),discrepancies=sum(r['status']=='discrepancy' for r in rows),incomplete=sum(r['status']=='incomplete' for r in rows),errors=len(errors))
 required={c['id'] for c in cases if not c['trace'].get('baseline_control') and name in c['trace'].get('baseline_sensitive_backends',['reference','production','conventional'])}
 controls={c['id'] for c in cases if c['trace'].get('baseline_control')}
 good=(required<=set(failed) and not controls.intersection(failed) and not errors) if a.expect_baseline else not failed
 report['backends'][name]=dict(counts=counts,failed_scenarios=failed,errors=errors,checks=rows,gate_pass=good);ok &= good
 print(json.dumps(dict(backend=name,**counts,failed_scenarios=failed,gate_pass=good)),flush=True)
a.report.parent.mkdir(parents=True,exist_ok=True);report['gate_pass']=ok;a.report.write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(not ok)
