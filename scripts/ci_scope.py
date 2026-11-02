"""Conservative PR selection; non-PR events always select the full offline suite."""
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess

GROUPS = ('gateway', 'study_d', 'gemma')
DOC_IGNORES = ('AGENTS.md', 'CLAUDE.md', 'docs/REPRODUCE.md',
               'docs/paper-map.md', 'docs/drafts/**')
SHARED = ('taa/**', 'agents/**', 'world/**', 'worlds/**', 'scenarios/**',
          'taa_gateway/**', 'taa_gateway_reference/**', 'conventional_gateway/**',
          'comparators/**', 'formation/**', 'evaluation/**', 'run.py',
          'requirements*', '*scorer*', '**/*scorer*', '*scoring*', '**/*scoring*',
          'gateway/**', 'scorer/**', 'scoring/**', '.github/workflows/**',
          'scripts/ci_scope.py',
          'scripts/run_fast_checks.py', 'tests/test_ci_tiers.py')
GATEWAY = ('scripts/check_gateway*', 'scripts/run_gateway*',
           'scripts/check_conventional*', 'scripts/run_tracegrant*',
           'tests/test_gateway*', 'tests/test_conventional*',
           'tests/test_tracegrant*', 'tests/test_cross_arm*',
           'tests/test_context_canonicalization.py', 'tests/test_commit_oracle.py',
           'tests/test_comparison_review_v02.py', 'tests/test_business_faults.py',
           'tests/expected_traces/**', 'tests/regression_scenarios/**',
           'tests/adversarial_scenarios/**', 'tests/gateway_properties/**',
           'tests/trace_support/**', 'live_demo/frozen/**', 'replay/**')
STUDY_D = ('scripts/study_d*', 'scripts/check_study_d*',
           'scripts/formation_study_d*', 'tests/test_study_d*',
           'tests/test_modal_serialization*', 'studies/**', 'results/**')
FAST_ONLY = ('experiment_a/**', 'experiment_b/**', 'step3_v02444/**',
             'tests/test_experiment_a*', 'tests/test_experiment_b.py',
             'tests/test_step3_v02444.py', 'live_demo/**',
             'scripts/live_demo*', 'scripts/check_live_demo*',
             'tests/test_live_demo*')


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def select_checks(paths):
    selected = set()
    for path in paths:
        if matches(path, DOC_IGNORES) or path.startswith('exploratory/'):
            continue
        if matches(path, SHARED):
            selected.update(GROUPS)
        elif matches(path, GATEWAY):
            selected.add('gateway')
        elif matches(path, STUDY_D):
            selected.update(('study_d', 'gemma'))
        elif not matches(path, FAST_ONLY):
            selected.update(GROUPS)
    return {group: group in selected for group in GROUPS}


def changed_paths(base, head):
    if not all(re.fullmatch(r'[0-9a-fA-F]{40}', revision) for revision in (base, head)):
        raise ValueError('PR base and head must be complete Git commit IDs')
    result = subprocess.check_output([
        'git', 'diff', '--no-renames', '--name-only', '-z', base + '...' + head,
    ])
    return result.decode('utf-8').rstrip('\0').split('\0') if result else []


def main():
    if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request':
        paths = changed_paths(os.environ['PR_BASE'], os.environ['PR_HEAD'])
        selected = select_checks(paths)
        print(json.dumps({'changed_paths': paths, 'selected': selected}, indent=2))
    else:
        selected = dict.fromkeys(GROUPS, True)
        print('Non-PR event: every old-evidence group selected')
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        for group, enabled in selected.items():
            output.write(group + '=' + str(enabled).lower() + '\n')


if __name__ == '__main__':
    main()
