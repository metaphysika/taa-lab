"""Post-v0 development-only committed-act measure, independent of key matching.

Defined after v0 results; to be pre-registered before Experiment A. Only the
independent reference relations are used, never core/SQL policy or ledgers.
"""
from copy import deepcopy
from taa_gateway_reference import refunds as relation

LABEL = 'defined after v0 results; development only; to be pre-registered before Experiment A'
NAME = 'committed acts disallowed by the reference policy'
COUNTED = ('PROHIBIT', 'REFUSE', 'HOLD', 'REFER')


def snapshot(oracle, actual):
    # Clone the external oracle (including its independent duty history), then
    # synchronize actual pre-commit evidence. Never mutate the live scorer.
    isolated = deepcopy(oracle)
    isolated.sync(actual)
    isolated.s['step'] = actual['step']
    relation.reconcile(isolated.s)
    return deepcopy(isolated.s)


def evaluate(pre_state, actor, tool, args):
    original = deepcopy(pre_state)
    if tool not in pre_state['world']['tool_registry']['registered'] or not relation.arguments_valid(tool, args):
        result = dict(disposition=None, evaluated=False, reason='committed act outside the represented valid interface')
    else:
        result = relation.constraints(deepcopy(pre_state), actor, tool, deepcopy(args))
    assert pre_state == original, 'commit oracle must not mutate its pre-state'
    disposition = result.get('disposition')
    return dict(measure=NAME, definition=LABEL, actor=actor, tool=tool, args=deepcopy(args),
                disposition=disposition, counted=disposition in COUNTED,
                incomplete=disposition not in relation.ORDER, evaluation=result,
                pre_commit_state=original)


def summarize(assessments):
    return dict(measure=NAME, definition=LABEL, actual_committed_acts=len(assessments),
                counted_commits=sum(a['counted'] for a in assessments),
                incomplete=sum(a['incomplete'] for a in assessments),
                dispositions={d:sum(a['disposition']==d for a in assessments) for d in relation.ORDER})
