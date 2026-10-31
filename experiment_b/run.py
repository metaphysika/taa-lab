"""No-credential offline entrypoint; live dispatch is separately gated."""
import argparse
import json
import os
import time

from experiment_b.approval import claim_approval
from experiment_b.audit import summarize
from experiment_b.budget import Budget
from experiment_b.fixtures import verify
from experiment_b.host import Stop
from experiment_b.ledger import check_ledger
from experiment_b.native import Native
from experiment_b.runner import Evidence, run
from experiment_b.standin import ScriptedWire
from experiment_b.transport import HTTPS


def offline(directory, mode='key_following'):
    pins = verify()
    evidence = Evidence(directory)
    try:
        evidence.retain('manifest', dict(mode='OFFLINE_SYNTHETIC', standin=mode, pins=pins,
                                         model_calls=0, spend='0', scientific_headroom=False))

        def factory(identity, host, log):
            provider = 'responses' if identity['model'] == 'Luna' else 'anthropic'
            model = 'offline-' + identity['model']
            return Native(provider, model, {}, ScriptedWire(host, provider, model, mode), log)

        rows = run(factory, evidence.retain)
        result = summarize(rows)
        result.update(mode='OFFLINE_SYNTHETIC', scientific_headroom=False, model_calls=0, spend='0')
        evidence.retain('summary', result)
        return result
    finally:
        evidence.close()


def approved_run(path, directory):
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise Stop('approved_actions_route_required')
    approval, configuration = claim_approval(path)
    if os.environ.get('GITHUB_SHA') != approval['commit']:
        raise Stop('actions_commit_mismatch')
    for field, variable in (('repository', 'GITHUB_REPOSITORY'), ('workflow_ref', 'GITHUB_WORKFLOW_REF'),
                            ('run_number', 'GITHUB_RUN_NUMBER'), ('run_attempt', 'GITHUB_RUN_ATTEMPT')):
        if os.environ.get(variable) != str(approval['actions'][field]):
            raise Stop('actions_run_binding_mismatch')
    evidence = Evidence(directory)
    budget = Budget(configuration, evidence.retain)
    started = time.monotonic()
    try:
        evidence.retain('manifest', dict(mode='GATE1B', approval=approval, pins=verify()))
        check_ledger(configuration, evidence.retain)

        def factory(identity, host, log):
            if time.monotonic() - started >= configuration['runtime_bound_seconds']:
                raise Stop('approved_runtime_bound')
            provider = configuration['providers'][identity['model']]
            return Native(provider['protocol'], provider['model_id'], provider['settings'],
                          HTTPS(provider, started + configuration['runtime_bound_seconds'], log),
                          log, account=budget.account(identity['model']))

        def after_episode(rows):
            budget.project(rows)
            if time.monotonic() - started >= configuration['runtime_bound_seconds']:
                raise Stop('approved_runtime_bound')

        rows = run(factory, evidence.retain, after_episode)
        result = summarize(rows)
        result.update(mode='GATE1B', dollars_upper=str(budget.spent), requests=budget.requests)
        evidence.retain('summary', result)
        return result
    except Stop as error:
        evidence.retain('stop', dict(reason=str(error), dollars_reserved_or_spent_upper=str(budget.spent)))
        raise
    finally:
        evidence.close()


def main():
    parser = argparse.ArgumentParser(description='Step 1 A0 probe; offline unless Gate 1b is supplied')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--offline', action='store_true')
    mode.add_argument('--approved-run', metavar='GATE1B_JSON')
    parser.add_argument('--output', required=True)
    parser.add_argument('--standin', choices=['key_following', 'compliant', 'cautious', 'adversarial'], default='key_following')
    args = parser.parse_args()
    try:
        result = offline(args.output, args.standin) if args.offline else approved_run(args.approved_run, args.output)
    except Stop as error:
        parser.exit(2, 'STOP: ' + str(error) + '\n')
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
