"""Wait for persisted real quota; never resume a new issued failure."""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.evaluation_qwen_continuation_v0221 import (
    OUTPUT, SUMMARY, read, review_source, verify_approval)
from formation.evaluation_runner_v0218 import atomic

BASE = Path('/workspace/haiku55-runtime')
HOLD = BASE / 'qwen38-maintenance.hold'
STATUS_NAME = 'continuation-controller-status.json'


def quota_ready_at(quota, now):
    events = sorted(e for e in quota.get('events', []) if now - e[0] < 86400)
    ready = max(now, quota.get('paused_until', 0))
    if events:
        ready = max(ready, events[-1][0] + 61)
    while events and (len(events) >= 1000 or sum(e[1] for e in events) + 8000 > 200000):
        ready = max(ready, events.pop(0)[0] + 86400)
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--approved-continuation', action='store_true')
    parser.add_argument('--reviewed-issued-failure', action='store_true')
    parser.add_argument('--confirm-groq-free', action='store_true')
    args = parser.parse_args()
    verify_approval(args.plan, ROOT, args.approved_continuation,
                    args.reviewed_issued_failure, args.confirm_groq_free)
    review_source(args.plan)
    source = ROOT / OUTPUT
    status_path = source / STATUS_NAME
    lock = (BASE / 'qwen38-continuation-controller.lock').open('a')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    # A missing controller may restart only from a verified pre-request quota boundary.
    if status_path.exists():
        if read(status_path)['state'] != 'waiting_pre_request_quota':
            lock.close()
            raise ValueError('terminal/uncertain controller state; separate review required')
    command = [sys.executable, 'scripts/formation_study_a_qwen38_continuation.py',
               '--plan', str(args.plan), '--approved-continuation',
               '--reviewed-issued-failure', '--confirm-groq-free']

    def status(state, **fields):
        atomic(status_path, dict(state=state, pid=os.getpid(), command=command,
               checkout_root=str(ROOT), output=OUTPUT,
               updated_at_utc=datetime.now(timezone.utc).isoformat(), **fields))

    try:
        while True:
            review_source(args.plan)
            progress_path = source / SUMMARY
            if progress_path.exists() and read(progress_path)['status'] == 'complete':
                status('complete', suffix_cells=236, cumulative_dollars=0)
                return
            quota = read(ROOT / 'results/formation-spending-v021/groq-rate.json')
            ready = quota_ready_at(quota, time.time())
            if time.time() < ready or HOLD.exists():
                status('waiting_pre_request_quota', maintenance_hold=HOLD.exists(),
                       next_allowed_utc=datetime.fromtimestamp(ready, timezone.utc).isoformat())
                # Long-lived controller waits; supervisor can inspect/hold it independently.
                time.sleep(30 if HOLD.exists() else min(30, max(1, ready - time.time())))
                continue
            review_source(args.plan)
            if HOLD.exists():
                continue
            number = max((int(p.stem.split('-')[1]) for p in source.glob('launch-*.log')), default=0) + 1
            status('running_approved_continuation', launch=number)
            with (source / ('launch-%06d.log' % number)).open('x') as log:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode != 0:
                raise ValueError('continuation CLI failed; no automatic retry')
            # review_source rejects stopped/fatal/guard/inflight/unclosed/invalid evidence.
            review_source(args.plan)
    except Exception:
        status('stopped_for_review', reason='continuation failure or evidence guard; inspect preserved journal/checkpoints')
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    main()
