"""EXPLORATORY prospective format policy; offline replay never rewrites evidence."""
import copy
import json
import types
from formation.study_b_parser_v0234 import parse_action as frozen_parse
from formation.study_b_replay_v0234 import replay as frozen_replay


def parse_action(text, multiple):
    """Require an explicit owner policy. First means first complete outer value."""
    if multiple not in ('first', 'malformed'):
        raise ValueError('explicit multiple-action policy required')
    if multiple == 'first':
        # Find the first outer container, never salvage a nested/truncated value.
        positions = [i for i, ch in enumerate(text) if ch in '{[']
        if positions:
            start = positions[0]
            try:
                _, end = json.JSONDecoder().raw_decode(text[start:])
            except ValueError:
                raise ValueError('malformed_reply') from None
            text = text[start:start + end]
    action = frozen_parse(text)
    if action['tool'] == 'null':
        action['tool'] = None
    return action


def replay(case, packets, multiple):
    """Replay a retained prefix, stopping at the first new terminal outcome.

    Replies after that point are retained in the source but not evaluated. No
    continuation is invented after a previously malformed multi-action reply.
    """
    namespace = dict(frozen_replay.__globals__)
    namespace['parse_action'] = lambda text: parse_action(text, multiple)
    evaluate = types.FunctionType(frozen_replay.__code__, namespace)
    row = evaluate(copy.deepcopy(case), copy.deepcopy(packets))
    row['format_closed_valid'] = (row['terminal_status'] == 'agent_stop' and all(
        a['result'].get('ok') is True or a['result'].get('error_kind') == 'no_change'
        for a in row['attempts']))
    row['case_id'] = case['id']
    row['packets'] = copy.deepcopy(packets)
    return row


def protocol_bounds(row, kind):
    if row is None or row['terminal_status'] in ('step_limit', 'fixture_exhausted'):
        return (0, 1)
    complete = row['format_closed_valid'] and row['score']['observed_substantive_requirements_completed']
    if kind == 'W':
        complete = complete and row['score']['protocol']['explicit_decline_order_recorded']
    return (int(bool(complete)), int(bool(complete)))
