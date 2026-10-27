"""Bounded successors of one owner receipt; no independent launch authority."""
from copy import deepcopy
import hashlib
from live_demo.adapter import Stop
from live_demo.evidence import encoded, verify

ALLOWED = frozenset(('executor_outage','state_publication_failed'))

def binding(approval):
    """Validate policy/derivation without widening the original owner receipt."""
    if type(approval)is not dict:raise Stop('standing_not_approved')
    if 'standing' not in approval:
        if 'standing_authorization' in approval:raise Stop('standing_not_approved')
        return None
    policy=approval['standing']
    if (type(policy)is not dict or set(policy)!= {'max_continuations','allowed_stop_reasons'} or
            type(policy['max_continuations'])is not int or not 1<=policy['max_continuations']<=3 or
            type(policy['allowed_stop_reasons'])is not list or not policy['allowed_stop_reasons'] or
            any(type(x)is not str or x not in ALLOWED for x in policy['allowed_stop_reasons']) or
            len(set(policy['allowed_stop_reasons']))!=len(policy['allowed_stop_reasons']) or
            type(approval.get('continuation'))is not int):
        raise Stop('standing_not_approved')
    authority=approval.get('standing_authorization')
    base=approval if authority is None else authority.get('receipt') if type(authority)is dict else None
    ordinal=1 if authority is None else authority.get('segment')
    if (type(base)is not dict or 'standing_authorization' in base or
            type(ordinal)is not int or not 1<=ordinal<=policy['max_continuations']):
        raise Stop('standing_limit_or_binding')
    digest=hashlib.sha256(encoded(base)).hexdigest()
    if authority is not None:
        if (set(authority)!= {'receipt','receipt_sha256','segment'} or ordinal<2 or
                authority['receipt_sha256']!=digest or
                set(base)!=set(approval)-{'standing_authorization'} or
                any(base.get(k)!=approval.get(k) for k in base if k not in ('continuation','source_checkpoints','start_index')) or
                approval['continuation']!=base['continuation']+ordinal-1 or
                approval['source_checkpoints'][:base['continuation']]!=base['source_checkpoints']):
            raise Stop('standing_limit_or_binding')
    return dict(receipt=base,receipt_sha256=digest,segment=ordinal)

def _successor(approval, sources):
    """Derive ONLY the next ordinal; source validation remains mandatory upstream."""
    from experiment_a.continuation import frames
    b=binding(approval)
    if b is None:raise Stop('standing_not_approved')
    if b['segment']>=approval['standing']['max_continuations']:raise Stop('standing_limit_or_binding')
    fs,_=frames(sources[-1])
    if fs[-1]['kind']!='closure' or fs[-1]['value']['stop'] not in approval['standing']['allowed_stop_reasons']:
        raise Stop('standing_stop_not_allowed')
    header=fs[0]['value']
    if header.get('approved_commit')!=approval['commit'] or header.get('approval')!=approval:
        raise Stop('standing_limit_or_binding')
    # Index advancement derives from touched child names, never a score/arm result.
    children=sorted(sources[-1].glob('episode-*'))
    if not children:raise Stop('standing_limit_or_binding')
    last=int(children[-1].name.split('-')[1])
    for source in sources:
        verify(source)
        for child in source.glob('episode-*'):verify(child)
        if (source/'publication').exists():verify(source/'publication')
    result=deepcopy(approval)
    result.update(continuation=approval['continuation']+1,start_index=last+1,
                  source_checkpoints=[verify(p)['head'] for p in sources],
                  standing_authorization=dict(receipt=b['receipt'],receipt_sha256=b['receipt_sha256'],segment=b['segment']+1))
    binding(result)
    return result

def successor(approval,sources):
    try:return _successor(approval,sources)
    except (ValueError,OSError,KeyError,TypeError,IndexError):
        raise Stop('standing_evidence_invalid') from None
