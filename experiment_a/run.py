"""One-shot D+P runner, no sealed inputs, quality retries or resume path."""
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
from experiment_a.standin import ScriptedTransport, reply, prices


def run(output, *, launch=False, approved_commit=None, approval=None):
    config.verify()
    if launch:
        for provider in config.MODELS:
            authorized(provider,launch,approved_commit,approval)
        state=State()
    elif approved_commit or approval:
        raise Stop('approval_supplied_without_launch')
    evidence=Evidence(output)
    schedule=config.load('pilot-order.json')
    evidence.write('run',dict(mode='live' if launch else 'CANNED ENGINEERING ONLY',pins=config.verify(),
                             schedule=schedule,measures=config.load('measures.json')))
    rows,stop=[], 'complete'
    try:
        with state.locked(output) if launch else nullcontext():
            if launch:
                state.claim_run(approval,output)
            adapters={}
            retry_tracker={'retry_needed':0}
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
    a=p.parse_args()
    result=run(a.output,launch=a.launch,approved_commit=a.approved_commit,
               approval=json.loads(a.approval.read_text()) if a.approval else None)
    print(json.dumps(dict(stop=result['stop'],episodes=len(result['episodes'])),indent=2))


if __name__=='__main__':main()
