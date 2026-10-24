"""Trusted business-adapter invocation observations; no authorization policy.

The adapter records the actual dispatched tool and all arguments, not a
certificate echo. A notice's physical argument body must agree with that
invocation. Receipts verify this evidence in addition to postconditions.
"""
from copy import deepcopy
import json


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def invocation(before,after):
    if len(after)!=len(before)+1 or canonical(after[:len(before)])!=canonical(before):
        raise ValueError('expected exactly one actual invocation with retained history')
    row=after[-1]
    if type(row['tool']) is not str or type(row['args']) is not dict or type(row['actor']) is not str:
        raise ValueError('invalid actual invocation')
    return dict(tool=row['tool'],arguments=deepcopy(row['args']),actor=row['actor'])


def check_notice(actual,effect):
    if actual['tool']=='message_party':
        physical={k:deepcopy(v) for k,v in effect.items() if k not in ('kind','actor')}
        if canonical(physical)!=canonical(actual['arguments']) or effect['actor']!=actual['actor']:
            raise ValueError('physical notice differs from complete actual invocation')
