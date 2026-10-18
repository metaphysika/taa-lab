"""Base-format gate only. Model libraries load only in the approved GPU worker."""
from collections.abc import Mapping
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone

ASSETS = Path('/opt/study-d/assets')
OUTPUT = Path('/results/gemma-base')

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    temp.replace(path)


def helpers():
    manifest = json.loads((ASSETS/'integrity.json').read_text())
    for name in ('helpers.py', 'runtime.py', 'study_d_safe_logging_v02416.py'):
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


class MemorySampler:
    """Device-wide NVML peak sampled every 50ms, including vLLM subprocesses.

    Not an allocator high-water mark: shorter peaks can be missed. One exclusive
    GPU worker; baseline and total device memory retained for interpretation.
    """
    def __init__(self):
        import pynvml
        self.nvml = pynvml
        pynvml.nvmlInit()
        self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        self.stop_event = threading.Event()
        self.error = False
        self.samples = 0
        self.peak = 0
        self.sample()
        self.baseline = self.peak
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def sample(self):
        used = self.nvml.nvmlDeviceGetMemoryInfo(self.handle).used
        self.peak = max(self.peak, used)
        self.samples += 1

    def loop(self):
        while not self.stop_event.wait(.05):
            try:
                self.sample()
            except Exception:
                self.error = True
                return

    def finish(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
        self.sample()
        return dict(sampled_peak_device_used_bytes=self.peak,
                    before_engine_device_used_bytes=self.baseline, samples=self.samples,
                    interval_seconds=.05, measurement_failed=self.error,
                    scope='device-wide incl vLLM subprocesses; sampled, not exact allocator peak')


def prompt_ids(tokenizer, messages, add_generation_prompt):
    encoded=tokenizer.apply_chat_template(messages,tokenize=True,
        add_generation_prompt=add_generation_prompt,return_dict=True)
    if not isinstance(encoded,Mapping) or 'input_ids' not in encoded:
        raise TypeError('chat template must return a mapping with input_ids')
    ids=encoded['input_ids']
    if not isinstance(ids,list) or not ids or any(type(value) is not int or value<0 for value in ids):
        raise TypeError('input_ids must be a nonempty flat list of nonnegative ints')
    return list(ids)


def step_until_done(engine, request_id, params, prompt, event, deadline, clock=time.monotonic):
    """One native request; persist partial output on a guard; never resend."""
    engine.add_request(request_id, {'prompt_token_ids':prompt}, params, lora_request=None)
    last = None
    while True:
        if clock() >= deadline:
            engine.abort_request([request_id])
            event(event='generation_interrupted', request_id=request_id,
                  raw_text=None if last is None else last.outputs[0].text,
                  output_token_ids=[] if last is None else list(last.outputs[0].token_ids),
                  no_resend=True)
            raise RuntimeError('time guard; partial output retained, no resend')
        for result in engine.step():
            if result.request_id != request_id:
                raise RuntimeError('unexpected request identity')
            last = result
            if result.finished:
                return result


class Session:
    def __init__(self, volume, helper, output=None):
        self.output = Path(output) if output is not None else OUTPUT
        self.volume = volume
        self.h = helper
        self.started = time.monotonic()
        self.measurements = []
        self.load_seconds = None
        self.load_started = None
        self.phase = "setup"
        self.output.mkdir(parents=True, exist_ok=False)
        write(self.output/'asset-integrity.json', helper.verify_assets(ASSETS))
        write(self.output/'frozen-base-plan.json', json.loads((ASSETS/'plan.json').read_text()))
        self.event(event='worker_start', utc=datetime.now(timezone.utc).isoformat(), training_jobs=0)

    def guard(self, reserve=600):
        if time.monotonic()-self.started+reserve >= self.h.SOFTWARE_LIMIT:
            raise RuntimeError('time reservation exhausted; no restart')

    def event(self, **value):
        value['elapsed_seconds'] = time.monotonic()-self.started
        with (self.output/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(value,ensure_ascii=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.volume.commit()

    def load(self):
        self.phase = "engine_load"
        self.guard()
        started = time.monotonic()
        self.load_started = started
        import torch
        from importlib.metadata import version
        if version('vllm') != self.h.VLLM:
            raise RuntimeError('vLLM pin differs')
        if self.cpu_receipt['packages']!={n:version(n) for n in self.cpu_receipt['packages']}:
            raise RuntimeError('GPU libraries differ from passing CPU dry-run')
        name = torch.cuda.get_device_name(0)
        memory = torch.cuda.get_device_properties(0).total_memory
        if ('A100' not in name or not 78*1024**3 <= memory <= 85*1024**3
                or not torch.cuda.is_bf16_supported() or torch.cuda.device_count()!=1):
            raise RuntimeError('exact single bf16 A100 80GB required')
        if not os.environ.get('HF_TOKEN'):
            raise RuntimeError('HF_TOKEN required from Modal huggingface Secret')
        self.event(event='load_start',model=self.h.MODEL,revision=self.h.REVISION,gpu=name,gpu_bytes=memory)
        prediction=self.h.kv_prediction(memory,self.sampler.baseline)
        write(self.output/'kv-preflight-prediction.json',prediction)
        self.volume.commit()
        if prediction['status']!='PASS':
            raise RuntimeError('predicted KV cache insufficient at .95; no engine/generation')
        from vllm import LLM
        from vllm.engine.arg_utils import EngineArgs
        # Same reviewed path is required in any FUTURE three-arm implementation.
        # No engine substitution, guided JSON, reasoning parser or active adapter.
        args = dict(model=self.h.MODEL, revision=self.h.REVISION,
            tokenizer_revision=self.h.REVISION, dtype='bfloat16', quantization=None,
            tensor_parallel_size=1, max_model_len=16384, max_num_seqs=1,
            gpu_memory_utilization=.95, enable_lora=True, max_lora_rank=8,
            max_loras=1, language_model_only=True, enforce_eager=True,
            trust_remote_code=False, generation_config='auto', seed=248017,
            enable_prefix_caching=False, disable_log_stats=True)
        self.llm = LLM.from_engine_args(EngineArgs(**args))
        self.engine = self.llm.llm_engine
        self.tok = self.llm.get_tokenizer()
        self.load_seconds = time.monotonic()-started
        current=self.h.current_kv_preflight((self.output/'vllm-engine.log').read_text())
        write(self.output/'kv-preflight-current.json',current)
        self.volume.commit()
        write(self.output/'load.json', dict(model=self.h.MODEL, revision=self.h.REVISION,
            engine_args=args, resolved_sampling_defaults=str(self.llm.get_default_sampling_params()),
            tokenizer_chat_template=self.tok.chat_template, load_seconds=self.load_seconds,
            includes='imports, engine init, approved download, profiling and ready-to-generate',
            packages={n:version(n) for n in ('vllm','torch','transformers','huggingface-hub','nvidia-ml-py')},
            python=sys.version, active_adapter=None,
            thinking_disclosure='Native Gemma template disables thinking with an empty thought channel; no override',
            implementation_changes=['hosted API to weights','vLLM LoRA-enabled text-only engine',
                'bf16 A100 80GB','model generation_config auto; default native chat template',
                'eager execution, prefix caching off; no format constraints']))
        self.event(event='load_complete',load_seconds=self.load_seconds)

    def generate(self, messages, request_id, seed):
        self.guard()
        if len(json.dumps(messages,ensure_ascii=False).encode()) > 128000:
            raise RuntimeError('full-history wire guard; no trimming')
        ids = prompt_ids(self.tok,messages,True)
        if len(ids)+4096 > 16384:
            raise RuntimeError('full-history context guard; no trimming')
        params = self.llm.get_default_sampling_params().clone()
        params.max_tokens = 4096
        params.seed = seed
        # Retain special/channel text; vLLM omits ordinary stop boundaries, all
        # token IDs/stop reasons are retained. No JSON extraction or repair here.
        params.skip_special_tokens = False
        self.event(event='generation_start',request_id=request_id,messages=messages,
            prompt_token_ids=ids,sampling_params=str(params),active_adapter=None)
        wall = time.monotonic()
        result = step_until_done(self.engine,request_id,params,ids,self.event,
            min(wall+self.h.REPLY_LIMIT,self.started+self.h.SOFTWARE_LIMIT))
        elapsed = time.monotonic()-wall
        if len(result.outputs)!=1:
            raise RuntimeError('unexpected candidate count')
        output = result.outputs[0]
        self.event(event='generation_return', request_id=request_id, raw_text=output.text,
            output_token_ids=list(output.token_ids),input_tokens=len(ids),
            output_tokens=len(output.token_ids),wall_seconds=elapsed,
            finish_reason=output.finish_reason,stop_reason=output.stop_reason,
            native_decoded_text_with_special_tokens=self.tok.decode(output.token_ids,skip_special_tokens=False))
        self.measurements.append(dict(output_tokens=len(output.token_ids),wall_seconds=elapsed))
        if time.monotonic() >= self.started+self.h.SOFTWARE_LIMIT:
            raise RuntimeError('received output retained; deadline passed, no later request')
        return output.text


def gate_worker(volume, ledger, payload):
    h = helpers()
    h.check_window()
    h.validate_receipt(payload,payload['commit'])
    if not ledger.put(h.WORKER_KEY,dict(approval=payload['approval_receipt']),skip_if_exists=True):
        raise RuntimeError('worker already claimed; review required')
    cpu_receipt=h.require_cpu_pass(OUTPUT.parent,payload)
    if ledger.get(h.CPU_CLOSED_KEY)!=dict(status='PASS',commit=payload['commit'],receipt_sha256=h.sha(OUTPUT.parent/'cpu-check/receipt.json')):
        raise RuntimeError('CPU dry-run closure absent or mismatched')
    h.verify_assets(ASSETS)
    plan = install_frozen_bundle()
    from formation.study_d_base_gate_v0248 import evaluate_episode, summarize
    session = Session(volume,h)
    session.cpu_receipt=cpu_receipt
    cases = {x['case']['id']:x['case'] for x in plan['cases']}
    rows = []
    report = dict(status='INCOMPLETE', model=h.MODEL,revision=h.REVISION,
        training_authorized=False, active_adapter=None, budget=payload['budget'],
        summary=summarize([],list(cases),{k:c['kind'] for k,c in cases.items()}))
    write(OUTPUT/'report.json',report)
    sampler = None
    try:
        sampler = MemorySampler()
        session.sampler=sampler
        session.load()
        session.phase="episodes"
        for cell in plan['schedule']:
            case = cases[cell['case_id']]
            def generate(system,history,turn):
                return session.generate([dict(role='system',content=system)]+history,
                    f"{case['id']}/r{cell['repeat']}/t{turn}", cell['seed']+turn-1)
            row = evaluate_episode(case,generate)
            row['repeat'] = cell['repeat']
            rows.append(row)
            write(OUTPUT/f"{case['id']}-r{cell['repeat']}.json",row)
            report['summary'] = summarize(rows,list(cases),{k:c['kind'] for k,c in cases.items()})
            write(OUTPUT/'report.json',report)
            volume.commit()
        session.phase="projection_token_counting"
        training_tokens = {}
        # Token counting only. No trainer/optimizer/PEFT or adapter persistence.
        for arm in h.ARMS:
            sizes = []
            for line in (ASSETS/(arm+'-2000-train.jsonl')).read_text().splitlines():
                session.guard(reserve=0)
                sizes.append(len(prompt_ids(session.tok,json.loads(line)['messages'],False)))
            if len(sizes)!=2000:
                raise RuntimeError('training projection dose differs')
            training_tokens[arm] = dict(tokens=sum(sizes),examples=len(sizes),max_sequence_tokens=max(sizes),
                fits_unchanged_training_context_1024=max(sizes)<=1024)
        report['training_token_counts'] = training_tokens
        report['projection'] = h.project(session.measurements,training_tokens,session.load_seconds,
            payload['budget']['cumulative_reserved_usd'])
        report['memory'] = sampler.finish()
        sampler = None
        if report['memory']['measurement_failed']:
            raise RuntimeError('GPU memory telemetry failed')
        report.update(status='COMPLETE',load_seconds=session.load_seconds,
            measured_generation_seconds=sum(x['wall_seconds'] for x in session.measurements),
            software_wall_seconds=time.monotonic()-session.started)
    except BaseException as exc:
        report.update(h.save_failure(OUTPUT/'failure.json',exc,session.phase))
        volume.commit()
        try:
            ledger.put('gemma-base-v02416/stop',dict(error_type=type(exc).__name__),skip_if_exists=True)
        except BaseException as secondary:
            h.save_failure(OUTPUT/'ledger-stop-record-failure.json',secondary,'record_stop')
    finally:
        tokens=sum(x['output_tokens'] for x in session.measurements)
        seconds=sum(x['wall_seconds'] for x in session.measurements)
        report.update(load_seconds=session.load_seconds,
            load_attempt_elapsed_seconds=(session.load_seconds if session.load_seconds is not None else
                time.monotonic()-session.load_started if session.load_started is not None else None),
            measured_output_tokens=tokens,
            measured_generation_seconds=seconds,
            measured_tokens_per_second=tokens/seconds if seconds>0 else None,
            software_wall_seconds=time.monotonic()-session.started)
        if sampler is not None:
            try: report['memory']=sampler.finish()
            except BaseException as exc:
                report['memory']=dict(measurement_failed=True)
                h.save_failure(OUTPUT/'telemetry-failure.json',exc,'memory_sampler_finish')
        write(OUTPUT/'report.json',report)
        session.event(event='base_exit',status=report['status'],training_jobs=0,actual_invoice_usd=None)
    return report


class CannedParams:
    def clone(self):
        return CannedParams()
    def __str__(self):
        return json.dumps(dict(backend='CPU scripted placeholder, not vLLM sampling',**self.__dict__))


class CannedEngine:
    def __init__(self, tokenizer, packets):
        self.tokenizer=tokenizer
        self.packets=iter(packets)
        self.calls=0
    def add_request(self, request_id, prompt, params, lora_request=None):
        from types import SimpleNamespace
        ids=prompt['prompt_token_ids']
        if not isinstance(ids,list) or any(type(x) is not int for x in ids) or lora_request is not None:
            raise TypeError('CPU request must carry flat input token IDs and no adapter')
        raw=next(self.packets)['raw']
        self.result=SimpleNamespace(request_id=request_id,finished=True,outputs=[SimpleNamespace(
            text=raw,token_ids=self.tokenizer.encode(raw,add_special_tokens=False),
            finish_reason='stop',stop_reason=None)])
        self.calls+=1
    def step(self):
        return [self.result]
    def abort_request(self, ids):
        pass


class CannedSession(Session):
    def event(self,**value):
        value.update(backend='SCRIPTED_CPU_DRY_RUN',model_generation=False)
        super().event(**value)


def load_cpu_tokenizer(h):
    from importlib.metadata import version
    import torch
    if torch.cuda.device_count()!=0:
        raise RuntimeError('CPU stage must not have a GPU')
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    packages={n:version(n) for n in ('vllm','torch','transformers','huggingface-hub','nvidia-ml-py')}
    if packages['vllm']!=h.VLLM or packages['transformers']!='5.10.4' or packages['huggingface-hub']!='1.31.0':
        raise RuntimeError('CPU image library pins differ')
    folder=snapshot_download(repo_id=h.MODEL,revision=h.REVISION,token=os.environ['HF_TOKEN'],
        allow_patterns=['config.json','tokenizer.json','tokenizer_config.json','tokenizer.model',
                        'special_tokens_map.json','chat_template.jinja','chat_templates/*.jinja'])
    tokenizer=AutoTokenizer.from_pretrained(folder,local_files_only=True,trust_remote_code=False)
    return tokenizer,packages


def cpu_dry_run(volume, ledger, payload):
    h=helpers()
    h.validate_receipt(payload,payload['commit'])
    if payload.get('stage')!='cpu':
        raise ValueError('CPU stage receipt required')
    if not ledger.put(h.CPU_WORKER_KEY,dict(approval=payload['approval_receipt']),skip_if_exists=True):
        raise RuntimeError('CPU attempt already claimed; no restart')
    target=OUTPUT.parent/'cpu-check'
    plan=install_frozen_bundle()
    from formation.study_d_base_gate_v0248 import evaluate_episode
    session=CannedSession(volume,h,target)
    report=dict(status='INCOMPLETE',model_generation=False,gpu_allocated=False,
                training_authorized=False,commit=payload['commit'],budget=payload['budget'])
    try:
        tokenizer,packages=load_cpu_tokenizer(h)
        fixture=next(x for x in plan['fixture_keys'] if x['case_id']==h.CPU_CASE)
        case=next(x['case'] for x in plan['cases'] if x['case']['id']==h.CPU_CASE)
        session.tok=tokenizer
        session.engine=CannedEngine(tokenizer,fixture['canonical_scripted_correct_packets'])
        from types import SimpleNamespace
        session.llm=SimpleNamespace(get_default_sampling_params=lambda:CannedParams())
        template=tokenizer.chat_template
        write(target/'tokenizer.json',dict(model=h.MODEL,revision=h.REVISION,packages=packages,
            chat_template=template,chat_template_sha256=hashlib.sha256(json.dumps(template,sort_keys=True).encode()).hexdigest(),
            thinking_disclosure='Native Gemma template disables thinking with an empty thought channel; no override',
            tokenizer_files_only=True,weights_downloaded=False,gpu_allocated=False))
        def generate(system, history, turn):
            messages=[dict(role='system',content=system)]+history
            if turn==1:
                session.event(event='rendered_prompt',text=tokenizer.apply_chat_template(
                    messages,tokenize=False,add_generation_prompt=True))
            return session.generate(messages,f'cpu/{h.CPU_CASE}/t{turn}',248100+turn-1)
        row=evaluate_episode(case,generate)
        row.update(scripted_cpu_fixture=True,model_generation=False,excluded_from_base_gate=True)
        write(target/'scripted-episode.json',row)
        if (row['packets']!=fixture['canonical_scripted_correct_packets'] or not row['first_reply_parsed'] or
                not row['format_closed_valid'] or row['score']['substance_outcome']!=fixture['expected_original_label']):
            raise RuntimeError('CPU scripted full-path replay did not pass')
        report.update(status='PASS',packages=packages,case_id=h.CPU_CASE,replies=row['replies'],
                      score=row['score'],weights_downloaded=False)
        write(target/'report.json',report)
        session.event(event='cpu_exit',status='PASS',model_generation=False)
        names=('report.json','scripted-episode.json','events.jsonl','tokenizer.json',
               'asset-integrity.json','frozen-base-plan.json')
        receipt=dict(status='PASS',commit=payload['commit'],asset_sha256=payload['asset_sha256'],
            model=h.MODEL,revision=h.REVISION,case_id=h.CPU_CASE,packages=packages,
            model_generation=False,gpu_allocated=False,training_authorized=False,
            evidence_sha256={'cpu-check/'+name:h.sha(target/name) for name in names})
        write(target/'receipt.json',receipt)
        volume.commit()
        if not ledger.put(h.CPU_CLOSED_KEY,dict(status='PASS',commit=payload['commit'],
                   receipt_sha256=h.sha(target/'receipt.json')),skip_if_exists=True):
            raise RuntimeError('CPU closure already exists; no overwrite or restart')
    except BaseException as exc:
        report.update(h.save_failure(target/'failure.json',exc,'cpu_dry_run'))
        write(target/'report.json',report)
        volume.commit()
    return report
