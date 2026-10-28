"""Manually approved Actions orchestration. No independent spending authority."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.request

from live_demo.adapter import Stop
from live_demo.evidence import Evidence, verify
from experiment_a import config, runtime_guard
from experiment_a.credentials import scan

KINDS = ('neutral check', 'pilot continuation', 'held-out run')


def git(repo, *args):
    try:
        return subprocess.check_output(['git', '-C', str(repo), *args],
                                       stderr=subprocess.PIPE, timeout=60, text=True).strip()
    except (OSError, subprocess.SubprocessError):
        raise Stop('runner_git_failure') from None


def validate(commit, receipt, kind, head, *, dry_run=False):
    if (kind not in KINDS or not re.fullmatch('[0-9a-f]{40}', commit or '') or
            head != commit or type(receipt) is not dict or receipt.get('commit') != commit or
            receipt.get('owner') != 'Chris' or (not dry_run and receipt.get('launch_approved') is not True) or
            receipt.get('step') != config.STEP):
        raise Stop('runner_approval_mismatch')
    if kind == 'neutral check':
        if receipt.get('provider') not in config.MODELS or type(receipt.get('check_attempt')) is not int or receipt['check_attempt'] < 1:
            raise Stop('runner_approval_mismatch')
    elif kind == 'pilot continuation':
        n = receipt.get('continuation')
        ids = receipt.get('source_runs')
        cps = receipt.get('source_checkpoints')
        if (type(n) is not int or n < 1 or type(ids) is not list or len(ids) != n or
                type(cps) is not list or len(cps) != n or
                any(type(x) is not str or not re.fullmatch('[0-9a-f]{64}', x) for x in ids + cps) or len(set(ids)) != n):
            raise Stop('runner_source_binding')


WORKFLOW_PATH = '.github/workflows/experiment-a-live.yml'


def receipt_digest(receipt):
    return hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()


def approval_phrase(receipt, attempt):
    """Text Chris types in the environment approval comment for this exact receipt and attempt."""
    return 'approve receipt ' + receipt_digest(receipt)[:16] + ' attempt ' + str(attempt)


def workflow_identity(commit, environ=os.environ):
    """The executed workflow file must come from the approved commit itself."""
    ref = environ.get('GITHUB_WORKFLOW_REF', '')
    if (environ.get('GITHUB_WORKFLOW_SHA') != commit or
            not ref.startswith(environ.get('GITHUB_REPOSITORY', '') + '/' + WORKFLOW_PATH + '@')):
        raise Stop('runner_workflow_mismatch')


def environment_review(repository, token, receipt=None, opener=urllib.request.urlopen):
    """Fail closed if the named environment lacks Chris as required reviewer, or if Chris's
    approval of this run does not name this receipt's digest and this run attempt."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise Stop('runner_environment_unverified')
    req = urllib.request.Request('https://api.github.com/repos/' + repository +
                                 '/environments/experiment-a-live', headers={
                                     'Authorization': 'Bearer ' + token,
                                     'Accept': 'application/vnd.github+json'})
    try:
        with opener(req, timeout=30) as response:
            data = json.load(response)
        reviewers = [r for rule in data['protection_rules'] if rule['type'] == 'required_reviewers'
                     for r in rule['reviewers']]
        if len(reviewers) != 1 or reviewers[0].get('type') != 'User' or reviewers[0]['reviewer'].get('login') != 'metaphysika':
            raise ValueError('reviewer')
        run_id = os.environ.get('GITHUB_RUN_ID', '')
        attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '')
        if not run_id.isdecimal() or not attempt.isdecimal() or type(receipt) is not dict:
            raise ValueError('run')
        phrase = approval_phrase(receipt, attempt)
        approval_request = urllib.request.Request('https://api.github.com/repos/' + repository +
            '/actions/runs/' + run_id + '/approvals', headers=dict(req.headers))
        with opener(approval_request, timeout=30) as response:
            reviews = json.load(response)
        if not any(r.get('state') == 'approved' and r.get('user', {}).get('login') == 'metaphysika' and
                   phrase in (r.get('comment') or '') and
                   any(e.get('name') == 'experiment-a-live' for e in r.get('environments', [])) for r in reviews):
            raise ValueError('run approval')
    except Exception:
        raise Stop('runner_environment_unverified') from None


def worktrees(repo, base):
    """Fresh detached linked worktrees; no reset, force push or state repair."""
    result = []
    for branch, name in (('experiment-state', 'state'), ('experiment-a-evidence', 'evidence')):
        ref = 'refs/remotes/origin/' + branch
        git(repo, 'fetch', '--no-tags', 'origin', 'refs/heads/' + branch + ':' + ref)
        path = base / name
        git(repo, 'worktree', 'add', '--detach', str(path), ref)
        result.append(path)
    return result


def restore_sources(evidence, receipt, base):
    """Copy only public D/P chains, byte-exact, then verify receipt checkpoints."""
    sources = []
    for number, identity in enumerate(receipt['source_runs']):
        source = evidence / 'runs' / identity
        target = base / ('source-%06d' % number)
        if not source.is_dir() or source.is_symlink():
            raise Stop('runner_source_missing')
        for path in source.rglob('*'):
            if path.is_symlink() or (path.is_file() and not re.fullmatch(
                    r'(root|episode-[0-9]{4})/([0-9]{6}|checkpoint)\.json', str(path.relative_to(source)))):
                raise Stop('runner_source_invalid')
            if path.is_file():
                scan(str(path.relative_to(source)), path.read_bytes())
        target.mkdir()
        for path in (source / 'root').glob('*.json'):
            shutil.copy2(path, target / path.name)
        for child in source.glob('episode-*'):
            shutil.copytree(child, target / child.name)
            verify(target / child.name)
        if verify(target)['head'] != receipt['source_checkpoints'][number]:
            raise Stop('runner_source_invalid')
        sources.append(target)
    return sources


def scan_files(base):
    if not base.is_dir():
        raise Stop('runner_output_missing')
    counts = 0
    for path in sorted(base.rglob('*')):
        if path.is_symlink():
            raise Stop('evidence_credential_scan_failed')
        if path.is_file():
            if path.name == 'keys.env':
                raise Stop('evidence_credential_scan_failed')
            scan(str(path.relative_to(base)), path.read_bytes())
            counts += 1
    return counts


def dispatch(kind, receipt, output, *, dry_run=False, sources=()):
    if dry_run:
        # The held-out choice exercises infrastructure with D/P stand-ins only.
        # No H definitions, expected key or provider transport is opened.
        if kind == 'neutral check':
            from experiment_a.check import run
            return run(receipt['provider'], output)
        from experiment_a.run import run
        return run(output)
    if kind == 'held-out run':
        raise Stop('held_out_sealed')
    if kind == 'neutral check':
        from experiment_a.check import run
        return run(receipt['provider'], output, launch=True,
                   approved_commit=receipt['commit'], approval=receipt)
    from experiment_a.run import run, run_standing
    runner = run_standing if 'standing' in receipt else run
    return runner(output, launch=True, approved_commit=receipt['commit'], approval=receipt,
                  continue_from=sources, continuation=receipt['continuation'])


def execute(commit, receipt, kind, base, *, dry_run=False, seconds=18000):
    validate(commit, receipt, kind, git(config.ROOT, 'rev-parse', 'HEAD'), dry_run=dry_run)
    if type(seconds) is not int or not 0 < seconds <= 18000:
        raise Stop('runner_timeout_configuration')
    base = Path(base).resolve()
    if base.is_relative_to(config.ROOT) or config.ROOT.is_relative_to(base):
        raise Stop('runner_separate_output_required')
    if git(config.ROOT, 'status', '--porcelain', '--untracked-files=all'):
        raise Stop('runner_checkout_dirty')
    base.mkdir(parents=True, exist_ok=False)
    journal = Evidence(base / 'automation')
    journal.write('runner', dict(commit=commit, kind=kind, dry_run=dry_run,
                                receipt_sha256=receipt_digest(receipt),
                                maximum_seconds=seconds))
    sources = []
    old_deadline = runtime_guard.deadline
    old_kind = os.environ.get('TAA_RUN_KIND')
    runtime_guard.deadline = time.monotonic() + seconds
    stop = 'runner_failure'
    try:
        with (base / 'process.log').open('x') as log, redirect_stdout(log), redirect_stderr(log):
            # Downstream publishers refuse public publication whenever this names held-out.
            os.environ['TAA_RUN_KIND'] = kind
            if not dry_run:
                if kind == 'held-out run':
                    raise Stop('held_out_sealed')
                if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('TAA_ACTIONS_APPROVED_ENVIRONMENT') != 'experiment-a-live':
                    raise Stop('runner_environment_unverified')
                workflow_identity(commit)
                environment_review(os.environ.get('GITHUB_REPOSITORY', ''), os.environ.get('GITHUB_TOKEN', ''), receipt)
                providers = [receipt['provider']] if kind == 'neutral check' else config.MODELS
                if any(not os.environ.get(config.KEY_VARIABLES[p]) for p in providers):
                    raise Stop('runner_environment_secret_missing')
                state, evidence = worktrees(config.ROOT, base)
                os.environ['TAA_EXPERIMENT_STATE_WORKTREE'] = str(state)
                os.environ['TAA_EXPERIMENT_EVIDENCE_WORKTREE'] = str(evidence)
                if kind == 'pilot continuation':
                    if git(state, 'log', '-1', '--format=%H', '--grep=^Experiment A: pilot truncated closure;'):
                        raise Stop('pilot_closed')
                    sources = restore_sources(evidence, receipt, base)
                runtime_guard.check()
            result = dispatch(kind, receipt, base / 'run', dry_run=dry_run, sources=sources)
            stop = result['stop']
    except Stop as error:
        stop = error.reason
    except Exception:
        stop = 'runner_failure'
    finally:
        runtime_guard.deadline = old_deadline
        if old_kind is None:
            os.environ.pop('TAA_RUN_KIND', None)
        else:
            os.environ['TAA_RUN_KIND'] = old_kind
    journal.close(dict(stop=stop))
    count = scan_files(base)
    summary = dict(stop=stop, dry_run=dry_run, scanned_files=count, credential_matches=0,
                   evidence_identity=hashlib.sha256(str(base/'run').encode()).hexdigest())
    (base / 'runner-result.json').write_text(json.dumps(summary, indent=2) + '\n')
    scan_files(base)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-commit')
    parser.add_argument('--kind', choices=KINDS)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--scan-only', action='store_true')
    args = parser.parse_args()
    try:
        if args.scan_only:
            result = dict(scanned_files=scan_files(args.output), credential_matches=0)
        else:
            receipt = json.loads(os.environ['EXPERIMENT_A_RECEIPT_JSON'])
            result = execute(args.approved_commit, receipt, args.kind, args.output, dry_run=args.dry_run)
        print(json.dumps(result))
        if result.get('stop', 'complete') != 'complete':
            raise SystemExit(1)
    except (Stop, ValueError, KeyError) as error:
        print(json.dumps(dict(stop=error.reason if isinstance(error, Stop) else 'runner_input_invalid')))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
