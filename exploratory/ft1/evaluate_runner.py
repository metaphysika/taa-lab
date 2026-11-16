"""Approved, local-only FT1 evaluation; importing never loads a model."""
import hashlib
import json
import os
import time
from collections import Counter
from pathlib import Path
from . import data, evaluation, kaggle, plan, scoring
from .runner import deadline, verify_source
from exploratory.k2_kaggle import core


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_hashes(root, targets, max_bytes=5*1024*1024):
    """One traversal; never read model weights, wheels or oversized JSON."""
    found = {name: [] for name in targets}
    for directory, _, names in os.walk(root):
        for name in names:
            path = Path(directory)/name
            try:
                if path.suffix.lower() != '.json' or path.stat().st_size > max_bytes:
                    continue
            except FileNotFoundError:
                continue
            digest = sha(path)
            for key, expected in targets.items():
                if digest == expected:
                    found[key].append(path)
    if any(len(paths) != 1 for paths in found.values()):
        raise ValueError('missing or ambiguous hash-bound JSON')
    return {key: paths[0] for key, paths in found.items()}


def find_hash(root, digest):
    return find_hashes(root, {'target': digest})['target']


def adapter_binding(folder, arm, seed):
    folder = Path(folder).resolve()
    candidate_parts = (*folder.parts, *(folder/'adapter').resolve().parts)
    if any(part.lower() == 'interrupted-adapter' or part.lower().startswith('checkpoint-') for part in candidate_parts):
        raise ValueError('interrupted adapters and intermediate checkpoints are not candidates')
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
    if not any(e.get('event') == 'adapter_saved' and e.get('tensors_finite') is True and e.get('sha256') == files for e in events):
        raise ValueError('adapter save binding required')
    return dict(adapter_sha256=core.digest(files), training_manifest_sha256=sha(folder/'manifest.json'),
                adapter_files=files, skipped_steps=completed[0]['skipped_steps'])


def prefill_options(config):
    mode = config.get('prefill_mode', 'current')
    size = config.get('prefill_chunk_size')
    if mode not in ('current', 'chunked') or (mode == 'current' and size is not None):
        raise ValueError('invalid prefill mode')
    if mode == 'chunked':
        if type(size) is not int or not 1 <= size <= 16384:
            raise ValueError('positive bounded prefill chunk size required')
        return dict(prefill_chunk_size=size, logits_to_keep=1)
    return {}


def validate_prefill(config, receipt):
    prefill_options(config)
    for key in ('prefill_mode', 'prefill_chunk_size'):
        if config.get(key) != receipt.get(key):
            raise ValueError('prefill receipt mismatch')


def validate(config, receipt):
    validate_prefill(config, receipt)
    if (config['arm'],config['seed']) not in plan.MODELS or config['phase'] not in ('gate','evaluate'):
        raise ValueError('unplanned evaluation')
    keys = ('repo_commit','phase','arm','seed','adapter_sha256','training_manifest_sha256',
            'data_manifest_sha256','sealed_sha256','gate_sha256','part','part_count','model_source','prompt_ceiling')
    if receipt.get('approved') is not True or any(receipt.get(k) != config.get(k) for k in keys):
        raise ValueError('separate exact evaluation approval required')
    ceiling = config.get('prompt_ceiling')
    if ceiling is not None and (type(ceiling) is not int or not 1 <= ceiling <= 16384):
        raise ValueError('invalid prompt ceiling')
    if config['phase'] == 'gate':
        fields = ('part','part_count','gate_sha256','sealed_sha256')
        if any(key not in receipt or receipt[key] is not None or config.get(key) is not None for key in fields):
            raise ValueError('gate receipt requires null test fields')
    if config['phase'] == 'evaluate':
        if type(config['part_count']) is not int or not 1 <= config['part_count'] <= 24 or config['part'] not in range(config['part_count']):
            raise ValueError('invalid evaluation part')
        if not config.get('gate_sha256') or not config.get('sealed_sha256'):
            raise ValueError('gate and sealed bindings required')
    if config['arm'] == 'base' and (config['adapter_sha256'] is not None or config['training_manifest_sha256'] is not None):
        raise ValueError('base cannot have an adapter')


def protocol(config, records, generate, count_tokens, retain, check, skipped):
    """Run the complete protocol once, without any sealed input."""
    from .memory import Tracker
    tracker = Tracker(retain)
    replies = []
    for i, record in enumerate(records):
        check()
        messages = record['messages'][:-1]
        system = messages[0]['content'] if messages[0]['role'] == 'system' else data.SYSTEM
        history = messages[1:] if messages[0]['role'] == 'system' else messages
        raw = tracker.call(lambda: generate(system, history, 1024, 448017+i), 0, dict(phase='acquisition',index=i))
        if tracker.stopped: return unknown_gate(config, skipped, tracker)
        if tracker.last_unknown: continue
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
        result = tracker.call(lambda: evaluation.episode(development[cell['case_id']],call,count_tokens,log,format_only=True), None, dict(phase='format',case_id=cell['case_id']))
        if tracker.stopped: return unknown_gate(config, skipped, tracker)
        if tracker.last_unknown: continue
        formats.append(raw_replies)
        retain(dict(event='format_only',case_id=cell['case_id'],raw_replies=raw_replies))
    if tracker.total: return unknown_gate(config, skipped, tracker)
    gate = scoring.eligibility(records,replies,formats,skipped)
    if prefill_options(config):
        gate.update(prefill_mode=config['prefill_mode'],prefill_chunk_size=config['prefill_chunk_size'])
    retain(dict(event='eligibility', **gate))
    return dict(gate, prompt_ceiling=config.get('prompt_ceiling'), **tracker.counts, status='complete', skipped_steps=skipped, arm=config['arm'], seed=config['seed'],
                adapter_sha256=config['adapter_sha256'],
                training_manifest_sha256=config['training_manifest_sha256'],
                repo_commit=config['repo_commit'],data_manifest_sha256=config['data_manifest_sha256'],
                model_source=config.get('model_source'))


def validate_gate(config, gate):
    for key in ('arm','seed','adapter_sha256','training_manifest_sha256','repo_commit','data_manifest_sha256','model_source'):
        if key not in gate or gate[key] != config.get(key):
            raise ValueError('gate identity mismatch')
    validate_prefill(config, gate)
    if gate.get('prompt_ceiling') != config.get('prompt_ceiling'):
        raise ValueError('gate prompt ceiling mismatch')
    if gate.get('status') in ('gate_mechanical_unknown','mechanical_unknown'):
        from .memory import GateDecisionRequired
        raise GateDecisionRequired('mechanically unknown gate requires a recorded owner decision on eligibility or reruns')
    if not isinstance(gate.get('acquired'),bool) or not isinstance(gate.get('trained'),bool):
        raise ValueError('invalid gate flags')
    return config['arm'] == 'base' or gate['acquired'] and gate['trained']


def part_indices(cases, part, part_count):
    """Assign first-seen twin pairs modulo part count; preserve original seeds."""
    if len(cases) != 48 or len({c['id'] for c in cases}) != 48:
        raise ValueError('sealed inventory mismatch')
    pairs = {}
    for i, case in enumerate(cases):
        pairs.setdefault(case['pair_id'], []).append(i)
    if len(pairs) != 24 or any(len(indices) != 2 for indices in pairs.values()):
        raise ValueError('sealed pair inventory mismatch')
    return {i for index, indices in enumerate(pairs.values()) if index % part_count == part for i in indices}


def check_part_balance(cases, indices, retain):
    groups = {case['difficulty_group'] for case in cases}
    counts = Counter(cases[i]['difficulty_group'] for i in indices)
    retain(dict(event='part_balance',counts={group:counts[group] for group in sorted(groups)}))
    pairs = {}
    for i, case in enumerate(cases):
        pairs.setdefault(case['pair_id'],[]).append(i)
    if (not indices or len(set(counts[group] for group in groups)) != 1 or
            any(len(pair) != 2 or sorted(cases[i]['kind'] for i in pair) != ['U','W'] or
                any(i in indices for i in pair) and not all(i in indices for i in pair)
                for pair in pairs.values())):
        raise ValueError('test part group or twin balance failed')


def test_cells(config, cases, gate, generate, count_tokens, retain, check):
    retain(dict(event='eligibility',**gate))
    if not validate_gate(config,gate):
        return dict(status='ineligible',eligibility=gate)
    from .memory import Tracker
    tracker = Tracker(retain)
    indices = part_indices(cases,config['part'],config['part_count'])
    check_part_balance(cases,indices,retain)
    for cell in plan.plan()['evaluation']:
        if (cell['arm'],cell['training_seed']) != (config['arm'],config['seed']) or cell['case_index'] not in indices:
            continue
        check()
        def guarded(system,history,cap,seed):
            check()
            return generate(system,history,cap,seed)
        tracker.call(lambda: evaluation.run_cell(cell,cases[cell['case_index']],guarded,count_tokens,retain), None, dict(case_id=cases[cell['case_index']]['id'],branch=cell['branch']))
        if tracker.stopped: break
    return dict(status='stopped_mechanical_oom' if tracker.stopped else 'complete', **tracker.counts, eligibility=gate)


def load_base(model_path, retain, check, attention=None):
    """Shared local NF4 inference loader for evaluation and throughput."""
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
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16),device_map={'':0}, **({'attn_implementation':attention} if attention else {}))
    retain(dict(event='attention_backend', requested=attention, implementation=getattr(model.config,'_attn_implementation',None), text_implementation=getattr(getattr(model.config,'text_config',None),'_attn_implementation',None), torch_version=torch.__version__, transformers_version=transformers.__version__))
    text = getattr(model.config,'text_config',model.config)
    retain(dict(event='base_model_identity',model_type=model.config.model_type,
                layers=text.num_hidden_layers,hidden_size=text.hidden_size,vocab=text.vocab_size,
                config_sha256=sha(Path(path)/'config.json')))
    from .memory import snapshot
    retain(dict(event='memory_snapshot',boundary='after_load',**snapshot()))
    return model,tokenizer,path


def prepare(model_path, adapter, retain, check, prompt_ceiling=None, prefill_mode="current", prefill_chunk_size=None):
    """Inference NF4 base, optionally the verified adapter; no new LoRA weights."""
    model,tokenizer,path = load_base(model_path,retain,check)
    if adapter is not None:
        from peft import PeftConfig, PeftModel
        adapter_config = PeftConfig.from_pretrained(adapter,local_files_only=True)
        adapter_config.base_model_name_or_path = str(path)
        model = PeftModel.from_pretrained(model,adapter,config=adapter_config,
            local_files_only=True,is_trainable=False)
    return generation_functions(model,tokenizer,check,prompt_ceiling=prompt_ceiling, prefill_mode=prefill_mode, prefill_chunk_size=prefill_chunk_size)


def generation_functions(model, tokenizer, check, prompt_ceiling=None, prefill_mode="current", prefill_chunk_size=None):
    import torch, transformers
    options = prefill_options(dict(prefill_mode=prefill_mode, prefill_chunk_size=prefill_chunk_size))
    model.eval()
    check()
    def generate(system,history,cap,seed, *, prompt_ids=None, return_ids=False):
        check()
        transformers.set_seed(seed)
        ids = prompt_ids if prompt_ids is not None else core.prompt(tokenizer,[dict(role='system',content=system)]+history,model='gemma-3-12b-it')
        if len(ids)+cap > 16384 or prompt_ceiling is not None and len(ids) > prompt_ceiling:
            from .memory import ContextLimit
            raise ContextLimit(len(ids),rule='16384' if len(ids)+cap > 16384 else 'prompt_ceiling')
        tensor = output = None
        oom = False
        try:
            tensor = torch.tensor([ids],device='cuda')
            with torch.inference_mode():
                output = model.generate(input_ids=tensor,attention_mask=torch.ones_like(tensor),max_new_tokens=cap,
                    do_sample=False,eos_token_id=core.end_token(tokenizer,'gemma-3-12b-it'),pad_token_id=tokenizer.pad_token_id, **options)
            generated_ids = output[0,len(ids):].tolist()
            return generated_ids if return_ids else core.decode_reply(tokenizer,generated_ids,'gemma-3-12b-it')
        except RuntimeError as exc:
            from .memory import is_oom
            if not is_oom(exc): raise
            oom = True
        finally:
            del tensor, output
        if oom:
            from .memory import cleanup, MechanicalOOM
            cleanup()
            raise MechanicalOOM(len(ids))
    return generate, lambda raw: len(tokenizer.encode(raw,add_special_tokens=False))


def run(config, model_path, data_folder, sealed_file, output, receipt, training_folder=None, seconds=27000, gate_file=None):
    validate(config,receipt)
    verify_source(config)
    if not 0 < seconds <= 27000:
        raise ValueError('deadline must be within 7.5 hours')
    check = deadline(seconds)
    if kaggle.verify_data(data_folder) != config['data_manifest_sha256']:
        raise ValueError('evaluation data hash mismatch')
    gate = None
    if config['phase'] == 'evaluate':
        if sha(sealed_file) != config['sealed_sha256'] or sha(gate_file) != config['gate_sha256']:
            raise ValueError('test input hash mismatch')
        gate = json.loads(Path(gate_file).read_bytes())
        validate_gate(config,gate)
    elif sealed_file is not None or gate_file is not None:
        raise ValueError('gate phase has no sealed or prior gate input')
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
        if gate is not None and not validate_gate(config,gate):
            retain(dict(event='eligibility',**gate))
            result = dict(status='ineligible',eligibility=gate)
        else:
            options = prefill_options(config)
            if options:
                retain(dict(event='prefill_config',prefill_mode=config['prefill_mode'],prefill_chunk_size=config['prefill_chunk_size']))
            generate,count_tokens = prepare(model_path,adapter,retain,check,**(dict(prefill_mode=config['prefill_mode'],prefill_chunk_size=config['prefill_chunk_size']) if options else {}),**({'prompt_ceiling':config['prompt_ceiling']} if config.get('prompt_ceiling') is not None else {}))
            if config['phase'] == 'gate':
                probe = data.PROBE_FILES.get(config['arm'],data.PROBE_FILES['3'])
                records = json.loads((Path(data_folder)/probe).read_bytes())
                gate = protocol(config,records,generate,count_tokens,retain,check,skipped)
                (folder/'gate.json').write_text(json.dumps(gate,indent=2),encoding='utf-8')
                result = dict(status=gate.get('status') if gate.get('status') == 'gate_mechanical_unknown' else 'gate_complete',eligibility=gate)
            else:
                cases = json.loads(Path(sealed_file).read_bytes())['cases']
                result = test_cells(config,cases,gate,generate,count_tokens,retain,check)
        (folder/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        (folder/'eligibility.json').write_text(json.dumps([dict(result['eligibility'],training_seed=config['seed'])]),encoding='utf-8')
        return result
    except BaseException as exc:
        retain(dict(event='run_failed',error=type(exc).__name__))
        raise
    finally:
        (folder/'metadata.json').write_text(json.dumps(dict(config,result=result),indent=2),encoding='utf-8')
        core.manifest(folder,dict(phase=config['phase'],status=result['status'],scientific=False))


def unknown_gate(config, skipped, tracker):
    retain = tracker.retain
    retain(dict(event='gate_mechanical_unknown',**tracker.counts))
    options = dict(prefill_mode=config['prefill_mode'],prefill_chunk_size=config['prefill_chunk_size']) if prefill_options(config) else {}
    return dict(**options, acquired=None, trained=plan.trained(skipped), status='gate_mechanical_unknown',
        decision_required='owner decision on eligibility and reruns', **tracker.counts, skipped_steps=skipped,
        **{k:config.get(k) for k in ('arm','seed','adapter_sha256','training_manifest_sha256','repo_commit','data_manifest_sha256','model_source','prompt_ceiling')})
