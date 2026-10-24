"""Native Responses function calls, fail-closed approval and paid-attempt guards.

No SDK retries, metadata probes, key-file reads, sampling/effort overrides or
quality retries. All uncertainty retains the full attempt reservation.
"""
import base64
from http.client import IncompleteRead, HTTPException, RemoteDisconnected
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from live_demo import config
from live_demo.evidence import encoded
from live_demo.surface import manifest
from taa_gateway.serialization import parse_json

D = Decimal
WAITS = (10, 30, 60, 120)


class Stop(RuntimeError):
    def __init__(self, reason, episode=None):
        self.reason, self.episode = reason, episode
        super().__init__(reason)


class TransportFailure(Exception):
    def __init__(self, status=None, partial=b'', retry_after=0):
        self.status, self.partial, self.retry_after = status, partial, retry_after


def authorized(launch, approved_commit, approval):
    # Called on EVERY physical attempt, before any key access or networking.
    if not launch or not approved_commit:
        raise Stop('launch_not_approved')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=config.ROOT, text=True).strip()
    # The paid ledger legitimately changes under our exclusive run lock. All
    # tracked source/input changes remain forbidden on every attempt.
    dirty = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--', '.',
        ':!results/formation-spending-v021/openai.json'], cwd=config.ROOT, text=True)
    if dirty or head != approved_commit or len(approved_commit) != 40:
        raise Stop('launch_commit_mismatch')
    if approval != dict(owner='Chris', commit=head, step='live-demo-v01', launch_approved=True):
        raise Stop('launch_not_approved')
    config.verify()


class Budget:
    def __init__(self, ledger, evidence, step_cap='5', provider_cap='8'):
        self.ledger, self.evidence = Path(ledger), evidence
        self.step_cap, self.provider_cap = D(step_cap), D(provider_cap)
        if self.step_cap > 5 or self.provider_cap > 8:
            raise ValueError('caps cannot be increased by this harness')
        self.spent = D('0')
        self.attempts, self.input_tokens, self.output_tokens = 0, 0, 0
        self.prices = config.load('prices.json')

    def _read(self):
        row = json.loads(self.ledger.read_text(), parse_float=D)
        amount = D(str(row['estimated_api_dollars']))
        if not amount.is_finite() or amount < 0:
            raise Stop('invalid_ledger')
        return amount

    def _book(self, delta):
        row = json.loads(self.ledger.read_text())
        prior = self._read()
        row['estimated_api_dollars'] = float(prior+delta)
        row['model'] = config.MODEL
        row['updated_at'] = time.time()
        # Caller holds the existing global formation run.lock throughout.
        # Journal precedes replacement; an interrupted write is a review stop.
        self.evidence.write('ledger_change', dict(prior=str(prior), delta=str(delta), after=str(prior+delta)))
        temporary = self.ledger.with_name(self.ledger.name+'.live-demo-pending')
        with temporary.open('xb') as stream:
            stream.write(encoded(row)+b'\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, self.ledger)

    def reserve(self, body):
        # Byte upper bound for all serialized input, tools and framing, with a
        # fixed 16K token allowance. Never omit tool schemas or prior output.
        prompt_bound = len(encoded(body))+16384
        if prompt_bound+config.OUTPUT_TOKENS > self.prices['long_context_threshold']:
            raise Stop('prompt_size')
        maximum_input = max(D(str(self.prices[k])) for k in
                            ('input_per_million', 'cached_input_per_million', 'cache_write_per_million'))
        reserve = (D(prompt_bound)*maximum_input + D(config.OUTPUT_TOKENS)*D(str(self.prices['output_per_million'])))/1000000
        if self.spent+reserve > self.step_cap or self._read()+reserve > self.provider_cap:
            self.evidence.write('cap_stop', dict(step=str(self.spent), provider=str(self._read()), reserve=str(reserve)))
            raise Stop('cap_stop')
        self.evidence.write('reservation', dict(prompt_bound=prompt_bound, dollars=str(reserve)))
        self._book(reserve)
        self.spent += reserve
        self.attempts += 1
        return reserve, prompt_bound

    def settle(self, reservation, prompt_bound, reply):
        if reply.get('model') != config.MODEL:
            raise Stop('model_identity')
        u = reply.get('usage')
        if type(u) is not dict or any(type(u.get(k)) is not int or u[k] < 0
                for k in ('input_tokens', 'output_tokens', 'total_tokens')):
            raise Stop('missing_usage')
        details = u.get('input_tokens_details', {})
        if type(details) is not dict:
            raise Stop('missing_usage')
        cached = details.get('cached_tokens', 0)
        if (type(cached) is not int or not 0 <= cached <= u['input_tokens'] or
                u['total_tokens'] != u['input_tokens']+u['output_tokens'] or
                u['input_tokens'] > prompt_bound or u['output_tokens'] > config.OUTPUT_TOKENS):
            raise Stop('usage_bound')
        actual = (D(u['input_tokens']-cached)*D(str(self.prices['input_per_million'])) +
                  D(cached)*D(str(self.prices['cached_input_per_million'])) +
                  D(u['output_tokens'])*D(str(self.prices['output_per_million'])))/1000000
        if actual > reservation:
            raise Stop('usage_bound')
        self.evidence.write('usage', dict(native=u, charged=str(actual), retained_reserve='0'))
        self._book(actual-reservation)
        self.spent += actual-reservation
        self.input_tokens += u['input_tokens']; self.output_tokens += u['output_tokens']


def retry_delay(value):
    try:
        return max(0, float(value))
    except (ValueError, TypeError):
        try:
            return max(0, (parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return 0


def http(body):
    key = os.environ.get('TAA_OPENAI_API_KEY')
    if not key:
        raise Stop('missing_configured_key')
    request = urllib.request.Request('https://api.openai.com/v1/responses', data=encoded(body),
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+key})
    chunks = []
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            while True:
                chunk = response.read1(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                if sum(map(len, chunks)) > 16*1024*1024:
                    raise TransportFailure(partial=b''.join(chunks))
    except urllib.error.HTTPError as error:
        # Error body is deliberately not echoed; no model reply was read.
        raise TransportFailure(error.code, retry_after=retry_delay(error.headers.get('Retry-After'))) from None
    except IncompleteRead as error:
        raise TransportFailure(partial=b''.join(chunks)+error.partial) from None
    except RemoteDisconnected:
        raise TransportFailure(partial=b''.join(chunks)) from None
    except HTTPException:
        # An HTTP protocol failure with no retained body is outcome-unknown;
        # do not silently retry it as a clean connection reset.
        raise Stop('unknown_output') from None
    except (TimeoutError, ConnectionResetError):
        raise TransportFailure(partial=b''.join(chunks)) from None
    except urllib.error.URLError as error:
        if isinstance(error.reason, (TimeoutError, ConnectionResetError)):
            raise TransportFailure(partial=b''.join(chunks)) from None
        raise Stop('transport_not_retryable') from None
    except OSError:
        raise Stop('transport_not_retryable') from None
    return b''.join(chunks)


class Adapter:
    def __init__(self, budget, evidence, *, launch=False, approved_commit=None, approval=None,
                 transport=None, sleeper=time.sleep):
        self.budget, self.evidence = budget, evidence
        self.launch, self.approved_commit, self.approval = launch, approved_commit, approval
        self.transport, self.sleeper = transport or http, sleeper
        self.retry_needed = 0

    def _authorize(self):
        authorized(self.launch, self.approved_commit, self.approval)

    def cost(self):
        return dict(dollars=str(self.budget.spent), attempts=self.budget.attempts,
                    input_tokens=self.budget.input_tokens, output_tokens=self.budget.output_tokens)

    def respond(self, history, spec, turn):
        body = dict(model=config.MODEL, instructions=(config.FROZEN/'system.txt').read_text(),
                    input=history, tools=manifest(), max_output_tokens=config.OUTPUT_TOKENS, store=False)
        for attempt in range(1, 6):
            self._authorize()
            reservation, bound = self.budget.reserve(body)
            self.evidence.write('request', dict(spec=spec, turn=turn, attempt=attempt, body=body))
            try:
                raw = self.transport(body)
            except TransportFailure as error:
                self.evidence.write('transport_failure', dict(status=error.status,
                    partial_base64=base64.b64encode(error.partial).decode(), reservation_retained=str(reservation)))
                if error.partial:
                    raise Stop('partial_reply') from None
                if error.status is not None and error.status != 429 and not 500 <= error.status <= 599:
                    raise Stop('transport_not_retryable') from None
                if attempt == 1:
                    self.retry_needed += 1
                if attempt == 5 or self.retry_needed > 10:
                    raise Stop('transport_exhaustion') from None
                wait = max(WAITS[attempt-1], error.retry_after)
                self.evidence.write('retry_wait', dict(seconds=wait, retry_needed=self.retry_needed))
                # Keep progress/interrupt opportunities while honoring long waits.
                remaining = wait
                while remaining > 0:
                    self.sleeper(min(remaining, 30)); remaining -= min(remaining, 30)
                continue
            self.evidence.write('native_reply', dict(base64=base64.b64encode(raw).decode()))
            try:
                reply = parse_json(raw.decode('utf-8'))
            except (ValueError, UnicodeError):
                raise Stop('unknown_output') from None
            if type(reply) is not dict:
                raise Stop('unknown_output')
            self.budget.settle(reservation, bound, reply)
            if reply.get('status') != 'completed' or type(reply.get('output')) is not list or not reply['output']:
                raise Stop('unknown_output')
            seen = set()
            for item in reply['output']:
                if type(item) is not dict or item.get('type') not in ('function_call', 'message', 'reasoning'):
                    raise Stop('unknown_output')
                if item['type'] == 'function_call':
                    if (any(type(item.get(k)) is not str for k in ('call_id', 'name', 'arguments')) or
                            item['call_id'] in seen):
                        raise Stop('unknown_output')
                    seen.add(item['call_id'])
            return reply
        raise AssertionError('unreachable')
