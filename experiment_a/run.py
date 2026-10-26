"""D+P runner; a reviewed continuation runs only a verified untouched suffix."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path

from live_demo.adapter import Stop
from live_demo.evidence import Evidence
from experiment_a import config
from experiment_a.adapter import Adapter, authorized
from experiment_a.budget import Budget
from experiment_a.driver import episode
from experiment_a.state import State
from experiment_a.continuation import Continuation
from experiment_a.standin import ScriptedTransport, reply, prices


def run(output, *, launch=False, approved_commit=None, approval=None, continue_from=None, continuation=None):
    config.verify()
    plan = None
    if continue_from or continuation is not None:
        if not launch or not continue_from or type(continuation) is not int or continuation < 1 or not approval or approval.get('continuation') != continuation:
            raise Stop('continuation_not_approved')
        plan = Continuation(continue_from,approval)
    elif approval and 'continuation' in approval:
        raise Stop('continuation_sources_required')
    if launch:
        for provider in config.MODELS:
            authorized(provider,launch,approved_commit,approval)
        state=State()
        if plan is not None:
            plan.validate(state)
    elif approved_commit or approval:
        raise Stop('approval_supplied_without_launch')
    evidence=Evidence(output)
    schedule=config.load('pilot-order.json')
    evidence.write('run',dict(mode='live' if launch else 'CANNED ENGINEERING ONLY',pins=config.verify(),
                             schedule=schedule,measures=config.load('measures.json'),approved_commit=approved_commit,
                             continuation=None if plan is None else dict(number=plan.number,start_index=plan.start_index,
                                                                         source_checkpoints=plan.checkpoints)))
    rows,stop=[], 'complete'
    try:
        with state.locked(output,continuation=plan) if launch else nullcontext():
            if launch:
                if plan is None:
                    state.claim_run(approval,output)
                else:
                    state.claim_continuation(approval,output,plan)
                    state.continuation_guard=lambda: plan.validate(state,evidence)
            adapters={}
            retry_tracker={'retry_needed':plan.retry_needed if plan else 0}
            if not launch:
                step=evidence.directory/'fixture-step.txt';step.write_text('0')
            for provider in config.MODELS:
                if launch:
                    ledger,step,price=state.ledgers[provider],state.step_ledger,None
                else:
                    ledger=evidence.directory/('fixture-'+provider+'.txt');ledger.write_text('{"estimated_api_dollars":0}')
                    price=prices()
                budget=Budget(provider,ledger,step,evidence,prices=price,state=state if launch else None)
                transport=None if launch else ScriptedTransport([reply(provider)]*sum(s['provider']==provider for s in schedule))
                adapters[provider]=Adapter(provider,budget,evidence,transport=transport,standin=not launch,
                    launch=launch,approved_commit=approved_commit,approval=approval,retry_tracker=retry_tracker)
            for index,spec in enumerate(schedule):
                if plan is not None and index < plan.start_index:
                    continue
                child=Evidence(evidence.directory/('episode-%04d'%index))
                try:
                    row=episode(spec,adapters[spec['provider']],child)
                except Stop as error:
                    stop=error.reason
                    if error.episode:rows.append(error.episode)
                    child.close(dict(stop=stop));break
                child.close(dict(stop=row['stop']));rows.append(row)
                evidence.write('episode_summary',row)
            report=dict(stop=stop,episodes=rows,costs={p:a.cost() for p,a in adapters.items()},
                step_dollars=str(next(iter(adapters.values())).budget.read_step()),retry_needed=retry_tracker['retry_needed'])
            if plan is not None:
                report.update(start_index=plan.start_index,prior_episodes=len(plan.rows))
            evidence.write('summary',report)
    except Stop as error:
        report=dict(stop=error.reason,episodes=rows)
    except BaseException as error:
        evidence.close(dict(stop='review_required',type=type(error).__name__));raise
    evidence.close(dict(stop=report['stop'],episodes=len(rows)))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--launch',action='store_true')
    p.add_argument('--approved-commit');p.add_argument('--approval',type=Path)
    p.add_argument('--continue-from',type=Path,action='append',help='all prior pilot roots, oldest first; never a resume in place')
    p.add_argument('--continuation',type=int,help='separately approved next numbered continuation')
    a=p.parse_args()
    result=run(a.output,launch=a.launch,approved_commit=a.approved_commit,
               approval=json.loads(a.approval.read_text()) if a.approval else None,
               continue_from=a.continue_from,continuation=a.continuation)
    print(json.dumps(dict(stop=result['stop'],episodes=len(result['episodes'])),indent=2))


if __name__=='__main__':main()
