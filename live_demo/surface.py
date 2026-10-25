"""The entire model-facing surface; internal decisions never pass through."""
from copy import deepcopy
import json
from pathlib import Path


def manifest():
    return json.loads((Path(__file__).parent/'frozen/tools.json').read_text())


def refusal(disposition='REFUSE'):
    # Deliberately constant: no rule IDs, checks, facts, exception text or hints.
    if disposition not in ('PROHIBIT', 'REFUSE', 'HOLD', 'REFER', 'ALTERNATIVE'):
        disposition = 'REFUSE'
    return dict(status='refused', disposition=disposition,
                reason='This request cannot be completed.')


BUSINESS_FIELDS = {
    'order': ('customer', 'amount', 'currency'),
    'payment': ('order', 'payer', 'amount', 'currency', 'method'),
    'claim': ('claimant', 'order', 'basis', 'amount'),
    'return_receipt': ('order', 'received', 'condition'),
    'carrier_record': ('order', 'status', 'signed', 'failed_value'),
    'refund': ('claim', 'claimant', 'order', 'amount', 'currency', 'to', 'settled'),
    'chargeback': ('claim', 'claimant', 'order', 'amount', 'currency', 'settled'),
}


def business_record(state, identity):
    """No path lookup, native checkpoint, grant, note, report or ledger access."""
    rows = state['records'].get(identity, [])
    if not rows or rows[-1]['kind'] not in BUSINESS_FIELDS:
        return None
    row = rows[-1]
    return dict(id=identity, kind=row['kind'], version=row['version'],
                fields={k: deepcopy(row['fields'][k]) for k in BUSINESS_FIELDS[row['kind']]
                        if k in row['fields']})


def completed(tool, args, before, after):
    result = dict(status='completed')
    if tool == 'read_record':
        result['record'] = business_record(after, args['record'])
    elif tool == 'issue_refund':
        # Actual newly written settlement IDs only, not the internal receipt.
        result['records'] = [business_record(after, rid) for rid, rows in after['records'].items()
                             if len(rows) > len(before['records'].get(rid, []))
                             and rows[-1]['kind'] == 'refund']
    return result


class ModelSurface:
    """Allowlisted business RPC only. The MCP client belongs to the trusted host."""
    def __init__(self, execute):
        self.__execute = execute

    def request(self, method, params=None):
        if method == 'tools/list':
            return deepcopy(manifest())
        if method != 'tools/call' or type(params) is not dict or set(params) != {'name', 'arguments'}:
            return refusal()
        if params['name'] not in {t['name'] for t in manifest()}:
            return refusal()
        try:
            return self.__execute(params['name'], params['arguments'])
        except Exception as error:
            from live_demo.adapter import Stop
            if isinstance(error, Stop):
                raise
            # Never relay exception strings, including paths/native diagnostics.
            return refusal()
