"""Shared $25 step cap; independently pinned Anthropic $25 / Google $8 stops."""
from decimal import Decimal
import json
import os
from pathlib import Path
import time

from live_demo.adapter import Stop
from live_demo.evidence import encoded
from experiment_a import config

D = Decimal
BUCKETS = ('input', 'cache_read', 'cache_write_5m', 'cache_write_1h', 'output', 'thinking')


def amount(value):
    if isinstance(value, bool):
        raise Stop('invalid_ledger')
    try:
        number = D(str(value))
    except Exception:
        raise Stop('invalid_ledger') from None
    if not number.is_finite() or number < 0:
        raise Stop('invalid_ledger')
    return number


class Budget:
    def __init__(self, provider, ledger, step_ledger, evidence, *, prices=None,
                 step_cap=config.STEP_CAP, provider_cap=None):
        if provider not in config.MODELS:
            raise Stop('unknown_provider')
        self.provider, self.ledger, self.step_ledger = provider, Path(ledger), Path(step_ledger)
        self.evidence = evidence
        self.step_cap = amount(step_cap)
        self.provider_cap = amount(provider_cap if provider_cap is not None else config.PROVIDER_CAPS[provider])
        if self.step_cap > amount(config.STEP_CAP) or self.provider_cap > amount(config.PROVIDER_CAPS[provider]):
            raise Stop('cap_increase_forbidden')
        if any(p.with_suffix('.pending').exists() for p in (self.ledger, self.step_ledger)):
            raise Stop('ledger_pending')
        self.prices = prices if prices is not None else config.load('prices.json')[provider]
        if self.prices.get('status') != 'verified':
            raise Stop('prices_unverified')
        if type(self.prices.get('context_window_tokens')) is not int or self.prices['context_window_tokens'] < 1:
            raise Stop('prices_unverified')
        self.rates = {k: amount(v) for k, v in self.prices['rates'].items()}
        required = {prefix+k+'_per_million' for prefix in ('', 'long_context_') for k in BUCKETS} | {'cache_storage_per_million_token_hours'}
        if set(self.rates) != required:
            raise Stop('prices_unverified')
        threshold = self.prices.get('long_context_threshold')
        if threshold is not None and (type(threshold) is not int or threshold < 1):
            raise Stop('prices_unverified')
        if threshold is None and any(self.rates[k+'_per_million'] != self.rates['long_context_'+k+'_per_million'] for k in BUCKETS):
            raise Stop('prices_unverified')
        self.phase_spent, self.attempts = D(0), 0
        self.tokens = {k: 0 for k in BUCKETS}
        self.read_step(); self.read_provider()

    def read_step(self):
        return amount(self.step_ledger.read_text())

    def read_provider(self):
        return amount(json.loads(self.ledger.read_text())['estimated_api_dollars'])

    def book(self, delta):
        # Caller owns the same global formation run.lock across both providers.
        step, prior = self.read_step(), self.read_provider()
        if min(step + delta, prior + delta) < 0:
            raise Stop('invalid_ledger')
        row = json.loads(self.ledger.read_text())
        row.update(estimated_api_dollars=float(prior+delta), updated_at=time.time())
        self.evidence.write('ledger_change', dict(provider=self.provider, prior=str(prior), delta=str(delta),
            after=str(prior+delta), step_prior=str(step), step_after=str(step+delta)))
        pending_step, pending_provider = self.step_ledger.with_suffix('.pending'), self.ledger.with_suffix('.pending')
        for path, blob in ((pending_step, str(step+delta).encode()), (pending_provider, encoded(row)+b'\n')):
            with path.open('xb') as f:
                f.write(blob); f.flush(); os.fsync(f.fileno())
        os.replace(pending_provider, self.ledger)
        os.replace(pending_step, self.step_ledger)
        self.phase_spent += delta

    def reserve(self, body):
        bound = len(encoded(body)) + 16384
        ceiling = config.OUTPUT_TOKENS[self.provider]
        if bound + ceiling > self.prices['context_window_tokens']:
            raise Stop('prompt_size')
        input_rate = max(self.rates[prefix+k+'_per_million'] for prefix in ('', 'long_context_')
                         for k in ('input', 'cache_read', 'cache_write_5m', 'cache_write_1h'))
        output_rate = max(self.rates[prefix+k+'_per_million'] for prefix in ('', 'long_context_') for k in ('output', 'thinking'))
        reserve = (bound * input_rate + ceiling * output_rate) / 1000000
        if self.read_step()+reserve > self.step_cap or self.read_provider()+reserve > self.provider_cap:
            self.evidence.write('cap_stop', dict(provider=self.provider, step=str(self.read_step()),
                provider_spend=str(self.read_provider()), reservation=str(reserve)))
            raise Stop('cap_stop')
        self.evidence.write('reservation', dict(provider=self.provider, dollars=str(reserve), input_bound=bound))
        self.book(reserve)
        self.attempts += 1
        return reserve, bound

    def settle(self, reservation, bound, buckets, native_usage):
        if buckets['input_total'] > bound or buckets['output_total'] > config.OUTPUT_TOKENS[self.provider]:
            raise Stop('usage_bound')
        threshold = self.prices['long_context_threshold']
        prefix = 'long_context_' if threshold is not None and buckets['input_total'] > threshold else ''
        actual = sum(D(buckets[k]) * self.rates[prefix+k+'_per_million'] for k in BUCKETS) / 1000000
        if actual > reservation:
            raise Stop('usage_bound')
        self.evidence.write('usage', dict(provider=self.provider, native=native_usage, buckets=buckets,
                                        charged=str(actual), retained_reserve='0'))
        self.book(actual-reservation)
        for k in BUCKETS:
            self.tokens[k] += buckets[k]
