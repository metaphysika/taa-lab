#!/usr/bin/env python3
"""Reviewed source programs plus separate Sol-authored adversarial controls.

No expected outcome is supplied to the actor or generated from either backend.
The three hidden-state controls remain detection guards, not ordinary failures.
"""
import argparse,json,hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--report',type=Path,required=True)
p.add_argument('--implementation-root',type=Path,default=ROOT)
p.add_argument('--controls-only',action='store_true')
p.add_argument('--expect-baseline',action='store_true')
a=p.parse_args()
implementation=a.implementation_root.resolve()
sys.path.insert(0,str(implementation))
import taa_gateway
from taa_gateway_reference import refunds as model
sys.path.insert(0,str(ROOT))
from tests.trace_support import reference_runner as runner,production_backend,regressions
from tests.trace_support.bundle import cases as frozen
from tests.adversarial_support import controls,coverage,actor_program
assert Path(taa_gateway.__file__).is_relative_to(implementation) and Path(model.__file__).is_relative_to(implementation)
if a.expect_baseline and not a.controls_only:p.error('baseline check must use --controls-only')
manifest,missing=coverage();report={'implementation_root':str(implementation),'baseline':a.expect_baseline,'scope':'Finite scripted adversarial coverage; not adaptive attacks, universal proof or H3 evidence','coverage':manifest,'missing_cases':missing,'backends':{}}
errors=[]
if missing:errors.append('coverage manifest names unavailable programs')
for name,backend in [('reference',None),('production',production_backend)]:
    source=controls() if a.controls_only else frozen()+controls()
    # The actor sees input-only programs. The runner holds the source assertions;
    # backend propose/execute receive only arguments/observed tool identities.
    programs=[actor_program(c) for c in source+([] if a.controls_only else regressions.cases())]
    rows=[row for c in source for row in runner.run(c,backend=backend)]
    reg={'assertions':[],'scenarios':0,'negative_controls':[]} if a.controls_only else regressions.run_suite(runner,backend=backend)
    rows+=reg['assertions']
    counts={'scenarios':len(source)+reg['scenarios'],'checks':len(rows),
            'source_assertions':sum(r.get('origin','source')=='source' and 'raw_observations' not in r for r in rows),
            'state_audits':sum(r.get('origin')=='state-audit' for r in rows),'guards':len(reg['negative_controls']),
            'discrepancies':sum(r['status']=='discrepancy' for r in rows),'incomplete':sum(r['status']=='incomplete' for r in rows)}
    failures={r['trace'] for r in rows if r['status']=='discrepancy'}
    if a.expect_baseline:
        good = failures == {'A-ISSUER-FORGE'} if name=='reference' else not counts['discrepancies'] and not counts['incomplete']
        if not good:errors.append(name+': targeted before/fix sensitivity did not reproduce')
    elif counts['discrepancies'] or counts['incomplete']:errors.append(name+': acceptance failed')
    report['backends'][name]={'counts':counts,'assertions':rows,'input_program_sha256':hashlib.sha256(json.dumps(programs,sort_keys=True).encode()).hexdigest()}
    print(json.dumps({'backend':name,**counts}),flush=True)
report['source_hashes']={str(p.relative_to(implementation)):hashlib.sha256(p.read_bytes()).hexdigest() for base in ('taa_gateway','taa_gateway_reference') for p in (implementation/base).rglob('*.py')}
report['errors']=errors;a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(bool(errors))
