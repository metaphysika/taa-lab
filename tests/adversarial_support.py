"""Fixed attacker inputs; expected outcomes remain solely with the outer runner."""
from copy import deepcopy
from pathlib import Path
import json
import yaml
from tests.trace_support.bundle import cases as frozen
from tests.trace_support.regressions import cases as regression

ROOT=Path(__file__).parent/'adversarial_scenarios'


def controls():
    p=ROOT/'sol_controls.yaml'
    return [{'id':t['id'],'trace':t,'parameters':{},'source':str(p)} for t in yaml.safe_load(p.read_text())]


def actor_program(case):
    return {'id':case['id'],'setup':deepcopy(case['trace'].get('setup',{})),
            'steps':[{k:deepcopy(v) for k,v in e.items() if k in ('step','events','propose','execute')} for e in case['trace']['steps']]}


def coverage():
    current=regression()
    aliases={c['historical_id']: c['id'] for c in current if 'historical_id' in c}
    available={c['id'] for c in frozen()+current+controls()}
    declared=json.loads((ROOT/'COVERAGE.json').read_text())['attacks']
    mapping={attack:[aliases.get(case,case) for case in cases] for attack,cases in declared.items()}
    missing={attack:sorted(set(ids)-available) for attack,ids in mapping.items() if set(ids)-available}
    return mapping,missing
