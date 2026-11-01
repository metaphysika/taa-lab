"""Versioned native adapter, injected transport and no quality retries."""
from copy import deepcopy
import json

from experiment_b.host import Stop
from experiment_b.native import Native, integer
from step3_v02444.fixtures import arm_block
from step3_v02444.host import SCHEMAS, definitions


class Mechanical(Stop):
    pass


class Wire(Native):
    def __init__(self, provider, arm, send, retain, account):
        super().__init__(provider['protocol'], provider['model_id'], provider['settings'], send, retain, account)
        self.block = arm_block(arm)

    def request(self):
        body = dict(model=self.model, **deepcopy(self.settings))
        if self.provider == 'responses':
            body.update(instructions=self.block, input=deepcopy(self.history),
                        tools=[dict(type='function', strict=False, **tool) for tool in definitions()],
                        parallel_tool_calls=True, store=False, include=['reasoning.encrypted_content'])
        else:
            body.update(system=self.block, messages=deepcopy(self.history),
                        tools=[dict(name=tool['name'], description=tool['description'], input_schema=tool['parameters'])
                               for tool in definitions()])
        self.retain('request', body)
        self.account.reserve(body)
        try:
            reply = self.send(deepcopy(body))
        except Stop:
            raise
        except Exception as error:
            self.retain('transport_failure', dict(type=type(error).__name__))
            raise Stop('transport_failure') from error
        self.retain('response', reply)
        if type(reply) is not dict or reply.get('model') != self.model or not reply.get('id'):
            raise Stop('identity_mismatch')
        usage = reply.get('usage')
        if type(usage) is not dict:
            raise Stop('missing_usage')
        if self.provider == 'responses':
            inp, out = integer(usage.get('input_tokens')), integer(usage.get('output_tokens'))
            if integer(usage.get('total_tokens')) != inp + out:
                raise Stop('usage_bound')
            if reply.get('status') != 'completed' or reply.get('error') or reply.get('incomplete_details'):
                raise Mechanical('MALFORMED')
            content = reply.get('output')
            allowed = ('message', 'reasoning', 'function_call')
        else:
            inp = sum(integer(usage.get(field, 0)) for field in ('cache_read_input_tokens', 'cache_creation_input_tokens'))
            inp += integer(usage.get('input_tokens'))
            out = integer(usage.get('output_tokens'))
            if reply.get('stop_reason') not in ('tool_use', 'end_turn'):
                raise Mechanical('MALFORMED')
            content = reply.get('content')
            allowed = ('text', 'thinking', 'redacted_thinking', 'tool_use')
        self.account.settle(dict(input=inp, output=out, native=usage))
        if not content:
            raise Mechanical('NO_REPLY')
        if type(content) is not list or any(type(item) is not dict or item.get('type') not in allowed for item in content):
            raise Mechanical('MALFORMED')
        calls, visible = [], False
        for item in content:
            if self.provider == 'responses' and item.get('status') not in (None, 'completed'):
                raise Mechanical('MALFORMED')
            if item['type'] in ('function_call', 'tool_use'):
                identity = item.get('call_id') if self.provider == 'responses' else item.get('id')
                if type(identity) is not str or not identity or identity in self.call_ids or item.get('name') not in SCHEMAS:
                    raise Mechanical('MALFORMED')
                self.call_ids.add(identity)
                try:
                    arguments = json.loads(item['arguments']) if self.provider == 'responses' else item['input']
                except (KeyError, TypeError, ValueError) as error:
                    raise Mechanical('MALFORMED') from error
                if type(arguments) is not dict:
                    raise Mechanical('MALFORMED')
                calls.append(dict(id=identity, name=item['name'], arguments=arguments))
                visible = True
            elif item['type'] == 'message':
                parts = item.get('content')
                if type(parts) is not list or any(type(part) is not dict or part.get('type') not in ('output_text', 'refusal') for part in parts):
                    raise Mechanical('MALFORMED')
                visible |= any(bool(part.get('text') or part.get('refusal')) for part in parts)
            elif item['type'] == 'text':
                visible |= bool(item.get('text'))
        if not visible:
            raise Mechanical('NO_REPLY')
        if self.provider == 'anthropic' and bool(calls) != (reply['stop_reason'] == 'tool_use'):
            raise Mechanical('MALFORMED')
        if self.provider == 'responses':
            self.history.extend(deepcopy(content))
        else:
            self.history.append(dict(role='assistant', content=deepcopy(content)))
        return calls

    def results(self, results):
        super().results(results, [])
