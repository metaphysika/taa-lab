#!/usr/bin/env python3
"""Keep all rule-derived before/fixed observations, with exact source hashes."""
import argparse,hashlib,importlib.util,json,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--implementation-root',type=Path,default=ROOT)
p.add_argument('--report',type=Path,required=True)
p.add_argument('--expect-baseline',action='store_true')
a=p.parse_args();sys.path.insert(0,str(a.implementation_root.resolve()))
from tests.trace_support import production_backend,mcp_backend
from taa_gateway_reference import refunds
from conventional_gateway import backend
spec=importlib.util.spec_from_file_location('assertion_binding_inputs',ROOT/'tests/trace_support/assertion_binding.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
socket.socket=lambda *args,**kwargs:(_ for _ in ()).throw(RuntimeError('offline sockets denied'))
rows=[]
for case in support.cases():
    for implementation in support.IMPLEMENTATIONS:
        observed=support.observe(case,implementation)
        failures=[]
        if observed['disposition']!=case['expected']:failures.append('disposition')
        if observed['pr1']!=case['expected_pr1']:failures.append('PR1')
        rows.append(dict(case=case['id'],implementation=implementation,expected=case['expected'],expected_pr1=case['expected_pr1'],observed=observed,failures=failures))
report=dict(claim='[Descriptive] Observations against previously authored synthetic rules, not an Experiment A blind key.',
    implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.implementation_root,text=True).strip(),
    source_sha256={str(f.relative_to(a.implementation_root.resolve())):hashlib.sha256(f.read_bytes()).hexdigest() for d in ('taa_gateway','taa_gateway_reference','conventional_gateway','comparators') for f in sorted((a.implementation_root.resolve()/d).glob('*.py'))},
    fixture_sha256=hashlib.sha256(support.FIXTURE.read_bytes()).hexdigest(),cases=len(support.cases()),checks=len(rows),
    discrepancies=sum(bool(r['failures']) for r in rows),rows=rows)
a.report.parent.mkdir(parents=True,exist_ok=True)
with a.report.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ('cases','checks','discrepancies','fixture_sha256')}))
if a.expect_baseline:
    for case in support.cases():
        for target in case['targets']:
            assert any(r['case']==case['id'] and r['implementation']==target and r['failures'] for r in rows),(case['id'],target)
else:
    assert report['discrepancies']==0,'assertion binding disagreement'
