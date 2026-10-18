"""Local submission handshake only; no Modal import or backend on import."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone


def persist(path, record):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    directory = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def submit_controller(controller, payload, app_id, receipt_path, policy, emit=print):
    """spawn() returns an acknowledged call ID; never wait for the result.

    A lost acknowledgement is UNKNOWN, not evidence that the server did nothing.
    The original attempt marker and this separate submission record prevent retry.
    """
    if not isinstance(app_id, str) or not app_id.startswith('ap-'):
        raise ValueError('hydrated running app ID required before submission')
    path = Path(receipt_path).with_suffix('.submission.json')
    record = dict(status='SUBMISSION_IN_PROGRESS', app_id=app_id,
                  commit=payload['commit'], approval_receipt=payload['approval_receipt'],
                  utc=datetime.now(timezone.utc).isoformat(), result_waited_for=False)
    # An exclusive local claim precedes the only spawn. Never reset on ambiguity.
    with path.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    try:
        call = controller.spawn(payload)
        call_id = call.object_id
        if not isinstance(call_id, str) or not call_id.startswith('fc-'):
            raise RuntimeError('spawn returned no valid server call ID; review, no resubmit')
        record.update(status='SUBMITTED', call_id=call_id,
                      acknowledged_utc=datetime.now(timezone.utc).isoformat())
        persist(path, record)
    except BaseException as exc:
        record.update(policy.failure_record(exc, 'controller_submission'))
        record['status'] = 'SUBMISSION_UNCONFIRMED_NO_RELAUNCH'
        persist(path, record)
        raise
    emit(f'SUBMITTED — safe to close laptop | app_id={app_id} | call_id={call_id}', flush=True)
    return record
