"""Public state-only Git worktree; every mutation must reach origin before use."""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

from live_demo.adapter import Stop
from live_demo.evidence import encoded
from experiment_a import config

STATE_ROOT = Path('/workspace/taa-experiment-state')
RUN_ROOT = config.ROOT
BRANCH = 'experiment-state'
LEDGER_NAMES = {'anthropic': 'ledgers/claude.json', 'google': 'ledgers/google.json'}
SPEC = dict(version=2, step=config.STEP, branch=BRANCH, provider_ledgers=LEDGER_NAMES)
BASE_FILES = frozenset(('state.json', 'step-budget.txt', *LEDGER_NAMES.values()))


def allowed(name):
    return (name in BASE_FILES or name in ('reconstruction.json', 'active-run.json', 'run.once') or
            re.fullmatch(r'check-(anthropic|google)-[0-9]{6,}\.once', name) is not None or
            re.fullmatch(r'continuation-[0-9]{6,}\.once', name) is not None)


class State:
    branch = BRANCH
    def __init__(self, root=None, *, run_root=None, sleeper=None, continuation=None):
        self.root = Path(root or os.environ.get('TAA_EXPERIMENT_STATE_WORKTREE', STATE_ROOT)).resolve()
        self.run_root = Path(run_root or RUN_ROOT).resolve()
        self.lease, self.failed, self.base = None, False, None
        self.pending_settlement = None
        self.continuation_guard = None
        self.evidence = None
        self.sleeper = time.sleep if sleeper is None else sleeper
        try:
            if (self.root.is_relative_to(self.run_root) or self.run_root.is_relative_to(self.root)
                    or not (self.root / '.git').is_file()):
                raise ValueError('separate linked worktree required')
            if Path(self._git('rev-parse', '--show-toplevel')).resolve() != self.root:
                raise ValueError('worktree root required')
            branch = self._git('branch', '--show-current')
            if branch not in ('', BRANCH):
                raise ValueError('wrong branch')
            common = Path(self._git('rev-parse', '--path-format=absolute', '--git-common-dir')).resolve()
            run_common = Path(self._git('rev-parse', '--path-format=absolute', '--git-common-dir', cwd=self.run_root)).resolve()
            if common != run_common:
                raise ValueError('not a worktree of the run repository')
            self.lock = common / 'experiment-state.lock'
            self.ledgers = {p: self.root / name for p, name in LEDGER_NAMES.items()}
            self.step_ledger = self.root / 'step-budget.txt'
            self.validate_files()
        except (OSError, ValueError, KeyError, TypeError, InvalidOperation):
            raise Stop('durable_state_missing_or_invalid') from None
        self.require_current(continuation=continuation)

    def _git(self, *args, cwd=None):
        try:
            result = subprocess.run(['git', '-C', str(cwd or self.root), *args],
                                    capture_output=True, text=True, timeout=60, check=True)
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            # Git stderr can contain remote credentials. Never relay it.
            raise Stop('state_git_failure') from None

    def validate_files(self):
        names = self._git('ls-files', '-z').split('\0')
        names = set(filter(None, names))
        if not BASE_FILES <= names or any(not allowed(name) for name in names):
            raise ValueError('state-only file allowlist')
        for name in names:
            path = self.root / name
            if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != self.root.parent):
                raise ValueError('state symlink')
        if json.loads((self.root / 'state.json').read_bytes()) != SPEC:
            raise ValueError('manifest')
        for path in (self.step_ledger, *self.ledgers.values()):
            if path.with_suffix('.pending').exists():
                raise ValueError('interrupted accounting')
            value = (json.loads(path.read_bytes())['estimated_api_dollars']
                     if path.suffix == '.json' else path.read_text())
            if isinstance(value, bool) or not Decimal(str(value)).is_finite() or Decimal(str(value)) < 0:
                raise ValueError('invalid amount')
        for name in names:
            if name.endswith('.once') and json.loads((self.root / name).read_bytes()).get('used') is not True:
                raise ValueError('invalid marker')

    def require_current(self, *, continuation=None):
        if self.failed:
            raise Stop('state_publication_failed')
        if self._git('status', '--porcelain', '--untracked-files=all'):
            raise Stop('state_worktree_dirty')
        # Fetch only observes. Never merge, reset, drop an ahead commit or clean up.
        self._git('fetch', '--no-tags', 'origin', 'refs/heads/' + self.branch)
        head = self._git('rev-parse', 'HEAD')
        remote = self._git('rev-parse', 'FETCH_HEAD')
        if continuation is not None:
            self.pending_settlement = continuation.prepare_state(self, head, remote)
        elif head != remote:
            raise Stop('state_worktree_stale')
        try:
            self.validate_files()
        except (ValueError, OSError, KeyError, TypeError, InvalidOperation):
            raise Stop('durable_state_missing_or_invalid') from None
        self.base = head

    def require_lease(self):
        if self.lease is None:
            raise Stop('state_lease_required')
        try:
            current = json.loads((self.root / 'active-run.json').read_bytes())
        except (OSError, ValueError):
            raise Stop('state_lease_lost') from None
        if current.get('lease') != self.lease:
            raise Stop('state_lease_lost')

    def before_change(self):
        self.require_current()
        self.require_lease()

    def publication_local(self, commit, parent):
        try:
            if (self._git('status', '--porcelain', '--untracked-files=all') or
                    self._git('rev-parse', 'HEAD') != commit or
                    self._git('rev-parse', commit + '^') != parent):
                raise Stop('state_publication_failed')
            self.validate_files()
        except (Stop, OSError, ValueError, KeyError, TypeError, InvalidOperation):
            raise Stop('state_publication_failed') from None

    def observe_publication(self, commit, parent, fields):
        try:
            self._git('fetch', '--no-tags', 'origin', 'refs/heads/' + self.branch)
            remote = self._git('rev-parse', 'FETCH_HEAD')
        except Stop:
            self.evidence.write('state_confirmation', dict(fields, outcome='unavailable'))
            return 'unavailable'
        outcome = ('exact_commit' if remote == commit else
                   'parent_commit' if remote == parent else 'different_tip')
        self.evidence.write('state_confirmation', dict(fields, remote_commit=remote, outcome=outcome))
        if outcome == 'different_tip':
            raise Stop('state_publication_failed')
        self.publication_local(commit, parent)
        if outcome == 'exact_commit':
            self.base = commit
        return outcome

    def confirm_publication(self, commit, parent):
        """Bounded same-commit recovery; foreign tips never authorize a push."""
        if self.evidence is None:
            raise Stop('state_publication_failed')
        repushes = 0
        for attempt, delay in enumerate((10, 30, 60), 1):
            fields = dict(commit=commit, parent=parent, attempt=attempt, delay_seconds=delay)
            self.evidence.write('state_confirmation_wait', fields)
            self.sleeper(delay)
            outcome = self.observe_publication(commit, parent, dict(fields, phase='before_repush'))
            if outcome == 'exact_commit':
                return
            if outcome != 'parent_commit':
                continue
            # One re-push per delayed round, at most three. Pin the same SHA,
            # recheck local state, and record intent durably before attempting it.
            self.publication_local(commit, parent)
            repushes += 1
            self.evidence.write('state_repush', dict(fields, repush=repushes))
            try:
                self._git('push', 'origin', commit + ':refs/heads/' + self.branch)
                result = 'acknowledged'
            except Stop:
                result = 'unavailable'
            self.evidence.write('state_repush_result', dict(fields, repush=repushes, outcome=result))
            # Observe even if the acknowledgement failed. Never infer arrival.
            outcome = self.observe_publication(commit, parent,
                dict(fields, delay_seconds=0, phase='after_repush'))
            if outcome == 'exact_commit':
                return
        raise Stop('state_publication_failed')

    def publish_stranded(self):
        """Called under flock, with verified sources and a new approved receipt."""
        if self.pending_settlement is None:
            return
        commit, parent = self.pending_settlement
        try:
            self.evidence.write('stranded_settlement', dict(commit=commit, parent=parent))
            self.confirm_publication(commit, parent)
            self.require_current()
            self.pending_settlement = None
        except BaseException as error:
            self.failed = True
            if isinstance(error, (Stop, OSError)):
                raise Stop('state_publication_failed') from None
            raise

    def publish(self, description, paths):
        """Publish one fixed direct child; recover only an exact remote acknowledgement."""
        if self.failed or self.base is None:
            raise Stop('state_publication_failed')
        names = [str(Path(path).relative_to(self.root)) for path in paths]
        if any(not allowed(name) for name in names):
            raise Stop('state_file_forbidden')
        parent = self.base
        try:
            if self._git('rev-parse', 'HEAD') != self.base:
                raise Stop('state_worktree_stale')
            changed = set(filter(None, self._git('diff', '--name-only').splitlines()))
            changed |= set(filter(None, self._git('ls-files', '--others', '--exclude-standard').splitlines()))
            if not changed <= set(names) or self._git('diff', '--cached', '--name-only'):
                raise Stop('state_worktree_dirty')
            self._git('add', '--', *names)
            self._git('commit', '--allow-empty', '-m', 'Experiment A: ' + description)
            commit = self._git('rev-parse', 'HEAD')
            if self._git('rev-parse', commit + '^') != self.base:
                raise Stop('state_worktree_stale')
            tree = self._git('ls-tree', '-r', '--name-only', commit).splitlines()
            delta = self._git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines()
            if any(not allowed(name) for name in tree) or not set(delta) <= set(names):
                raise Stop('state_file_forbidden')
            try:
                # The commit was checked above to be a direct child of our tip.
                # A normal push rejects divergence, without any force option.
                self._git('push', 'origin', commit + ':refs/heads/' + self.branch)
                self.require_current()
                if self.base != commit:
                    raise Stop('state_publication_failed')
            except Stop as error:
                if error.reason == 'state_worktree_stale':
                    # require_current already observed a tip. A known foreign
                    # tip is final; an unchanged parent may use delayed recovery.
                    remote = self._git('rev-parse', 'FETCH_HEAD')
                    if remote not in (commit, parent):
                        if self.evidence is not None:
                            self.evidence.write('state_confirmation', dict(commit=commit, parent=parent,
                                attempt=0, delay_seconds=0, remote_commit=remote, outcome='different_tip'))
                        raise
                elif error.reason != 'state_git_failure':
                    if self.evidence is not None:
                        self.evidence.write('state_confirmation', dict(commit=commit, parent=parent,
                            attempt=0, delay_seconds=0, outcome='guard_stop', reason=error.reason))
                    raise
                self.confirm_publication(commit, parent)
        except BaseException as error:
            # Preserve dirty files/ahead commits and any remote lease. No rollback.
            self.failed = True
            if isinstance(error, (Stop, OSError)):
                raise Stop('state_publication_failed') from None
            raise

    def _write(self, path, payload):
        with path.open('xb') as stream:
            stream.write(encoded(payload) + b'\n'); stream.flush(); os.fsync(stream.fileno())

    def claim_check(self, provider, approval, output):
        number = approval.get('check_attempt')
        if provider not in config.MODELS or type(number) is not int or number < 1:
            raise Stop('launch_not_approved')
        self.claim(self.root / ('check-%s-%06d.once' % (provider, number)),
                   approval, output, 'check_attempt_used')

    def claim_run(self, approval, output):
        self.claim(self.root / 'run.once', approval, output, 'run_already_used')

    def claim_continuation(self, approval, output, plan):
        self.claim(self.root / ('continuation-%06d.once' % plan.number), approval, output,
                   'continuation_already_used', extra=dict(continuation=plan.number,
                   source_checkpoints=plan.checkpoints, start_index=plan.start_index,
                   **plan.standing_marker()))

    def claim(self, path, approval, output, reason, *, extra=None):
        self.before_change()
        if path.exists():
            raise Stop(reason)
        commit = approval.get('commit')
        if commit is not None and (type(commit) is not str or not re.fullmatch('[0-9a-f]{40}', commit)):
            raise Stop('launch_not_approved')
        # No raw request, response, key, arbitrary receipt field or local path is public.
        self._write(path, dict(used=True, step=config.STEP, approved_commit=commit, lease=self.lease,
                    output_sha256=hashlib.sha256(str(output).encode()).hexdigest(), **(extra or {})))
        self.publish('claim ' + path.name, [path])

    def before_request(self, provider, approval, neutral):
        from experiment_a.runtime_guard import check
        check()
        self.before_change()
        name = ('check-%s-%06d.once' % (provider, approval['check_attempt']) if neutral else
                'continuation-%06d.once' % approval['continuation'] if 'continuation' in approval else 'run.once')
        try:
            marker = json.loads((self.root / name).read_bytes())
        except (OSError, ValueError):
            raise Stop('state_claim_required') from None
        if marker.get('lease') != self.lease or marker.get('approved_commit') != approval.get('commit'):
            raise Stop('state_claim_required')
        if 'continuation' in approval:
            if any(marker.get(k) != approval[k] for k in ('continuation','source_checkpoints','start_index')):
                raise Stop('state_claim_required')
            if 'standing' in approval:
                from experiment_a.standing import binding
                authority=binding(approval)
                if (marker.get('standing_receipt_sha256')!=authority['receipt_sha256'] or
                        marker.get('standing_segment')!=authority['segment']):
                    raise Stop('state_claim_required')
            if self.continuation_guard is None:
                raise Stop('continuation_verification_required')
            self.continuation_guard()
        check()

    @contextmanager
    def locked(self, output, *, continuation=None):
        fd = os.open(self.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Stop('shared_lock_exists') from None
            self.require_current(continuation=continuation)
            active = self.root / 'active-run.json'
            if continuation is not None:
                continuation.validate(self)
            if active.exists() and continuation is None:
                raise Stop('shared_lock_exists')
            if active.exists():
                prior = json.loads(active.read_bytes())
                marker = continuation.previous_marker(self)
                if any(prior.get(k) != marker.get(k) for k in ('lease', 'output_sha256', 'step')):
                    raise Stop('continuation_lease_mismatch')
            self.publish_stranded()
            self.lease = uuid.uuid4().hex
            payload = dict(step=config.STEP, lease=self.lease,
                           output_sha256=hashlib.sha256(str(output).encode()).hexdigest())
            if active.exists():
                # The old lease remains in Git history; only an approved,
                # evidence-verified continuation can supersede it.
                pending = self.root / 'active-run.pending'
                self._write(pending, payload)
                os.replace(pending, active)
            else:
                self._write(active, payload)
            self.publish('acquire continuation lease' if continuation else 'acquire run lease', [active])
            try:
                yield
            finally:
                if not self.failed:
                    self.before_change()
                    active.unlink()
                    self.publish('release run lease', [active])
                    self.lease = None
        finally:
            os.close(fd)
