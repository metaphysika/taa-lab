"""Durable experiment state, one shared provider lock, no implicit provisioning."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess

from live_demo.adapter import Stop
from live_demo.evidence import encoded
from experiment_a import config

STATE_ROOT = Path('/workspace/taa-experiment-a-evidence/state')
ACCOUNTING_ROOT = Path('/workspace/taa-lab/results/formation-spending-v021')
LEDGER_NAMES = {'anthropic': 'claude.json', 'google': 'google.json'}


class State:
    def __init__(self):
        self.root = STATE_ROOT.resolve()
        try:
            if subprocess.run(['git', '-C', str(self.root), 'rev-parse', '--show-toplevel'],
                              capture_output=True).returncode == 0:
                raise ValueError('state inside checkout')
            spec = json.loads((self.root / 'state.json').read_bytes())
            if spec.get('version') != 1 or type(spec.get('version')) is not int or spec.get('step') != config.STEP:
                raise ValueError('manifest')
            self.ledgers = {p: Path(spec['provider_ledgers'][p]) for p in config.MODELS}
            self.lock = Path(spec['provider_lock'])
            self.step_ledger = self.root / 'step-budget.txt'
            if (not self.lock.is_absolute() or not self.lock.parent.is_dir() or
                    not self.step_ledger.is_file() or any(not f.is_absolute() or not f.is_file() for f in self.ledgers.values())):
                raise ValueError('missing accounting')
            if set(spec['provider_ledgers']) != set(config.MODELS):
                raise ValueError('provider set')
            if (self.lock != ACCOUNTING_ROOT/'run.lock' or
                    any(self.ledgers[p] != ACCOUNTING_ROOT/LEDGER_NAMES[p] for p in config.MODELS)):
                raise ValueError('not shared canonical accounting')
            if any(p.with_suffix('.pending').exists() for p in [self.step_ledger, *self.ledgers.values()]):
                raise ValueError('interrupted accounting')
        except (ValueError, KeyError, TypeError, OSError):
            raise Stop('durable_state_missing_or_invalid') from None

    def claim_check(self, provider, approval, output):
        number = approval.get('check_attempt')
        if provider not in config.MODELS or type(number) is not int or number < 1:
            raise Stop('launch_not_approved')
        self.claim(self.root / ('check-%s-%06d.once' % (provider, number)),
                   dict(used=True, approval=approval, output=str(output)), 'check_attempt_used')

    def claim_run(self, approval, output):
        self.claim(self.root / 'run.once', dict(used=True, approval=approval, output=str(output)), 'run_already_used')

    @staticmethod
    def claim(path, payload, reason):
        try:
            with path.open('xb') as f:
                f.write(encoded(payload) + b'\n'); f.flush(); os.fsync(f.fileno())
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except FileExistsError:
            raise Stop(reason) from None

    @contextmanager
    def locked(self, output):
        payload = encoded(dict(step=config.STEP, output=str(output)))
        try:
            fd = os.open(self.lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise Stop('shared_lock_exists') from None
        try:
            os.write(fd, payload); os.fsync(fd)
            yield
        finally:
            os.close(fd)
            if self.lock.read_bytes() == payload:
                self.lock.unlink()  # Only this process's coordination lock, never a once marker.
