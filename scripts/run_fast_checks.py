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
    'tests.test_ft1_prefill', 'tests.test_ft1_memory', 'tests.test_ft1_evaluate', 'tests.test_ft1_throughput',
    'tests.test_ft1r_layout', 'tests.test_ft1r_data_job', 'tests.test_ft1_pressure_split', 'tests.test_ft1_wiring',
    'tests.test_seed2_v02482',
    'tests.test_track_b_corruption_data', 'tests.test_track_b_batteries',
    'tests.test_track_b_repair_domain', 'tests.test_track_b_verdict',
    'tests.test_track_b_training', 'tests.test_track_b_repair_data',
    'tests.test_track_b_analysis', 'tests.test_track_b_launch',
    'tests.test_ci_tiers', 'tests.test_v020', 'tests.test_v0206',
    'tests.test_obligations', 'tests.test_premise_repairs',
    'tests.test_gateway_foundation', 'tests.test_gateway_executor',
    'tests.test_assertion_binding', 'tests.test_measurement_v02456', 'tests.test_step4_cases',
    'tests.test_experiment_b', 'tests.test_step3_v02444', 'tests.test_step4_harness', 'tests.test_step4_modal_backend', 'tests.test_step4_remainder', 'tests.test_step4_crossing', 'tests.test_step4_crossing_analysis', 'tests.test_k1', 'tests.test_k2b', 'tests.test_k2_ft0', 'tests.test_k2_ft0b', 'tests.test_k2_kaggle', 'tests.test_k2_kaggle_launch', 'tests.test_l1', 'tests.test_l2',
)


SEALED_ADJACENT = ('tests.test_ft1_blind',)

def exploratory_syntax():
    for path in sorted((ROOT / 'exploratory' / 'scripts').rglob('*.py')):
        compile(path.read_bytes(), str(path), 'exec')
    for path in sorted((ROOT / 'exploratory' / 'scenarios').rglob('*.json')):
        json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--agent-safe', action='store_true', help='Skip sealed-adjacent tests')
    args = parser.parse_args()
    if (ROOT / 'keys.env').exists():
        parser.error('Use a checkout without keys.env for offline checks')
    started = time.perf_counter()
    if args.agent_safe:
        from agent_safe_imports import install
        install()
    exploratory_syntax()
    commands = [[sys.executable, '-m', 'unittest', *(SMOKE if args.smoke else FAST + (() if args.agent_safe else SEALED_ADJACENT)), '-v']]
    if not args.smoke:
        commands.append([sys.executable, 'run.py', '--scenario', 'all'])
    for command in commands:
        if args.agent_safe:
            command = [sys.executable, str(ROOT/'scripts'/'agent_safe_imports.py'), *command[1:]]
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode
    print(json.dumps({'set': 'smoke' if args.smoke else 'fast',
                      'elapsed_seconds': round(time.perf_counter() - started, 3)}), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
