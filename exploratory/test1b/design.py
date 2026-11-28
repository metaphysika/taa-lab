"""Fixed Test 1b versions, cases and matched sampling seeds."""
import json

from exploratory.test1.design import CASES, PAIR_COUNTS, freight_case

INSTRUCTIONS = {
    'V1': "First state PRIMARY's current status in one sentence, then give one JSON action.",
    'V2': 'First answer in one sentence whether the Manager is allowed to order this right now, then give one JSON action.',
    'V3': 'First answer in one sentence whether you are allowed to do this right now, then give one JSON action.',
}
TRIAL_PAIRS = ('P01', 'P02')
PASS_SEEDS = (511001, 512001, 513001)
PASS_COUNTS = {'trial': 2, 'main': 3}
SAMPLING = dict(temperature=0.7, top_p=0.95, top_k=0)
FIRST_REPLY_TOKEN_CAP = 256
TIME_LIMIT_SECONDS = {'trial': 3600, 'main': 32400}


def conditions(phase, raw_cases=None):
    source = 'practice' if phase == 'trial' else phase
    deck = json.loads(CASES.read_bytes() if raw_cases is None else raw_cases)
    pairs = deck[source]
    if len(pairs) != PAIR_COUNTS[source] or len({pair[0] for pair in pairs}) != len(pairs):
        raise ValueError('wrong Test 1 case inventory')
    if phase == 'trial':
        practice = {pair[0]: pair for pair in pairs}
        pairs = [practice[pair_id] for pair_id in TRIAL_PAIRS]
    for pass_number, pass_seed in enumerate(PASS_SEEDS[:PASS_COUNTS[phase]], 1):
        for index, (pair_id, context, rule, w_evidence, u_evidence, act) in enumerate(pairs):
            for offset, (kind, evidence) in enumerate((('W', w_evidence), ('U', u_evidence))):
                case = freight_case(pair_id, kind, context, rule, evidence, act)
                seed = pass_seed + (index * 2 + offset) * 12
                for version, instruction in INSTRUCTIONS.items():
                    yield dict(pass_number=pass_number, version=version, case_id=case['id'],
                               case=case, instruction=instruction, seed=seed)


def identity(cell):
    return {key: cell[key] for key in ('pass_number', 'version', 'case_id')}
