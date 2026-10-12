"""Reviewed-source Gemma suffix and replacements; execution approval required."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from agents.call_telemetry import BudgetStopped
from agents.gemini_client import parse_first_json
from formation.clients import ProviderError, ReplyError
from formation.evaluation_gemma_v0222 import (ROOT, MODEL, BASE, OUTPUT, PRICES,
    GemmaChat, GemmaQuota, GemmaRecorder, read, sha, append, atomic, body_hash, name)
from formation.evaluation_runner_v0218 import execute_cell
from formation.limits import RatePaused
from formation.study_a import load_cases, replay_episode
from formation.transport_retry_v0223 import (RetryTransport, RetryExhausted,
    RetryRunLimit, ReplyReceivedFailure)
from scripts.formation_study_a_gate3 import verify_freeze

PLAN = ROOT / 'studies/formation-study-a-gemma31-continuation-plan-v0223.json'
APPROVAL_TEXT = ('Approve Gemma’s 237 untouched Study A episodes and one fresh replacement '
                 'for P_R02 repeat 1 at $0, under the reviewed five-attempt transport retry policy; '
                 'retain all original evidence and score the first received reply.')


def review_source(plan_path=PLAN, root=ROOT, execution=False):
    plan = read(plan_path)
    if str(root.resolve()) != plan['checkout_root'] or verify_freeze() != 59:
        raise ValueError('original checkout/freeze required')
    source = root / plan['output']
    for p, digest in plan['adapter_sha256'].items():
        if sha(root / p) != digest:
            raise ValueError('pinned adapter/policy differs: ' + p)
    for p, digest in plan['source_sha256'].items():
        if sha(source / p) != digest:
            raise ValueError('original source evidence differs: ' + p)
    for p, digest in plan['other_ledger_sha256'].items():
        if sha(root / p) != digest:
            raise ValueError('protected ledger/quota differs: ' + p)
    ledger = root / 'results/formation-spending-v021/google.json'
    if read(ledger)['estimated_api_dollars'] != plan['Google_cumulative_dollars']:
        raise ValueError('Google cumulative amount differs; never reset')
    if not (source / 'continuation-manifest.json').exists() and sha(ledger) != plan['Google_ledger_start_sha256']:
        raise ValueError('Google starting ledger bytes differ')
    original = read(root / 'studies/formation-study-a-gemma31-plan-v0222.json')
    summary = read(source / 'progress-summary.json')
    if summary['completed_cells'] != 3 or summary['records'] != plan['retained_records'] or \
            plan['pending_cells'] != original['cells'][3:] or len(plan['pending_cells']) != 237:
        raise ValueError('retained prefix or untouched suffix differs')
    if read(source / 'controller-status.json')['state'] != 'stopped_for_review':
        raise ValueError('source controller must stay stopped')
    pid = read(source / 'controller-status.json')['pid']
    if root == ROOT:
        stat = Path('/proc') / str(pid) / 'stat'
        if stat.exists() and stat.read_text().split(') ')[1].split()[0] != 'Z':
            raise ValueError('original controller still active; no duplicate')
    events = [json.loads(l) for l in (source / 'calls.jsonl').read_text().splitlines()]
    starts = [e['id'] for e in events if e['event'] == 'attempt_start']
    ends = [e for e in events if e['event'] == 'attempt_end']
    if len(starts) != 9 or len(set(starts)) != 9 or set(starts) != {e['id'] for e in ends} or len(ends) != 9:
        raise ValueError('source attempt closure differs')
    for e in ends:
        if e['id'] == 'A000009':
            if e.get('status') != 503 or e.get('error') != 'HTTP 503' or not e['reserve_retained']:
                raise ValueError('retained original failure differs')
        elif e.get('error') or e.get('model_returned') != MODEL or e.get('usage_missing') or e.get('estimated_charge_dollars') != 0:
            raise ValueError('source identity/usage differs')
    for cell in original['cells'][:3]:
        state = read(source / (name(cell) + '-checkpoint.json'))
        case = load_cases([root / cell['path']])[0]
        if state['phase'] != 'complete' or read(source / (name(cell) + '.json')) != state['result'] or \
                replay_episode(case, state['packets'])['score'] != state['result']['score']:
            raise ValueError('retained result/replay differs')
    if (root / 'results/formation-spending-v021/run.lock').exists():
        raise ValueError('shared run lock exists; never clear automatically')
    if execution:
        receipt = root / plan['execution_approval_path']
        if not receipt.exists():
            raise ValueError('separate execution approval absent; offline preparation is not execution approval')
        approval = read(receipt)
        if approval.get('approval') != APPROVAL_TEXT or approval.get('plan_sha256') != sha(plan_path):
            raise ValueError('execution approval does not bind exact continuation plan')
    return plan


class RetryQuota(GemmaQuota):
    def failure(self, meta, kind):
        self.state.setdefault('transport_failure_evidence', []).append(dict(meta, kind=kind, at=self.now()))
        if meta['status'] == 429:
            self.state['rate_errors'] += 1
            self.state['consecutive_rate_errors'] += 1
        if meta['reset_seconds'] is not None:
            self.state['paused_until'] = max(self.state['paused_until'], self.now() + meta['reset_seconds'])
        self.save()  # New retry limits supersede old 4-rate/2-consecutive stops.


class RetryGemmaChat(GemmaChat):
    def __init__(self, recorder, quota, retry, hold=None):
        super().__init__(recorder, quota)
        self.retry = retry
        self.last_transport_lost = False
        self.hold = Path(hold) if hold else None

    def reserve(self, kind, tokens=0):
        if self.hold and self.hold.exists():
            self.quota.ready_at = self.quota.now() + 30
            raise RatePaused('owned maintenance boundary; no HTTP issued')
        return self.quota.reserve(kind, tokens)

    def native_send(self, url, body, received):
        request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=self.headers(self._key()))
        chunks = []
        with urllib.request.urlopen(request, timeout=120) as response:
            while True:
                try:
                    chunk = response.read1(65536) if hasattr(response, 'read1') else response.read(65536)
                except Exception as error:
                    partial = getattr(error, 'partial', b'')
                    if partial:
                        received()
                        chunks.append(partial)
                    if chunks:
                        self.recorder._write({'event': 'partial_native_response',
                            'logical_id': self.recorder.logical_id,
                            'raw_utf8': b''.join(chunks).decode('utf-8', errors='replace')})
                    raise
                if not chunk:
                    break
                received()  # BEFORE native JSON decoding or reply-quality checks.
                chunks.append(chunk)
                if sum(map(len, chunks)) > 2 * 1024 * 1024:
                    raise ReplyReceivedFailure('native response size guard')
            raw = b''.join(chunks)
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                self.recorder._write({'event': 'malformed_native_response',
                    'logical_id': self.recorder.logical_id, 'raw_utf8': raw.decode('utf-8', errors='replace')})
                raise ReplyReceivedFailure('received native bytes cannot be decoded') from None
            return data

    def count(self, body):
        self.quota.guard()
        digest = body_hash(body)
        if digest in self.quota.counts:
            return self.quota.counts[digest]
        job = 'countTokens:' + digest
        def begin():
            token = self.reserve('countTokens')
            self.quota.state['metadata_inflight'] = job
            self.quota.save()
            append(self.quota.receipts, {'event': 'count_start', 'body_sha256': digest, 'attempt_index': token})
            return token
        def failed(token, meta, output, reply):
            append(self.quota.receipts, dict(event='count_error', body_sha256=digest,
                model_reply_received=output, estimated_dollars=0, outcome_uncertain=meta['status'] is None, **meta))
            self.quota.state['metadata_inflight'] = None
            self.quota.failure(meta, 'countTokens')
        data = self.retry.execute(job, body, begin,
            lambda received: self.native_send(BASE + ':countTokens', {
                'generateContentRequest': dict(body, model='models/' + MODEL)}, received),
            failed, quota_ready=lambda: max(self.quota.ready_at, self.quota.state['paused_until']))
        count = data.get('totalTokens')
        if type(count) is not int or count < 1:
            raise BudgetStopped('received count response lacks valid token count; no resend')
        append(self.quota.receipts, {'event': 'count_complete', 'body_sha256': digest, 'totalTokens': count})
        self.quota.state['metadata_inflight'] = None
        self.quota.save()
        self.quota.counts[digest] = count
        return count

    def chat(self, system, messages):
        self.last_transport_lost = False
        if not isinstance(system, str) or not messages or messages[-1].get('role') != 'user' or any(
                m.get('role') not in ('user', 'assistant') or not isinstance(m.get('content'), str) for m in messages):
            raise ValueError('valid full history ending with user required')
        self._key()
        body = self.body(system, messages)
        if len(json.dumps(body).encode()) > 32000:
            raise BudgetStopped('frozen byte ceiling exceeded')
        try:
            count = self.count(body)
        except RatePaused:
            raise
        except (RetryExhausted, RetryRunLimit, ReplyReceivedFailure, urllib.error.HTTPError):
            raise BudgetStopped('metadata transport/protocol stop; no new model request') from None
        if count + 2048 + 128 > 16000:
            raise BudgetStopped('combined token guard exceeded; never trim')
        job = 'generation:' + json.dumps(self.recorder.context, sort_keys=True)
        logical_started = [False]
        def begin():
            self.reserve('generation', count + 128)
            if not logical_started[0]:
                self.recorder.logical(json.dumps({'system': system, 'messages': messages}), 'formation chat')
                self.calls += 1
                logical_started[0] = True
            aid = self.recorder.before_attempt(body)
            self.recorder._write({'event': 'token_preflight', 'id': aid,
                'counted_prompt_tokens': count, 'body_sha256': body_hash(body),
                'framing_buffer': 128, 'completion_allowance': 2048})
            return aid
        def failed(aid, meta, output, reply):
            if reply is not None:
                self.recorder._write({'event': 'native_reply_on_error_status', 'id': aid, 'response': reply})
            self.recorder._write({'event': 'transport_failure', 'id': aid,
                'model_reply_received': output, 'outcome_uncertain': meta['status'] is None, **meta})
            self.recorder.finish_attempt(aid, error='HTTP %s' % meta['status'] if meta['status'] else meta['error_class'], status=meta['status'])
            self.quota.failure(meta, 'generation')
            self.last_transport_lost = not output
        try:
            response = self.retry.execute(job, body, begin,
                lambda received: self.native_send(BASE + ':generateContent', body, received),
                failed, quota_ready=lambda: max(self.quota.ready_at, self.quota.state['paused_until']))
        except RatePaused:
            raise
        except (RetryExhausted, RetryRunLimit):
            raise ProviderError('transport retry policy exhausted; failure retained') from None
        except BudgetStopped:
            raise
        except Exception:
            raise ProviderError('received/ineligible transport failure retained; no resend') from None
        self.last_transport_lost = False
        events = [json.loads(l) for l in self.recorder.path.read_text().splitlines()]
        aid = next(e['id'] for e in reversed(events) if e['event'] == 'attempt_start')
        self.recorder.finish_native(aid, response, 'google')
        self.quota.success(response['usageMetadata']['promptTokenCount'])
        text, stop = self.extract(response)
        label = ('unfinished_reply' if stop == 'MAX_TOKENS' else
                 'provider_refusal' if stop in ('SAFETY', 'BLOCKLIST', 'PROHIBITED_CONTENT') or self.refused(response) else
                 'silent_reply' if not text.strip() else None)
        if label:
            self.recorder.raw_reply(text, error=label)
            raise ReplyError(label)
        try:
            parsed = parse_first_json(text)
        except ValueError:
            self.recorder.raw_reply(text, error='malformed_reply')
            raise ReplyError('malformed_reply') from None
        self.recorder.raw_reply(text, parsed=parsed)
        return parsed


def run_continuation(plan_path=PLAN, approved=False, root=ROOT, now=time.time, sleep=time.sleep):
    if not approved:
        raise ValueError('separate execution approval required; no model calls')
    plan = review_source(plan_path, root, execution=True)
    output = root / plan['output']
    status_path = output / 'continuation-controller-status.json'
    if status_path.exists() and read(status_path)['state'] in ('stopped_for_review', 'running'):
        raise BudgetStopped('review stop or uncertain interrupted run; no automatic restart')
    manifest = output / 'continuation-manifest.json'
    expected = {'plan_sha256': sha(plan_path), 'plan': plan}
    if manifest.exists() and read(manifest) != expected:
        raise ValueError('continuation manifest differs')
    lock = root / 'results/formation-spending-v021/run.lock'
    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, str(os.getpid()).encode())
        if not manifest.exists():
            atomic(manifest, expected)
        quota_path = output / 'continuation-quota.json'
        if not quota_path.exists():
            atomic(quota_path, read(output / 'gemma-quota.json'))
        quota = RetryQuota(quota_path, output / 'continuation-token-counts.jsonl', now=now)
        quota.guard()
        journal = output / 'continuation-calls.jsonl'
        if journal.exists():
            events = [json.loads(l) for l in journal.read_text().splitlines()]
            starts = [e['id'] for e in events if e['event'] == 'attempt_start']
            ends = [e for e in events if e['event'] == 'attempt_end']
            if len(starts) != len(set(starts)) or set(starts) != {e['id'] for e in ends} or len(starts) != len(ends):
                raise BudgetStopped('unclosed continuation attempt')
        ledger = root / 'results/formation-spending-v021/google.json'
        rec = GemmaRecorder(journal, PRICES, MODEL, max_logical=5700, max_attempts=5740,
                            max_dollars=8, prior_spend=read(ledger)['estimated_api_dollars'], ledger_path=ledger)
        def status(state, **fields):
            atomic(status_path, dict(state=state, pid=os.getpid(), at=now(), **fields))
        retry = RetryTransport(output / 'continuation-retry-state.json',
            output / 'continuation-transport-attempts.jsonl', now=now, sleep=sleep,
            waiting=lambda reason, ready: status(reason, next_allowed_epoch=ready))
        client = RetryGemmaChat(rec, quota, retry, plan.get('maintenance_hold'))
        rows, replacements = [], list(plan['initial_replacements'])
        cases = {c['id']: c for c in load_cases([root / p for p in {
            c['path'] for c in plan['pending_cells'] + replacements}])}
        def summary(state):
            data = {'status': state, 'planned_untouched_cells': 237,
                'completed_untouched_cells': sum(not r['replacement'] for r in rows),
                'replacement_completed_cells': sum(r['replacement'] for r in rows),
                'records': rows, 'retained_original_records': plan['retained_records'],
                'pending_replacements': replacements, 'accounting': rec.snapshot(),
                'requests_needing_retry': retry.state['requests_needing_retry'],
                'Gemma_estimated_dollars': 0, 'Google_cumulative_dollars': read(ledger)['estimated_api_dollars']}
            atomic(output / 'continuation-progress-summary.json', data)
            return data
        index = 0
        while index < len(plan['pending_cells']) + len(replacements):
            cell = dict(plan['pending_cells'][index], replacement=False) if index < len(plan['pending_cells']) else \
                dict(replacements[index - len(plan['pending_cells'])], replacement=True)
            checkpoint = output / ('continuation-' + name(cell) + '-checkpoint.json')
            if checkpoint.exists() and read(checkpoint)['phase'] not in ('paused', 'complete'):
                raise BudgetStopped('guard/inflight continuation checkpoint')
            while True:
                if read(ledger)['estimated_api_dollars'] != plan['Google_cumulative_dollars']:
                    raise BudgetStopped('Google ledger changed; preserve accounting')
                status('running', cell=name(cell))
                result, state = execute_cell(cell, cases[cell['case_id']], client, rec, checkpoint)
                if result is None:
                    if state != 'paused':
                        raise BudgetStopped('pre-request guard or retry limit; no further requests')
                    summary('paused')
                    ready = max(quota.ready_at, quota.state['paused_until'])
                    status('waiting_pre_request_quota', next_allowed_epoch=ready)
                    retry.wait_until(max(now() + .01, ready), 'waiting_pre_request_quota')
                    continue
                transport_lost = client.last_transport_lost if result['fatal_transport'] else False
                if checkpoint.exists() and 'transport_lost' in read(checkpoint).get('result', {}):
                    transport_lost = read(checkpoint)['result']['transport_lost']
                result.update(replacement=cell['replacement'], transport_lost=transport_lost,
                              replacement_of=name(dict(cell, replacement=False)) if cell['replacement'] else None)
                saved = output / ('continuation-' + name(cell) + '.json')
                if saved.exists() and read(saved) != result:
                    raise BudgetStopped('completed continuation result differs')
                if not saved.exists():
                    atomic(saved, result)
                    atomic(checkpoint, {'phase': 'complete', 'packets': read(checkpoint)['packets'], 'result': result})
                rows.append(dict(cell, outcome=result['score']['outcome'], identity_valid=result['identity_valid'],
                                 transport_lost=transport_lost, status='complete'))
                if transport_lost and not cell['replacement']:
                    replacements.append(cell)
                summary('running')
                if retry.state['stop']:
                    raise BudgetStopped('transport stop: ' + retry.state['stop'])
                if result['fatal_transport'] and not transport_lost:
                    raise BudgetStopped('received native identity/usage/protocol guard; never resend')
                break
            index += 1
        final = summary('complete')
        status('complete', untouched_completed=237, replacements_completed=final['replacement_completed_cells'])
        return final
    except Exception as error:
        if 'summary' in locals():
            summary('stopped_for_review')
        atomic(status_path, {'state': 'stopped_for_review', 'pid': os.getpid(),
                            'reason': str(error) if isinstance(error, BudgetStopped) else type(error).__name__})
        raise
    finally:
        inode = os.fstat(fd)
        os.close(fd)
        if lock.exists() and lock.stat().st_ino == inode.st_ino:
            lock.unlink()
