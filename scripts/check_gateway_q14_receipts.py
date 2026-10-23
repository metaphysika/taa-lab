#!/usr/bin/env python3
"""Q14 receipt-presence control on actual business records; original state stays intact."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import yaml

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--implementation-root',type=Path,default=ROOT)
p.add_argument('--expect-baseline',action='store_true')
p.add_argument('--report',type=Path,required=True)
a=p.parse_args();implementation=a.implementation_root.resolve();sys.path.insert(0,str(implementation))
import comparators
from comparators.business import Backend
from comparators.duty_oracle import Oracle
from tests.trace_support.bundle import world
assert Path(comparators.__file__).resolve().is_relative_to(implementation)
setup=yaml.safe_load((ROOT/'tests/regression_scenarios/q14.yaml').read_text())[0]['setup']
results=[]
for arm in ('floor','static'):
    backend=Backend(arm);state=backend.start(world(),setup)
    for args in [dict(claim='CL7',to='K2',template='refund_issued',amount=250,cites='REF1'),
                 dict(claim='CL7',to='K2',template='refund_denied',amount=150,basis='DEL2')]:
        state,proposal=backend.propose(state,'A','message_party',args)
        state,result=backend.execute(state,'A',proposal['execution_intent'])
        assert result['execute_result']=='committed'
    assert len(state['receipts'])==len(state['notices'])==2
    original=deepcopy(state)
    probe=deepcopy(state);probe['receipts']=deepcopy(state['receipts'][:-1])
    oracle=Oracle(probe);oracle.clock(probe['step']);oracle.reconcile(probe)
    assert state==original
    observed=oracle.board()['D_resolve(CL7)']['resolution']
    good=(observed=='discharged') if a.expect_baseline else observed=='unresolved'
    results.append(dict(arm=arm,expected_correct='unresolved',observed=observed,
        gate_pass=good,original_state=state,controlled_receipt_omission=probe))
report=dict(scope='Sol-authored from Claude Q14; original state retained. Controlled evidence omission, not a model run or score.',
    implementation_root=str(implementation),baseline=a.expect_baseline,results=results,
    gate_pass=all(r['gate_pass'] for r in results))
a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({r['arm']:dict(expected_correct=r['expected_correct'],observed=r['observed'],gate_pass=r['gate_pass']) for r in results}))
raise SystemExit(not report['gate_pass'])
