"""Prospectively approved Gemma transport and quota policy; frozen science unchanged."""
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path

from agents.call_telemetry import BudgetStopped, CallRecorder
from agents.gemini_client import parse_first_json
from formation.clients import GeminiChat, ProviderError, ReplyError
from formation.evaluation_runner_v0218 import atomic, execute_cell
from formation.evaluation_transport_v0218 import EvaluationRecorder
from formation.limits import RatePaused
from formation.study_a import ROOT, load_cases, replay_episode
from scripts.formation_study_a_gate3 import verify_freeze

MODEL = 'gemma-4-31b-it'
BASE = 'https://generativelanguage.googleapis.com/v1beta/models/' + MODEL
PLAN_PATH = ROOT / 'studies/formation-study-a-gemma31-plan-v0222.json'
APPROVAL_PATH = ROOT / 'studies/formation-study-a-gemma31-approval-2026-10-11.json'
OUTPUT = ROOT / 'results/2026-10-11 v0.22.2 gemma31-none r10 study-a evaluation'
PRICES = {MODEL: {'provider': 'google', 'input_per_million': 0, 'output_per_million': 0}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def body_hash(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def append(path, event):
    with Path(path).open('a') as stream:
        stream.write(json.dumps(event, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def reset_seconds(headers, details, now):
    """Only explicit server reset information. Never retain the raw error body."""
    values = []
    retry = headers.get('retry-after')
    if retry is not None:
        try:
            values.append(float(retry))
        except (ValueError, TypeError):
            try:
                values.append(parsedate_to_datetime(retry).timestamp() - now)
            except (ValueError, TypeError, OverflowError):
                pass
    for key, value in headers.items():
        if key.startswith('x-ratelimit-reset-'):
            parts = re.findall(r'([0-9.]+)(ms|s|m|h|d)', str(value))
            if parts:
                factors = {'ms': .001, 's': 1, 'm': 60, 'h': 3600, 'd': 86400}
                values.append(sum(float(n) * factors[u] for n, u in parts))
    for detail in details:
        if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
            delay = detail.get('retryDelay', '')
            if re.fullmatch(r'\d+(\.\d+)?s', str(delay)):
                values.append(float(delay[:-1]))
    values = [v for v in values if math.isfinite(v) and v >= 0]
    return max(values) if values else None


def safe_headers(headers):
    return {k.lower(): v for k, v in headers.items()
            if k.lower() == 'retry-after' or k.lower().startswith('x-ratelimit-')}


class GemmaQuota:
    """Persistent sliding-window reservations; retain every event and count receipt."""
    def __init__(self, path, receipts, now=time.time):
        self.path, self.receipts, self.now = Path(path), Path(receipts), now
        self.state = read(path) if self.path.exists() else {
            'events': [], 'rate_errors': 0, 'consecutive_rate_errors': 0,
            'paused_until': 0, 'stopped_for_review': False, 'metadata_inflight': None}
        self.last_generation = None
        self.counts = {}
        if self.receipts.exists():
            for line in self.receipts.read_text().splitlines():
                e = json.loads(line)
                if e['event'] == 'count_complete':
                    self.counts[e['body_sha256']] = e['totalTokens']
        self.ready_at = self.now()

    def save(self):
        atomic(self.path, self.state)

    def guard(self):
        if self.state['stopped_for_review'] or self.state['metadata_inflight']:
            raise BudgetStopped('Gemma quota guard or unclosed metadata request; review required')

    def reserve(self, kind, tokens=0):
        self.guard()
        now = self.now()
        if tokens > 14400:
            raise BudgetStopped('request exceeds Gemma input pacing allowance')
        events = self.state['events']
        ready = max(now, self.state['paused_until'])
        minute = [e for e in events if now - e['at'] < 61]
        day = [e for e in events if now - e['at'] < 86400]
        if len(minute) >= 24:
            ready = max(ready, minute[-24]['at'] + 61)
        if len(day) >= 12960:
            ready = max(ready, day[-12960]['at'] + 86400)
        used = sum(e['tokens'] for e in minute)
        for e in minute:
            if used + tokens <= 14400:
                break
            ready = max(ready, e['at'] + 61)
            used -= e['tokens']
        self.ready_at = ready
        if ready > now:
            raise RatePaused('pre-request Gemma quota reservation pending')
        event = {'at': now, 'kind': kind, 'tokens': tokens, 'index': len(events)}
        events.append(event)
        self.save()
        if kind == 'generation':
            self.last_generation = event['index']
        return event['index']

    def reject(self, headers, details, kind):
        seconds = reset_seconds(headers, details, self.now())
        self.state['rate_errors'] += 1
        self.state['consecutive_rate_errors'] += 1
        evidence = {'kind': kind, 'at': self.now(), 'reset_seconds': seconds}
        self.state.setdefault('rate_error_evidence', []).append(evidence)
        safety = self.state['rate_errors'] > 3 or self.state['consecutive_rate_errors'] >= 2
        if safety or seconds is None:
            self.state['stopped_for_review'] = True
        else:
            self.state['paused_until'] = max(self.state['paused_until'], self.now() + seconds)
        self.save()

    def success(self, prompt_tokens):
        event = self.state['events'][self.last_generation]
        if prompt_tokens > event['tokens']:
            self.state['stopped_for_review'] = True
            self.save()
            raise BudgetStopped('native prompt usage exceeds exact-count reservation; inspect tokenizer')
        # Retain framing safety reserve; never discount cached prompt tokens.
        self.state['consecutive_rate_errors'] = 0
        self.save()


class GemmaRecorder(EvaluationRecorder):
    def finish_native(self, aid, response, provider, status=200):
        self._write({'event': 'native_response', 'id': aid, 'response': response})
        u = response.get('usageMetadata') or {}
        names = ('promptTokenCount', 'candidatesTokenCount', 'thoughtsTokenCount', 'totalTokenCount')
        # Google omits a zero final-answer count on thought-only exhausted replies.
        # Preserve native response and flag any derived zero in separate evidence.
        normalized = response
        if 'candidatesTokenCount' not in u:
            final = any(p.get('text') and not p.get('thought')
                        for c in response.get('candidates', [])
                        for p in c.get('content', {}).get('parts', []))
            needed = ('promptTokenCount', 'thoughtsTokenCount', 'totalTokenCount')
            if not final and all(type(u.get(k)) is int and u[k] >= 0 for k in needed) and \
                    u['totalTokenCount'] == u['promptTokenCount'] + u['thoughtsTokenCount']:
                self._write({'event': 'derived_zero_final_tokens', 'id': aid,
                             'basis': 'no final parts; total equals prompt plus thought; native field absent'})
                normalized = dict(response, usageMetadata=dict(u, candidatesTokenCount=0))
                u = normalized['usageMetadata']
        valid = all(type(u.get(k, 0)) is int and u.get(k, 0) >= 0 for k in names)
        valid = valid and 'promptTokenCount' in u and 'candidatesTokenCount' in u and \
            'totalTokenCount' in u and u['totalTokenCount'] == \
            u['promptTokenCount'] + u['candidatesTokenCount'] + u.get('thoughtsTokenCount', 0)
        if not valid:
            self.finish_attempt(aid, error='invalid_native_usage', status=status)
            self.missing_usage = True
            raise BudgetStopped('invalid Gemma native usage; review required')
        usage = {'prompt_tokens': u['promptTokenCount'],
                 'completion_tokens': u['candidatesTokenCount'] + u.get('thoughtsTokenCount', 0),
                 'prompt_tokens_details': {'cached_tokens': u.get('cachedContentTokenCount', 0)}}
        if type(usage['prompt_tokens_details']['cached_tokens']) is not int or not \
                0 <= usage['prompt_tokens_details']['cached_tokens'] <= usage['prompt_tokens']:
            self.finish_attempt(aid, error='invalid_native_cache_usage', status=status)
            raise BudgetStopped('invalid Gemma cache usage')
        returned = response.get('modelVersion')
        normalized = {'usage': usage, 'model': returned, 'id': response.get('responseId'),
                      'stop_reason': ((response.get('candidates') or [{}])[0]).get('finishReason')}
        CallRecorder.finish_attempt(self, aid, response=normalized, status=status)
        if returned != MODEL:
            self._write({'event': 'identity_missing', 'id': aid})
            self.missing_usage = True
            raise BudgetStopped('missing Gemma pinned model identity')
        self.last_identity_valid = True
        if u['candidatesTokenCount'] + u.get('thoughtsTokenCount', 0) > 2048:
            raise BudgetStopped('native completion exceeds frozen 2048 ceiling')


class GemmaChat(GeminiChat):
    def __init__(self, recorder, quota):
        super().__init__(MODEL, recorder, max_output_tokens=2048)
        self.quota = quota
        self.last_issued_429 = False

    def transport(self, url, body):
        request = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers=self.headers(self._key()))
        with urllib.request.urlopen(request, timeout=120) as reply:
            return json.loads(reply.read()), safe_headers(reply.headers)

    def rejection(self, error, kind):
        headers = safe_headers(error.headers or {})
        details = []
        try:
            data = json.loads(error.read(65536))
            details = [d for d in data.get('error', {}).get('details', [])
                       if isinstance(d, dict) and d.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo']
        except Exception:
            pass
        self.quota.reject(headers, details, kind)

    def count(self, body):
        self.quota.guard()
        digest = body_hash(body)
        if digest in self.quota.counts:
            return self.quota.counts[digest]
        self.quota.reserve('countTokens')
        self.quota.state['metadata_inflight'] = digest
        self.quota.save()
        append(self.quota.receipts, {'event': 'count_start', 'body_sha256': digest,
                                    'model': MODEL, 'at': self.quota.now()})
        try:
            data, headers = self.transport(BASE + ':countTokens', {
                'generateContentRequest': dict(body, model='models/' + MODEL)})
        except urllib.error.HTTPError as error:
            append(self.quota.receipts, {'event': 'count_error', 'body_sha256': digest,
                                        'status': error.code})
            self.quota.state['metadata_inflight'] = None
            self.quota.save()
            if error.code == 429:
                self.rejection(error, 'countTokens')
                if self.quota.state['stopped_for_review']:
                    raise BudgetStopped('Gemma metadata rate safety/reset guard') from None
                raise RatePaused('countTokens rate rejected before generation; wait reported reset') from None
            raise BudgetStopped('countTokens HTTP error; no generation issued') from None
        except Exception:
            # Unclosed metadata is persisted; never automatically repeat it.
            raise BudgetStopped('uncertain countTokens request; review required') from None
        count = data.get('totalTokens')
        if type(count) is not int or count < 1:
            raise BudgetStopped('countTokens response lacks valid token count')
        append(self.quota.receipts, {'event': 'count_complete', 'body_sha256': digest,
                                    'totalTokens': count, 'model': MODEL})
        self.quota.state['metadata_inflight'] = None
        self.quota.save()
        self.quota.counts[digest] = count
        return count

    def chat(self, system, messages):
        self.last_issued_429 = False
        if not isinstance(system, str) or not messages or messages[-1].get('role') != 'user':
            raise ValueError('full history ending with user required')
        self._key()  # Availability check only; never expose the configured value.
        body = self.body(system, messages)
        if len(json.dumps(body).encode()) > 32000:
            raise BudgetStopped('frozen 32000-byte request ceiling exceeded')
        count = self.count(body)
        if count + 2048 + 128 > 16000:
            raise BudgetStopped('Gemma request exceeds 16000 combined-token guard; no trimming')
        self.quota.reserve('generation', count + 128)
        self.recorder.logical(json.dumps({'system': system, 'messages': messages}), 'formation chat')
        self.calls += 1
        aid = self.recorder.before_attempt(body)
        self.recorder._write({'event': 'token_preflight', 'id': aid, 'body_sha256': body_hash(body),
                              'counted_prompt_tokens': count, 'framing_buffer': 128,
                              'completion_allowance': 2048})
        try:
            response, headers = self.transport(BASE + ':generateContent', body)
        except urllib.error.HTTPError as error:
            self.recorder._write({'event': 'response_headers', 'id': aid,
                                  'headers': safe_headers(error.headers or {})})
            self.recorder.finish_attempt(aid, error='HTTP %s' % error.code, status=error.code)
            if error.code == 429:
                self.last_issued_429 = True
                self.rejection(error, 'generation')
                raise RatePaused('issued HTTP 429 retained; no retry') from None
            raise ProviderError('HTTP error; no retry') from None
        except Exception as error:
            self.recorder.finish_attempt(aid, error=type(error).__name__)
            raise ProviderError('uncertain generation; no retry; review required') from None
        self.recorder._write({'event': 'response_headers', 'id': aid, 'headers': headers})
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


def check_plan(plan, root=ROOT):
    if str(root.resolve()) != plan['checkout_root']:
        raise ValueError('original checkout root required')
    if verify_freeze() != 59:
        raise ValueError('freeze count differs')
    for p, digest in plan['sha256'].items():
        if sha(root / p) != digest:
            raise ValueError('pinned file changed: ' + p)
    approval = read(root / plan['approval_path'])
    if approval['plan_sha256'] != sha(root / plan['plan_path']) or not approval['approved']:
        raise ValueError('hash-bound written approval required')


def name(cell):
    return '%s-r%02d%s' % (cell['case_id'], cell['repeat'], '-replacement-01' if cell.get('replacement') else '')


def journal_guard(path):
    if not path.exists():
        return
    events = [json.loads(line) for line in path.read_text().splitlines()]
    starts = [e['id'] for e in events if e['event'] == 'attempt_start']
    ends = [e for e in events if e['event'] == 'attempt_end']
    if len(set(starts)) != len(starts) or set(starts) != {e['id'] for e in ends} or len(starts) != len(ends):
        raise BudgetStopped('unclosed/duplicate generation journal; review required')
    for e in ends:
        if e.get('status') == 429 and e.get('error') == 'HTTP 429':
            continue  # Prospectively approved retained failures, not retryable requests.
        if e.get('error') or e.get('usage_missing') or e.get('model_mismatch') or e.get('model_returned') != MODEL or \
                e.get('estimated_charge_dollars') != 0:
            raise BudgetStopped('prior generation identity/usage/transport failure; review required')


def run(plan, output, root=ROOT, now=time.time, sleep=time.sleep):
    """One owner-approved run; waits occur only at fully checkpointed boundaries."""
    check_plan(plan, root)
    output = Path(output)
    if output.resolve() != (root / plan['output']).resolve():
        raise ValueError('original output required')
    output.mkdir(exist_ok=True)
    status_path = output / 'controller-status.json'
    if status_path.exists() and read(status_path)['state'] == 'stopped_for_review':
        raise BudgetStopped('previous review stop; no automatic restart')
    manifest = output / 'execution-manifest.json'
    expected = {'plan_sha256': sha(root / plan['plan_path']), 'plan': plan}
    if manifest.exists():
        if read(manifest) != expected:
            raise ValueError('resume manifest differs')
    else:
        atomic(manifest, expected)
    lock = root / 'results/formation-spending-v021/run.lock'
    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode())
    try:
        ledger = root / 'results/formation-spending-v021/google.json'
        prior = read(ledger)['estimated_api_dollars']
        if prior != plan['google_prior_dollars'] or prior >= 8:
            raise BudgetStopped('Google ledger amount differs; no reset')
        journal = output / 'calls.jsonl'
        journal_guard(journal)
        for p in output.glob('*-checkpoint.json'):
            state = read(p)
            if state['phase'] not in ('paused', 'complete'):
                raise BudgetStopped('guard/inflight/ready checkpoint; review required')
        quota = GemmaQuota(output / 'gemma-quota.json', output / 'token-counts.jsonl', now=now)
        quota.guard()
        recorder = GemmaRecorder(journal, PRICES, MODEL, max_logical=2916, max_attempts=2916,
                                 max_dollars=8, prior_spend=prior, ledger_path=ledger)
        client = GemmaChat(recorder, quota)
        primaries, replacements, rows = plan['cells'], [], []
        cases = {c['id']: c for c in load_cases([root / p for p in {c['path'] for c in primaries}])}

        def status(state, **fields):
            atomic(status_path, dict(state=state, pid=os.getpid(), updated_at=now(),
                                    checkout_root=str(root), output=plan['output'], **fields))

        def summary(state):
            data = {'model': MODEL, 'status': state, 'planned_cells': 240,
                    'completed_cells': sum(not r['replacement'] for r in rows),
                    'replacement_completed_cells': sum(r['replacement'] for r in rows),
                    'records': rows, 'rate_errors': quota.state['rate_errors'],
                    'batch_estimated_dollars': 0, 'accounting': recorder.snapshot(),
                    'google_cumulative_dollars': read(ledger)['estimated_api_dollars']}
            atomic(output / 'progress-summary.json', data)
            return data

        for index in range(len(primaries) + 3):
            if index < len(primaries):
                cell = dict(primaries[index], replacement=False)
            else:
                replacement_index = index - len(primaries)
                if replacement_index >= len(replacements):
                    break
                cell = dict(replacements[replacement_index], replacement=True)
            state_path = output / (name(cell) + '-checkpoint.json')
            while True:
                check_plan(plan, root)
                if read(ledger)['estimated_api_dollars'] != prior:
                    raise BudgetStopped('concurrent Google ledger change; review required')
                status('running', cell=name(cell), issued_requests=recorder.attempt_count)
                result, state = execute_cell(cell, cases[cell['case_id']], client, recorder, state_path)
                if result is not None:
                    # For recovery, classify closure from persisted request context, not RAM.
                    events = [json.loads(line) for line in journal.read_text().splitlines()]
                    logicals = {e['id']: e for e in events if e['event'] == 'logical_start'}
                    closed = [e for e in events if e['event'] == 'attempt_end' and
                              logicals[e['logical_id']]['context'].get('case_id') == cell['case_id'] and
                              logicals[e['logical_id']]['context'].get('repeat') == cell['repeat'] and
                              logicals[e['logical_id']]['context'].get('replacement', False) == cell['replacement']]
                    rate_lost = bool(closed and closed[-1].get('status') == 429)
                    result.update(replacement=cell['replacement'], original_slot='%s-r%02d' % (cell['case_id'], cell['repeat']),
                                  rate_lost=rate_lost, replacement_of=name(dict(cell, replacement=False)) if cell['replacement'] else None)
                    atomic(output / (name(cell) + '.json'), result)
                    atomic(state_path, {'phase': 'complete', 'packets': read(state_path)['packets'], 'result': result})
                    rows.append(dict(cell, outcome=result['score']['outcome'], identity_valid=result['identity_valid'],
                                     rate_lost=rate_lost, status='complete'))
                    if result['fatal_transport'] and not rate_lost:
                        raise BudgetStopped('issued failure retained; stop for review')
                    if rate_lost:
                        if not cell['replacement']:
                            replacements.append(cell)
                        if quota.state['stopped_for_review']:
                            raise BudgetStopped('Gemma rate-error safety stop or missing server reset')
                    summary('running')
                    break
                if state != 'paused':
                    raise BudgetStopped('Gemma pre-request guard stop; review required')
                summary('paused')
                hold = Path(plan['maintenance_hold'])
                while True:
                    ready = max(quota.ready_at, quota.state['paused_until'])
                    held = hold.exists()
                    status('waiting_pre_request_quota', cell=name(cell), next_allowed_epoch=ready,
                           maintenance_hold=held, issued_requests=recorder.attempt_count)
                    if now() >= ready and not held:
                        break
                    sleep(min(30, max(1, ready - now())))
            # Respect an issued reset before any next primary/replacement/preflight.
            if quota.state['paused_until'] > now():
                summary('paused')
                while now() < quota.state['paused_until'] or Path(plan['maintenance_hold']).exists():
                    status('waiting_pre_request_quota', next_allowed_epoch=quota.state['paused_until'],
                           issued_requests=recorder.attempt_count, after_retained_429=True)
                    sleep(min(30, max(1, quota.state['paused_until'] - now())))
        journal_guard(journal)
        final = summary('complete')
        status('complete', completed_cells=240, issued_requests=recorder.attempt_count,
               replacement_completed_cells=final['replacement_completed_cells'], estimated_dollars=0)
        return final
    except Exception as error:
        if 'summary' in locals():
            summary('stopped_for_review')
        atomic(status_path, {'state': 'stopped_for_review', 'pid': os.getpid(),
                             'updated_at': now(), 'reason': str(error) if isinstance(error, BudgetStopped) else type(error).__name__,
                             'checkout_root': str(root), 'output': plan['output']})
        raise
    finally:
        inode = os.fstat(fd)
        os.close(fd)
        if lock.exists() and lock.stat().st_ino == inode.st_ino:
            lock.unlink()
