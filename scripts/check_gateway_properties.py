#!/usr/bin/env python3
"""P1–P6 bounded checks and mutant sensitivity. Strict gate includes open gaps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.gateway_properties.checks import PropertyFailure
from tests.gateway_properties.driver import run_program
from tests.gateway_properties.generated import GENERATED, GeneratedGatewayProperties, MAX_EXAMPLES, MAX_COMMANDS, SEED
from tests.gateway_properties.mutants import FIXTURES, Installed, PROBES
from tests.gateway_properties.probes import acceptance_authority, offer_window
from tests.trace_support import reference_runner
from tests.trace_support.bundle import cases


def worker(name):
    initial = name not in ('P2', 'P4', 'P5')
    normal = run_program(PROBES[name], initial=initial, compare=False)
    row = {'property': name, 'normal': normal, 'detected': False}
    with Installed(name) as backend:
        try:
            run_program(PROBES[name], initial=initial, backend=backend, compare=False)
        except PropertyFailure as error:
            row.update(detected=error.property_id == name, failure=str(error), evidence=getattr(error, 'evidence', None))
        except Exception as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
        if name in FIXTURES:
            case = next(c for c in cases() if c['id'] == FIXTURES[name])
            checks = reference_runner.run(case, backend=backend)
            row['independent_fixture'] = {'id': case['id'], 'source_failures': [r for r in checks if r.get('origin') == 'source' and r['status'] == 'discrepancy']}
        else:
            row['independent_spec_assertion'] = 'Design v0.3 P6: fixed world/script/seed must produce byte-identical authenticated JSONL; not reference agreement'
    return row


def source_hashes():
    paths = [p for folder in ('taa_gateway', 'taa_gateway_reference', 'tests/trace_support', 'tests/gateway_properties')
             for p in (ROOT / folder).rglob('*') if p.suffix in ('.py', '.json', '.yaml')]
    paths += [Path(__file__).resolve(), ROOT / 'requirements-gateway-properties.txt']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--worker', choices=tuple(PROBES))
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker)))
        return 0
    if args.report is None:
        parser.error('--report required')
    hashes_at_start = source_hashes()
    os.environ['TAA_PROPERTY_ATTEMPT_LOG'] = str(args.report.with_suffix('.attempts.jsonl'))
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GeneratedGatewayProperties))
    mutants = []
    for name in PROBES:
        child = subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()), '--worker', name], capture_output=True, text=True)
        if child.returncode:
            mutants.append({'property': name, 'detected': False, 'worker_error': child.stderr or child.stdout})
        else:
            mutants.append(json.loads(child.stdout))
        print(name, 'mutant detected' if mutants[-1]['detected'] else 'MUTANT NOT DETECTED', flush=True)
    clarification_checks = [acceptance_authority(), offer_window()]
    pending = [r for r in clarification_checks if r['status'] != 'pass']
    comparisons = [d for row in GENERATED for d in row.get('result', {}).get('model_differences', [])]
    normal_rows = [row['result'] for row in GENERATED if 'result' in row]
    counts = {'attempted_programs': len(GENERATED), 'unique_programs': len({json.dumps([r['commands'], r['initial'], r['absent']], sort_keys=True) for r in GENERATED}),
              'world_executions': sum(r['world_executions'] for r in normal_rows),
              'property_assertions': {p: sum(r['property_assertions'][p] for r in normal_rows) for p in PROBES},
              'state_audits': sum(r['state_audits'] for r in normal_rows),
              'checks': sum(r['checks'] for r in normal_rows),
              'native_discrepant_attempts': sum(r['status'] == 'discrepancy' for r in GENERATED),
              'incomplete_attempts': sum(r['status'] == 'incomplete' for r in GENERATED),
              'model_differing_transitions': len(comparisons),
              'model_differing_programs': sum(bool(r['model_differences']) for r in normal_rows),
              'pending_scope_questions': 0,
              'clarification_probe_discrepancies': len(pending),
              'model_unrepresented_report_fields': sum(str(d.get('reference', {})).count('unrepresented_field') for d in comparisons),
              'mutants_detected': sum(r['detected'] for r in mutants)}
    errors = []
    if not result.wasSuccessful(): errors.append('generated independent property checks did not all pass')
    if any(not r['detected'] or ('independent_fixture' in r and not r['independent_fixture']['source_failures']) for r in mutants):
        errors.append('mutant sensitivity or independent assertion failed')
    if comparisons: errors.append('core/reference disagreements require review; neither output is an expected outcome')
    if pending: errors.append('Claude Q11/Q12 clarification checks failed')
    hashes_at_end = source_hashes()
    if hashes_at_start != hashes_at_end: errors.append('source changed during the campaign')
    report = {'label': 'DESCRIPTIVE: bounded development checks, not proof or H3 evidence', 'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'settings': {'hypothesis': '6.142.4', 'max_examples': MAX_EXAMPLES, 'max_commands': MAX_COMMANDS, 'seed': SEED, 'database': None, 'deadline': None},
              'source_hashes': hashes_at_start, 'source_hashes_unchanged': hashes_at_start == hashes_at_end,
              'counts': counts, 'attempts': GENERATED, 'mutants': mutants, 'clarification_checks': clarification_checks, 'pending': pending, 'gate_errors': errors}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(counts)); print(json.dumps({'gate_errors': errors}))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
