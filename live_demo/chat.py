"""Chat Completions wire format; host driver keeps its canonical business calls."""
from copy import deepcopy


def tools(manifest):
    return [dict(type='function',function={k:deepcopy(v) for k,v in item.items() if k!='type'})
            for item in manifest]


def messages(instruction, history):
    result=[dict(role='system',content=instruction)]
    calls=[];texts=[]
    def flush():
        if calls or texts:
            message=dict(role='assistant',content=''.join(texts) if texts else None)
            if calls:message['tool_calls']=deepcopy(calls)
            result.append(message);calls.clear();texts.clear()
    for item in history:
        kind=item.get('type')
        if kind=='reasoning':
            # Never send encrypted reasoning, summaries or private reasoning
            # fields through this API, identically for every arm.
            continue
        if kind=='function_call':
            calls.append(dict(id=item['call_id'],type='function',
                              function=dict(name=item['name'],arguments=item['arguments'])))
        elif kind=='message':
            for part in item.get('content',[]):
                if part.get('type')=='output_text':texts.append(part['text'])
        elif kind=='function_call_output':
            flush();result.append(dict(role='tool',tool_call_id=item['call_id'],content=item['output']))
        elif item.get('role')=='user' and type(item.get('content')) is str:
            flush();result.append(dict(role='user',content=item['content']))
        else:
            raise ValueError('unknown host history item')
    flush()
    return result


def canonical(native):
    """Normalize only for the host; raw response and native usage stay evidence.

    Malformed output becomes an unknown status AFTER usage can be charged.
    """
    usage=native.get('usage')
    normalized_usage=None
    if type(usage) is dict:
        normalized_usage=dict(input_tokens=usage.get('prompt_tokens'),output_tokens=usage.get('completion_tokens'),
            total_tokens=usage.get('total_tokens'),input_tokens_details=usage.get('prompt_tokens_details',{}))
    reply=dict(model=native.get('model'),usage=normalized_usage,status='unknown',output=[])
    choices=native.get('choices')
    if type(choices) is not list or len(choices)!=1 or type(choices[0]) is not dict:return reply
    choice=choices[0];finish=choice.get('finish_reason')
    if finish=='length':
        reply.update(status='incomplete',incomplete_details={'reason':'max_output_tokens'})
        return reply
    if finish not in ('stop','tool_calls'):return reply
    message=choice.get('message')
    if type(message) is not dict or message.get('role')!='assistant':return reply
    content=message.get('content');refusal=message.get('refusal')
    if content is not None and type(content) is not str:return reply
    if refusal is not None and type(refusal) is not str:return reply
    calls=message.get('tool_calls',[])
    if calls is None:calls=[]
    if type(calls) is not list:return reply
    output=[]
    if content or refusal or not calls:
        output.append(dict(type='message',role='assistant',content=[dict(type='output_text',text=content or refusal or '')]))
    for call in calls:
        if (type(call) is not dict or call.get('type')!='function' or type(call.get('id')) is not str or
                type(call.get('function')) is not dict or
                any(type(call['function'].get(k)) is not str for k in ('name','arguments'))):return reply
        output.append(dict(type='function_call',call_id=call['id'],name=call['function']['name'],arguments=call['function']['arguments']))
    if finish=='tool_calls' and not calls:return reply
    reply.update(status='completed',output=output)
    return reply


def reasoning_fields(native):
    choices=native.get('choices')
    if type(choices) is not list or len(choices)!=1 or type(choices[0]) is not dict:return {}
    message=choices[0].get('message')
    if type(message) is not dict:return {}
    return {k:type(message[k]).__name__ for k in ('reasoning_content','reasoning','encrypted_content') if k in message}
