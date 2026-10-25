#!/usr/bin/env python3
"""Retain every ruling-authored Q18 case, including pre-change failures."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--implementation-root', type=Path, default=ROOT)
p.add_argument('--report', type=Path, required=True)
p.add_argument('--expect-baseline', action='store_true')
a = p.parse_args()
sys.path.insert(0, str(a.implementation_root.resolve()))
# Bind runtime modules to the chosen implementation before loading new fixtures.
from tests.trace_support import production_backend, mcp_backend
from taa_gateway_reference import refunds
from conventional_gateway import backend
import importlib.util
spec = importlib.util.spec_from_file_location('q18_input_support', ROOT/'tests/trace_support/q18.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('offline Q18 checks'))
rows=[]
for case in support.cases():
    for implementation in ('reference', 'core', 'mcp', 'conventional'):
        result=support.observe(case, implementation)
        rows.append(dict(case=case['id'], implementation=implementation, expected=case['expected'],
                         observed=result.get('disposition'), passed=result.get('disposition')==case['expected'],result=result))
source_hashes={str(f.relative_to(a.implementation_root.resolve())):hashlib.sha256(f.read_bytes()).hexdigest() for d in ('taa_gateway','taa_gateway_reference','conventional_gateway') for f in sorted((a.implementation_root.resolve()/d).glob('*.py'))}
report=dict(implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.implementation_root,text=True).strip(),source_sha256=source_hashes,additional_fixture_sha256=hashlib.sha256(support.FIXTURES.with_name('q18_additional.json').read_bytes()).hexdigest(),claim='[Descriptive] Offline observations against previously authored rule expectations.',
            fixture_sha256=hashlib.sha256(support.FIXTURES.read_bytes()).hexdigest(),
            implementation_root=str(a.implementation_root),cases=len(support.cases()),checks=len(rows),
            discrepancies=sum(not row['passed'] for row in rows),rows=rows)
a.report.parent.mkdir(parents=True,exist_ok=True)
with a.report.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps({key:report[key] for key in ('cases','checks','discrepancies','fixture_sha256')}))
if a.expect_baseline:
    for case in support.cases():
        for target in case.get('targets',[]):
            assert any(row['case']==case['id'] and row['implementation']==target and not row['passed'] for row in rows),(case['id'],target)
else:
    assert report['discrepancies']==0
