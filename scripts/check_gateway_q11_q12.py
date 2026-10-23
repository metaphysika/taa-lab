#!/usr/bin/env python3
"""Q11/Q12 sensitivity against pinned pre-change implementation packages.

Use today's common runner/observer and hand-authored scenarios with either
checkout's implementation. No expectations are computed from either backend.
"""
import argparse
import hashlib
import importlib
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
from taa_gateway_reference import refunds as model
# Package paths remain pinned to implementation; tests and observations are current.
sys.path.insert(0, str(ROOT))
from tests.trace_support import reference_runner as runner, production_backend, regressions
from worlds.refunds.token_bindings import prepare
for package in (taa_gateway, model):
    assert Path(package.__file__).resolve().is_relative_to(implementation)
inputs = [c for c in regressions.cases() if c['id'].startswith(('R-Q11-', 'R-Q12-'))]
required = {
    'reference': {'R-Q11-no-standing', 'R-Q11-out-of-scope', 'R-Q12-fallback-accept',
                  'R-Q12-fallback-lapse', 'R-Q12-parallel-L', 'R-Q12-parallel-F',
                  'R-Q12-parallel-lapse', 'R-Q12-parallel-last-window'},
    'production': {'R-Q11-tool-message', 'R-Q11-no-standing', 'R-Q12-parallel-L',
                   'R-Q12-parallel-F', 'R-Q12-parallel-lapse', 'R-Q12-parallel-last-window'},
}
report = {'implementation_root': str(implementation), 'baseline': a.expect_baseline,
          'scenario_sha256': hashlib.sha256((regressions.ROOT / 'q11_q12.yaml').read_bytes()).hexdigest(),
          'source_hashes': {str(f.relative_to(implementation)): hashlib.sha256(f.read_bytes()).hexdigest()
                            for base in ('taa_gateway', 'taa_gateway_reference')
                            for f in sorted((implementation / base).rglob('*.py'))}, 'backends': {}}
ok = True
for name, backend in [('reference', None), ('production', production_backend)]:
    rows, errors = [], []
    for case in inputs:
        checks = []
        prepared, token_bindings = prepare(case)
        try:
            runner._run(prepared, backend or runner.model, checks, token_bindings)
        except (ValueError, KeyError, TypeError) as error:
            if not a.expect_baseline:
                raise
            errors.append({'trace': case['id'], 'error': type(error).__name__, 'message': str(error)})
        rows.extend(checks)
    failures = {row['trace'] for row in rows if row['status'] == 'discrepancy'}
    incomplete = sum(row['status'] == 'incomplete' for row in rows)
    counts = {'scenarios': len(inputs), 'assertions': len(rows),
              'source_assertions': sum(row['origin'] == 'source' for row in rows),
              'state_audits': sum(row['origin'] == 'state-audit' for row in rows),
              'discrepancies': sum(row['status'] == 'discrepancy' for row in rows), 'incomplete': incomplete}
    good = (required[name].issubset(failures | {e['trace'] for e in errors}) if a.expect_baseline else not failures and not incomplete)
    report['backends'][name] = dict(counts=counts, failures=sorted(failures), errors=errors, assertions=rows, gate_pass=good)
    ok &= good
    print(json.dumps({'backend': name, **counts, 'failures': sorted(failures), 'errors': errors, 'gate_pass': good}), flush=True)
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(report, indent=2) + '\n')
raise SystemExit(not ok)
