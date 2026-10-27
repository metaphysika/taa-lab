"""D+P runner; a reviewed continuation runs only a verified untouched suffix."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path

from live_demo.adapter import Stop
from live_demo.evidence import Evidence, verify
from experiment_a import config
from experiment_a.adapter import Adapter, authorized
from experiment_a.budget import Budget
from experiment_a.driver import episode
from experiment_a.state import State
from experiment_a.publication import Publisher
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
        state=State(continuation=plan) if plan is not None else State()
        if plan is not None:
            plan.validate(state)
        publisher=Publisher()
    elif approved_commit or approval:
        raise Stop('approval_supplied_without_launch')
    evidence=Evidence(output)
    if launch:
        state.evidence=evidence
    schedule=config.load('pilot-order.json')
    evidence.write('run',dict(mode='live' if launch else 'CANNED ENGINEERING ONLY',pins=config.verify(),
                             schedule=schedule,measures=config.load('measures.json'),approved_commit=approved_commit,
                             continuation=None if plan is None else dict(number=plan.number,start_index=plan.start_index,
                                                                         source_checkpoints=plan.checkpoints),
                             **(dict(approval=approval) if launch and approval.get('standing') else {})))
    rows,stop=[], 'complete'
    try:
        with state.locked(output,continuation=plan) if launch else nullcontext():
            if launch:
                if plan is None:
                    state.claim_run(approval,output)
                else:
                    state.claim_continuation(approval,output,plan)
                    state.continuation_guard=lambda: plan.validate(state,evidence)
            if launch and plan is not None:
                for source in plan.sources:
                    for child in sorted(source.glob('episode-*')):
                        publish_child(publisher,state,child,evidence,source_root=source)
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
                    child.close(dict(stop=stop))
                    if launch:publish_child(publisher,state,child.directory,evidence)
                    break
                child.close(dict(stop=row['stop']));rows.append(row)
                evidence.write('episode_summary',row)
                if launch:publish_child(publisher,state,child.directory,evidence)
            report=dict(stop=stop,episodes=rows,costs={p:a.cost() for p,a in adapters.items()},
                step_dollars=str(next(iter(adapters.values())).budget.read_step()),retry_needed=retry_tracker['retry_needed'])
            if plan is not None:
                report.update(start_index=plan.start_index,prior_episodes=len(plan.rows))
            evidence.write('summary',report)
    except Stop as error:
        if launch:state.failed=True
        report=dict(stop=error.reason,episodes=rows)
    except BaseException as error:
        evidence.close(dict(stop='review_required',type=type(error).__name__));raise
    evidence.close(dict(stop=report['stop'],episodes=len(rows)))
    if launch and not publisher.failed and list(evidence.directory.glob('episode-*')):
        # Root closure/summary is durable too. Confirmation evidence has its own
        # chain: never append to, or rewrite, the just-sealed root.
        publication=Evidence(evidence.directory/'publication')
        try:
            publisher.publish_episode(sorted(evidence.directory.glob('episode-*'))[-1],publication,
                                      source_root=evidence.directory)
        except Stop as error:
            publication.close(dict(stop=error.reason))
            report['stop']=error.reason
        else:publication.close(dict(stop='complete'))
    return report


def publish_child(publisher,state,child,evidence,**kwargs):
    try: publisher.publish_episode(child,evidence,**kwargs)
    except BaseException:
        state.failed=True
        raise


def run_standing(output, *, approval, continue_from, continuation, approved_commit, launch=False, standing_next=False):
    from experiment_a.standing import binding, successor
    from experiment_a.continuation import frames
    b=binding(approval)
    if not launch or b is None:raise Stop('standing_not_approved')
    sources=list(continue_from or [])
    if standing_next:
        if not sources:raise Stop('standing_not_approved')
        fs,_=frames(Path(sources[-1]));prior=fs[0]['value'].get('approval')
        pb=binding(prior) if isinstance(prior,dict) else None
        if pb is None or pb['receipt']!=b['receipt']:raise Stop('standing_not_approved')
        approval=successor(prior,[Path(p) for p in sources]);continuation=approval['continuation']
    for provider in config.MODELS:
        authorized(provider,True,approved_commit,approval)
    initial=Path(output)
    controller=Evidence(initial.parent/(initial.name+'-standing'))
    try:
        while True:
            controller.write('standing_segment',dict(approval=approval,output=str(output)))
            result=run(output,launch=True,approved_commit=approved_commit,approval=approval,
                       continue_from=sources,continuation=continuation)
            sources.append(Path(output))
            controller.write('segment_result',dict(stop=result['stop'],checkpoint=verify(output)))
            if result['stop']=='complete' or result['stop'] not in approval['standing']['allowed_stop_reasons']:
                break
            try: approval=successor(approval,sources)
            except Stop as error:
                controller.write('standing_refused',dict(reason=error.reason));break
            continuation=approval['continuation']
            output=initial.parent/(initial.name+'-continuation-%06d'%continuation)
    except Stop as error:
        controller.close(dict(stop=error.reason));raise
    except BaseException:
        controller.close(dict(stop='review_required'));raise
    controller.close(dict(stop=result['stop']))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--launch',action='store_true')
    p.add_argument('--approved-commit');p.add_argument('--approval',type=Path)
    p.add_argument('--continue-from',type=Path,action='append',help='all prior pilot roots, oldest first; never a resume in place')
    p.add_argument('--continuation',type=int,help='separately approved next numbered continuation')
    p.add_argument('--standing-next',action='store_true',help='derive the next segment from the same standing receipt and every closed prior root; never resume a root')
    a=p.parse_args()
    approval=json.loads(a.approval.read_text()) if a.approval else None
    runner=run_standing if approval and 'standing' in approval else run
    if a.standing_next and runner is run:raise Stop('standing_not_approved')
    result=runner(a.output,launch=a.launch,approved_commit=a.approved_commit,approval=approval,
               continue_from=a.continue_from,continuation=a.continuation,
               **(dict(standing_next=a.standing_next) if runner is run_standing else {}))
    print(json.dumps(dict(stop=result['stop'],episodes=len(result['episodes'])),indent=2))


if __name__=='__main__':main()
