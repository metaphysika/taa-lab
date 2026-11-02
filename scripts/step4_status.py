"""Explicit read-only Modal result poll; never launches or retries work."""
import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path


def modal_exception(exc, modal, name):
    cls = getattr(getattr(modal, 'exception', None), name, None)
    return isinstance(cls, type) and isinstance(exc, cls)


def remote_failure(exc, modal):
    # Modal 1.6.3 appends remote frames with task-ID-prefixed filenames.
    tb = exc.__traceback__
    while tb:
        if re.match(r'^<ta-[0-9A-Z]{26}>:', tb.tb_frame.f_code.co_filename):
            return True
        tb = tb.tb_next
    classes = tuple(cls for name in ('RemoteError', 'FunctionTimeoutError', 'InternalFailure', 'InputCancellation')
                    if isinstance(cls := getattr(getattr(modal, 'exception', None), name, None), type))
    if isinstance(exc, classes):
        return True
    return modal_exception(exc, modal, 'ExecutionError') and str(exc).startswith((
        'Could not deserialize remote exception', 'Got remote exception of incorrect type'))


def poll(call_id, output, modal):
    polling = False
    try:
        call = modal.FunctionCall.from_id(call_id)
        polling = True
        result = call.get(timeout=0)
    except BaseException as exc:
        remote = remote_failure(exc, modal) if polling else False
        if isinstance(exc, (KeyboardInterrupt, SystemExit)) and not remote:
            raise
        if polling and not remote and type(exc) is TimeoutError and not str(exc):
            return 2  # Bare polling timeout; no final-status file.
        expired = modal_exception(exc, modal, 'OutputExpiredError')
        status = dict(status='expired' if expired else 'failed' if remote else 'poll_error',
                      type=type(exc).__name__, message=str(exc))
        code = 4 if expired else 1 if remote else 3
    else:
        status = dict(status='complete', result=result)
        code = 0
    status.update(function_call_id=call_id, finished_utc=datetime.now(timezone.utc).isoformat())
    # Poll errors are observations, not terminal results. Keep the final path free.
    target = Path(str(output) + '.poll-error.json') if code == 3 else Path(output)
    with target.open('w' if code == 3 else 'x') as stream:
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
