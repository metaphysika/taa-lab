"""Explicit read-only Modal result poll; never launches or retries work."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def poll(call_id, output, modal):
    polling = False
    try:
        call = modal.FunctionCall.from_id(call_id)
        polling = True
        result = call.get(timeout=0)
    except BaseException as exc:
        if polling and type(exc) is TimeoutError and not str(exc):
            return 2  # Bare polling timeout; no final-status file.
        status = dict(status='failed', type=type(exc).__name__, message=str(exc))
        code = 1
    else:
        status = dict(status='complete', result=result)
        code = 0
    status.update(function_call_id=call_id, finished_utc=datetime.now(timezone.utc).isoformat())
    with Path(output).open('x') as stream:
        json.dump(status, stream, indent=2)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--call-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import modal
    return poll(args.call_id, args.output, modal)


if __name__ == '__main__':
    raise SystemExit(main())
