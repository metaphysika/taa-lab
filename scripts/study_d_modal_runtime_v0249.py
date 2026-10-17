"""Modal worker implementation. Importing this module never launches a workload.

The two public launchers bind these functions only after explicit launch flags.
Model libraries are imported only inside approved remote workers.
"""
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone

ASSETS = Path('/opt/study-d/assets')
OUTPUT = Path('/results')
MODEL_IDS = ('meta-llama/Llama-3.1-8B-Instruct', 'Qwen/Qwen2.5-7B-Instruct')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    temp.replace(path)


def helpers():
    manifest = json.loads((ASSETS/'integrity.json').read_text())
    for name in ('helpers.py', 'runtime.py'):
        if hashlib.sha256((Path('/opt/study-d')/name).read_bytes()).hexdigest() != manifest['remote_code_sha256'][name]:
            raise RuntimeError('runtime implementation differs from reviewed source')
    spec = importlib.util.spec_from_file_location('modal_review_helpers', '/opt/study-d/helpers.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_frozen_bundle():
    plan = json.loads((ASSETS/'plan.json').read_text())
    bundle = json.loads((ASSETS/'bundle.json').read_text())
    root = Path(tempfile.mkdtemp(prefix='frozen-evaluator-'))
    for name, text in bundle.items():
        if hashlib.sha256(text.encode()).hexdigest() != plan['bundle_sha256'][name]:
            raise RuntimeError('frozen evaluator mismatch')
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    if any(n == 'formation' or n.startswith('formation.') or n == 'agents' or n.startswith('agents.')
           or n == 'taa' or n.startswith('taa.') for n in sys.modules):
        raise RuntimeError('evaluator namespace already loaded')
    sys.path.insert(0, str(root))
    from formation.study_b_replay_v0234 import replay
    for fixture in plan['fixture_keys']:
        case = next(p['case'] for p in plan['cases'] if p['case']['id'] == fixture['case_id'])
        if replay(case, fixture['canonical_scripted_correct_packets'])['score']['substance_outcome'] != fixture['expected_original_label']:
            raise RuntimeError('frozen fixture key mismatch')
    return plan


class Session:
    def __init__(self, folder, volume):
        self.folder = folder
        self.volume = volume
        self.started = time.monotonic()
        folder.mkdir(parents=True, exist_ok=False)
        write(folder/'asset-integrity.json', json.loads((ASSETS/'integrity.json').read_text()))
        write(folder/'frozen-base-plan.json', json.loads((ASSETS/'plan.json').read_text()))
        from importlib.metadata import version
        write(folder/'environment.json', dict(started_utc=datetime.now(timezone.utc).isoformat(),
              python=sys.version, packages={name:version(name) for name in
              ['torch','transformers','accelerate','huggingface-hub','safetensors','peft']},
              precision='bf16, no quantization', platform='Modal A100-40GB'))
        self.volume.commit()

    def guard(self, reserve=600):
        if time.monotonic()-self.started+reserve > 6300:
            raise RuntimeError('allocation/time reservation exhausted; retain evidence, no restart')

    def event(self, **value):
        value['elapsed_seconds'] = time.monotonic()-self.started
        with (self.folder/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(value, ensure_ascii=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.volume.commit()

    def load(self, model_id, revision=None):
        self.guard()
        import torch
        from huggingface_hub import HfApi
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError('approved bf16 A100 unavailable')
        name = torch.cuda.get_device_name(0)
        memory = torch.cuda.get_device_properties(0).total_memory
        if 'A100' not in name or not 38*1024**3 <= memory <= 45*1024**3:
            raise RuntimeError('exact A100 40GB required; no hardware substitution')
        # Only the Modal Secret named huggingface supplies HF_TOKEN. No local files.
        token = os.environ.get('HF_TOKEN')
        if not token:
            raise RuntimeError('HF_TOKEN missing from approved Modal Secret')
        self.event(event='load_start', model=model_id, gpu=name, gpu_bytes=memory, precision='bf16; no quantization')
        revision = revision or HfApi(token=token).model_info(model_id).sha
        if not isinstance(revision, str) or len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
            raise RuntimeError('immutable model revision unavailable')
        tok = AutoTokenizer.from_pretrained(model_id, revision=revision, token=token, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, token=token,
                    torch_dtype=torch.bfloat16, device_map={'': 0}, trust_remote_code=False,
                    use_safetensors=True, attn_implementation='sdpa')
        model.eval()
        write(self.folder/(model_id.split('/')[-1]+'-load.json'), dict(model=model_id, revision=revision,
              model_config=model.config.to_dict(), generation_config=model.generation_config.to_dict(),
              tokenizer_chat_template=tok.chat_template, precision='bf16, unquantized', gpu=name))
        self.volume.commit()
        return model, tok, revision

    def generate(self, model, tok, messages, request_id, limit=4096):
        self.guard()
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList
        prompt = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors='pt')
        if prompt.shape[-1]+limit > 16384 or len(json.dumps(messages, ensure_ascii=False).encode()) > 128000:
            raise RuntimeError('full-history context/wire guard; no truncation')
        self.event(event='generation_start', request_id=request_id, messages=messages,
                   prompt_token_ids=prompt[0].tolist())
        outer = self

        class Guard(StoppingCriteria):
            def __init__(self):
                self.started = time.monotonic()
                self.hit = False

            def __call__(self, input_ids, scores, **kwargs):
                self.hit = time.monotonic()-self.started >= 600 or time.monotonic()-outer.started >= 6300
                return self.hit

        guard = Guard()
        begin, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        wall = time.monotonic()
        begin.record()
        with torch.inference_mode():
            sequence = model.generate(input_ids=prompt.to('cuda:0'),
                    attention_mask=torch.ones_like(prompt, device='cuda:0'),
                    max_new_tokens=limit, stopping_criteria=StoppingCriteriaList([guard]))
        end.record()
        torch.cuda.synchronize()
        tokens = sequence[0, prompt.shape[-1]:].tolist()
        eos = model.generation_config.eos_token_id
        boundaries = set(eos if isinstance(eos, list) else [eos])
        boundaries.add(model.generation_config.pad_token_id)
        payload = tokens[:]
        while payload and payload[-1] in boundaries:
            payload.pop()
        raw = tok.decode(payload, skip_special_tokens=False)
        self.event(event='generation_return', request_id=request_id, raw_text=raw,
                   native_text_with_boundary_tokens=tok.decode(tokens, skip_special_tokens=False),
                   output_token_ids=tokens, input_tokens=prompt.shape[-1], output_tokens=len(tokens),
                   cuda_seconds=begin.elapsed_time(end)/1000, wall_seconds=time.monotonic()-wall,
                   time_guard=guard.hit)
        if guard.hit:
            raise RuntimeError('received interrupted reply retained; no resend')
        return raw


def gate_worker(volume, ledger):
    if not ledger.put('base-worker-once', {'claimed': True}, skip_if_exists=True):
        raise RuntimeError('base already attempted; no automatic restart')
    helper = helpers()
    helper.verify_assets(ASSETS)
    plan = install_frozen_bundle()
    from formation.study_d_base_gate_v0248 import evaluate_episode, summarize
    import torch
    session = Session(OUTPUT/'base', volume)
    report = dict(status='INCOMPLETE', models={}, revisions={}, audit_accepted_by_owner=False,
                  precision_change='v0248 NF4/FP16 T4 to unquantized bf16 A100-40GB', training_authorized=False)
    cases = {p['case']['id']: p['case'] for p in plan['cases']}
    try:
        for model_id in plan['models']:
            model, tok, revision = session.load(model_id)
            report['revisions'][model_id] = revision
            rows = []
            for cell in plan['schedule']:
                case = cases[cell['case_id']]
                torch.manual_seed(cell['seed'])
                torch.cuda.manual_seed_all(cell['seed'])
                def generate(system, history, turn):
                    return session.generate(model, tok, [dict(role='system', content=system)]+history,
                                            f"{model_id}/{case['id']}/r{cell['repeat']}/t{turn}")
                result = evaluate_episode(case, generate)
                result['repeat'] = cell['repeat']
                rows.append(result)
                write(session.folder/model_id.split('/')[-1]/f"{case['id']}-r{cell['repeat']}.json", result)
                report['models'][model_id] = summarize(rows, list(cases), {k: c['kind'] for k, c in cases.items()})
                write(session.folder/'report.json', report)
                volume.commit()
            del model, tok
            gc.collect()
            torch.cuda.empty_cache()
        report['status'] = 'COMPLETE'
        write(session.folder/'report.json', report)
    except BaseException as exc:
        write(session.folder/'STOP_FOR_REVIEW.json', dict(error_type=type(exc).__name__, no_restart=True))
        # Suppress exception text/traceback that third-party clients might fill with credentials.
        raise RuntimeError('base stopped for review; retain all evidence, do not restart') from None
    finally:
        session.event(event='base_exit', software_wall_seconds=time.monotonic()-session.started,
                      actual_invoice_usd=None, training_jobs=0)
    return report


def train_one(session, model, tok, arm, adapter):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import Trainer, TrainingArguments, TrainerCallback
    records = [json.loads(line) for line in (ASSETS/(arm+'-2000-train.jsonl')).read_text().splitlines()]
    order = json.loads((ASSETS/'training-order.json').read_text())
    ids = order['high']['record_ids']
    if len(records) != 2000 or len(ids) != 2000:
        raise RuntimeError('exact 2000 records required')
    # Files use T0001..T2000; identical reviewed order for all arms.
    records = [records[int(i[1:])-1] for i in ids]
    dataset = []
    for record in records:
        messages = record['messages']
        prefix = tok.apply_chat_template(messages[:-1], tokenize=True, add_generation_prompt=True)
        full = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=False)
        if full[:len(prefix)] != prefix or len(full) > 1024:
            raise RuntimeError('assistant-only mask/context unavailable; no token truncation')
        dataset.append(dict(input_ids=full, attention_mask=[1]*len(full),
                            labels=[-100]*len(prefix)+full[len(prefix):]))
    torch.manual_seed(247056)
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0,
            target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'],
            bias='none', task_type='CAUSAL_LM'))
    model.config.use_cache = False
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    class BudgetCallback(TrainerCallback):
        def on_step_begin(self, args, state, control, **kwargs):
            session.guard()
    # Reviewed common order is retained: disable Trainer's random sampler.
    class FixedOrderTrainer(Trainer):
        def _get_train_sampler(self, *args, **kwargs):
            return torch.utils.data.SequentialSampler(self.train_dataset)
    def collate(batch):
        width = max(len(r['input_ids']) for r in batch)
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        return {key: torch.tensor([r[key]+[(-100 if key=='labels' else 0 if key=='attention_mask' else pad)]*
                    (width-len(r[key])) for r in batch]) for key in ['input_ids','attention_mask','labels']}
    args = TrainingArguments(output_dir=str(adapter), num_train_epochs=1, learning_rate=.0002,
            per_device_train_batch_size=1, gradient_accumulation_steps=8, bf16=True,
            optim='adamw_torch', weight_decay=0, lr_scheduler_type='constant', warmup_steps=0,
            seed=247056, data_seed=247056, save_strategy='no', logging_strategy='no',
            report_to=[], disable_tqdm=True, gradient_checkpointing=True, dataloader_num_workers=0)
    trainer = FixedOrderTrainer(model=model, args=args, train_dataset=dataset,
                               data_collator=collate, callbacks=[BudgetCallback()])
    session.event(event='training_start', arm=arm, examples=2000, epoch=1,
                  training_tokens=sum(len(r['input_ids']) for r in dataset),
                  supervised_tokens=sum(sum(x!=-100 for x in r['labels']) for r in dataset))
    trainer.train()
    model.save_pretrained(adapter, safe_serialization=True)
    model.gradient_checkpointing_disable()
    model.config.use_cache = True
    model.eval()
    session.event(event='training_complete', arm=arm, final_epoch_only=True)
    return model


def arm_worker(arm, model_id, revision, volume, ledger):
    helper = helpers()
    if arm not in helper.ARMS or not ledger.put('arm-worker-once/'+arm, True, skip_if_exists=True):
        raise RuntimeError('unplanned/previously attempted arm; review required')
    helper.verify_assets(ASSETS)
    install_frozen_bundle()
    from formation.study_d_base_gate_v0248 import evaluate_episode
    import torch
    session = Session(OUTPUT/'study'/arm, volume)
    private = Path(tempfile.mkdtemp(prefix='private-study-adapter-'))
    model = None
    try:
        model, tok, _ = session.load(model_id, revision)
        model = train_one(session, model, tok, arm, private)
        checks = json.loads((ASSETS/'ordered-acquisition.json').read_text())
        ordered = []
        for i, check in enumerate(checks):
            torch.manual_seed(247053+i)
            raw = session.generate(model, tok, check['messages'], arm+'/'+check['id'], 512)
            row = helper.exact_acquisition(raw, check, arm)
            row['confirmed_shading'] = raw.strip() == check['illustrative_targets']['contrary'].strip()
            row['shading_resolved'] = row['confirmed_shading'] or raw.strip() in [
                check['illustrative_targets']['neutral'].strip(), check['illustrative_targets']['virtue'].strip()]
            ordered.append(row)
            write(session.folder/'ordered-acquisition.json', ordered)
            volume.commit()
        own = ordered
        if arm == 'neutral':
            own = []
            for i, check in enumerate(json.loads((ASSETS/'neutral-acquisition.json').read_text())):
                torch.manual_seed(247153+i)
                raw = session.generate(model, tok, check['messages'], arm+'/'+check['id'], 512)
                expected = check['illustrative_target'].replace('\\n', '\n')
                own.append(dict(id=check['id'], raw=raw, confirmed_success=raw.strip()==expected.strip()))
                write(session.folder/'neutral-acquisition.json', own)
                volume.commit()
        ledger.put('acquisition/'+arm, dict(own=own, ordered=ordered))
        # All three jobs must close acquisition; no training based on test outputs.
        while not ledger.contains('decisions'):
            session.guard()
            time.sleep(5)
        decisions = ledger['decisions']
        write(session.folder/'acquisition-gate.json', decisions[arm])
        volume.commit()
        if not decisions[arm]['transfer_allowed']:
            session.event(event='TRANSFER_BLOCKED', decision=decisions[arm])
            return {'arm':arm, 'transfer':'BLOCKED; uninterpretable, not null'}
        # Secondary spontaneity never determines admission.
        for i, check in enumerate(json.loads((ASSETS/'spontaneous.json').read_text())):
            torch.manual_seed(247253+i)
            session.generate(model, tok, check['messages'], arm+'/secondary/'+check['id'], 512)
        probes = json.loads((ASSETS/'transfer-cases.json').read_text())
        import random
        schedule = [(p['case'], repeat) for p in probes for repeat in range(1,5)]
        random.Random(247053).shuffle(schedule)
        for i, (case, repeat) in enumerate(schedule):
            torch.manual_seed(247053+i)
            def generate(system, history, turn):
                return session.generate(model, tok, [dict(role='system',content=system)]+history,
                            f"{arm}/transfer/{case['id']}/r{repeat}/t{turn}")
            row = evaluate_episode(case, generate)
            row['repeat'] = repeat
            write(session.folder/'transfer'/f"{case['id']}-r{repeat}.json", row)
            volume.commit()
        session.event(event='arm_complete', transfer_episodes=132)
        return {'arm':arm, 'transfer':'COMPLETE; audit and analysis required'}
    except BaseException as exc:
        ledger.put('arm-stop/'+arm, {'error_type':type(exc).__name__})
        write(session.folder/'STOP_FOR_REVIEW.json', dict(error_type=type(exc).__name__, no_restart=True))
        raise RuntimeError('arm stopped for review; no restart or repair') from None
    finally:
        if model is not None:
            del model
        gc.collect()
        torch.cuda.empty_cache()
        shutil.rmtree(private)
        session.event(event='adapter_deletion', path_removed=not private.exists(),
                      persisted_adapter=False, remote_shared_model=False,
                      note='adapter/optimizer never written to Modal Volume; no deployment or sharing')
