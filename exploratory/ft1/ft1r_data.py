"""FT1-R revision 2 data layout and offline diagnostics."""
import json

from . import data, data_diagnostics, selection

ARMS = ('2', '3')
PROBE_FILE = 'acquisition-ft1-r-v1.json'
HISTORY_HEADER = 'Earlier turns (action-only):'
TOOL_RESULT = 'recorded'


def ordered(target, reason=''):
    return dict(tool=target['tool'], args=target['args'], reason=reason)


def prompt(lines, history=(), latest=''):
    messages = [dict(role='system', content=data.FT1R_SYSTEM),
                dict(role='user', content='\n'.join(lines))]
    for i, action in enumerate(history):
        reason = latest if i == len(history) - 1 else ''
        messages.extend((dict(role='assistant', content=data.dump(ordered(action, reason))),
                         dict(role='user', content=TOOL_RESULT)))
    return messages


def split_history(lines):
    if HISTORY_HEADER not in lines:
        return lines, []
    start = lines.index(HISTORY_HEADER)
    return lines[:start], [json.loads(line.removesuffix(' -> recorded')) for line in lines[start + 1:]]


def choose(counter, target, reasons, lines, balance, prompts=(), preferred=None):
    """Match complete variants, with the original choice first when it fits."""
    eligible = [line for line in lines if not data.BANNED.search(line)]
    rests = ['\n'.join(eligible[:n]) for n in range(1, len(eligible) + 1)]
    restatable = counter.trained('\n'.join(eligible))
    room2, room3 = (min(640, 1024 - counter.prompt(mm)) for mm in prompts) if prompts else (640, 640)

    def trained(text):
        return counter.trained(data.dump(ordered(target, text)))

    def fits(t2, t3):
        return t2 <= room2 and t3 <= room3 and abs(t2 - t3) <= max(8, .05 * t3)

    if preferred is not None:
        reason, rest = preferred[:2]
        t2, t3 = trained(rest), trained(reason)
        if counter.trained(reason) <= restatable and fits(t2, t3):
            return reason, rest, t2, t3

    rest_counts = [(rest, trained(rest)) for rest in rests]
    options = []
    for reason in reasons:
        if counter.trained(reason) > restatable:
            continue
        t3 = trained(reason)
        for rest, t2 in rest_counts:
            if fits(t2, t3):
                delta = t2 - t3
                options.append((abs(balance + delta), abs(delta), reason, rest, t2, t3))
    if not options:
        raise data.InfeasibleCandidate(0)
    return min(options)[2:]


def match_record(counter, index, card, original, balance):
    _, target, reasons, lines, meta = card
    context, history = split_history(lines)
    reason = rest = ''
    history_status = 'correction' if meta['correction'] else 'no_history'
    if history and not meta['correction']:
        _, prior_target, prior_reasons, prior_lines, _ = data.card(
            index, meta['type'], previous_step=True)
        if prior_target != history[-1]:
            raise ValueError('previous step does not match the most recent action')
        try:
            reason, rest, _, _ = choose(counter, prior_target, prior_reasons, prior_lines, 0)
        except data.InfeasibleCandidate:
            history_status = 'unmatched'
        else:
            history_status = 'reason_bearing'
    prompts = (prompt(context, history, rest), prompt(context, history, reason))
    # Use the original action-only source lines as before. Rendered chat turns,
    # including the arm's own text, never enter the restatement candidates.
    choice = choose(counter, target, reasons, lines, balance, prompts, original)
    return prompts, choice, history_status


def row(counter, messages, target, meta):
    messages = messages + [dict(role='assistant', content=data.dump(target))]
    data.validate_roles(messages)
    render = getattr(counter, 'render_record', None)
    if render:
        render(messages)
    p, t = data.limits(counter, messages[:-1], target)
    return dict(meta, messages=messages, prompt_tokens=p, trained_tokens=t)


def generate_training(counter):
    original, _, _ = selection.select_training(counter)
    selected = {}
    balances = {}
    refused = []
    balance = 0
    for slot, (index, card, choice) in original.items():
        balances[slot] = balance
        try:
            matched = match_record(counter, index, card, choice, balance)
        except data.InfeasibleCandidate:
            selected[slot] = None
            refused.append(slot)
        else:
            selected[slot] = (index, card, matched)
            balance += matched[1][2] - matched[1][3]

    def candidate(slot, index):
        card = data.card(index, data.MIX[slot])
        matched = match_record(counter, index, card, None, balances[slot])
        return index, card, matched

    used = set(range(2000)) | {entry[0] for entry in original.values()}
    selected, replacements = selection.replace_refused(selected, refused, candidate, used)
    output = {arm: [] for arm in ARMS}
    history = {}
    endings = {}
    changes = []
    table = []
    for slot in range(len(data.MIX)):
        index, card, (prompts, (reason, rest, t2, t3), status) = selected[slot]
        _, target, reasons, _, meta = card
        ident = meta['id']
        history[ident] = status
        remain_slot = (reasons.index(reason) + list(data.REASONS).index('remain')) % 4
        prefix = data.REASONS['remain'][remain_slot].split('{remaining}')[0]
        _, marker, remaining = reason.rpartition(prefix)
        if not marker or not remaining.endswith('.') or '\n' in remaining:
            raise ValueError('missing final remaining-work slot: ' + ident)
        endings[ident] = marker + remaining
        for arm, messages, text, expected in zip(ARMS, prompts, (rest, reason), (t2, t3)):
            record = row(counter, messages, ordered(target, text), meta)
            if record['trained_tokens'] != expected:
                raise ValueError('inconsistent token measurement: ' + ident)
            output[arm].append(record)
        table.append(dict(id=ident, arm2=t2, arm3=t3, difference=t2-t3))
        old_index, old_card, old_choice = original[slot]
        if (old_index, old_choice[:2]) != (index, (reason, rest)):
            changes.append(dict(slot=slot, original=old_card[-1]['id'], selected=ident,
                                original_variant=old_card[2].index(old_choice[0]),
                                selected_variant=reasons.index(reason),
                                original_restatement_lines=len(old_choice[1].splitlines()),
                                selected_restatement_lines=len(rest.splitlines())))
    for entry in replacements:
        entry['ft1_index'] = original[entry['slot']][0]
    failures = []
    try:
        data.matching(table)
    except ValueError as exc:
        failures.append(str(exc))
    report = dict(passed=not failures, failures=[], aggregate_failures=failures,
                  changes=changes, matching_change_count=len(changes)-len(replacements),
                  replacements=replacements, replacement_count=len(replacements),
                  refused_slots=refused, history=history,
                  history_counts=dict(data.Counts(history.values())), arm3_last_slots=endings,
                  matching=dict(per_record=table,
                                arm2_total=sum(r['arm2'] for r in table),
                                arm3_total=sum(r['arm3'] for r in table)),
                  fit={arm: fit(rows) for arm, rows in output.items()},
                  samples={arm: rows[::len(rows)//10] for arm, rows in output.items()})
    manifest = dict(layout=data.FT1R_LAYOUT, partition='train', token_table=table,
                    record_tokens={arm: [dict(id=r['id'], prompt=r['prompt_tokens'],
                                              trained=r['trained_tokens']) for r in rows]
                                   for arm, rows in output.items()})
    return output, manifest, report


def fit(rows):
    return dict(prompt=data_diagnostics.distribution(r['prompt_tokens'] for r in rows),
                trained=data_diagnostics.distribution(r['trained_tokens'] for r in rows),
                total=data_diagnostics.distribution(r['prompt_tokens'] + r['trained_tokens'] for r in rows))


def probes(counter):
    """Re-render FT1's shared 40 decision points with the FT1-R wire order."""
    rows = []
    for i in range(40):
        index, kind = data_diagnostics.heldout_case(i)
        _, target, _, lines, meta = data.card(index, kind, 'heldout')
        context, history = split_history(lines)
        if history:
            context = context + [HISTORY_HEADER] + [data.dump(ordered(a)) + ' -> recorded' for a in history]
        rows.append(row(counter, prompt(context), ordered(target), meta))
    return rows
