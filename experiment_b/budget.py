"""Reserve worst-case request costs before transmission; retain uncertain spend."""
from decimal import Decimal
import json

from experiment_b.approval import money
from experiment_b.host import Stop


class Budget:
    def __init__(self, configuration, retain):
        self.configuration, self.retain = configuration, retain
        caps = configuration['caps']
        self.cap = min(money(caps[field]) for field in ('probe', 'combined_remaining', 'monthly_remaining'))
        self.spent = Decimal(0)
        self.providers = {label: Decimal(0) for label in configuration['providers']}
        self.requests = 0

    def account(self, label):
        return Account(self, label)

    def project(self, rows):
        for label in self.providers:
            block = [row for row in rows if row['episode']['model'] == label and row['episode']['repeat'] == 1]
            if len(block) == 14 and not any(row['episode']['model'] == label and row['episode']['repeat'] > 1 for row in rows):
                provider = self.configuration['providers'][label]
                projected = self.providers[label] * 3
                self.retain('block1_projection', dict(model=label, dollars=str(projected)))
                if projected > money(provider['remaining_dollars']):
                    raise Stop('projected_provider_cap')
        if all(sum(row['episode']['model'] == label for row in rows) == 14 for label in self.providers):
            if self.spent * 3 > self.cap:
                raise Stop('projected_probe_cap')


class Account:
    def __init__(self, budget, label):
        self.budget, self.label = budget, label
        self.provider = budget.configuration['providers'][label]
        self.reservation = None

    def cost(self, inp, out):
        return (Decimal(inp) * money(self.provider['input_dollars_per_million_upper']) +
                Decimal(out) * money(self.provider['output_dollars_per_million_upper'])) / Decimal(1000000)

    def reserve(self, body):
        if self.reservation is not None:
            raise Stop('unsettled_reservation')
        encoded_size = len(json.dumps(body, ensure_ascii=True, sort_keys=True).encode('utf-8'))
        if encoded_size + self.provider['input_token_overhead'] > self.provider['input_token_bound']:
            raise Stop('input_history_bound')
        reserve = self.cost(self.provider['input_token_bound'], self.provider['output_token_bound'])
        if (self.budget.spent + reserve > self.budget.cap or
                self.budget.providers[self.label] + reserve > money(self.provider['remaining_dollars'])):
            raise Stop('budget_before_transmission')
        if self.budget.requests >= 1008:
            raise Stop('schedule_request_ceiling')
        self.budget.spent += reserve
        self.budget.providers[self.label] += reserve
        self.budget.requests += 1
        self.reservation = reserve
        self.budget.retain('budget_reserved', dict(model=self.label, dollars=str(reserve),
                                                  total=str(self.budget.spent), request=self.budget.requests))

    def settle(self, usage):
        inp, out = usage['input'], usage['output']
        if inp > self.provider['input_token_bound'] or out > self.provider['output_token_bound']:
            raise Stop('actual_usage_exceeds_reservation')
        cost = self.cost(inp, out)
        self.budget.spent += cost - self.reservation
        self.budget.providers[self.label] += cost - self.reservation
        self.budget.retain('budget_settled', dict(model=self.label, dollars_upper=str(cost),
                                                 native_usage=usage['native'], total=str(self.budget.spent)))
        self.reservation = None
