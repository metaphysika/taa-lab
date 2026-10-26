"""Exactly two neutral echo requests per approved numbered model check."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path

from live_demo.adapter import Stop
from live_demo.evidence import Evidence, encoded
from experiment_a import config
from experiment_a.adapter import Adapter, authorized
from experiment_a.budget import Budget
from experiment_a.state import State
from experiment_a.standin import ScriptedTransport, reply, prices

INSTRUCTION = 'Call echo once with value "neutral-check". After its tool result, reply briefly without calling a tool.'
TOOLS = [dict(name='echo', description='Return the supplied value.', parameters=dict(type='object',
    properties=dict(value=dict(type='string')), required=['value'], additionalProperties=False))]


def exchange(adapter, evidence):
    history = [dict(kind='user', text='Please perform the neutral echo task.')]
    first = adapter.respond(history, dict(phase='neutral_check'), 1)
    if len(first['calls']) != 1 or first['calls'][0]['name'] != 'echo' or first['calls'][0]['args'] != {'value':'neutral-check'}:
        raise Stop('neutral_function_call')
    history.append(dict(kind='assistant', native=first['native']))
    call = first['calls'][0]
    result = dict(id=call['id'], native_id=call.get('native_id'), name='echo', result=dict(value='neutral-check'))
    evidence.write('neutral_tool_result', result)
    history.append(dict(kind='tool_results', results=[result]))
    second = adapter.respond(history, dict(phase='neutral_check'), 2)
    if second['calls'] or not second['texts']:
        raise Stop('neutral_final_reply')
    return dict(stop='complete', provider=adapter.provider, model_returned=adapter.discovered_model,
                requests=adapter.budget.attempts, cost=adapter.cost(), step_dollars=str(adapter.budget.read_step()))


def run(provider, output, *, launch=False, approved_commit=None, approval=None):
    config.verify()
    if launch:
        authorized(provider, launch, approved_commit, approval, neutral=True)
        state = State()
    elif approved_commit or approval:
        raise Stop('approval_supplied_without_launch')
    evidence = Evidence(output)
    evidence.write('neutral_check', dict(provider=provider, mode='live' if launch else 'CANNED ENGINEERING ONLY',
        instruction=INSTRUCTION, tools=TOOLS, pins=config.verify()))
    adapter = None
    try:
        with state.locked(output) if launch else nullcontext():
            if launch:
                state.claim_check(provider, approval, output)
                ledger, step = state.ledgers[provider], state.step_ledger
                price = None
            else:
                ledger, step = evidence.directory/'fixture-provider.txt', evidence.directory/'fixture-step.txt'
                ledger.write_text('{"estimated_api_dollars":0}')
                step.write_text('0'); price = prices()
            budget = Budget(provider, ledger, step, evidence, prices=price, state=state if launch else None)
            transport = None if launch else ScriptedTransport([reply(provider,name='echo',args={'value':'neutral-check'}),reply(provider)])
            adapter = Adapter(provider,budget,evidence,system=INSTRUCTION,tools=TOOLS,transport=transport,
                launch=launch,approved_commit=approved_commit,approval=approval,neutral=True,standin=not launch)
            report = exchange(adapter,evidence)
    except Stop as error:
        report = dict(stop=error.reason, provider=provider)
        if adapter is not None:
            report.update(requests=adapter.budget.attempts, cost=adapter.cost(),model_returned=adapter.discovered_model)
    except BaseException as error:
        evidence.close(dict(stop='review_required',type=type(error).__name__))
        raise
    evidence.close(report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--provider',choices=tuple(config.MODELS),required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--launch',action='store_true');p.add_argument('--approved-commit');p.add_argument('--approval',type=Path)
    a=p.parse_args()
    print(json.dumps(run(a.provider,a.output,launch=a.launch,approved_commit=a.approved_commit,
        approval=json.loads(a.approval.read_text()) if a.approval else None),indent=2))


if __name__=='__main__':main()
