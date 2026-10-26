"""Canned protocol fixtures only, not a model or a policy oracle."""
from copy import deepcopy
from live_demo.evidence import encoded
from experiment_a import config


def reply(provider, *, name=None, args=None, text='Done.', ceiling=False, thinking=True):
    if provider == 'anthropic':
        blocks = [dict(type='thinking', thinking='Canned protocol fixture.', signature='canned-signature')] if thinking else []
        blocks += ([dict(type='tool_use', id='canned-call', name=name, input=args)] if name else [dict(type='text', text=text)])
        return dict(type='message', role='assistant', model=config.MODELS[provider], content=blocks,
                    stop_reason='max_tokens' if ceiling else 'tool_use' if name else 'end_turn',
                    usage=dict(input_tokens=20, output_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0))
    parts = [dict(text='Canned protocol fixture.', thought=True, thoughtSignature='canned-thought-signature')] if thinking else []
    parts += ([dict(functionCall=dict(id='canned-call', name=name, args=args), thoughtSignature='canned-call-signature')] if name else [dict(text=text)])
    return dict(modelVersion=config.MODELS[provider], candidates=[dict(content=dict(role='model', parts=parts),
                finishReason='MAX_TOKENS' if ceiling else 'STOP')],
                usageMetadata=dict(promptTokenCount=20, candidatesTokenCount=7, thoughtsTokenCount=3, totalTokenCount=30))


class ScriptedTransport:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def __call__(self, body):
        self.requests.append(deepcopy(body))
        if not self.replies:
            raise AssertionError('canned replies exhausted; no network fallback')
        value = self.replies.pop(0)
        if isinstance(value, BaseException):
            raise value
        return encoded(value)


def prices():
    # Artificial $1/M bucket prices are tests, never a launch price source.
    row = deepcopy(config.load('prices.json')['anthropic'])
    row.update(status='verified', context_window_tokens=200000, long_context_threshold=None)
    row['rates'] = {name: '1' for name in row['rates']}
    row['source_url'] = 'fixture://not-provider-prices'
    return row
