#!/usr/bin/env python3
"""Q17 source assertions through the unchanged common runner; no model calls."""
import argparse,hashlib,json,sys,subprocess
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--implementation-root',type=Path,default=ROOT);p.add_argument('--report',type=Path,required=True);p.add_argument('--expect-baseline',action='store_true');a=p.parse_args()
sys.path.insert(0,str(a.implementation_root.resolve()))
from tests.trace_support import reference_runner as runner,production_backend as core
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as conventional
from worlds.refunds.token_bindings import prepare
path=ROOT/'tests/regression_scenarios/q17.yaml';cases=[dict(id=t['id'],trace=t,parameters={},source=str(p)) for p in (path,ROOT/'tests/regression_scenarios/q17_1.yaml') for t in yaml.safe_load(p.read_text())]
report=dict(scope='Q17 ruling-derived expectations; no generated expected outcomes',implementation_root=str(a.implementation_root.resolve()),fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (path,path.with_name('q17_1.yaml'))}, implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.implementation_root,text=True).strip(), source_hashes={str(f.relative_to(a.implementation_root.resolve())):hashlib.sha256(f.read_bytes()).hexdigest() for base in ('taa_gateway','taa_gateway_reference','conventional_gateway','tests/trace_support') for f in sorted((a.implementation_root.resolve()/base).glob('*.py'))},backends={})
for name,b in [('core',core),('reference',reference),('conventional',conventional)]:
 rows=[];by_case={}
 for c in cases:
  program,bindings=prepare(c);checks=runner.run(program,backend=b,token_bindings=bindings);rows+=checks
  by_case[c['id']]=dict(discrepancies=sum(r['status']=='discrepancy' for r in checks),incomplete=sum(r['status']=='incomplete' for r in checks),checks=checks)
 report['backends'][name]=dict(cases=by_case,counts=dict(scenarios=len(cases),source=sum(r.get('origin')=='source' for r in rows),audits=sum(r.get('origin')=='state-audit' for r in rows),discrepancies=sum(r['status']=='discrepancy' for r in rows),incomplete=sum(r['status']=='incomplete' for r in rows)))
a.report.parent.mkdir(parents=True,exist_ok=True)
if a.report.exists():raise ValueError('preserve existing report')
a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v['counts'] for k,v in report['backends'].items()},indent=2))
if a.expect_baseline:
 targeted=['R-Q17-leaf-template','R-Q17-parent-template','R-Q17-free-prose-limited']
 assert all(report['backends']['core']['cases'][k]['discrepancies'] for k in targeted)
else:assert all(v['counts']['discrepancies']==v['counts']['incomplete']==0 for v in report['backends'].values())
