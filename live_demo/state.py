"""Operator-provisioned live state shared by every checkout; never auto-reset."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from live_demo.adapter import Stop
from live_demo.evidence import encoded

# Deliberately independent of checkout, cwd, output directory and environment.
# Only offline tests patch this constant. Live CLI has no state-path override.
STATE_ROOT = Path('/workspace/taa-live-demo-evidence/state')


class LiveState:
    def __init__(self):
        self.root = STATE_ROOT.resolve()
        try:
            spec = json.loads((self.root/'state.json').read_bytes())
            if (type(spec) is not dict or type(spec.get('version')) is not int or spec.get('version') != 1 or
                    spec.get('used_check_attempts') != [1, 2]):
                raise ValueError('invalid manifest')
            # State must live outside every Git checkout, not just this one.
            if subprocess.run(['git','-C',str(self.root),'rev-parse','--show-toplevel'],
                              capture_output=True).returncode == 0:
                raise ValueError('state inside checkout')
            self.ledger = Path(spec['provider_ledger'])
            self.lock = Path(spec['provider_lock'])
            self.step_ledger = self.root/'step-budget.txt'
            if (not self.ledger.is_absolute() or not self.lock.is_absolute() or
                    not self.ledger.is_file() or not self.lock.parent.is_dir() or
                    not self.step_ledger.is_file()):
                raise ValueError('missing accounting')
            for number in (1, 2):
                marker = self.root/('check-attempt-%06d.once'%number)
                if hashlib.sha256(marker.read_bytes()).hexdigest() != spec['imported_marker_sha256'][str(number)]:
                    raise ValueError('imported marker changed')
        except (OSError, ValueError, KeyError, TypeError):
            raise Stop('durable_state_missing_or_invalid') from None

    def claim_check(self, approval, output):
        number = approval.get('check_attempt')
        if type(number) is not int or number < 1:
            raise Stop('launch_not_approved')
        if number in (1, 2):
            raise Stop('check_attempt_used')
        self._claim(self.root/('check-attempt-%06d.once'%number),
                    dict(used=True, check_attempt=number, approval=approval, output=str(output)),
                    'check_attempt_used')

    def claim_run(self, commit, output):
        self._claim(self.root/'run.once',dict(used=True,commit=commit,output=str(output)), 'run_already_used')

    @staticmethod
    def _claim(path, value, reason):
        try:
            with path.open('xb') as stream:
                stream.write(encoded(value)+b'\n');stream.flush();os.fsync(stream.fileno())
            descriptor=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(descriptor)
            finally:os.close(descriptor)
        except FileExistsError:
            raise Stop(reason) from None
