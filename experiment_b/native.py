"""Native wire adapters with injected transport; no credentials or network imports."""
from copy import deepcopy
import json

from experiment_b.fixtures import BRIEF, TOOLS, definitions
from experiment_b.host import Stop


def integer(value):
    if type(value) is not int or value < 0:
        raise Stop('missing_or_invalid_usage')
    return value


class Native:
    def __init__(self, provider, model, settings, send, retain, account=None):
        if provider not in ('responses', 'anthropic') or not model:
            raise Stop('unknown_identity')
        reserved = {'model', 'input', 'messages', 'system', 'instructions', 'tools',
                    'stream', 'previous_response_id', 'parallel_tool_calls', 'store', 'include', 'tool_choice'}
        if reserved.intersection(settings):
            raise Stop('reserved_settings')
        self.provider, self.model = provider, model
        self.settings, self.send, self.retain = deepcopy(settings), send, retain
        self.history = []
        self.call_ids = set()
        self.account = account

    def start(self, initial):
        self.history = [dict(role='user', content=json.dumps(initial, sort_keys=True))]

    def request(self):
        body = dict(model=self.model, **deepcopy(self.settings))
        if self.provider == 'responses':
            body.update(instructions=BRIEF.read_text(encoding='utf-8'), input=deepcopy(self.history),
                        tools=[dict(type='function', strict=False, **tool) for tool in definitions()],
                        parallel_tool_calls=True, store=False, include=['reasoning.encrypted_content'])
        else:
            body.update(system=BRIEF.read_text(encoding='utf-8'), messages=deepcopy(self.history),
                        tools=[dict(name=tool['name'], description=tool['description'],
                                    input_schema=tool['parameters']) for tool in definitions()])
        self.retain('request', body)
        if self.account:
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
            if reply.get('status') != 'completed' or reply.get('error') or reply.get('incomplete_details'):
                raise Stop('incomplete_response')
            inp, out = integer(usage.get('input_tokens')), integer(usage.get('output_tokens'))
            if integer(usage.get('total_tokens')) != inp + out:
                raise Stop('usage_bound')
            cached = integer(usage.get('input_tokens_details', {}).get('cached_tokens', 0))
            reasoning = integer(usage.get('output_tokens_details', {}).get('reasoning_tokens', 0))
            if cached > inp or reasoning > out:
                raise Stop('usage_bound')
            native = reply.get('output')
            allowed = {'message', 'reasoning', 'function_call'}
        else:
            if reply.get('stop_reason') not in ('tool_use', 'end_turn'):
                raise Stop('incomplete_response')
            inp = sum(integer(usage.get(field, 0)) for field in (
                'cache_read_input_tokens', 'cache_creation_input_tokens')) + integer(usage.get('input_tokens'))
            out = integer(usage.get('output_tokens'))
            native = reply.get('content')
            allowed = {'text', 'thinking', 'redacted_thinking', 'tool_use'}
        if type(native) is not list or not native or any(
                type(item) is not dict or item.get('type') not in allowed for item in native):
            raise Stop('unknown_output')
        calls = []
        for item in native:
            if self.provider == 'responses' and item.get('status') not in (None, 'completed'):
                raise Stop('incomplete_output_item')
            if item['type'] == 'message':
                if any(part.get('type') not in ('output_text', 'refusal') for part in item.get('content', [])):
                    raise Stop('unknown_output')
            if item['type'] in ('function_call', 'tool_use'):
                identity = item.get('call_id') if self.provider == 'responses' else item.get('id')
                if not identity or identity in self.call_ids or item.get('name') not in TOOLS:
                    raise Stop('invalid_tool_id')
                self.call_ids.add(identity)
                try:
                    arguments = json.loads(item['arguments']) if self.provider == 'responses' else item['input']
                except (KeyError, ValueError, TypeError) as error:
                    raise Stop('invalid_tool_arguments') from error
                if type(arguments) is not dict:
                    raise Stop('invalid_tool_arguments')
                calls.append(dict(id=identity, name=item['name'], arguments=arguments))
        if self.provider == 'anthropic' and bool(calls) != (reply['stop_reason'] == 'tool_use'):
            raise Stop('inconsistent_stop_reason')
        if self.provider == 'responses':
            self.history.extend(deepcopy(native))
        else:
            self.history.append(dict(role='assistant', content=deepcopy(native)))
        receipt = dict(input=inp, output=out, native=deepcopy(usage))
        if self.account:
            self.account.settle(receipt)
        return calls, receipt

    def results(self, results, updates):
        if self.provider == 'responses':
            self.history.extend(dict(type='function_call_output', call_id=result['id'],
                                     output=json.dumps(result['result'], sort_keys=True)) for result in results)
            if updates:
                self.history.append(dict(role='user', content=json.dumps(dict(updates=updates))))
        else:
            content = [dict(type='tool_result', tool_use_id=result['id'],
                            content=json.dumps(result['result'], sort_keys=True)) for result in results]
            if updates:
                content.append(dict(type='text', text=json.dumps(dict(updates=updates))))
            self.history.append(dict(role='user', content=content))
