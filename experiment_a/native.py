"""Native requests and lossless assistant history; no sampling overrides."""
from copy import deepcopy
import json

from live_demo.adapter import Stop
from live_demo.evidence import encoded
from experiment_a import config

OUTPUT_TYPES = frozenset(('text', 'thinking', 'redacted_thinking', 'tool_use'))


def integer(value):
    if type(value) is not int or value < 0:
        raise Stop('missing_usage')
    return value


def body(provider, system, tools, history):
    if provider == 'anthropic':
        messages = []
        for event in history:
            if event['kind'] == 'user':
                content = event['text']
                if not messages:
                    # The initial brief is the stable conversation prefix. Three
                    # 5m breakpoints total; never annotate signed assistant blocks.
                    content = [dict(type='text', text=content,
                                    cache_control=dict(type='ephemeral'))]
                messages.append(dict(role='user', content=content))
            elif event['kind'] == 'assistant':
                messages.append(deepcopy(event['native']))
            elif event['kind'] == 'tool_results':
                messages.append(dict(role='user', content=[dict(type='tool_result',
                    tool_use_id=r['id'], content=encoded(r['result']).decode()) for r in event['results']]))
            else:
                raise Stop('unknown_history')
        definitions = [dict(name=t['name'], description=t['description'],
                            input_schema=deepcopy(t['parameters'])) for t in tools]
        if definitions:
            # A breakpoint on the last tool caches the whole definitions prefix.
            definitions[-1]['cache_control'] = dict(type='ephemeral')
        return dict(model=config.MODELS[provider],
                    system=[dict(type='text', text=system, cache_control=dict(type='ephemeral'))],
                    messages=messages, tools=definitions,
                    max_tokens=config.OUTPUT_TOKENS[provider])
    if provider == 'google':
        contents = []
        for event in history:
            if event['kind'] == 'user':
                contents.append(dict(role='user', parts=[dict(text=event['text'])]))
            elif event['kind'] == 'assistant':
                # Entire content, including thoughtSignature, is returned intact.
                contents.append(deepcopy(event['native']))
            elif event['kind'] == 'tool_results':
                parts = []
                for r in event['results']:
                    response = dict(name=r['name'], response=deepcopy(r['result']))
                    if type(r.get('native_id')) is not str or not r['native_id']:
                        raise Stop('unknown_history')
                    # Migration notes call this call_id. generateContent's REST
                    # FunctionResponse schema spells the wire field "id".
                    response['id'] = r['native_id']
                    parts.append(dict(functionResponse=response))
                contents.append(dict(role='user', parts=parts))
            else:
                raise Stop('unknown_history')
        return dict(systemInstruction=dict(parts=[dict(text=system)]), contents=contents,
                    tools=[dict(functionDeclarations=[dict(name=t['name'], description=t['description'],
                         parametersJsonSchema=deepcopy(t['parameters'])) for t in tools])],
                    generationConfig=dict(maxOutputTokens=config.OUTPUT_TOKENS[provider]))
    raise Stop('unknown_provider')


def usage(provider, reply):
    """Disjoint priced buckets, plus exact native usage retained separately."""
    if provider == 'anthropic':
        u = reply.get('usage')
        if type(u) is not dict:
            raise Stop('missing_usage')
        inp, out = integer(u.get('input_tokens')), integer(u.get('output_tokens'))
        read = integer(u.get('cache_read_input_tokens', 0))
        created = integer(u.get('cache_creation_input_tokens', 0))
        details = u.get('cache_creation', {})
        if type(details) is not dict:
            raise Stop('missing_usage')
        five = integer(details.get('ephemeral_5m_input_tokens', 0))
        hour = integer(details.get('ephemeral_1h_input_tokens', 0))
        if five + hour != created:
            # Never guess cache TTL pricing when billed creation is unpartitioned.
            raise Stop('missing_cache_write_usage')
        return dict(input=inp, cache_read=read, cache_write_5m=five, cache_write_1h=hour,
                    output=out, thinking=0, input_total=inp+read+created, output_total=out,
                    thinking_tokens_reported=None,
                    thinking_accounting='included in output_tokens; not separately reported'), u
    u = reply.get('usageMetadata')
    if type(u) is not dict:
        raise Stop('missing_usage')
    inp = integer(u.get('promptTokenCount'))
    visible = integer(u.get('candidatesTokenCount'))
    thinking = integer(u.get('thoughtsTokenCount', 0))
    cached = integer(u.get('cachedContentTokenCount', 0))
    tool = integer(u.get('toolUsePromptTokenCount', 0))
    if cached > inp or integer(u.get('totalTokenCount')) != inp + visible + thinking + tool:
        raise Stop('usage_bound')
    return dict(input=inp-cached+tool, cache_read=cached, cache_write_5m=0, cache_write_1h=0,
                output=visible, thinking=thinking, input_total=inp+tool, output_total=visible+thinking,
                thinking_tokens_reported=thinking,
                thinking_accounting='thoughtsTokenCount priced separately from candidatesTokenCount'), u


def parse(provider, reply, turn):
    """Parse only complete tool calls; a ceiling reply executes no calls."""
    calls, texts = [], []
    if provider == 'anthropic':
        if reply.get('type') != 'message' or reply.get('role') != 'assistant':
            raise Stop('unknown_output')
        reason, content = reply.get('stop_reason'), reply.get('content')
        native = dict(role='assistant', content=deepcopy(content))
        returned = reply.get('model')
        if reason == 'max_tokens':
            return dict(model=returned, ceiling=True, native=native, calls=[], texts=[], finish=reason)
        if reason not in ('end_turn', 'tool_use', 'refusal') or type(content) is not list or not content:
            raise Stop('unknown_output')
        for block in content:
            if type(block) is not dict or block.get('type') not in OUTPUT_TYPES:
                raise Stop('unknown_output')
            kind = block['type']
            if kind == 'tool_use':
                if (any(type(block.get(k)) is not str or not block[k] for k in ('id', 'name')) or
                        type(block.get('input')) is not dict):
                    raise Stop('unknown_output')
                calls.append(dict(id=block['id'], native_id=block['id'], name=block['name'], args=deepcopy(block['input'])))
            elif kind == 'text':
                if type(block.get('text')) is not str:
                    raise Stop('unknown_output')
                texts.append(block['text'])
            elif kind == 'thinking':
                if type(block.get('thinking')) is not str or type(block.get('signature')) is not str:
                    raise Stop('unknown_output')
            elif type(block.get('data')) is not str:
                raise Stop('unknown_output')
        if (reason == 'tool_use') != bool(calls):
            raise Stop('unknown_output')
    elif provider == 'google':
        candidates = reply.get('candidates')
        if type(candidates) is not list or len(candidates) != 1 or type(candidates[0]) is not dict:
            raise Stop('unknown_output')
        candidate = candidates[0]
        reason, native = candidate.get('finishReason'), deepcopy(candidate.get('content'))
        returned = reply.get('modelVersion')
        if reason == 'MAX_TOKENS':
            return dict(model=returned, ceiling=True, native=native, calls=[], texts=[], finish=reason)
        if reason != 'STOP' or type(native) is not dict or native.get('role') != 'model':
            raise Stop('unknown_output')
        parts = native.get('parts')
        if type(parts) is not list or not parts:
            raise Stop('unknown_output')
        for i, part in enumerate(parts):
            if type(part) is not dict or set(part)-{'text','thought','thoughtSignature','functionCall'}:
                raise Stop('unknown_output')
            if 'thoughtSignature' in part and type(part['thoughtSignature']) is not str:
                raise Stop('unknown_output')
            if 'thought' in part and type(part['thought']) is not bool:
                raise Stop('unknown_output')
            if set(part) == {'thoughtSignature'} and part['thoughtSignature']:
                # Metadata-only parts are opaque history, not executable output.
                continue
            if ('text' in part) == ('functionCall' in part):
                raise Stop('unknown_output')
            if 'functionCall' in part:
                call = part['functionCall']
                if (type(call) is not dict or type(call.get('name')) is not str or not call['name'] or
                        type(call.get('args')) is not dict or
                        type(call.get('id')) is not str or not call['id']):
                    raise Stop('unknown_output')
                calls.append(dict(id=call['id'], native_id=call['id'],
                                  name=call['name'], args=deepcopy(call['args'])))
            elif type(part['text']) is not str:
                raise Stop('unknown_output')
            elif not part.get('thought', False):
                texts.append(part['text'])
    else:
        raise Stop('unknown_provider')
    if len({c['id'] for c in calls}) != len(calls) or not (calls or texts):
        raise Stop('unknown_output')
    if type(returned) is not str or not returned:
        raise Stop('model_identity')
    return dict(model=returned, ceiling=False, native=native, calls=calls, texts=texts, finish=reason)
