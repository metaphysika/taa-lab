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
from comparators.business_faults import NOT_APPLICABLE
for package in (taa_gateway,taa_gateway_reference,conventional_gateway,comparators):
    assert Path(package.__file__).resolve().is_relative_to(implementation)
verify_bundle()
def extra(name):
    path=ROOT/'tests/regression_scenarios'/name
    return [dict(id=t['id'],trace=t,parameters={},source=str(path)) for t in yaml.safe_load(path.read_text())]
class FaultStateCapture:
    """Harness-only copies of actual states; never returned state descriptions."""
    def __init__(self, wrapped):
        self.wrapped, self.states = wrapped, []

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    def execute(self, before, actor, token, fault=None):
        prior = deepcopy(before)
        after, result = self.wrapped.execute(before, actor, token, fault)
        if fault is not None:self.states.append(dict(boundary=fault, before=prior, after=deepcopy(after)))
        return after, result


suites={'frozen':cases(),'permanent-regressions':regressions.cases(),'H1':extra('h1.yaml'),'Q14-null':extra('q14_null_allocation.yaml'),'Q15':extra('q15.yaml'),'Q16':extra('q16.yaml'),'Q14':extra('q14.yaml'),'Q14-overlap':extra('q14_overlap.yaml'),'comparison-review':extra('comparison_review_v02.yaml'),'Q17':extra('q17.yaml'),'Q17.1':extra('q17_1.yaml')}
manifest=json.loads((implementation/'comparators/contracts/v0.1/MANIFEST.json').read_text())
contract_ids={Path(k).stem for k in manifest['contracts']}
report=dict(scope='Input replay and full-state audits only. No semantic scores, no oracle metrics, no final comparison.',
            implementation_root=str(implementation),tracegrant_limit='Only the ten predeclared development programs have frozen POEC contracts. No new contracts are authored for these replay suites; semantic cross-arm scoring remains limited to those ten development programs.',arms={})
ok=True
selected_arms=a.arms or ARMS
if any(arm not in ARMS for arm in selected_arms):p.error('unknown arm')
if a.suites and any(name not in suites for name in a.suites):p.error('unknown suite')
for arm in selected_arms:
    groups={}
    for name,inputs in suites.items():
        if a.suites and name not in a.suites:continue
        rows=[];errors=[];unavailable=[];not_applicable=[];nonatomic=[];unexpected=[];fault_states=[];executed=0
        for source in inputs:
            if arm=='tracegrant' and source['id'] not in contract_ids:
                unavailable.append(dict(trace=source['id'],reason='No frozen POEC contract for this task; not run'))
                continue
            points=set()
            for entry in source['trace']['steps']:
                point=entry.get('execute',{}).get('inject_fault')
                if point is None:continue
                if point.startswith('${'):point=source['parameters'][point[2:-1]]
                points.add(point)
            if len(points)>1:raise ValueError('fault applicability must be reported per action for a multi-fault source')
            fault=next(iter(points)) if points else None
            if arm in ('floor','static') and fault in NOT_APPLICABLE:
                not_applicable.append(dict(trace=source['id'],boundary=fault,classification='not applicable by design',reason=NOT_APPLICABLE[fault]))
                continue
            program,bindings=prepare(source)
            program=inputs_only(program)
            program["parameters"]=deepcopy(source.get("parameters",{}))
            executed+=1
            try:
                host=backend(arm,source['id'])
                captured=FaultStateCapture(host) if arm in ('floor','static') and fault is not None else None
                checks=runner.run(program,backend=captured or host,token_bindings=bindings)
                if captured:
                    fault_states.append(dict(trace=source['id'],states=captured.states))
                rows.extend(checks)
                for check in checks:
                    if check['status']!='discrepancy':continue
                    if (arm in ('floor','static') and fault in ('during_effect_commit','during_receipt_write') and
                        check['origin']=='state-audit' and check['assertion'].endswith('.record_effects_match_receipts') and
                        isinstance(check['expectation'],list) and check['expectation'] and check['observed']==[]):
                        nonatomic.append(check)  # Retain the failing audit verbatim; never waive it.
                    else:unexpected.append(check)
            except Exception as error:errors.append(dict(trace=source['id'],type=type(error).__name__,message=str(error)))
        counts=dict(planned_scenarios=len(inputs),executed_scenarios=executed,unavailable_scenarios=len(unavailable),not_applicable_scenarios=len(not_applicable),
            checks=len(rows),source_assertions=sum(r.get('origin')=='source' for r in rows),
            state_audits=sum(r.get('origin')=='state-audit' for r in rows),
            discrepancies=sum(r['status']=='discrepancy' for r in rows),incomplete=sum(r['status']=='incomplete' for r in rows),errors=len(errors),observed_nonatomic_fault_audits=len(nonatomic),unexpected_discrepancies=len(unexpected))
        good=not unexpected and not counts['incomplete'] and not errors
        ok &= good;groups[name]=dict(counts=counts,gate_pass=good,unavailable=unavailable,not_applicable_by_design=not_applicable,observed_nonatomic_faults=nonatomic,actual_fault_states=fault_states,unexpected_discrepancies=unexpected,errors=errors,assertions=rows)
        print(json.dumps(dict(arm=arm,suite=name,**counts)),flush=True)
        report['arms'][arm]=groups
        a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
        if not good:raise SystemExit(1)
report['gate_pass']=ok
report['coverage_complete']=all(not g['counts']['unavailable_scenarios'] for v in report['arms'].values() for g in v.values())
a.report.write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(not ok)
