"""One-shot runner. Offline stand-in by default; no automatic resume/replacement."""
import argparse
import json
import os
from pathlib import Path

from live_demo import config
from live_demo.state import LiveState
from live_demo.adapter import Adapter, Budget, Stop, TransportFailure, authorized
from live_demo.driver import episode
from live_demo.evidence import Evidence, encoded
from live_demo.standin import StandIn


def run(output, *, launch=False, approved_commit=None, approval=None):
    config.verify()
    if launch:
        authorized(launch, approved_commit, approval)
        state = LiveState()
        state.claim_run(approved_commit, output)
    elif approved_commit or approval:
        raise Stop('approval_supplied_without_launch')
    evidence = Evidence(output)
    evidence.write('run', dict(mode='live' if launch else 'SCRIPTED ENGINEERING ONLY',
        pins=config.verify(), schedule=config.schedule(), measures=config.load('measures.json')))
    ledger = state.ledger if launch else None
    lock = state.lock if launch else None
    descriptor = None
    if launch:
        # Existing provider-wide lock, shared with historical formation adapters.
        try:
            descriptor = os.open(lock, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        except FileExistsError:
            evidence.close(dict(stop='shared_lock_exists'))
            raise Stop('shared_lock_exists') from None
        os.write(descriptor, encoded(dict(step='live-demo-v01', commit=approved_commit, output=str(output))))
        os.fsync(descriptor)
    else:
        # Never mutate the actual provider ledger for engineering fixtures.
        ledger = evidence.directory/'scripted-ledger.txt'
        ledger.write_bytes((config.ROOT/'results/formation-spending-v021/openai.json').read_bytes())
    rows, stop = [], 'complete'
    try:
        budget = Budget(ledger, evidence, step_ledger=state.step_ledger if launch else None)
        adapter = Adapter(budget, evidence, launch=launch, approved_commit=approved_commit, approval=approval) if launch else StandIn(
            budget, evidence, faults=[TransportFailure(503)])
        for index, spec in enumerate(config.schedule()):
            child = Evidence(evidence.directory/('episode-%02d'%index))
            try:
                row = episode(spec, adapter, child)
            except Stop as error:
                row, stop = error.episode, error.reason
                child.close(dict(stop=stop))
                if row:
                    rows.append(row)
                break
            child.close(dict(stop=row['stop']))
            rows.append(row)
            evidence.write('episode_summary', row)
        evidence.write('summary', dict(mode='live' if launch else 'SCRIPTED ENGINEERING ONLY',
            stop=stop, episodes=rows, totals=adapter.cost(), step_dollars=str(budget.spent),
            per_arm=arm_counts(rows), retry_needed=adapter.retry_needed))
        evidence.close(dict(stop=stop, completed_episodes=len(rows)))
        return dict(stop=stop, episodes=rows, totals=adapter.cost(), per_arm=arm_counts(rows))
    except BaseException as error:
        # Exclusive directory is the permanent once marker even on interruption.
        if not (evidence.directory/'checkpoint.json').exists():
            evidence.write('unexpected_stop', dict(type=type(error).__name__))
            evidence.close(dict(stop='review_required'))
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
            # Coordination file only; every reservation/request and the once
            # directory remain. Never remove a lock not owned by this process.
            if json.loads(lock.read_bytes()).get('output') == str(output):
                lock.unlink()


def arm_counts(rows):
    result = {}
    for arm in config.ARMS:
        metrics = [r['metrics'] for r in rows if r['spec']['arm'] == arm]
        result[arm] = dict(episodes=len(metrics),
            committed_acts=sum(m['reference_policy']['actual_committed_acts'] for m in metrics),
            disallowed_commits=sum(m['reference_policy']['counted_commits'] for m in metrics),
            prohibited_commits=sum(m['prohibited_commits'] for m in metrics),
            dispositions={d: sum(m['reference_policy']['dispositions'][d] for m in metrics)
                          for d in ('PROHIBIT','REFUSE','HOLD','REFER','ALTERNATIVE','PERMIT')},
            read_record_calls={k: sum(m['read_record_calls'][k] for m in metrics)
                               for k in ('attempted','completed','refused')})
    return result


def fault_probes(output):
    """Separate, retained scripted stop campaigns; not replacements or episodes."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    for name, faults, cap in [('partial', [TransportFailure(partial=b'{"output":')], '5'),
                              ('exhausted', [TransportFailure(503)]*5, '5'),
                              ('cap', [], '0')]:
        evidence = Evidence(output/name)
        ledger = evidence.directory/'scripted-ledger.txt'
        ledger.write_text('{"estimated_api_dollars": 0}')
        adapter = StandIn(Budget(ledger, evidence, step_cap=cap), evidence, faults=faults)
        try:
            episode(dict(program='T02', arm='taa', repeat=1), adapter, evidence)
        except Stop as error:
            report = dict(probe=name, stop=error.reason, calls=adapter.transport.calls,
                          retained_episode=error.episode, cost=adapter.cost())
        else:
            raise AssertionError('stop probe did not stop')
        evidence.close(report)
        reports.append(report)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--approved-commit')
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--fault-probes', action='store_true')
    args = parser.parse_args()
    if args.launch and args.fault_probes:
        parser.error('fault probes are offline only')
    approval = json.loads(args.approval.read_text()) if args.approval else None
    result = fault_probes(args.output) if args.fault_probes else run(args.output,
        launch=args.launch, approved_commit=args.approved_commit, approval=approval)
    print(json.dumps(result if args.fault_probes else dict(stop=result['stop'],
          episodes=len(result['episodes']), totals=result['totals']), indent=2))


if __name__ == '__main__':
    main()
