"""Read-only actual-state retention, independent of returned descriptions.

Owned ledgers are recorded for inspection only. Scoring still uses the common
external oracle, never these arm-internal duty or allocation values.
"""
from copy import deepcopy
import json

CHANNELS=('records','tokens','duties','reports','receipts','notices','allocations',
          'cases','grants','orders','revision','step','business_operations')


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)


def value(s,key):
    return dict(present=True,value=deepcopy(s[key])) if key in s else dict(present=False)


def initial(s):
    return dict(channels={k:value(s,k) for k in CHANNELS},event_log=deepcopy(s['log']))


def change(before,after):
    if type(before) is dict and type(after) is dict:
        return {'entries':{k:{'before':value(before,k),'after':value(after,k)}
            for k in sorted(before.keys()|after.keys()) if canonical(value(before,k))!=canonical(value(after,k))}}
    if type(before) is list and type(after) is list and len(after)>=len(before) and canonical(after[:len(before)])==canonical(before):
        return dict(prefix_retained=True,before_length=len(before),after_length=len(after),appended=deepcopy(after[len(before):]))
    return dict(before=deepcopy(before),after=deepcopy(after))


def transition(before,after,phase,inputs):
    channels={}
    for k in CHANNELS:
        if canonical(value(before,k))!=canonical(value(after,k)):
            channels[k]=change(before[k],after[k]) if k in before and k in after else dict(before=value(before,k),after=value(after,k))
    return dict(phase=phase,step=after['step'],inputs=deepcopy(inputs),actual_channels=channels,
                actual_event_log=change(before['log'],after['log']))
