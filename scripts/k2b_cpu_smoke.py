"""CPU smoke of the REAL (non-dry) k2_eval notebook path with a tiny random Gemma 4.

Plumbing only: random weights, so no reply means anything. Exercises model.generate,
the stop token, decoding, history replay, qualification probes, the L2 shard and the
format audit. Run from the repo root with torch and transformers 5.20.2 installed.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
import torch
import transformers
from transformers import Gemma4Config, Gemma4ForConditionalGeneration, LogitsProcessor, LogitsProcessorList
from jinja2 import Environment
from exploratory.k2_kaggle import core, screen

TEMPLATE = (ROOT / 'exploratory/k2_kaggle/gemma4-31b-reference.jinja').read_text(encoding='utf8')
SPECIAL = {'<pad>': 0, '<eos>': 1, '<bos>': 2, '<|turn>': 105, '<turn|>': 106, '<|channel>': 100, '<channel|>': 101}
INVERSE = {v: k for k, v in SPECIAL.items()}
OFFSET = 300


class Tok:
    """Byte-level tokenizer with atomic specials and the retained 31B template."""
    eos_token_id, pad_token_id, unk_token_id, chat_template = 1, 0, 3, TEMPLATE

    def encode(self, text, add_special_tokens=False):
        out, i = [], 0
        while i < len(text):
            for name, ident in SPECIAL.items():
                if text.startswith(name, i):
                    out.append(ident)
                    i += len(name)
                    break
            else:
                out.extend(OFFSET + b for b in text[i].encode('utf8'))
                i += 1
        return out

    def decode(self, ids, skip_special_tokens=False):
        parts, buf = [], bytearray()
        for x in ids:
            if x in INVERSE:
                parts.append(buf.decode('utf8', 'replace')); buf = bytearray()
                if not skip_special_tokens: parts.append(INVERSE[x])
            elif OFFSET <= x < OFFSET + 256: buf.append(x - OFFSET)
        parts.append(buf.decode('utf8', 'replace'))
        return ''.join(parts)

    def convert_tokens_to_ids(self, t): return SPECIAL.get(t, 3)
    def convert_ids_to_tokens(self, i): return INVERSE.get(i, '<unk>')

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=True):
        def fail(x): raise ValueError(x)
        text = Environment().from_string(TEMPLATE).render(
            messages=messages, add_generation_prompt=add_generation_prompt, bos_token='<bos>', eos_token='<eos>', raise_exception=fail)
        if not tokenize: return text
        # Byte tokens run far longer than real ones and would trip the 16384 context guard
        # (a smoke artefact), so thin plain bytes in the INPUT only; specials stay atomic.
        ids, plain = [], 0
        for x in self.encode(text):
            if x in INVERSE: ids.append(x)
            else:
                plain += 1
                if plain % 5 == 0: ids.append(x)
        return ids


class Script(LogitsProcessor):
    """Force a fixed JSON reply then the real stop token, through the real generate loop."""
    def __init__(self, tok, reply):
        self.ids, self.start = tok.encode(reply) + [106], None

    def __call__(self, input_ids, scores):
        if self.start is None: self.start = input_ids.shape[1]
        n = input_ids.shape[1] - self.start
        forced = torch.full_like(scores, -1e9)
        forced[:, self.ids[min(n, len(self.ids) - 1)]] = 0
        return forced


def build_model(tok, reply):
    text = dict(hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                head_dim=8, max_position_embeddings=8192, vocab_size=1024, layer_types=['sliding_attention', 'full_attention'])
    config = Gemma4Config.from_dict(dict(text_config=text, vision_config=None, audio_config=None, tie_word_embeddings=True))
    torch.manual_seed(1)
    model = Gemma4ForConditionalGeneration(config).float().eval()
    real = model.generate
    # Alternate a tool call with a stop so action episodes run two turns: enough to
    # replay a reply through the history without crawling on CPU.
    finish = '{"tool":null,"args":{},"reason":"done"}'
    calls = [0]

    def generate(*args, **kwargs):
        calls[0] += 1
        kwargs['logits_processor'] = LogitsProcessorList([Script(tok, reply if calls[0] % 2 else finish)])
        return real(*args, **kwargs)
    model.generate = generate
    return model


def notebook(mode, battery, kind, out, model):
    tok = Tok()
    nb = json.loads((ROOT / 'exploratory/k2_kaggle/k2_eval.ipynb').read_text(encoding='utf8'))
    values = [("DRY_RUN = True", "DRY_RUN = False"), ("PINNED_COMMIT = ''", "PINNED_COMMIT = '" + 'a' * 40 + "'"),
              ("assert (REPO/'COMMIT.txt').read_text().strip()==PINNED_COMMIT", "pass"),
              ("MODEL = 'gemma-3-1b-it'", "MODEL = 'gemma-4-e2b-it'"), ("MODEL_REVISION = ''", "MODEL_REVISION = 'google/gemma-4/transformers/gemma-4-e2b-it/1'"),
              ("BASE_SCREEN = False", "BASE_SCREEN = True"), ("MODE = 'evaluate'", "MODE = " + repr(mode)),
              ("SCREEN_BATTERY = 'k2'", "SCREEN_BATTERY = " + repr(battery)),
              ("SHARD_ARM = None", "SHARD_ARM = " + repr(None if mode == 'qualify' else 'base')), ("SHARD_KIND = None", "SHARD_KIND = " + repr(kind)),
              ("Path('/kaggle/input/taa-k2-repo/taa-lab')", "Path(" + repr(str(ROOT)) + ")"),
              ("Path('/kaggle/working/k2-output')", "Path(" + repr(str(out)) + ")"), ("device='cuda:0'", "device='cpu'")]
    props = type('P', (), dict(total_memory=16 * 2**30))
    patches = [patch.object(core, 'install_wheels', lambda: {}), patch.object(core, 'check_stack', lambda: dict(core.STACK)),
               patch.object(core, 'resolve_model_path', lambda p: p), patch.object(core, 'inventory', lambda p: {}),
               patch.object(core, 'load_model', lambda *a, **k: model), patch.object(transformers.AutoTokenizer, 'from_pretrained', lambda *a, **k: tok),
               patch.object(transformers, 'BitsAndBytesConfig', lambda **k: None), patch.object(torch.cuda, 'device_count', lambda: 1),
               patch.object(torch.cuda, 'get_device_name', lambda i: 'cpu-smoke'), patch.object(torch.cuda, 'synchronize', lambda: None),
               patch.object(torch.cuda, 'reset_peak_memory_stats', lambda: None), patch.object(torch.cuda, 'max_memory_allocated', lambda: 0),
               patch.object(torch.cuda, 'get_device_properties', lambda i: props)]
    for p in patches: p.start()
    try:
        ns = {}
        for cell in nb['cells']:
            if cell['cell_type'] != 'code': continue
            code = ''.join(cell['source'])
            for old, new in values: code = code.replace(old, new)
            exec(compile(code, 'k2_eval', 'exec'), ns)
    finally:
        for p in patches: p.stop()


def main():
    tok = Tok()
    reply = '{"tool":"report_issue","args":{"issue_id":"ISSUE","authority_id":"Inez"},"reason":"smoke"}'
    limit = 4 if '--short' in sys.argv else None
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        model = build_model(tok, reply)
        plan = screen.plan
        if limit: screen.plan = lambda: plan()[:limit]
        notebook('qualify', 'k2', None, tmp / 'q', model)
        q = json.loads((tmp / 'q/qualification.json').read_text(encoding='utf8'))
        for r in q['probes']:
            print(r['name'], 'len', len(r['input_ids']), 'stop', r['stopped_on_turn'], 'cap', r['hit_cap'], 'json', r['parseable_json'], 'last', r['last_token'], 'reply_has_turn', '<turn|>' in r['decoded_reply'])
            assert r['stopped_on_turn'] and r['parseable_json'] and '<turn|>' not in r['decoded_reply'] and r['last_token'] == 106
        second = next(r for r in q['probes'] if r['name'] == 'second_turn')
        print('--- rendered second_turn ---'); print(second['rendered_prompt'])
        assert second['rendered_prompt'].count('<turn|>') == second['rendered_prompt'].count('<|turn>') - 1, 'turn markers unbalanced'
        assert second['rendered_prompt'].startswith('<bos><|turn>system\n') and second['rendered_prompt'].endswith('<|turn>model\n<|channel>thought\n<channel|>')
        assert len(q['probes'][-1]['input_ids']) >= q['long_context_target'] * .9, 'long probe too short'
        print('--- rendered long head ---'); print(q['probes'][-1]['rendered_prompt'][:120], 'target', q['long_context_target'])
        print('metadata equals_31b', json.loads((tmp / 'q/metadata.json').read_text(encoding='utf8')).get('equals_31b_template'))

        notebook('evaluate', 'l2', None, tmp / 'l2', model)
        print('L2 summary', (tmp / 'l2/l2-summary.json').read_text(encoding='utf8'))
        audit = json.loads((tmp / 'l2/format-audit.json').read_text(encoding='utf8')); print('L2 audit', audit)
        assert audit['stop_token'] == audit['replies'] and not audit.get('special_tokens_in_reply') and not audit.get('generation_failures')
        events = [json.loads(x) for x in (tmp / 'l2/events.jsonl').read_text(encoding='utf8').splitlines()]
        print('run_failed', [e for e in events if e.get('event') == 'run_failed'])
        multi = [e for e in events if e.get('event') == 'native_tokens' and e['input_ids'].count(106) >= 1]
        print('multi-turn requests', len(multi))
        for e in multi: assert 106 not in [a for a, b in zip(e['input_ids'], e['input_ids'][1:]) if a == b == 106], 'doubled turn end in history'
        notebook('evaluate', 'k2', 'U', tmp / 'k2', model)
        print('K2 audit', (tmp / 'k2/format-audit.json').read_text(encoding='utf8'))
        print('manifests', [(d, (tmp / d / 'manifest.json').exists()) for d in ('q', 'l2', 'k2')])
    print('SMOKE OK')


if __name__ == '__main__':
    main()
