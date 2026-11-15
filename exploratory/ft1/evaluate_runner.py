"""Approved, local-only FT1 evaluation; importing never loads a model."""
import hashlib
import json
import os
import time
from pathlib import Path
from . import data, evaluation, kaggle, plan, scoring
from .runner import deadline, verify_source
from exploratory.k2_kaggle import core


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_hash(root, digest):
    found = [p for p in Path(root).rglob('*') if p.is_file() and sha(p) == digest]
    if len(found) != 1:
        raise ValueError('missing or ambiguous hash-bound file')
    return found[0]


def adapter_binding(folder, arm, seed):
    folder = Path(folder)
    manifest = json.loads((folder/'manifest.json').read_bytes())
    meta = json.loads((folder/'metadata.json').read_bytes())
    if (meta.get('arm'), meta.get('seed'), meta.get('phase'), meta.get('status')) != (arm, seed, 'train', 'trained'):
        raise ValueError('completed matching FT1 training required')
    for name in ('metadata.json', 'events.jsonl'):
        if sha(folder/name) != manifest['sha256'].get(name):
            raise ValueError('training evidence mismatch')
    files = core.inventory(folder/'adapter')
    bound = {k[len('adapter/'):]: v for k,v in manifest['sha256'].items() if k.startswith('adapter/')}
    if not files or files != bound or 'adapter_config.json' not in files or not any(n.endswith('.safetensors') for n in files):
        raise ValueError('adapter files mismatch')
    events = [json.loads(s) for s in (folder/'events.jsonl').read_text().splitlines()]
    completed = [e for e in events if e.get('event') == 'training_complete']
    if len(completed) != 1 or completed[0].get('qualification') is not False or completed[0].get('steps') != 250:
        raise ValueError('250-step training completion required')
    if not any(e.get('event') == 'adapter_saved' and e.get('sha256') == files for e in events):
        raise ValueError('adapter save binding required')
    return dict(adapter_sha256=core.digest(files), training_manifest_sha256=sha(folder/'manifest.json'),
                adapter_files=files, skipped_steps=completed[0]['skipped_steps'])


def validate(config, receipt):
    if (config['arm'],config['seed']) not in plan.MODELS or config['phase'] != 'evaluate':
        raise ValueError('unplanned evaluation')
    keys = ('repo_commit','phase','arm','seed','adapter_sha256','training_manifest_sha256',
            'data_manifest_sha256','sealed_sha256','part')
    if receipt.get('approved') is not True or any(receipt.get(k) != config.get(k) for k in keys):
        raise ValueError('separate exact evaluation approval required')
    if config['part'] not in range(4):
        raise ValueError('invalid evaluation part')
    if config['arm'] == 'base' and (config['adapter_sha256'] is not None or config['training_manifest_sha256'] is not None):
        raise ValueError('base cannot have an adapter')


def protocol(config, records, cases, generate, count_tokens, retain, check, skipped):
    """Four disjoint 12-case parts; each repeats the full protocol."""
    replies = []
    for i, record in enumerate(records):
        check()
        messages = record['messages'][:-1]
        system = messages[0]['content'] if messages[0]['role'] == 'system' else data.SYSTEM
        history = messages[1:] if messages[0]['role'] == 'system' else messages
        raw = generate(system, history, 1024, 448017+i)
        retain(dict(event='acquisition_turn', index=i, raw=raw, reply_tokens=count_tokens(raw)))
        replies.append(raw)
    formats = []
    development = {c['id']: c for c in core.manager_cases()}
    for cell in plan.plan()['format_evaluation']:
        if (cell['arm'],cell['training_seed']) != (config['arm'],config['seed']):
            continue
        raw_replies = []
        def log(event):
            if event['event'] == 'turn':
                raw_replies.append(event['raw'])
                retain(dict(event, event='format_turn', case_id=cell['case_id']))
        turn = 0
        def call(system, history, cap):
            nonlocal turn
            check()
            raw = generate(system, history, cap, cell['sampling_seed']+turn)
            turn += 1
            return raw
        evaluation.episode(development[cell['case_id']],call,count_tokens,log,format_only=True)
        formats.append(raw_replies)
        retain(dict(event='format_only',case_id=cell['case_id'],raw_replies=raw_replies))
    gate = scoring.eligibility(records,replies,formats,skipped)
    retain(dict(event='eligibility', **gate))
    if not gate['acquired'] or not gate['trained']:
        return dict(status='ineligible',eligibility=gate)
    if len(cases) != 48 or len({c['id'] for c in cases}) != 48:
        raise ValueError('sealed inventory mismatch')
    for cell in plan.plan()['evaluation']:
        if (cell['arm'],cell['training_seed']) != (config['arm'],config['seed']) or cell['case_index']//12 != config['part']:
            continue
        check()
        def guarded(system,history,cap,seed):
            check()
            return generate(system,history,cap,seed)
        evaluation.run_cell(cell,cases[cell['case_index']],guarded,count_tokens,retain)
    return dict(status='complete',eligibility=gate)


def prepare(model_path, adapter, retain, check):
    """Inference NF4 base, optionally the verified adapter; no new LoRA weights."""
    retain(dict(event='local_wheels',sha256=core.install_wheels()))
    core.check_stack()
    import torch, transformers
    if torch.cuda.device_count() != 1:
        raise ValueError('one visible GPU required')
    check()
    path = core.resolve_model_path(model_path)
    tokenizer = transformers.AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
    model = core.load_model('gemma-3-12b-it',transformers,path,
        quantization_config=transformers.BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16),device_map={'':0})
    if adapter is not None:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model,adapter,local_files_only=True,is_trainable=False)
    model.eval()
    check()
    def generate(system,history,cap,seed):
        check()
        transformers.set_seed(seed)
        ids = core.prompt(tokenizer,[dict(role='system',content=system)]+history,model='gemma-3-12b-it')
        if len(ids)+cap > 16384:
            raise ValueError('evaluation context limit')
        tensor = torch.tensor([ids],device='cuda')
        with torch.inference_mode():
            output = model.generate(input_ids=tensor,attention_mask=torch.ones_like(tensor),max_new_tokens=cap,
                do_sample=False,eos_token_id=core.end_token(tokenizer,'gemma-3-12b-it'),pad_token_id=tokenizer.pad_token_id)
        return core.decode_reply(tokenizer,output[0,len(ids):].tolist(),'gemma-3-12b-it')
    return generate, lambda raw: len(tokenizer.encode(raw,add_special_tokens=False))


def run(config, model_path, data_folder, sealed_file, output, receipt, training_folder=None, seconds=27000):
    validate(config,receipt)
    verify_source(config)
    if not 0 < seconds <= 27000:
        raise ValueError('deadline must be within 7.5 hours')
    check = deadline(seconds)
    if kaggle.verify_data(data_folder) != config['data_manifest_sha256'] or sha(sealed_file) != config['sealed_sha256']:
        raise ValueError('evaluation data hash mismatch')
    skipped = []
    adapter = None
    if config['arm'] != 'base':
        binding = adapter_binding(training_folder,config['arm'],config['seed'])
        if any(binding[k] != config[k] for k in ('adapter_sha256','training_manifest_sha256')):
            raise ValueError('training binding mismatch')
        skipped = binding['skipped_steps']
        adapter = Path(training_folder)/'adapter'
    elif training_folder is not None:
        raise ValueError('base cannot mount adapter')
    folder = data.safe_output(output)
    folder.mkdir(parents=True)
    def retain(event):
        with (folder/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(dict(event,arm=config['arm'],training_seed=config['seed']),allow_nan=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
    result = dict(status='incomplete')
    try:
        generate,count_tokens = prepare(model_path,adapter,retain,check)
        probe = data.PROBE_FILES.get(config['arm'],data.PROBE_FILES['3'])
        records = json.loads((Path(data_folder)/probe).read_bytes())
        cases = json.loads(Path(sealed_file).read_bytes())['cases']
        result = protocol(config,records,cases,generate,count_tokens,retain,check,skipped)
        (folder/'eligibility.json').write_text(json.dumps([dict(result['eligibility'],arm=config['arm'],training_seed=config['seed'])]),encoding='utf-8')
        return result
    except BaseException as exc:
        retain(dict(event='run_failed',error=type(exc).__name__))
        raise
    finally:
        (folder/'metadata.json').write_text(json.dumps(dict(config,result=result),indent=2),encoding='utf-8')
        core.manifest(folder,dict(phase='evaluate',status=result['status'],scientific=False))
