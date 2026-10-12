"""Prospective provider-neutral transport retries. No response-quality selection."""
import hashlib
import json
import socket
import time
import urllib.error
from pathlib import Path

from agents.call_telemetry import BudgetStopped
from formation.evaluation_gemma_v0222 import atomic, append, reset_seconds, safe_headers
from formation.limits import RatePaused

RETRYABLE_HTTP = {429, 500, 502, 503, 504}
WAITS = (10, 30, 60, 120)


class RetryExhausted(RuntimeError):
    pass


class RetryRunLimit(RuntimeError):
    pass


class ReplyReceivedFailure(RuntimeError):
    """Bytes/reply arrived, but transport or native decoding did not complete."""
    pass


def retryable(error):
    if isinstance(error, urllib.error.HTTPError):
        return error.code in RETRYABLE_HTTP
    if isinstance(error, urllib.error.URLError):
        return retryable(error.reason)
    return isinstance(error, (TimeoutError, socket.timeout, ConnectionResetError))


def error_metadata(error, now):
    """Keep only numeric reset and reply-presence information, never error messages."""
    status, headers, details, reply = None, {}, [], None
    if isinstance(error, urllib.error.HTTPError):
        status = error.code
        headers = safe_headers(error.headers or {})
        try:
            data = json.loads(error.read(65536))
            if any(key in data for key in ('candidates', 'choices', 'output')) or \
                    (data.get('type') == 'message' and 'content' in data):
                reply = data
            details = [d for d in data.get('error', {}).get('details', [])
                       if isinstance(d, dict) and d.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo']
        except Exception:
            pass
    return {'status': status, 'error_class': type(error).__name__,
            'reset_seconds': reset_seconds(headers, details, now)}, reply


class RetryTransport:
    """Five total attempts, persistent job/run limits, first-byte no-resend barrier.

    begin() must reserve provider quota AND dollars and journal every attempt.
    failed() must close that attempt, retaining ambiguous usage/reserves.
    send(mark_received) must mark any received model bytes before decoding.
    Parsing/scoring and usage validation happen AFTER this function returns.
    """
    def __init__(self, path, journal, now=time.time, sleep=time.sleep, waiting=None):
        self.path, self.journal = Path(path), Path(journal)
        self.now, self.sleep, self.waiting = now, sleep, waiting
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            'jobs': {}, 'requests_needing_retry': 0, 'stop': None}

    def save(self):
        atomic(self.path, self.state)

    def wait_until(self, ready, reason):
        while self.now() < ready:
            if self.waiting:
                self.waiting(reason, ready)
            self.sleep(min(30, ready - self.now()))

    def execute(self, job_id, body, begin, send, failed, quota_ready=None):
        if self.state['stop']:
            raise BudgetStopped('retry policy stopped for review; no automatic restart')
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        job = self.state['jobs'].setdefault(job_id, {
            'body_sha256': digest, 'attempts': 0, 'received': False,
            'phase': 'ready', 'ready_at': 0, 'counted_retry': False})
        if job['body_sha256'] != digest:
            raise BudgetStopped('retry request body changed')
        if job['received'] or job['phase'] in ('complete', 'inflight', 'failed'):
            raise BudgetStopped('received/unclosed/completed request cannot be resent')
        while job['attempts'] < 5:
            self.wait_until(job['ready_at'], 'waiting_transport_retry')
            try:
                token = begin()
            except RatePaused:
                if not job['attempts']:
                    self.save()
                    raise  # Safe pre-request pause; no attempt consumed.
                if quota_ready is None:
                    raise BudgetStopped('retry quota deadline missing') from None
                self.wait_until(max(self.now() + .01, quota_ready()), 'waiting_retry_quota')
                continue
            job.update(attempts=job['attempts'] + 1, phase='inflight')
            self.save()
            append(self.journal, {'event': 'transport_attempt_start', 'job': job_id,
                                  'attempt': job['attempts'], 'body_sha256': digest,
                                  'at': self.now()})

            def received():
                if not job['received']:
                    job['received'] = True
                    self.save()
                    append(self.journal, {'event': 'received_reply_barrier', 'job': job_id,
                                          'attempt': job['attempts'], 'at': self.now()})
            try:
                result = send(received)
                # Even an empty decoded native response must never be re-sent.
                received()
            except Exception as error:
                meta, reply = error_metadata(error, self.now())
                if reply is not None:
                    received()
                failed(token, meta, job['received'], reply)
                append(self.journal, dict(event='transport_attempt_end', job=job_id,
                    attempt=job['attempts'], model_reply_received=job['received'],
                    outcome_uncertain=meta['status'] is None, **meta))
                if job['received'] or not retryable(error):
                    job['phase'] = 'failed'
                    self.save()
                    if job['received']:
                        raise ReplyReceivedFailure('received output retained; never resend') from None
                    raise
                if job['attempts'] == 5:
                    job['phase'] = 'failed'
                    self.state['stop'] = 'five_attempts_exhausted'
                    self.save()
                    raise RetryExhausted('five transport attempts exhausted') from None
                if not job['counted_retry']:
                    job['counted_retry'] = True
                    self.state['requests_needing_retry'] += 1
                    if self.state['requests_needing_retry'] > 10:
                        job['phase'] = 'failed'
                        self.state['stop'] = 'eleventh_request_needing_retry'
                        self.save()
                        raise RetryRunLimit('eleventh distinct request needs retry; stopped before resend') from None
                delay = max(WAITS[job['attempts'] - 1], meta['reset_seconds'] or 0)
                job.update(phase='waiting', ready_at=self.now() + delay)
                self.save()
                append(self.journal, {'event': 'transport_retry_scheduled', 'job': job_id,
                                      'next_attempt': job['attempts'] + 1, 'wait_seconds': delay,
                                      'reason': meta, 'outcome_uncertain': meta['status'] is None})
                continue
            job['phase'] = 'complete'
            self.save()
            append(self.journal, {'event': 'transport_attempt_end', 'job': job_id,
                                  'attempt': job['attempts'], 'model_reply_received': True,
                                  'status': 200, 'error_class': None})
            return result
        raise RetryExhausted('five attempts already consumed')
