"""Operational wall-clock guard; inactive outside an explicitly timed runner."""
import time
from live_demo.adapter import Stop

deadline = None


def check():
    if deadline is not None and time.monotonic() >= deadline:
        raise Stop('runner_timeout')
