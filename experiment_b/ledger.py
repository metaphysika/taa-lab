"""Preflight cumulative provider stops and this month's recorded API spend."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json

from experiment_b.approval import money
from experiment_b.fixtures import ROOT
from experiment_b.host import Stop


LEDGER_START = ROOT / 'experiment_b/ledger_start.json'


def balance(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise Stop('invalid_ledger_balance') from error
    if not result.is_finite() or result < 0:
        raise Stop('invalid_ledger_balance')
    return result


def check_ledger(configuration, retain):
    try:
        ledger = json.loads(LEDGER_START.read_text(encoding='utf-8'))
        if ledger['month'] != datetime.now(timezone.utc).strftime('%Y-%m'):
            raise Stop('monthly_ledger_refresh_required')
        if set(ledger['providers']) != set(configuration['providers']):
            raise Stop('ledger_providers_mismatch')
        total = Decimal(0)
        provider_stop = False
        for label, entry in ledger['providers'].items():
            current = max(balance(entry['cumulative_dollars']), balance(json.loads(
                (ROOT / entry['ledger_path']).read_text(encoding='utf-8'))['estimated_api_dollars']))
            stop = money(entry['stop_dollars'])
            remaining = money(configuration['providers'][label]['remaining_dollars'])
            row = dict(model=label, provider=entry['provider'], cumulative_dollars=str(current),
                       stop_dollars=str(stop), remaining_dollars=str(remaining), source=entry['source'])
            print(json.dumps(dict(provider_ledger=row), sort_keys=True))
            retain('provider_ledger', row)
            total += current
            provider_stop |= current + remaining > stop
        for entry in ledger['other_month_spend']:
            total += max(balance(entry['cumulative_dollars']), balance(json.loads(
                (ROOT / entry['ledger_path']).read_text(encoding='utf-8'))['estimated_api_dollars']))
        monthly = dict(month=ledger['month'], recorded_spend_dollars=str(total), total_cap_dollars='50.00',
                       remaining_dollars=configuration['caps']['monthly_remaining'])
        print(json.dumps(dict(monthly_ledger=monthly), sort_keys=True))
        retain('monthly_ledger', monthly)
        if provider_stop:
            raise Stop('provider_stop_would_be_exceeded')
        if total + money(configuration['caps']['monthly_remaining']) > Decimal('50.00'):
            raise Stop('monthly_total_would_be_exceeded')
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise Stop('invalid_ledger_start') from error
