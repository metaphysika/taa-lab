"""Provider adapters with per-attempt authorization and v0.22.3 transport."""
import base64
from http.client import HTTPException, IncompleteRead, RemoteDisconnected
import os
import re
import subprocess
import time
import urllib.error
import urllib.request

from live_demo.adapter import Stop, OutputCeiling, TransportFailure, retry_delay, shape, WAITS
from live_demo.evidence import encoded
from taa_gateway.serialization import parse_json
from experiment_a import config, native

RETRYABLE = frozenset((429, 500, 502, 503, 504))
ENDPOINTS = {'anthropic': 'https://api.anthropic.com/v1/messages',
             'google': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent'}


def authorized(provider, launch, commit, approval, *, neutral=False):
    if provider not in config.MODELS or not launch or type(commit) is not str or not re.fullmatch('[0-9a-f]{40}', commit):
        raise Stop('launch_not_approved')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=config.ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=config.ROOT, text=True)
    if head != commit or dirty:
        raise Stop('launch_commit_mismatch')
    if type(approval) is not dict:
        raise Stop('launch_not_approved')
    expected = dict(owner='Chris', commit=commit, step=config.STEP, launch_approved=True)
    if neutral:
        number, returned = approval.get('check_attempt'), approval.get('model_returned')
        if type(number) is not int or number < 1 or not (returned is None or type(returned) is str and returned):
            raise Stop('launch_not_approved')
        expected.update(provider=provider, check_attempt=number, model_returned=returned)
    else:
        returned = approval.get('model_returned')
        if (type(returned) is not dict or set(returned) != set(config.MODELS) or
                any(type(v) is not str or not v for v in returned.values())):
            raise Stop('launch_not_approved')
        expected.update(model_returned=returned)
    if approval != expected or approval.get('launch_approved') is not True:
        raise Stop('launch_not_approved')
    config.verify()
    config.launch_ready(neutral=neutral)


def error_fields(error):
    fields = dict(type=None, code=None, param='withheld')
    types = {'invalid_request_error','authentication_error','permission_error','not_found_error',
             'rate_limit_error','api_error','overloaded_error','INVALID_ARGUMENT','UNAUTHENTICATED',
             'PERMISSION_DENIED','NOT_FOUND','RESOURCE_EXHAUSTED','INTERNAL','UNAVAILABLE'}
    codes = {'invalid_api_key','insufficient_quota',400,401,403,404,408,429,500,502,503,504}
    try:
        payload = parse_json(error.read(65536).decode('utf-8'))
        row = payload.get('error') if type(payload) is dict else None
        if type(row) is dict:
            typ = row.get('type', row.get('status'))
            fields['type'] = typ if type(typ) is str and typ in types else None if typ is None else 'withheld'
            code = row.get('code')
            fields['code'] = code if type(code) in (str, int) and code in codes else None if code is None else 'withheld'
            param = row.get('param')
            if type(param) is str and re.fullmatch(r'[A-Za-z0-9_.\[\]]{1,128}', param):
                fields['param'] = param
    except (ValueError, UnicodeError, OSError, HTTPException):
        pass
    return fields


def http(provider, body):
    key = os.environ.get(config.KEY_VARIABLES[provider])
    if not key:
        raise Stop('missing_configured_key')
    headers = {'Content-Type': 'application/json'}
    if provider == 'anthropic':
        headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
    else:
        headers['x-goog-api-key'] = key
    request = urllib.request.Request(ENDPOINTS[provider], data=encoded(body), headers=headers)
    chunks = []
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            while True:
                chunk = response.read1(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                if sum(map(len, chunks)) > 16*1024*1024:
                    raise TransportFailure(partial=b''.join(chunks))
    except urllib.error.HTTPError as error:
        raise TransportFailure(error.code, retry_after=retry_delay((error.headers or {}).get('Retry-After')),
                               error_fields=error_fields(error)) from None
    except IncompleteRead as error:
        raise TransportFailure(partial=b''.join(chunks)+error.partial) from None
    except (TimeoutError, ConnectionResetError, RemoteDisconnected):
        raise TransportFailure(partial=b''.join(chunks)) from None
    except urllib.error.URLError as error:
        if isinstance(error.reason, (TimeoutError, ConnectionResetError)):
            raise TransportFailure(partial=b''.join(chunks)) from None
        raise Stop('transport_not_retryable') from None
    except (OSError, HTTPException):
        raise Stop('unknown_output') from None
    return b''.join(chunks)


class Adapter:
    def __init__(self, provider, budget, evidence, *, system=None, tools=None, transport=None,
                 launch=False, approved_commit=None, approval=None, neutral=False,
                 sleeper=time.sleep, standin=False, retry_tracker=None):
        self.provider, self.budget, self.evidence = provider, budget, evidence
        self.system = config.system() if system is None else system
        if tools is None:
            from live_demo.surface import manifest
            tools = manifest()
        self.tools, self.transport = tools, transport
        self.launch, self.commit, self.approval = launch, approved_commit, approval
        self.neutral, self.sleeper, self.standin = neutral, sleeper, standin
        self.discovered_model = None
        self.retry_tracker = {'retry_needed': 0} if retry_tracker is None else retry_tracker

    @property
    def retry_needed(self):
        return self.retry_tracker['retry_needed']

    @retry_needed.setter
    def retry_needed(self, value):
        self.retry_tracker['retry_needed'] = value

    def _authorize(self):
        if self.standin:
            from experiment_a.standin import ScriptedTransport
            if type(self.transport) is not ScriptedTransport or self.launch or self.approval or self.commit:
                raise Stop('standin_transport_only')
            config.verify()
        else:
            authorized(self.provider, self.launch, self.commit, self.approval, neutral=self.neutral)
            if self.budget.prices != config.load('prices.json')[self.provider]:
                raise Stop('prices_unverified')
            if self.budget.state is None:
                raise Stop('durable_state_required')
            self.budget.state.before_request(self.provider, self.approval, self.neutral)

    def body(self, history):
        return native.body(self.provider, self.system, self.tools, history)

    def cost(self):
        return dict(dollars=str(self.budget.phase_spent), attempts=self.budget.attempts, **self.budget.tokens)

    def respond(self, history, spec, turn):
        body = self.body(history)
        maximum = 1 if self.neutral else 5
        for attempt in range(1, maximum+1):
            self._authorize()
            reservation, bound = self.budget.reserve(body)
            self.evidence.write('request', dict(provider=self.provider, spec=spec, turn=turn, attempt=attempt, body=body))
            if not self.standin:
                self.budget.state.before_request(self.provider, self.approval, self.neutral)
            try:
                raw = self.transport(body) if self.transport is not None else http(self.provider, body)
            except TransportFailure as error:
                self.evidence.write('transport_failure', dict(status=error.status, error=error.error_fields,
                    partial_base64=base64.b64encode(error.partial).decode(), retained_reserve=str(reservation)))
                if error.partial:
                    raise Stop('partial_reply') from None
                if error.status is not None and error.status not in RETRYABLE:
                    raise Stop('transport_not_retryable') from None
                if attempt == 1:
                    self.retry_needed += 1
                if attempt == maximum or self.retry_needed > 10:
                    raise Stop('transport_exhaustion') from None
                wait = max(WAITS[attempt-1], error.retry_after)
                self.evidence.write('retry_wait', dict(seconds=wait, retry_needed=self.retry_needed))
                while wait > 0:
                    self.sleeper(min(30, wait)); wait -= min(30, wait)
                continue
            self.evidence.write('native_reply', dict(base64=base64.b64encode(raw).decode()))
            try:
                reply = parse_json(raw.decode('utf-8'))
            except (ValueError, UnicodeError):
                raise Stop('unknown_output') from None
            if type(reply) is not dict:
                raise Stop('unknown_output')
            # Usage is booked even when the finish reason is a ceiling or refusal.
            buckets, usage = native.usage(self.provider, reply)
            returned = reply.get('model' if self.provider == 'anthropic' else 'modelVersion')
            expected = (self.approval.get('model_returned') if self.neutral else
                        self.approval['model_returned'][self.provider]) if self.approval else config.MODELS[self.provider]
            if self.neutral:
                if type(returned) is not str or not returned:
                    raise Stop('model_identity')
                expected = self.discovered_model or expected or returned
                self.discovered_model = expected
            if returned != expected:
                raise Stop('model_identity')
            self.budget.settle(reservation, bound, buckets, usage)
            result = native.parse(self.provider, reply, turn)
            self.evidence.write('native_format', dict(model_returned=returned, usage_shape=shape(usage),
                finish_reason=result['finish'], thinking_format=shape(result['native']), carry_over='unchanged assistant content'))
            if result['ceiling']:
                raise OutputCeiling()
            return result
        raise AssertionError('unreachable')
