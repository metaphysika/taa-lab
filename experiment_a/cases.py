"""Structural validation only. No policy dispositions or expected-outcome key."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from live_demo.evidence import encoded
from experiment_a import config


def encode_program(definition):
    """Canonical bytes for an owner-supplied, fully specified program document.

    This serializes definitions; it never infers facts, rules or outcomes.
    Sealed definitions are supplied only at a separately approved unsealing.
    """
    if type(definition) is not dict or set(definition) != {'brief', 'events', 'rung', 'setup'}:
        raise ValueError('complete program definition required')
    return (json.dumps(definition, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def pair_check(directory, pairs):
    directory = Path(directory)
    results = []
    assertions = {'P01':['item returned undamaged'], 'P02':['item returned undamaged'],
                  'P09':['return received'], 'P10':['return received'],
                  'H01':['return received'], 'H02':['return received'],
                  'H09':['item returned undamaged'], 'H10':['item returned undamaged']}
    staff = json.loads((config.ROOT/'live_demo/frozen/programs.json').read_bytes())['T01']['brief']['staff']
    for pair in pairs:
        left, right = [json.loads((directory/(identity+'.json')).read_bytes()) for identity in pair['pair']]
        stripped = []
        deciding = []
        for identity, prog in zip(pair['pair'], (left, right)):
            copy = deepcopy(prog)
            deciding.append(copy['setup']['records'].pop(pair['deciding_record'], None))
            stripped.append(encoded(copy))
            assert prog['brief']['staff'] == staff
            events = prog['events']['1']
            assert len(events) == 1 and events[0]['from'] == 'L' and events[0]['to'] == 'A'
            effects = events[0]['requested_effects']
            assert len(effects) == 1
            effect = effects[0]
            assert set(effect) == {'tool','claim','amount','to'} | ({'asserts'} if identity in assertions else set())
            assert effect['tool'] == 'issue_refund' and effect['claim'] == prog['brief']['claim']
            assert effect.get('asserts', []) == assertions.get(identity, [])
            assert prog['brief']['requested_effects'] == effects
            assert bool(prog['brief']['visible_record_ids']) == (pair['rung'] in (2, 3))
            claim = prog['setup']['records'][effect['claim']]
            order = prog['setup']['records'][claim['order']]
            assert order['amount'] == claim['amount'] == effect['amount']
            payments = [r for r in prog['setup']['records'].values() if r['kind'] == 'payment' and r['order'] == claim['order']]
            assert len(payments) == 1 and payments[0]['settled'] is True
            assert payments[0]['payer'] == claim['claimant'] and payments[0]['amount'] == claim['amount']
        assert stripped[0] == stripped[1], 'twin differs outside deciding record'
        assert deciding[0] != deciding[1], 'deciding record does not differ'
        results.append(dict(pair=pair['pair'], twin_diff='only deciding record'))
    return results


def sealed_digest(directory):
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(directory).glob('*.json'))}
    blob = (json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    return hashlib.sha256(blob).hexdigest()
