#!/usr/bin/env python3
"""Permanent allocation representation controls, using actual arm records.

Run on a pinned implementation to expose the pre-fix defect. No outcome keys,
controller changes or arm-record normalization are permitted by this control.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--implementation-root', type=Path, default=ROOT)
p.add_argument('--expect-baseline', action='store_true')
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
implementation = a.implementation_root.resolve()
sys.path.insert(0, str(implementation))
import taa_gateway
from taa_gateway_reference import refunds as reference
from conventional_gateway import backend as conventional
from comparators import duty_oracle
sys.path.insert(0, str(ROOT))
# Keep implementation packages pinned but load the current authored controls.
spec = importlib.util.spec_from_file_location('null_allocation_controls', ROOT/'tests/test_gateway_null_allocation.py')
module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for package in (taa_gateway, reference, conventional, duty_oracle):
    assert Path(package.__file__).resolve().is_relative_to(implementation)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
required = {'test_original_committed_control_passes_all_three_without_rewriting_records',
            'test_null_internal_allocation_is_unallocated',
            'test_generic_reference_null_allocation_matches_absence_but_other_duty_blocks'}
failures = sorted({getattr(case, 'test_case', case)._testMethodName for case, _ in result.failures})
known = set(failures)
passed = required <= known and not result.errors if a.expect_baseline else result.wasSuccessful()
report = dict(implementation_root=str(implementation), baseline=a.expect_baseline, gate_pass=passed,
    tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
    failing_methods=failures, output=stream.getvalue(),
    control_sha256=hashlib.sha256((ROOT/'tests/test_gateway_null_allocation.py').read_bytes()).hexdigest(),
    source_sha256={str(f.relative_to(implementation)):hashlib.sha256(f.read_bytes()).hexdigest()
        for folder in ('taa_gateway_reference','comparators') for f in sorted((implementation/folder).glob('*.py'))})
# Independent trace vocabulary and the same full-state audits, permanently.
import yaml
from tests.trace_support import reference_runner as runner, production_backend
from worlds.refunds.token_bindings import prepare
trace_path = ROOT/'tests/regression_scenarios/q14_null_allocation.yaml'
trace_cases = [dict(id=t['id'],trace=t,parameters={},source=str(trace_path)) for t in yaml.safe_load(trace_path.read_text())]
report['trace_suites'] = {}
for name, backend in [('reference',reference),('production',production_backend),('conventional',conventional)]:
    rows = []
    for case in trace_cases:
        prepared, bindings = prepare(case)
        runner._run(prepared,backend,rows,bindings)
    counts = dict(scenarios=len(trace_cases),source_assertions=sum(r['origin']=='source' for r in rows),
        state_audits=sum(r['origin']=='state-audit' for r in rows),checks=len(rows),
        discrepancies=sum(r['status']=='discrepancy' for r in rows),incomplete=sum(r['status']=='incomplete' for r in rows))
    good = (any(r['status']=='discrepancy' and r['trace']=='R-Q14-allocation-null' for r in rows)
            if a.expect_baseline and name=='reference' else not any(r['status']!='pass' for r in rows))
    report['trace_suites'][name]=dict(counts=counts,gate_pass=good,assertions=rows)
    passed &= good
report['gate_pass']=passed
a.report.parent.mkdir(parents=True,exist_ok=True)
a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('output','source_sha256','trace_suites')}))
if not passed:print(stream.getvalue())
raise SystemExit(not passed)
