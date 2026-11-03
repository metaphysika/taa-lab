"""EXPLORATORY prospective format policy; offline replay never rewrites evidence."""
import copy
import json
import types
from formation.study_b_parser_v0234 import parse_action as frozen_parse, reject_constant
from formation.study_b_replay_v0234 import replay as frozen_replay


def first_json_span(text):
    """Match v0234's outer-span scan, skipping complete non-JSON prose.

    Never search inside an incomplete/mismatched container. Once a complete
    JSON value is found, the first-only policy ignores subsequent text/actions.
    Schema and duplicate-field validation still run in the frozen parser.
    """
    stack = []
    quoted = escaped = False
    start = None
    for i, ch in enumerate(text):
        if not stack:
            if ch in '{[':
                start, stack = i, [ch]
                quoted = escaped = False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch in '{[':
            stack.append(ch)
        elif ch in '}]':
            if (ch == '}' and stack[-1] != '{') or (ch == ']' and stack[-1] != '['):
                raise ValueError('malformed_reply')
            stack.pop()
            if not stack:
                raw = text[start:i+1]
                try:
                    json.loads(raw, parse_constant=reject_constant)
                except ValueError:
                    continue
                return raw
    raise ValueError('malformed_reply')


def parse_action(text, multiple):
    """Require an explicit owner policy. First means first complete outer value."""
    if multiple not in ('first', 'malformed'):
        raise ValueError('explicit multiple-action policy required')
    if multiple == 'first':
        text = first_json_span(text)
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
    if row is None or not row['format_closed_valid']:
        return (0, 1)
    complete = row['format_closed_valid'] and row['score']['observed_substantive_requirements_completed']
    if kind == 'W':
        complete = complete and row['score']['protocol']['explicit_decline_order_recorded']
    return (int(bool(complete)), int(bool(complete)))
