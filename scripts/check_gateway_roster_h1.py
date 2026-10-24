#!/usr/bin/env python3
"""H1 regression-world checks against current or pinned pre-change implementations.

No expected values are derived from a backend. New scenarios stay outside W0.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

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
import yaml
from jsonschema.exceptions import ValidationError
from tests.trace_support import reference_runner as runner, production_backend
from worlds.refunds.token_bindings import prepare
for package in (taa_gateway, reference, conventional, duty_oracle):
    assert Path(package.__file__).resolve().is_relative_to(implementation)
path = ROOT / 'tests/regression_scenarios/h1.yaml'
cases = [dict(id=t['id'], trace=t, parameters={}, source=str(path)) for t in yaml.safe_load(path.read_text())]
report = dict(implementation_root=str(implementation), baseline=a.expect_baseline,
              scenarios_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), backends={})
ok = True
for name, backend in [('reference', reference), ('production', production_backend), ('conventional', conventional)]:
    rows, errors = [], []
    for case in cases:
        prepared, bindings = prepare(case)
        checks = []
        try:
            runner._run(prepared, backend, checks, bindings)
        except (ValueError, KeyError, TypeError, AttributeError, ValidationError, production_backend.UnsupportedCapability) as error:
            if not a.expect_baseline:
                raise
            errors.append(dict(trace=case['id'], error=type(error).__name__, message=str(error)))
        rows.extend(checks)
    failed = {r['trace'] for r in rows if r['status'] != 'pass'}
    exposed = failed | {r['trace'] for r in errors}
    counts = dict(scenarios=len(cases), checks=len(rows),
        source_assertions=sum(r['origin'] == 'source' for r in rows),
        state_audits=sum(r['origin'] == 'state-audit' for r in rows),
        discrepancies=sum(r['status'] == 'discrepancy' for r in rows),
        incomplete=sum(r['status'] == 'incomplete' for r in rows), errors=len(errors))
    expected_source = sum(len(entry.get('expect', {})) for c in cases for entry in c['trace']['steps'])
    good = exposed == {c['id'] for c in cases} if a.expect_baseline else (
        not failed and not errors and counts['source_assertions'] == expected_source)
    report['backends'][name] = dict(counts=counts, gate_pass=good, errors=errors, assertions=rows)
    ok &= good
    print(json.dumps(dict(backend=name, **counts, gate_pass=good)), flush=True)
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(report, indent=2) + '\n')
raise SystemExit(not ok)
