"""Explicit offline fast/smoke sets; never load credentials or invoke model clients."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SMOKE = (
    'tests.test_ci_tiers',
    'tests.test_gateway_foundation.FoundationTests.test_assertions_cannot_become_evidence',
    'tests.test_gateway_foundation.FoundationTests.test_forged_session_and_wrong_source_rejected',
    'tests.test_experiment_b.FixtureTests.test_exact_schedule',
    'tests.test_step3_v02444.FixturesTests.test_schedule_two_models_three_repeats',
)
FAST = (
    'tests.test_ci_tiers', 'tests.test_v020', 'tests.test_v0206',
    'tests.test_obligations', 'tests.test_premise_repairs',
    'tests.test_gateway_foundation', 'tests.test_gateway_executor',
    'tests.test_assertion_binding',
    'tests.test_experiment_b', 'tests.test_step3_v02444',
)


def exploratory_syntax():
    for path in sorted((ROOT / 'exploratory' / 'scripts').rglob('*.py')):
        compile(path.read_bytes(), str(path), 'exec')
    for path in sorted((ROOT / 'exploratory' / 'scenarios').rglob('*.json')):
        json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if (ROOT / 'keys.env').exists():
        parser.error('Use a checkout without keys.env for offline checks')
    started = time.perf_counter()
    exploratory_syntax()
    commands = [[sys.executable, '-m', 'unittest', *(SMOKE if args.smoke else FAST), '-v']]
    if not args.smoke:
        commands.append([sys.executable, 'run.py', '--scenario', 'all'])
    for command in commands:
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode
    print(json.dumps({'set': 'smoke' if args.smoke else 'fast',
                      'elapsed_seconds': round(time.perf_counter() - started, 3)}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
