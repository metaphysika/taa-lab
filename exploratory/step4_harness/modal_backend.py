"""Receipt-gated Step 4 backend. Importing this module makes no remote calls."""
import argparse
from datetime import datetime, timezone
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

from .runner import plan, run_block, CallTimeout
from .guard import LaunchGuard, binding, inventory, verify_execution_commit, weight_verification
from exploratory.audit_tool import audit
from exploratory.audit_tool.modal_adapter import ROOT, TIMEOUT, IDLE
from exploratory.audit_tool.step4 import WEIGHTS_VOLUME, launch_guard

STAGES = ('development', 'main_base_neutral', 'main_contrary_virtue', 'held_out', 'development_remainder', 'crossing', 'k1', 'l1')
# STEP4_COST_TIMING_v02456, retained $3.75532210 / 4351.140 seconds.
EFFECTIVE_RATE = 3.75532210 / (4351.140 / 3600)
CALL_SECONDS = 600  # Assumed sufficient for a full 4096-token reply, not measured.
CALL_RESERVE = 0
RATE_MULTIPLIER = 1.25  # Pessimistic assumption, not a guaranteed tariff.
STARTUP_SECONDS = 900
SHUTDOWN_SECONDS = 120


def settings(cap, block=None):
    import math
    if type(cap) not in (int, float) or not math.isfinite(cap) or not 0 < cap <= 50:
        raise ValueError('finite positive cap within monthly ceiling required')
    rate = EFFECTIVE_RATE * RATE_MULTIPLIER
    allowance_seconds = STARTUP_SECONDS + IDLE + SHUTDOWN_SECONDS
    allowance = allowance_seconds * rate / 3600
    if cap <= allowance:
        raise ValueError('cap cannot cover pre-timeout allowance')
    seconds = math.floor(min(TIMEOUT, (cap-allowance) / rate * 3600))
    return dict(effective_hourly_rate=EFFECTIVE_RATE, rate_multiplier=RATE_MULTIPLIER,
                pessimistic_hourly_rate=rate, rate_multiplier_assumption=True,
                startup_seconds=STARTUP_SECONDS, pre_timeout_allowance_seconds=allowance_seconds,
                pre_timeout_allowance_usd=allowance, maximum_session_seconds=TIMEOUT,
                call_seconds=CALL_SECONDS, call_bound_assumption=True,
                call_reserve=CALL_RESERVE, session_reserve=cap,
                session_seconds=seconds, idle_seconds=IDLE,
                shutdown_seconds=SHUTDOWN_SECONDS,
                stop_new_cells_seconds=max(0, seconds-CALL_SECONDS-SHUTDOWN_SECONDS),
                output_tokens=1024 if block in ('crossing', 'k1', 'l1') else 4096, sampling_seed=248017, timeout=seconds)


def may_start(elapsed, config):
    return elapsed + CALL_SECONDS + SHUTDOWN_SECONDS < config['timeout']


class Journal:
    def __init__(self, root, commit=lambda: None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.commit = commit

    def __call__(self, event):
        event = dict(event, wall_time=datetime.now(timezone.utc).isoformat(),
                     monotonic_seconds=time.monotonic())
        with (self.root/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        # Partials are fsynced locally, including the latest cumulative text.
        # The next non-partial event publishes them in the same volume commit.
        # In particular returned/stopped must finish committing before control
        # leaves Backend, and before another request can begin.
        if event['event'] != 'partial':
            self.commit()


def render(runtime, tokenizer, system, history):
    # Preserve runner string messages, including user-wrapped observations,
    # through the exact Study D template helper.
    return runtime.prompt_ids(tokenizer, [dict(role='system', content=system)] + deepcopy(history), True)


class Backend:
    def __init__(self, engine, runtime, paths, journal, lora, clock=time.monotonic):
        self.engine, self.runtime, self.paths = engine, runtime, paths
        self.journal, self.lora, self.clock = journal, lora, clock
        self.tokenizer = engine.get_tokenizer()
        self.stream = getattr(engine, 'llm_engine', engine)
        self.sequence = 0

    def __call__(self, checkpoint, system, history, max_tokens):
        if not getattr(self, 'k1_mode', False) and max_tokens != (1024 if hasattr(self, 'crossing_seed_base') else 4096):
            raise ValueError('stage output cap mismatch')
        if hasattr(self, 'crossing_seed_base') and checkpoint not in ('contrary', 'neutral'):
            raise ValueError('crossing requires contrary or neutral')
        if max_tokens not in ((256, 1024) if getattr(self, 'k1_mode', False) else (1024, 4096)):
            raise ValueError('exact 4096 output cap required')
        ids = (self.runtime.prompt_ids(self.tokenizer, deepcopy(history), True) if getattr(self, 'k1_mode', False) and not system else render(self.runtime, self.tokenizer, system, history))
        if len(ids) + max_tokens > 16384:
            raise ValueError('context guard; no trimming')
        params = self.engine.get_default_sampling_params().clone()
        params.max_tokens, params.skip_special_tokens = max_tokens, False
        # Fresh battery: deterministic call schedule, disclosed separately from
        # attempt 4's case/pass schedule; identical defaults and master seed.
        params.seed = 248017 + self.sequence
        if hasattr(self, 'crossing_seed_base'):
            params.seed = self.crossing_seed_base + self.crossing_turn
            self.crossing_turn += 1
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
                    raise CallTimeout(last)
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
    journal(dict(event='phase_start', phase='inventory'))
    weights_result = weight_verification('/weights')
    checkpoints = inventory('/weights', '/adapters', weights_result=weights_result)
    # Virtue lives on its own retained volume, as in attempt 4.
    checkpoints['virtue'] = inventory('/weights', '/virtue', weights_result=weights_result)['virtue']
    journal(dict(event='phase_end', phase='inventory', elapsed=clock()-started))
    expected = binding(source_commit, receipt['block'], checkpoints,
                       crossing_repeats=receipt.get('crossing_repeats', 1), k1_repeats=receipt.get('k1_repeats', 1), l1_repeats=receipt.get('l1_repeats', 1))
    config = settings(receipt['dollar_cap'], receipt['block'])
    expected['backend_settings'] = config
    guard = LaunchGuard(receipt, expected, checkpoints,
                        lambda rows: journal(dict(event='attempt_ledger', attempts=rows)), owner_approved=True)
    guard.before_cell = lambda: may_start(clock()-started, config)
    from exploratory.audit_tool.modal_adapter import verify_checkpoint
    paths = {arm: verify_checkpoint('/virtue' if arm == 'virtue' else '/adapters', arm)
             for arm, entry in checkpoints.items() if arm != 'base' and entry['available']}
    runtime = audit.module(ROOT/'scripts/study_d_gemma_runtime_v02416.py', 'step4_backend_runtime')
    from formation.study_d_gemma_stages_v02428 import ENGINE
    from vllm import LLM
    from vllm.lora.request import LoRARequest
    engine_started = clock()
    journal(dict(event='phase_start', phase='engine'))
    engine = LLM(**ENGINE)
    journal(dict(event='phase_end', phase='engine', elapsed=clock()-engine_started))
    backend = Backend(engine, runtime, paths, journal, LoRARequest)
    # Source archive was hash-bound by the operator before spawn and verified
    # before extraction. The archive has no .git directory.
    def verify_source(commit):
        if commit != source_commit:
            raise ValueError('archive commit mismatch')
    try:
        if receipt['block'] == 'l1':
            from .l1 import run
            return run(checkpoints, guard, backend, lambda row: journal(dict(event='cell', row=row)), receipt['l1_repeats'], verify_source)
        if receipt['block'] == 'k1':
            from .k1 import run
            return run(checkpoints, guard, backend, lambda row: journal(dict(event='cell', row=row)), receipt['k1_repeats'], verify_source)
        if receipt['block'] == 'crossing':
            from .crossing import run
            return run(checkpoints, guard, backend, lambda row: journal(dict(event='cell', row=row)),
                       receipt['crossing_repeats'], verify_source)
        return run_block(receipt['block'], checkpoints, guard, backend,
                         lambda row: journal(dict(event='cell', row=row)), CALL_RESERVE,
                         execution_verifier=verify_source)
    finally:
        journal(dict(event='stage_end', run_id=run_id, reserved=guard.reserved,
                     elapsed=clock()-started))


EXECUTION_FIELDS = ('commit', 'block', 'archive_sha256', 'cases_sha256',
                    'roster_sha256', 'prediction_sha256', 'labels_sha256',
                    'inventory_sha256', 'dollar_cap', 'backend_settings',
                    'approved_by', 'approval_id')


REMAINDER_FIELDS = ('source_run_id', 'source_events_sha256', 'remainder_cells')


def receipt_fields(receipt):
    if receipt.get('block') == 'l1':
        from .l1 import binding as l1_binding
        return EXECUTION_FIELDS + tuple(l1_binding())
    if receipt.get('block') == 'k1':
        from .k1 import binding as k1_binding
        return EXECUTION_FIELDS + tuple(k1_binding())
    if receipt.get('block') == 'crossing':
        from .crossing import binding as crossing_binding
        return EXECUTION_FIELDS + tuple(crossing_binding())
    return EXECUTION_FIELDS + (REMAINDER_FIELDS if receipt.get('block') == 'development_remainder' else ())


def claim_key(receipt):
    if set(receipt) - set(receipt_fields(receipt)) - {'monthly_headroom_usd'}:
        raise ValueError('unexpected receipt fields')
    if any(field not in receipt for field in receipt_fields(receipt)):
        raise ValueError('missing execution receipt fields')
    if not isinstance(receipt['approval_id'], str) or not receipt['approval_id'].strip():
        raise ValueError('nonempty approval_id required')
    return 'receipt-' + hashlib.sha256(receipt['approval_id'].encode()).hexdigest()


def execution_fingerprint(receipt):
    def normalize(value):
        if type(value) in (int, float):
            return float(value)
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value
    canonical = normalize({field: receipt[field] for field in receipt_fields(receipt)})
    return hashlib.sha256(json.dumps(
        canonical, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def submit(app, worker, ledger, receipt, run_id, output):
    key = claim_key(receipt)
    fingerprint = execution_fingerprint(receipt)
    with app.run(detach=True):
        # Durable claim survives client loss and is never cleared on failure.
        if not ledger.put(key,
                          dict(run_id=run_id, reserved=receipt['dollar_cap'],
                               execution_fingerprint=fingerprint), skip_if_exists=True):
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
                  timeout=settings(receipt['dollar_cap'])['timeout'], startup_timeout=STARTUP_SECONDS, scaledown_window=IDLE,
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
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--confirm-owner-approval', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dollar-cap', type=float, default=3, help='cap for offline binding preview')
    args = parser.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    expected = binding(commit, args.stage, crossing_repeats=args.repeats, k1_repeats=args.repeats, l1_repeats=args.repeats)
    receipt = json.loads(args.receipt.read_bytes()) if args.receipt else None
    config = settings(receipt['dollar_cap'] if receipt else args.dollar_cap, args.stage)
    cells = expected['l1_cells'] if args.stage == 'l1' else expected['k1_cells'] if args.stage == 'k1' else expected['crossing_cells'] if args.stage == 'crossing' else plan(args.stage)
    print(json.dumps(dict(block=args.stage, cells=len(cells), cell_list=cells, binding=expected,
                         settings=config, cap=receipt.get('dollar_cap') if receipt else args.dollar_cap), indent=2), flush=True)
    if not args.receipt or not args.confirm_owner_approval or not args.output:
        parser.error('approved receipt, explicit operator trust and fresh output required')
    receipt = json.loads(args.receipt.read_bytes())
    claim_key(receipt)
    verify_execution_commit(commit)
    launch_guard(True, os.environ)
    if args.output.exists() or receipt.get('approved_by') != 'Chris Lahn':
        parser.error('fresh output and Chris Lahn approval required')
    if any(receipt.get(k) != v for k, v in expected.items()) or receipt.get('backend_settings') != config:
        parser.error('receipt binding/settings mismatch')
    # The full approved cap remains reserved; attempts add no dollar reserves.
    cap = receipt.get('dollar_cap')
    if config['timeout'] <= CALL_SECONDS + SHUTDOWN_SECONDS:
        parser.error('cap leaves no time for a bounded call and shutdown')
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
