"""Prospective crossing only. No clients or remote imports."""
from copy import deepcopy
import hashlib
import json
import types
from pathlib import Path
from exploratory.measurement_v02456.policy import parse_action, first_json_span
from formation.study_b_replay_v0234 import replay as original_replay
from formation.study_d_base_gate_v0248 import SYSTEM
from .runner import CallTimeout

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT/'studies/formation-study-d-gemma-stages-v02429/transfer-cases.json'
ASSET_SHA = '6870a565d7a95558a36d3eeef02d5dc69b4dda078554df9017c362a80eb4e708'
STAGE = 'crossing'
ARMS = ('crossing_noprefix', 'crossing_prefix')


def cases():
    # Frozen assets use LF in Git; do not alter source bytes on Windows.
    data = ASSET.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(data).hexdigest() != ASSET_SHA:
        raise ValueError('attempt-4 battery hash mismatch')
    return [x['case'] for x in json.loads(data) if x['case']['kind'] in ('W', 'U')]


def plan(repeats=1, checkpoint='contrary'):
    if checkpoint != 'contrary':
        raise ValueError('crossing requires contrary only')
    if type(repeats) is not int or repeats < 1:
        raise ValueError('positive integer repeats required')
    return [dict(block=STAGE, case_id=c['id'], checkpoint=checkpoint, repeat=r,
                 branch='action', crossing_arm=arm)
            for r in range(1, repeats+1) for c in cases() for arm in ARMS]


def binding(repeats=1):
    return dict(crossing_repeats=repeats, crossing_cells=plan(repeats),
                crossing_asset_sha256=ASSET_SHA, crossing_case_hashes={c['id']: hashlib.sha256(
                    json.dumps(c, sort_keys=True, separators=(',', ':')).encode()).hexdigest() for c in cases()},
                crossing_output_tokens=1024,
                crossing_parser='first', crossing_prefix='PRIMARY record presentation v1')


def replay(case, packets):
    namespace = dict(original_replay.__globals__)
    namespace['parse_action'] = lambda raw: parse_action(raw, multiple='first')
    return types.FunctionType(original_replay.__code__, namespace)(deepcopy(case), deepcopy(packets))


def history_for(case, packets, arm):
    # Same task-context/world and feedback serialization as attempt 4.
    from formation.study_b_v0227 import visible
    history = []
    for turn in range(len(packets)+1):
        prior = replay(case, packets[:turn])
        view = visible(case)
        view['world'] = prior['final_world']; view['world']['step'] = turn+1
        feedback = {'task_context': view} if not history else {
            'last_tool_result': prior['attempts'][-1]['result'], 'world': view['world']}
        history.append(dict(role='user', content=json.dumps(feedback, ensure_ascii=False)))
        if turn == 0 and arm == 'crossing_prefix':
            # Presentation only: original interface has no read_record tool.
            history.extend([dict(role='assistant', content=json.dumps(
                {'tool': 'read_record', 'args': {'record_id': 'PRIMARY'}})),
                dict(role='user', content=json.dumps({'last_tool_result': {
                    'ok': True, 'record_id': 'PRIMARY', 'record': case['world']['records']['PRIMARY']}}, ensure_ascii=False))])
        if turn < len(packets):
            history.append(dict(role='assistant', content=packets[turn]['raw']))
    return history


def episode(case, arm, generate):
    if arm not in ARMS:
        raise ValueError('unknown crossing arm')
    packets, retained = [], []
    for turn in range(1, 13):
        history = history_for(case, packets, arm)
        try:
            raw = generate(SYSTEM, history, 1024)
        except CallTimeout as exc:
            row = replay(case, packets)
            row.update(terminal_status='call_timeout', packets=packets, partial=exc.raw,
                       retained=retained, format_closed_valid=False)
            return row
        except Exception as exc:
            row = replay(case, packets)
            row.update(terminal_status='generation_failed', packets=packets,
                       error=type(exc).__name__, retained=retained, format_closed_valid=False)
            return row
        packets.append(dict(kind='reply', raw=raw))
        try:
            span = first_json_span(raw)
            extra = raw.replace(span, '', 1)
            retained.append(dict(raw=raw, first_span=span, extra_content=extra,
                                 has_extra_content=bool(extra.strip())))
        except (ValueError, TypeError):
            retained.append(dict(raw=raw, first_span=None, extra_content=raw, has_extra_content=bool(raw)))
        row = replay(case, packets)
        if row['terminal_status'] != 'fixture_exhausted':
            break
    row.update(packets=packets, retained=retained, format_closed_valid=(
        row['terminal_status'] == 'agent_stop' and all(a['result'].get('ok') is True or
        a['result'].get('error_kind') == 'no_change' for a in row['attempts'])))
    return row


def run(checkpoints, guard, backend, retain, repeats, verify):
    if guard.block != STAGE or guard.started or guard.checkpoints != checkpoints:
        raise ValueError('matching fresh crossing guard required')
    if any(c['checkpoint'] != 'contrary' for c in plan(repeats)):
        raise ValueError('contrary required')
    verify(guard.commit); guard.started = True
    roster = {c['id']: c for c in cases()}; rows = []
    for cell in plan(repeats):
        if not guard.before_cell():
            break
        if not checkpoints.get('contrary', {}).get('available'):
            row = dict(cell, terminal_status='blocked', format_closed_valid=False)
        else:
            # Pair arms at the original attempt-4 case/turn seed, including original RD offset.
            original = [x['case']['id'] for x in json.loads(ASSET.read_bytes())]
            backend.crossing_seed_base = 248017 + original.index(cell['case_id'])*12 + (cell['repeat']-1)*396
            backend.crossing_turn = 0
            row = dict(cell, **episode(roster[cell['case_id']], cell['crossing_arm'],
                lambda system, history, cap: guard.call('contrary', 0,
                    lambda: backend('contrary', system, history, cap))))
        retain(deepcopy(row)); rows.append(row)
        if row['terminal_status'] in ('call_timeout', 'generation_failed'):
            break
    return rows


if __name__ == '__main__':
    import argparse
    from .modal_backend import settings
    parser = argparse.ArgumentParser(description='Offline crossing preview; no launch')
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--dollar-cap', type=float, default=5)
    args = parser.parse_args()
    print(json.dumps(dict(approved=False, binding=binding(args.repeats),
        settings=settings(args.dollar_cap, 'crossing')), indent=2))
