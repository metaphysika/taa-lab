"""Run new regression guards against any checkout, including pre-fix main."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import hashlib
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--implementation-root', type=Path, default=ROOT)
p.add_argument('--report', type=Path, required=True)
p.add_argument('--expect-baseline', action='store_true')
a = p.parse_args()
sys.path.insert(0, str(a.implementation_root.resolve()))
from tests.trace_support import reference_runner as runner
spec = importlib.util.spec_from_file_location('spot_regressions', ROOT / 'tests/trace_support/regressions.py')
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)
r = suite.run_suite(runner, include_clarifications=not a.expect_baseline)
r['implementation_root'] = str(a.implementation_root.resolve())
r['implementation_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.implementation_root, text=True).strip()
r['implementation_source_hashes'] = {
    name: hashlib.sha256((a.implementation_root / name).read_bytes()).hexdigest()
          if (a.implementation_root / name).exists() else None
    for name in ('taa_gateway_reference/refunds.py', 'tests/trace_support/reference_runner.py',
                 'tests/trace_support/state_observations.py')}
r['scenario_sha256'] = hashlib.sha256((ROOT / 'tests/regression_scenarios/astra_spot_check.yaml').read_bytes()).hexdigest()
assert Path(runner.__file__).resolve().is_relative_to(a.implementation_root.resolve())
rows = r['assertions']
r['counts'] = {'scenarios': r['scenarios'], 'assertions': len(rows),
               'source_assertions': sum(x.get('origin', 'source') == 'source' for x in rows if 'raw_observations' not in x),
               'state_audits': sum(x.get('origin') == 'state-audit' for x in rows),
               'detection_guards': len(r['negative_controls']),
               'discrepancies': sum(x['status'] == 'discrepancy' for x in rows),
               'incomplete': sum(x['status'] == 'incomplete' for x in rows)}
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(r, indent=2) + '\n')
print(json.dumps(r['counts']))
for x in rows:
    if x['status'] != 'pass':
        print(json.dumps({k: v for k,v in x.items() if k != 'raw_observations'}))
failed = r['counts']['discrepancies'] + r['counts']['incomplete']
if a.expect_baseline:
    required = {'R-B2', 'R-B3', 'R-B4-split', 'R-cache', 'R-B1-extra-refund', 'R-B1-refused-write', 'R-B1-rewritten-version'}
    failures = {x['trace'] for x in rows if x['status'] != 'pass'}
    raise SystemExit(failures != required or r['counts']['incomplete'] != 0)
raise SystemExit(bool(failed))
