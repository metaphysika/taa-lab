"""Two-request neutral compatibility check. Canned stand-in unless launched.

No W0/program inputs. A separately approved real check uses its own once claim,
the existing provider lock and the SAME persisted $5 step budget as the run.
"""
import argparse
import json
import os
from pathlib import Path

from live_demo import config
from live_demo.adapter import Adapter, Budget, Stop, authorized
from live_demo.evidence import Evidence, encoded
from live_demo.standin import ScriptedTransport, function, done
from taa_gateway.serialization import parse_json

INSTRUCTION = 'Call echo once with value "neutral-check". After receiving the result, reply briefly without a tool call.'
TOOLS = [dict(type='function', name='echo', description='Return the supplied value.', strict=False,
    parameters=dict(type='object', properties=dict(value=dict(type='string')),
                    required=['value'], additionalProperties=False))]


class CheckAdapter(Adapter):
    max_attempts = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.discovered_model = self.approval.get('model_returned') if self.approval is not None else None

    def _authorize(self):
        authorized(self.launch, self.approved_commit, self.approval, allow_model_discovery=True)

    def body(self, history):
        return dict(model=config.MODEL, instructions=INSTRUCTION, input=history, tools=TOOLS,
                    max_output_tokens=config.OUTPUT_TOKENS, store=False,
                    include=['reasoning.encrypted_content'])

    def expected_model(self, reply):
        returned = reply.get('model')
        if type(returned) is not str or not returned:
            raise Stop('model_identity')
        if self.discovered_model is None:
            self.discovered_model = returned
        return self.discovered_model


class CheckStandIn(CheckAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, transport=ScriptedTransport(), **kwargs)

    def _authorize(self):
        if type(self.transport) is not ScriptedTransport:
            raise Stop('standin_transport_only')

    def respond(self, history, spec, turn):
        reasoning = dict(type='reasoning', id='neutral-reasoning-%s'%turn,
                         encrypted_content='canned-encrypted-%s'%turn,
                         summary=[dict(type='summary_text', text='Canned neutral fixture.')])
        self.transport.output = [reasoning, function('echo', {'value':'neutral-check'}, 1) if turn == 1 else done()]
        return super().respond(history, spec, turn)


def exchange(adapter, evidence):
    history = [dict(role='user', content='Please perform the neutral echo task.')]
    first = adapter.respond(history, dict(phase='neutral_check'), 1)
    calls = [item for item in first['output'] if item['type'] == 'function_call']
    if len(calls) != 1 or calls[0]['name'] != 'echo':
        raise Stop('neutral_function_call')
    try:
        args = parse_json(calls[0]['arguments'])
    except (ValueError, TypeError):
        raise Stop('neutral_function_arguments') from None
    if args != {'value':'neutral-check'}:
        raise Stop('neutral_function_arguments')
    history.extend(first['output'])
    result = dict(type='function_call_output', call_id=calls[0]['call_id'], output=encoded(args).decode())
    evidence.write('neutral_tool_result', result)
    history.append(result)
    second = adapter.respond(history, dict(phase='neutral_check'), 2)
    if (any(item['type'] == 'function_call' for item in second['output']) or
            not any(item['type'] == 'message' for item in second['output'])):
        raise Stop('neutral_final_reply')
    return dict(stop='complete', model_returned=adapter.discovered_model,
                requests=adapter.budget.attempts, cost=adapter.cost(), step_dollars=str(adapter.budget.spent))


def run(output, *, launch=False, approved_commit=None, approval=None):
    config.verify()
    if launch:
        # Null model_returned is permitted only for first-check discovery. Its
        # returned string is pinned immediately for the second request.
        authorized(launch, approved_commit, approval, allow_model_discovery=True)
        with (config.ROOT/'results/live-demo-check-v01.once').open('xb') as stream:
            stream.write(encoded(dict(commit=approved_commit, output=str(output))))
            stream.flush(); os.fsync(stream.fileno())
    elif approved_commit or approval:
        raise Stop('approval_supplied_without_launch')
    evidence = Evidence(output)
    evidence.write('neutral_check', dict(mode='live' if launch else 'CANNED ENGINEERING ONLY',
        instruction=INSTRUCTION, tools=TOOLS, pins=config.verify()))
    lock = config.ROOT/'results/formation-spending-v021/run.lock'
    ledger = config.ROOT/'results/formation-spending-v021/openai.json'
    descriptor = None
    adapter = None
    try:
        if launch:
            try:
                descriptor = os.open(lock, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            except FileExistsError:
                raise Stop('shared_lock_exists') from None
            os.write(descriptor, encoded(dict(step='live-demo-v01', phase='neutral', output=str(output))))
            os.fsync(descriptor)
        else:
            ledger = evidence.directory/'scripted-ledger.txt'
            ledger.write_bytes((config.ROOT/'results/formation-spending-v021/openai.json').read_bytes())
        budget = Budget(ledger, evidence, step_ledger=config.ROOT/'results/live-demo-v01-budget.txt' if launch else None)
        adapter = (CheckAdapter if launch else CheckStandIn)(budget, evidence,
            launch=launch, approved_commit=approved_commit, approval=approval)
        report = exchange(adapter, evidence)
    except Stop as error:
        report = dict(stop=error.reason)
        if adapter is not None:
            report.update(model_returned=adapter.discovered_model, requests=adapter.budget.attempts,
                          cost=adapter.cost(), step_dollars=str(adapter.budget.spent))
    except BaseException as error:
        evidence.close(dict(stop='review_required', type=type(error).__name__))
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
            if json.loads(lock.read_bytes()).get('output') == str(output):
                lock.unlink()
    evidence.close(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--approved-commit')
    parser.add_argument('--approval', type=Path)
    args = parser.parse_args()
    report = run(args.output, launch=args.launch, approved_commit=args.approved_commit,
                 approval=json.loads(args.approval.read_text()) if args.approval else None)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['stop'] == 'complete' else 1)


if __name__ == '__main__':
    main()
