"""Offline-review proposal: exact Gemma count recovery, metadata-only fallback.

No credentials, network client, launch, or approval bypass lives in this module.
Frozen generation RetryTransport is used unchanged. Callers must separately pass
the approved runtime, immutable-source, byte, quota, and readiness checks.
"""
import copy
import json
from pathlib import Path

from agents.call_telemetry import BudgetStopped
from formation.evaluation_gemma_v0222 import append, body_hash

MODEL = 'gemma-4-31b-it'
ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/' + MODEL + ':countTokens'


def events(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def verified_counts(sources):
    """Sources are explicit receipt/state paths pinned by the review manifest.

    The caller verifies their file SHA256 bindings before using this function.
    A usable receipt needs a matching closed received job for the exact body.
    Never infer a token count from bytes, usage, a similar body, or a job alone.
    """
    found = {}
    for receipt_path, state_path, receipt_sha, state_sha in sources:
        import hashlib
        rp, sp = Path(receipt_path), Path(state_path)
        if hashlib.sha256(rp.read_bytes()).hexdigest() != receipt_sha or hashlib.sha256(sp.read_bytes()).hexdigest() != state_sha:
            raise BudgetStopped('count recovery source binding differs')
        state = json.loads(sp.read_text())
        for e in events(rp):
            if e.get('event') != 'count_complete':
                continue
            digest, count = e.get('body_sha256'), e.get('totalTokens')
            if not isinstance(digest, str) or len(digest) != 64 or any(x not in '0123456789abcdef' for x in digest) or type(count) is not int or count < 1:
                raise BudgetStopped('invalid prior count receipt')
            job_id = e.get('metadata_job_id', 'countTokens:' + digest)
            job = state.get('jobs', {}).get(job_id)
            if not job or job.get('body_sha256') != digest or job.get('phase') != 'complete' or job.get('received') is not True or type(job.get('attempts')) is not int or not 1 <= job['attempts'] <= 5:
                raise BudgetStopped('count receipt lacks matching closed received job')
            if digest in found and found[digest]['totalTokens'] != count:
                raise BudgetStopped('conflicting exact-body count receipts')
            record = dict(totalTokens=count, body_sha256=digest, metadata_job_id=job_id,
                          receipt_source=str(rp), receipt_source_sha256=receipt_sha,
                          retry_source=str(sp), retry_source_sha256=state_sha)
            found.setdefault(digest, record)
    return found


def metadata_job(retry, body, endpoint=ENDPOINT, model=MODEL):
    """Choose at most one new metadata job; never change an original job.

    Only call this inside countTokens, after checking for a usable count. A
    generation job cannot enter through this API. Existing unclosed jobs or
    exhaustion/run-limit stops remain review stops, even for metadata.
    """
    if endpoint != ENDPOINT or model != MODEL:
        raise BudgetStopped('metadata exemption requires exact Gemma countTokens endpoint')
    if retry.state.get('stop'):
        raise BudgetStopped('transport stop remains in force')
    digest = body_hash(body)
    original = 'countTokens:' + digest
    old = retry.state['jobs'].get(original)
    if old is None:
        return original
    if old.get('body_sha256') != digest:
        raise BudgetStopped('metadata body differs')
    if old.get('phase') == 'ready' and old.get('attempts') == 0 and old.get('received') is False:
        return original
    if old.get('phase') not in ('complete', 'failed') or old.get('received') is not True:
        raise BudgetStopped('unclosed/interrupted metadata job requires review')
    new = 'countTokens:v0243:' + digest + ':metadata-only-1'
    if new in retry.state['jobs']:
        pending = retry.state['jobs'][new]
        if pending.get('body_sha256') == digest and pending.get('phase') == 'ready' and pending.get('attempts') == 0 and pending.get('received') is False:
            return new  # Same unsent job after normal quota pacing, no new job.
        raise BudgetStopped('metadata-only replacement already exists; no second replacement')
    # Original job, counters, quota and shared generation transport are untouched.
    append(retry.journal, dict(event='metadata_only_new_job', original_job=original,
                              new_job=new, body_sha256=digest,
                              original_job_snapshot=copy.deepcopy(old),
                              reason='no usable exact-body count receipt'))
    return new


def count_body(client, body, recovered):
    """Proposed CChat.count implementation; only metadata can be transmitted.

    client is the existing Gemma client: its reserve/native_send callbacks retain
    full native metadata, quota pacing, shared retry counters and closure policy.
    No generation send method is called or modified.
    """
    if client.model != MODEL:
        raise BudgetStopped('count remedy is Gemma metadata only')
    if client.retry.state.get('stop'):
        raise BudgetStopped('transport stop remains in force')
    outer = {'generateContentRequest': dict(body, model='models/' + MODEL)}
    if len(json.dumps(outer).encode()) > 64000:
        raise BudgetStopped('metadata secondary byte guard before HTTP')
    client.quota.guard()
    digest = body_hash(body)
    if digest in client.quota.counts:
        count = client.quota.counts[digest]
        if digest in recovered and recovered[digest]['totalTokens'] != count:
            raise BudgetStopped('current/prior exact count conflict')
        return count
    if digest in recovered:
        record = recovered[digest]
        append(client.quota.receipts, dict(event='count_complete', **record,
               receipt_kind='recovered_exact_body_v0243', no_HTTP_request=True))
        client.quota.counts[digest] = record['totalTokens']
        return record['totalTokens']
    job_id = metadata_job(client.retry, body)

    def begin():
        token = client.reserve('countTokens')
        client.quota.state['metadata_inflight'] = job_id
        client.quota.save()
        append(client.quota.receipts, dict(event='count_start', body_sha256=digest,
                                          metadata_job_id=job_id, attempt_index=token))
        return token

    def failed(token, meta, output, reply):
        append(client.quota.receipts, dict(event='count_error', body_sha256=digest,
               metadata_job_id=job_id, model_reply_received=output,
               estimated_dollars=0, outcome_uncertain=meta['status'] is None, **meta))
        client.quota.state['metadata_inflight'] = None
        client.quota.failure(meta, 'countTokens')

    data = client.retry.execute(job_id, body, begin,
        lambda received: client.native_send(ENDPOINT, outer, received), failed,
        quota_ready=lambda: max(client.quota.ready_at, client.quota.state['paused_until']))
    count = data.get('totalTokens')
    if type(count) is not int or count < 1:
        raise BudgetStopped('received metadata lacks valid token count; review')
    append(client.quota.receipts, dict(event='count_complete', body_sha256=digest,
                                      metadata_job_id=job_id, totalTokens=count))
    client.quota.state['metadata_inflight'] = None
    client.quota.save()
    client.quota.counts[digest] = count
    return count


def verify_unstarted_boundary(output, index):
    """Read-only admission for the unsent first request, not episode resumption.

    Exact archived stop evidence must remain pinned. No request/history/row is
    reused as an episode result; no resume or native-format-rerun label is added.
    Actual admission needs separate owner approval and both readiness CI checks.
    """
    import hashlib
    output = Path(output)
    for name, digest in index['files_sha256'].items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
            raise BudgetStopped('original unsent-stop artifact differs')
    state = json.loads((output / 'controller-status.json').read_text())
    cps = list(output.glob('C-*-checkpoint.json'))
    if state.get('state') != 'stopped_for_review' or state.get('completed') != 0 or len(cps) != 1:
        raise BudgetStopped('not the zero-request Gemma boundary')
    cp = json.loads(cps[0].read_text())
    if cp.get('phase') != 'guard' or cp.get('packets') != [] or cp['cell']['sequence'] != 1:
        raise BudgetStopped('first unsent request differs')
    if (output / 'calls.jsonl').exists() or (output / 'progress-summary.json').exists():
        raise BudgetStopped('Gemma generation/output already begun')
    return copy.deepcopy(cp['cell'])
