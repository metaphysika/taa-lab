#!/usr/bin/env python3
"""Engineering input replay and state audits; never cross-arm performance scoring.

Normative verdicts are checked by the separate unchanged acceptance gates.
Ablations/floor/static intentionally differ in policy, so this gate supplies only
original inputs and proposal-origin bindings. Unfrozen POEC tasks stay explicit.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--implementation-root', type=Path, default=ROOT)
p.add_argument('--report', type=Path, required=True)
p.add_argument('--arms', nargs='+', help='Optional named subset; default is every arm (no aggregate scores)')
p.add_argument('--suites', nargs='+', help='Optional named subset; default is every declared suite')
a=p.parse_args();implementation=a.implementation_root.resolve()
sys.path.insert(0,str(implementation))
import taa_gateway
import taa_gateway_reference
import conventional_gateway
import comparators
sys.path.insert(0,str(ROOT))
from tests.trace_support import reference_runner as runner, regressions
from tests.trace_support.bundle import cases, verify_bundle
from worlds.refunds.catalog import inputs_only
from worlds.refunds.token_bindings import prepare
from comparators.cross_arm import ARMS, backend
for package in (taa_gateway,taa_gateway_reference,conventional_gateway,comparators):
    assert Path(package.__file__).resolve().is_relative_to(implementation)
verify_bundle()
def extra(name):
    path=ROOT/'tests/regression_scenarios'/name
    return [dict(id=t['id'],trace=t,parameters={},source=str(path)) for t in yaml.safe_load(path.read_text())]
suites={'frozen':cases(),'permanent-regressions':regressions.cases(),'H1':extra('h1.yaml'),'Q14-null':extra('q14_null_allocation.yaml')}
manifest=json.loads((implementation/'comparators/contracts/v0.1/MANIFEST.json').read_text())
contract_ids={Path(k).stem for k in manifest['contracts']}
report=dict(scope='Input replay and full-state audits only. No semantic scores, no oracle metrics, no final comparison.',
            implementation_root=str(implementation),arms={})
ok=True
selected_arms=a.arms or ARMS
if any(arm not in ARMS for arm in selected_arms):p.error('unknown arm')
if a.suites and any(name not in suites for name in a.suites):p.error('unknown suite')
for arm in selected_arms:
    groups={}
    for name,inputs in suites.items():
        if a.suites and name not in a.suites:continue
        rows=[];errors=[];unavailable=[];executed=0
        for source in inputs:
            if arm=='tracegrant' and source['id'] not in contract_ids:
                unavailable.append(dict(trace=source['id'],reason='No frozen POEC contract for this task; not run'))
                continue
            if arm in ('floor','static') and source.get('parameters',{}).get('fault_at'):
                unavailable.append(dict(trace=source['id'],reason='Business host has no transaction fault adapter; real T23 fault injection unsupported'))
                continue
            program,bindings=prepare(source)
            program=inputs_only(program)
            program["parameters"]=deepcopy(source.get("parameters",{}))
            executed+=1
            try:rows.extend(runner.run(program,backend=backend(arm,source['id']),token_bindings=bindings))
            except Exception as error:errors.append(dict(trace=source['id'],type=type(error).__name__,message=str(error)))
        counts=dict(planned_scenarios=len(inputs),executed_scenarios=executed,unavailable_scenarios=len(unavailable),
            checks=len(rows),source_assertions=sum(r.get('origin')=='source' for r in rows),
            state_audits=sum(r.get('origin')=='state-audit' for r in rows),
            discrepancies=sum(r['status']=='discrepancy' for r in rows),incomplete=sum(r['status']=='incomplete' for r in rows),errors=len(errors))
        good=not counts['discrepancies'] and not counts['incomplete'] and not errors
        ok &= good;groups[name]=dict(counts=counts,gate_pass=good,unavailable=unavailable,errors=errors,assertions=rows)
        print(json.dumps(dict(arm=arm,suite=name,**counts)),flush=True)
        report['arms'][arm]=groups
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
        if not good:raise SystemExit(1)
report['gate_pass']=ok
report['coverage_complete']=all(not g['counts']['unavailable_scenarios'] for v in report['arms'].values() for g in v.values())
a.report.write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(not ok)
