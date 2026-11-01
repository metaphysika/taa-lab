"""Dry run by default. Live entry requires a separate exact-commit Actions approval."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

from experiment_b.budget import Budget
from experiment_b.host import Stop
from experiment_b.runner import Evidence
from step3_v02444.audit import audit, summarize
from step3_v02444.config import HARD_CAP, MODELS, configuration, estimate
from step3_v02444.fixtures import DIRECTORY, MAX_REQUESTS, MAX_STEPS, ROOT, arm_block, digest, schedule, text_pin, verify_pins
from step3_v02444.host import Host
from step3_v02444.native import Mechanical
from step3_v02444.standin import Scripted


def source_pins():
    paths = list(DIRECTORY.glob('*.py')) + list(DIRECTORY.glob('*.json')) + [
        DIRECTORY / 'README.md', ROOT / 'tests/test_step3_v02444.py',
        ROOT / '.github/workflows/step3-v02444.yml', ROOT / 'LAB_NOTEBOOK.md', ROOT / 'README.md']
    paths += list((ROOT / 'docs/exploratory/step3-catches').glob('*.md'))
    return {path.relative_to(ROOT).as_posix(): digest(path.read_text(encoding='utf-8').encode('utf-8')) for path in sorted(paths)}


def episode(identity, factory, retain):
    host = Host(identity['case'], identity['twin'])
    retain('episode_start', dict(episode=identity, initial=host.initial(),
                                 arm_block=arm_block(identity['arm']), arm_pin=text_pin(arm_block(identity['arm']))))
    client = factory(identity, host, retain)
    mechanical, horizon, requests, stop_reason = None, None, 0, None
    for request in range(MAX_REQUESTS):
        requests += 1
        try:
            calls = client.request()
        except Mechanical as error:
            mechanical = str(error)
            break
        except Stop as error:
            mechanical, stop_reason = 'NO_REPLY', str(error)
            break
        if not calls:
            break
        results = []
        for call in calls:
            if host.steps >= MAX_STEPS or host.closed:
                horizon = 'step_limit' if host.steps >= MAX_STEPS else 'closed'
                break
            result = host.execute(call['name'], call['arguments'])
            results.append(dict(id=call['id'], name=call['name'], result=result))
            if result['status'] == 'error':
                mechanical = 'MALFORMED'
                break
        retain('host_journal', deepcopy(host.journal))
        client.results(results)
        if mechanical:
            break
        if host.closed or host.steps >= MAX_STEPS:
            horizon = 'closed' if host.closed else 'step_limit'
            break
    else:
        horizon = 'request_limit'
    row = dict(episode=identity, requests=requests, horizon=horizon, stop_reason=stop_reason, journal=host.journal,
               audit=audit(identity['case'], identity['twin'], host.journal, mechanical))
    retain('episode_end', row)
    return row


def pipeline(factory, retain, models=MODELS):
    rows = []
    for identity in schedule(models):
        rows.append(episode(identity, factory, retain))
        if rows[-1]['audit']['mechanical']:
            break
    result = summarize(rows, models)
    result['stop_reason'] = rows[-1]['stop_reason'] or rows[-1]['audit']['mechanical'] if rows else None
    retain('summary', result)
    return result


def offline(directory, mode):
    evidence = Evidence(directory)
    try:
        evidence.retain('manifest', dict(mode='OFFLINE_SCRIPTED', model_calls=0, spend='0', pins=verify_pins(), estimate=estimate()))
        result = pipeline(lambda identity, host, retain: Scripted(host, mode), evidence.retain)
        result.update(mode='OFFLINE_SCRIPTED', standin=mode, scientific_headroom=False, model_calls=0, spend='0')
        return result
    finally:
        evidence.close()


def claim_approval(path):
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise Stop('separate_exact_commit_actions_approval_required')
    approval = json.loads(Path(path).read_text(encoding='utf-8'))
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise Stop('clean_checkout_required')
    if (approval.get('gate') != 'STEP3_V02444' or approval.get('approved_by') != 'Chris Lahn'
            or approval.get('commit') != head or os.environ.get('GITHUB_SHA') != head
            or approval.get('configuration') != configuration() or approval.get('source_pins') != source_pins()):
        raise Stop('exact_commit_configuration_or_source_approval_mismatch')
    if not approval.get('approval_quote') or approval.get('acknowledged_model_count') != 2:
        raise Stop('explicit_paid_approval_and_two_model_acknowledgment_required')
    expiry = datetime.fromisoformat(approval['expires_utc'].replace('Z', '+00:00'))
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise Stop('approval_expired')
    for field, variable in (('repository', 'GITHUB_REPOSITORY'), ('workflow_ref', 'GITHUB_WORKFLOW_REF'),
                            ('run_number', 'GITHUB_RUN_NUMBER'), ('run_attempt', 'GITHUB_RUN_ATTEMPT')):
        if str(approval.get('actions', {}).get(field)) != os.environ.get(variable):
            raise Stop('actions_run_binding_mismatch')
    if approval['actions']['repository'] != 'metaphysika/taa-lab' or os.environ.get('GITHUB_RUN_ATTEMPT') != '1':
        raise Stop('repository_or_rerun_not_approved')
    with Path(str(path) + '.used').open('x', encoding='utf-8') as handle:
        handle.write(head)
    return approval


def approved_run(path, directory):
    approval = claim_approval(path)
    from experiment_b.ledger import check_ledger
    from experiment_b.transport import HTTPS
    from step3_v02444.native import Wire

    config = configuration()
    evidence = Evidence(directory)
    budget = Budget(config, evidence.retain)
    budget.cap = min(budget.cap, HARD_CAP)
    deadline = time.monotonic() + config['runtime_bound_seconds']
    try:
        evidence.retain('manifest', dict(mode='EXPLORATORY_STEP3', approval=approval, pins=verify_pins(), estimate=estimate()))
        check_ledger(config, evidence.retain)

        def factory(identity, host, retain):
            if time.monotonic() >= deadline:
                raise Stop('approved_runtime_bound')
            provider = config['providers'][identity['model']]
            client = Wire(provider, identity['arm'], HTTPS(provider, deadline, retain), retain,
                          budget.account(identity['model']))
            client.start(host.initial())
            return client

        result = pipeline(factory, evidence.retain)
        if result['stop_reason']:
            evidence.retain('stop', dict(reason=result['stop_reason'], dollars_reserved_or_spent_upper=str(budget.spent)))
        return result
    except Exception as error:
        evidence.retain('stop', dict(reason=str(error), dollars_reserved_or_spent_upper=str(budget.spent),
                                     provider_spend={model: str(value) for model, value in budget.providers.items()}))
        raise
    finally:
        evidence.retain('spend', dict(total=str(budget.spent), cap=str(HARD_CAP),
                                      providers={model: str(value) for model, value in budget.providers.items()}))
        evidence.close()


def main():
    parser = argparse.ArgumentParser(description='EXPLORATORY step 3 v0.24.44; default is dry run, no calls')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--scripted', choices=('obedient', 'careful'))
    mode.add_argument('--approved-run')
    parser.add_argument('--output')
    args = parser.parse_args()
    print(json.dumps(dict(cost_estimate=estimate()), sort_keys=True), flush=True)
    if not args.scripted and not args.approved_run:
        print(json.dumps(dict(mode='DRY_RUN', model_calls=0, spend='0', pins=verify_pins(),
                              schedule=schedule(MODELS), configuration=configuration()), sort_keys=True, indent=2))
        return
    if not args.output:
        parser.error('--output must name a NEW directory outside the repository')
    if Path(args.output).resolve().is_relative_to(ROOT):
        parser.error('evidence output must be outside the repository; existing journals/results stay untouched')
    try:
        result = offline(args.output, args.scripted) if args.scripted else approved_run(args.approved_run, args.output)
    except (Stop, ValueError, KeyError, OSError) as error:
        parser.exit(2, 'STOP: ' + str(error) + '\n')
    print(json.dumps(result, sort_keys=True, indent=2))
    if result.get('stop_reason'):
        parser.exit(2, 'STOP: ' + result['stop_reason'] + '\n')


if __name__ == '__main__':
    main()
