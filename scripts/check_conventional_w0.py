#!/usr/bin/env python3
"""Run unchanged authoritative sources against the independent SQL arm."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from conventional_gateway import backend
from tests.trace_support import reference_runner as runner
from tests.trace_support.bundle import cases, verify_bundle
from tests.trace_support.regressions import run_suite, cases as regression_cases
from tests.adversarial_support import controls


def source_blocks(case):
    return sum(len(e.get('expect', {})) for e in case['trace']['steps']) + len(case['trace'].get('final', {}))


def coverage_gaps(observed):
    guards = json.loads((ROOT/'tests/regression_scenarios/mutations.json').read_text())
    regression = regression_cases()
    expected = {'frozen': (len(cases()), sum(map(source_blocks, cases()))),
                'adversarial': (len(controls()), sum(map(source_blocks, controls()))),
                'regression': (len(regression), sum(source_blocks(c) for c in regression if c['id'] not in guards))}
    gaps = []
    for name, (scenarios, blocks) in expected.items():
        result = observed[name]
        count = sum(a.get('origin') == 'source' for a in result['assertions'])
        if result['scenarios'] != scenarios or count != blocks:
            gaps.append({'suite': name, 'expected': {'scenarios': scenarios, 'source': blocks},
                         'observed': {'scenarios': result['scenarios'], 'source': count}})
        unknown = sorted({a['status'] for a in result['assertions']} - {'pass', 'discrepancy', 'incomplete'})
        if unknown:
            gaps.append({'suite': name, 'unknown_statuses': unknown})
    negative = observed['regression'].get('negative_controls', [])
    if {g['trace'] for g in negative} != set(guards) or len(negative) != len(guards):
        gaps.append({'suite': 'regression', 'missing_or_duplicate_negative_controls': True})
    sources = {c['id']: c for c in regression}
    for control in negative:
        expected_count = source_blocks(sources[control['trace']])
        actual_count = sum(a.get('origin') == 'source' for a in control['raw_observations'])
        if actual_count != expected_count:
            gaps.append({'suite': 'regression', 'guard': control['trace'], 'source_expected': expected_count, 'source_observed': actual_count})
    return gaps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    options = parser.parse_args()
    if options.report.exists():
        raise FileExistsError('keep prior outcomes; choose a new report path')
    verify_bundle()
    files = (list((ROOT/'conventional_gateway').glob('*.py')) + list((ROOT/'tests/trace_support').glob('*.py')) +
             list((ROOT/'tests/regression_scenarios').glob('*.yaml')) + list((ROOT/'tests/adversarial_scenarios').glob('*.yaml')) +
             [Path(__file__).resolve(), ROOT/'tests/regression_scenarios/mutations.json', ROOT/'tests/adversarial_support.py',
              ROOT/'docs/process/TAA_CONVENTIONAL_W0_MAPPING_v0.md'])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    observed = {}
    for label, sources in (('frozen', cases()), ('adversarial', controls())):
        rows = []
        for source in sources:
            try:
                rows.extend(runner.run(source, backend=backend))
            except Exception as error:
                rows.append({'trace': source['id'], 'assertion': 'unhandled_execution', 'status': 'incomplete',
                             'observed': type(error).__name__ + ': ' + str(error), 'origin': 'execution'})
        observed[label] = {'scenarios': len(sources), 'assertions': rows}
    try:
        observed['regression'] = run_suite(runner, backend=backend)
    except Exception as error:
        observed['regression'] = {'scenarios': 32, 'assertions': [{'trace': 'regression_harness', 'assertion': 'unhandled_execution',
            'status': 'incomplete', 'observed': type(error).__name__ + ': ' + str(error), 'origin': 'execution'}]}
    for result in observed.values():
        rows = result['assertions']
        counts = Counter(row['status'] for row in rows)
        result['counts'] = {name: counts[name] for name in ('pass', 'discrepancy', 'incomplete')}
        result['source_assertions'] = sum(row.get('origin') == 'source' for row in rows)
        result['state_audits'] = sum(row.get('origin') == 'state-audit' for row in rows)
        result['negative_controls_detected'] = sum(row['status'] == 'pass' for row in result.get('negative_controls', []))
    gaps = coverage_gaps(observed)
    truncated = deepcopy(observed)
    source_index = next(i for i, row in enumerate(truncated['frozen']['assertions']) if row.get('origin') == 'source')
    dropped = truncated['frozen']['assertions'].pop(source_index)
    control_gaps = coverage_gaps(truncated)
    coverage_control = {'label': 'omit one checked source block from the observed report; no fixture edited',
                        'omitted': dropped['trace'] + '.' + dropped['assertion'], 'detected': bool(control_gaps),
                        'gaps': control_gaps}
    verify_bundle()
    unchanged = all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha for name, sha in hashes.items())
    gate = unchanged and not gaps and coverage_control['detected'] and all(not r['counts']['discrepancy'] and not r['counts']['incomplete'] for r in observed.values())
    report = {'schema': 'conventional-W0-evidence/0.1', 'hashes': hashes, 'inputs_unchanged': unchanged,
              'results': observed, 'coverage_gaps': gaps, 'coverage_negative_control': coverage_control, 'gate_pass': gate}
    options.report.parent.mkdir(parents=True, exist_ok=True)
    options.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'gate_pass': gate, 'inputs_unchanged': unchanged, **{k: {n:r[n] for n in ('scenarios','counts','source_assertions','state_audits','negative_controls_detected')} for k,r in observed.items()}}, indent=2))
    return 0 if gate else 1


if __name__ == '__main__':
    sys.exit(main())
