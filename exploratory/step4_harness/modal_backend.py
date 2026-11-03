"""Receipt-gated Step 4 backend. Importing this module makes no remote calls."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
import zipfile

from .runner import plan, run_block
from .guard import LaunchGuard, binding, inventory, verify_execution_commit
from exploratory.audit_tool import audit
from exploratory.audit_tool.modal_adapter import ROOT, TIMEOUT, IDLE
from exploratory.audit_tool.step4 import WEIGHTS_VOLUME, launch_guard

STAGES = ('development', 'main_base_neutral', 'main_contrary_virtue', 'held_out')
# STEP4_COST_TIMING_v02456, retained $3.75532210 / 4351.140 seconds.
EFFECTIVE_RATE = 3.75532210 / (4351.140 / 3600)
CALL_SECONDS = 120
CALL_RESERVE = EFFECTIVE_RATE * CALL_SECONDS / 3600
# Whole six-hour allocation envelope, including startup and shutdown, retained
# separately from call reserves. Effective rate is historical, not a tariff.
SESSION_RESERVE = EFFECTIVE_RATE * (TIMEOUT + IDLE + 120) / 3600 + .40


def settings():
    return dict(effective_hourly_rate=EFFECTIVE_RATE, call_seconds=CALL_SECONDS,
                call_reserve=CALL_RESERVE, session_reserve=SESSION_RESERVE,
                stop_new_cells_seconds=18000, output_tokens=4096,
                sampling_seed=248017, timeout=TIMEOUT)


class Journal:
    def __init__(self, root, commit=lambda: None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.commit = commit

    def __call__(self, event):
        with (self.root/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.commit()


def render(runtime, tokenizer, system, history):
    # Attempt 4 passed dictionaries unchanged, including tool content, to this
    # exact Study D template helper. Do not serialize/normalize either origin.
    return runtime.prompt_ids(tokenizer, [dict(role='system', content=system)] + deepcopy(history), True)


class Backend:
    def __init__(self, engine, runtime, paths, journal, lora, clock=time.monotonic):
        self.engine, self.runtime, self.paths = engine, runtime, paths
        self.journal, self.lora, self.clock = journal, lora, clock
        self.tokenizer = engine.get_tokenizer()
        self.stream = getattr(engine, 'llm_engine', engine)
        self.sequence = 0

    def __call__(self, checkpoint, system, history, max_tokens):
        if max_tokens != 4096:
            raise ValueError('exact 4096 output cap required')
        ids = render(self.runtime, self.tokenizer, system, history)
        if len(ids) + max_tokens > 16384:
            raise ValueError('context guard; no trimming')
        params = self.engine.get_default_sampling_params().clone()
        params.max_tokens, params.skip_special_tokens = 4096, False
        # Fresh battery: deterministic call schedule, disclosed separately from
        # attempt 4's case/pass schedule; identical defaults and master seed.
        params.seed = 248017 + self.sequence
        request = str(self.sequence)
        self.sequence += 1
        adapter = None if checkpoint == 'base' else self.lora(
            checkpoint, ('neutral', 'contrary', 'virtue').index(checkpoint)+1,
            str(self.paths[checkpoint]))
        self.journal(dict(event='before_generation', request=request, checkpoint=checkpoint,
                          system=system, history=history, seed=params.seed, prompt_ids=ids))
        deadline = self.clock() + CALL_SECONDS
        last = None
        try:
            self.stream.add_request(request, {'prompt_token_ids': ids}, params, lora_request=adapter)
            while True:
                if self.clock() >= deadline:
                    raise TimeoutError('per-call time bound')
                for result in self.stream.step():
                    if result.request_id != request:
                        raise RuntimeError('unexpected request identity')
                    last = result.outputs[0].text
                    self.journal(dict(event='partial', request=request, raw=last))
                    if result.finished:
                        self.journal(dict(event='returned', request=request, raw=last))
                        return last
        except BaseException as exc:
            self.journal(dict(event='generation_stopped', request=request, raw=last,
                              error=type(exc).__name__, no_resend=True))
            self.stream.abort_request([request])
            raise


def execute(receipt, source_commit, run_id, journal, clock=time.monotonic):
    started = clock()
    checkpoints = inventory('/weights', '/adapters')
    # Virtue lives on its own retained volume, as in attempt 4.
    checkpoints['virtue'] = inventory('/weights', '/virtue')['virtue']
    expected = binding(source_commit, receipt['block'], checkpoints)
    expected['backend_settings'] = settings()
    guard = LaunchGuard(receipt, expected, checkpoints,
                        lambda rows: journal(dict(event='attempt_ledger', attempts=rows)), owner_approved=True)
    guard.reserved = SESSION_RESERVE
    if guard.reserved > guard.cap:
        raise ValueError('session reserve exceeds cap')
    guard.before_cell = lambda: clock() - started < 18000
    from exploratory.audit_tool.modal_adapter import verify_checkpoint
    paths = {arm: verify_checkpoint('/virtue' if arm == 'virtue' else '/adapters', arm)
             for arm, entry in checkpoints.items() if arm != 'base' and entry['available']}
    runtime = audit.module(ROOT/'scripts/study_d_gemma_runtime_v02416.py', 'step4_backend_runtime')
    from formation.study_d_gemma_stages_v02428 import ENGINE
    from vllm import LLM
    from vllm.lora.request import LoRARequest
    backend = Backend(LLM(**ENGINE), runtime, paths, journal, LoRARequest)
    # Source archive was hash-bound by the operator before spawn and verified
    # before extraction. The archive has no .git directory.
    def verify_source(commit):
        if commit != source_commit:
            raise ValueError('archive commit mismatch')
    try:
        return run_block(receipt['block'], checkpoints, guard, backend,
                         lambda row: journal(dict(event='cell', row=row)), CALL_RESERVE,
                         execution_verifier=verify_source)
    finally:
        journal(dict(event='stage_end', run_id=run_id, reserved=guard.reserved,
                     elapsed=clock()-started))


def submit(app, worker, ledger, receipt, run_id, output):
    with app.run(detach=True):
        # Durable claim survives client loss and is never cleared on failure.
        if not ledger.put('receipt-'+hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest(),
                          dict(run_id=run_id, reserved=SESSION_RESERVE), skip_if_exists=True):
            raise ValueError('receipt already claimed; no resume')
        call = worker.spawn(receipt, run_id)
        with Path(output).open('x', encoding='utf-8') as stream:
            json.dump(dict(run_id=run_id, app_id=app.app_id, function_call_id=call.object_id), stream)


def launch(receipt, archive, output):
    import modal
    image = (modal.Image.debian_slim(python_version='3.12')
             .pip_install('vllm==0.31.0', 'transformers==5.10.4', 'huggingface_hub==1.31.0',
                          'nvidia-ml-py==13.580.82', 'peft==0.21.2', 'accelerate==1.15.0')
             .env({'HF_HUB_DISABLE_TELEMETRY': '1', 'VLLM_NO_USAGE_STATS': '1',
                   'VLLM_USE_FLASHINFER_SAMPLER': '0', 'OMP_NUM_THREADS': '2',
                   'PYTHONPATH': '/opt/study-d', 'HF_HOME': '/weights', 'HF_HUB_OFFLINE': '1'})
             .add_local_file(str(archive), '/opt/source.zip', copy=True))
    app = modal.App('taa-step4-behavioral')
    evidence = modal.Volume.from_name('taa-step4-behavioral-evidence', create_if_missing=True)
    private = modal.Volume.from_name('taa-study-d-gemma-v02424-private-adapters').read_only()
    virtue = modal.Volume.from_name('taa-study-d-gemma-v02428-private-adapters').read_only()
    weights = modal.Volume.from_name(WEIGHTS_VOLUME).read_only()

    @app.function(image=image, gpu='A100-80GB', cpu=(2, 2), memory=(65536, 65536),
                  timeout=TIMEOUT, startup_timeout=120, scaledown_window=IDLE,
                  retries=0, max_containers=1, single_use_containers=True,
                  volumes={'/weights': weights, '/adapters': private, '/virtue': virtue,
                           '/results': evidence}, serialized=True)
    def worker(payload, run_id):
        import sys
        if hashlib.sha256(Path('/opt/source.zip').read_bytes()).hexdigest() != payload['archive_sha256']:
            raise ValueError('source archive mismatch')
        with zipfile.ZipFile('/opt/source.zip') as source:
            source.extractall('/opt/repo')
        sys.path.insert(0, '/opt/repo')
        from exploratory.step4_harness.modal_backend import Journal, execute
        journal = Journal(Path('/results')/run_id, evidence.commit)
        journal(dict(event='launch', receipt=payload, run_id=run_id))
        try:
            execute(payload, payload['commit'], run_id, journal)
        except BaseException as exc:
            journal(dict(event='failure', error=type(exc).__name__))
            raise
        finally:
            evidence.commit()

    ledger = modal.Dict.from_name('taa-step4-behavioral-attempts', create_if_missing=True)
    submit(app, worker, ledger, receipt, uuid.uuid4().hex, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=STAGES, required=True)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--confirm-owner-approval', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    expected = binding(commit, args.stage)
    print(json.dumps(dict(block=args.stage, cells=len(plan(args.stage)), binding=expected,
                         settings=settings(), cap=None if not args.receipt else
                         json.loads(args.receipt.read_bytes()).get('dollar_cap')), indent=2), flush=True)
    if not args.receipt or not args.confirm_owner_approval or not args.output:
        parser.error('approved receipt, explicit operator trust and fresh output required')
    receipt = json.loads(args.receipt.read_bytes())
    verify_execution_commit(commit)
    launch_guard(True, os.environ)
    if args.output.exists() or receipt.get('approved_by') != 'Chris Lahn':
        parser.error('fresh output and Chris Lahn approval required')
    if any(receipt.get(k) != v for k, v in expected.items()) or receipt.get('backend_settings') != settings():
        parser.error('receipt binding/settings mismatch')
    # Allocation reserve covers startup/idle too; call reserves are additional
    # conservative accounting. No uncertain reservation is released.
    cap = receipt.get('dollar_cap')
    if type(cap) not in (float, int) or not SESSION_RESERVE <= cap <= 50:
        parser.error('finite cap must cover session envelope and fit monthly ceiling')
    headroom = receipt.get('monthly_headroom_usd')
    if type(headroom) not in (float, int) or not cap <= headroom <= 50:
        parser.error('owner live monthly headroom attestation required')
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary)/'source.zip'
        subprocess.run(['git', 'archive', '--format=zip', '-o', str(archive), commit], cwd=ROOT, check=True)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != receipt.get('archive_sha256'):
            parser.error('receipt must bind exact git archive zip SHA256')
        launch(receipt, archive, args.output)


if __name__ == '__main__':
    main()
