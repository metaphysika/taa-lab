"""OS clock isolation for historical CPU rehearsals, including python -I children."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


def frozen_env():
    libraries = list(Path('/usr/lib').glob('*/faketime/libfaketime.so.1')) if sys.platform == 'linux' else []
    if not libraries:
        message = 'historical CPU rehearsal requires Linux libfaketime for python -I child clocks'
        if os.environ.get('TAA_REQUIRE_FAKETIME') == '1':
            raise AssertionError(message)
        raise unittest.SkipTest(message)
    env = os.environ.copy()
    env.update(LD_PRELOAD=str(libraries[0]), FAKETIME='@2026-10-20 12:00:00', TZ='UTC')
    # Fail if installed interception does not reach isolated Python and its child.
    probe = "from datetime import datetime, timezone; import time; now = datetime.now(timezone.utc); assert (now.year, now.month, now.day) == (2026, 10, 20), now; a=time.monotonic(); time.sleep(.05); assert .03 < time.monotonic()-a < 5"
    child = "import subprocess, sys; subprocess.run([sys.executable, '-I', '-c', " + repr(probe) + "], check=True)"
    subprocess.run([sys.executable, '-I', '-c', child], env=env, check=True, timeout=30)
    return env


def run_frozen(command, **kwargs):
    return subprocess.run(command, env=frozen_env(), **kwargs)


if __name__ == '__main__':
    raise SystemExit(run_frozen([sys.executable] + sys.argv[1:]).returncode)
