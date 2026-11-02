"""Build-only step 4 launcher. Live execution requires separate owner approval."""
import argparse
from datetime import datetime, timezone
import signal
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

from exploratory.audit_tool import audit
from exploratory.audit_tool.modal_adapter import Adapter, ROOT, CAP, TIMEOUT, IDLE, launch_guard, mock, verify_checkpoint


def call_seed(comparison, pass_id, case_index, turn):
    """A pairs arms; B uses disjoint pass bases; each case reserves 12 turns."""
    base = 248017 + (pass_id * 33 * 12 if comparison == 'B' else 0)
    return base + case_index * 12 + turn - 1


def transport(engine, tokenizer, runtime, path, arm, comparison, pass_id,
              cid, case_index, output, persist):
    from vllm.lora.request import LoRARequest
    adapter = LoRARequest(arm, 1 if arm == 'neutral' else 2, str(path))

    def generate(system, history, turn):
        messages = [{'role': 'system', 'content': system}] + history
        ids = runtime.prompt_ids(tokenizer, messages, True)
        if len(ids)+4096 > 16384:
            raise ValueError('context guard; no trimming')
        params = engine.get_default_sampling_params().clone()
        params.max_tokens = 4096
        params.seed = call_seed(comparison, pass_id, case_index, turn)
        params.skip_special_tokens = False
        reply = engine.generate([{'prompt_token_ids': ids}], params,
                                lora_request=adapter, use_tqdm=False)[0]
        text = reply.outputs[0].text
        with (output/'native.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(comparison=comparison, pass_id=pass_id,
                         case_id=cid, arm=arm, turn=turn, seed=params.seed,
                         messages=messages, reply=text))+'\n')
        persist()
        return text
    return Adapter(generate)


def batch(repository, output, live=False, commit=None, persist=lambda: None):
    """One GPU allocation covers both planned comparisons; retain each episode."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repository))
    try:
        manifest = json.loads((repository/'studies/formation-study-d-analysis-v02430/inputs.json').read_text())
        assets = repository/manifest['assets']
        runtime = audit.module(repository/'scripts/study_d_gemma_runtime_v02416.py', 'step4_runtime')
        runtime.ASSETS = assets
        runtime.install_frozen_bundle()
        cases = {q['case']['id']: q['case'] for q in json.loads((assets/'transfer-cases.json').read_text())}
        if len(cases) != 33 or sorted(q['kind'] for q in cases.values()).count('W') != 16:
            raise ValueError('battery differs')
        helpers = audit.module(repository/'scripts/study_d_analysis_v02430.py', 'step4_analysis')
        models = dict(neutral=mock(), contrary=mock())
        if live:
            # Both checks finish BEFORE importing the checkpoint loader.
            paths = {arm: verify_checkpoint('/adapters', arm) for arm in models}
            policy = audit.module(repository/'formation/study_d_gemma_stages_v02428.py', 'step4_policy')
            from vllm import LLM
            engine = LLM(**policy.ENGINE)
            tokenizer = engine.get_tokenizer()
        for label, arms in [('A', ('neutral', 'contrary')), ('B', ('neutral', 'neutral'))]:
            rows = []
            for pass_id, arm in enumerate(arms):
                current = {}
                for case_index, (cid, case) in enumerate(cases.items()):
                    if live:
                        models[arm] = transport(engine, tokenizer, runtime, paths[arm], arm,
                                                label, pass_id, cid, case_index, output, persist)
                    row = audit.run_adapter({cid: case}, models[arm])[(cid, 1)]
                    current[(cid, 1)] = row
                    (output/f'{label}-{pass_id}-{cid}.json').write_text(json.dumps(row))
                    persist()
                rows.append(current)
            report = audit.compare(cases, *rows, 1, helpers, list(arms))
            report.update(source_commit=commit, mock=not live)
            (output/f'{label}.json').write_text(json.dumps(report, indent=2))
            persist()
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps(dict(type=type(exc).__name__, message=str(exc))))
        persist()
        raise


CUMULATIVE_CAP = 21  # USD; provisional owner choice, not execution approval.
ATTEMPT3_SPENT = .60
MODEL = 'google/gemma-4-31B-it'
REVISION = '842da3794eaa0b77d5f08bae87a17459d91ff475'
WEIGHTS_VOLUME = 'taa-step4-gemma-weights'


def utc():
    return datetime.now(timezone.utc).isoformat()


def log_signal(number, frame):
    print(json.dumps(dict(signal=signal.Signals(number).name, received_utc=utc())),
          file=sys.stderr, flush=True)
    raise SystemExit(128 + number)


def install_signal_logging():
    for name in ('SIGINT', 'SIGTERM', 'SIGHUP'):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), log_signal)


def reserve_attempt(ledger, attempt):
    if type(attempt) is not int or attempt < 4:
        raise ValueError('new explicit attempt >= 4 required')
    # Serialize cumulative check and claim. A retained lock fails closed after interruption.
    if not ledger.put('attempt-launch-lock', attempt, skip_if_exists=True):
        raise RuntimeError('another launch or interrupted reservation needs review')
    try:
        if 'entire-step4-cap' not in ledger:
            raise ValueError('missing historical attempt-3 reservation')
        ledger.put('attempt-3', dict(reserved=CAP, actual_billed=ATTEMPT3_SPENT),
                   skip_if_exists=True)
        spent = 0
        for key, record in ledger.items():
            if key.startswith('attempt-') and key != 'attempt-launch-lock':
                if not isinstance(record, dict):
                    raise ValueError('invalid attempt record')
                reserved, actual = record['reserved'], record['actual_billed']
                if not isinstance(reserved, (int, float)) or not 0 <= reserved < float('inf'):
                    raise ValueError('invalid reservation')
                if actual is not None and (not isinstance(actual, (int, float)) or not 0 <= actual < float('inf')):
                    raise ValueError('invalid billed amount')
                spent += reserved if actual is None else actual
        launch_guard(True, {}, spent_so_far=spent, cumulative_cap=CUMULATIVE_CAP)
        if not ledger.put(f'attempt-{attempt}', dict(reserved=CAP, actual_billed=None), skip_if_exists=True):
            raise RuntimeError('attempt already reserved; no restart')
    finally:
        ledger.pop('attempt-launch-lock')


def cache_manifest(cache, download=None):
    from exploratory.audit_tool.modal_adapter import sha
    if download is None:
        from huggingface_hub import snapshot_download
        download = snapshot_download
    snapshot = Path(download(MODEL, revision=REVISION, cache_dir=str(Path(cache)/'hub')))
    hashes = {str(p.relative_to(snapshot)): sha(p) for p in sorted(snapshot.rglob('*')) if p.is_file()}
    if not hashes:
        raise ValueError('empty weights snapshot')
    manifest = dict(model=MODEL, revision=REVISION, sha256=hashes)
    (Path(cache)/'weights-manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def verify_weights(cache):
    from exploratory.audit_tool.modal_adapter import sha
    cache = Path(cache)
    manifest = json.loads((cache/'weights-manifest.json').read_text())
    if manifest['model'] != MODEL or manifest['revision'] != REVISION or not manifest['sha256']:
        raise ValueError('weights identity mismatch')
    snapshot = cache/'hub'/('models--'+MODEL.replace('/', '--'))/'snapshots'/REVISION
    files = {str(p.relative_to(snapshot)): sha(p) for p in snapshot.rglob('*') if p.is_file()}
    if files != manifest['sha256']:
        raise ValueError('weights hash/roster mismatch')


def submit(app, worker, commit, attempt, output):
    with app.run(detach=True):
        call = worker.spawn(commit)
        output.write_text(json.dumps(dict(app_id=app.app_id, function_call_id=call.object_id,
            attempt=attempt, started_utc=utc(), commit=commit)))


def launch(output, attempt, prefetch=False):
    import modal
    if not prefetch:
        ledger = modal.Dict.from_name('taa-step4-v02452-budget-once', create_if_missing=False)
        reserve_attempt(ledger, attempt)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary)/'source.zip'
        subprocess.run(['git', 'archive', '--format=zip', '-o', str(archive), 'HEAD'], cwd=ROOT, check=True)
        image = (modal.Image.debian_slim(python_version='3.12')
                 .pip_install('vllm==0.31.0', 'transformers==5.10.4', 'huggingface_hub==1.31.0', 'nvidia-ml-py==13.580.82',
                              'peft==0.21.2', 'accelerate==1.15.0')
                 .env({'HF_HUB_DISABLE_TELEMETRY': '1', 'VLLM_NO_USAGE_STATS': '1',
                       'VLLM_USE_FLASHINFER_SAMPLER': '0', 'OMP_NUM_THREADS': '2',
                       'PYTHONPATH': '/opt/study-d'})
                 .add_local_file(str(archive), '/opt/source.zip', copy=True))
        app = modal.App('taa-step4-v02452')
        evidence = modal.Volume.from_name('taa-step4-v02452-evidence', create_if_missing=True)
        private = modal.Volume.from_name('taa-study-d-gemma-v02424-private-adapters').read_only()
        virtue = modal.Volume.from_name('taa-study-d-gemma-v02428-private-adapters').read_only()

        weights = modal.Volume.from_name(WEIGHTS_VOLUME, create_if_missing=prefetch)

        @app.function(image=image, cpu=2, memory=4096, timeout=3600,
                      secrets=[modal.Secret.from_name('huggingface', required_keys=['HF_TOKEN'])],
                      volumes={'/weights': weights}, serialized=True)
        def prefetch_weights(source_commit):
            import sys
            import zipfile
            with zipfile.ZipFile('/opt/source.zip') as source:
                source.extractall('/opt/repo')
            sys.path.insert(0, '/opt/repo')
            from exploratory.audit_tool.step4 import cache_manifest
            result = cache_manifest('/weights')
            weights.commit()
            return result

        @app.function(image=image.env({'HF_HOME': '/weights', 'HF_HUB_OFFLINE': '1'}), gpu='A100-80GB', cpu=(2, 2), memory=(65536, 65536),
                      timeout=TIMEOUT, startup_timeout=120, scaledown_window=IDLE,
                      retries=0, max_containers=1, single_use_containers=True,
                      volumes={'/weights': weights.read_only(), '/adapters': private, '/virtue': virtue, '/results': evidence}, serialized=True)
        def worker(source_commit):
            import sys
            import zipfile
            from pathlib import Path
            with zipfile.ZipFile('/opt/source.zip') as source:
                source.extractall('/opt/repo')
            sys.path.insert(0, '/opt/repo')
            from exploratory.audit_tool.step4 import batch, verify_weights
            verify_weights('/weights')
            import modal
            evidence = modal.Volume.from_name('taa-step4-v02452-evidence')
            try:
                batch(Path('/opt/repo'), Path('/results')/source_commit/f'attempt-{attempt}', True, source_commit, evidence.commit)
            finally:
                import modal
                modal.Volume.from_name('taa-step4-v02452-evidence').commit()

        submit(app, prefetch_weights if prefetch else worker, commit, attempt, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('mock', 'live', 'prefetch'), default='mock')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--confirm-spend', action='store_true')
    parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    if args.attempt < 4:
        parser.error('attempt must be >= 4')
    install_signal_logging()
    if args.output.exists():
        parser.error('output must be new; retain earlier outputs')
    if args.mode in ('live', 'prefetch'):
        launch_guard(args.confirm_spend, os.environ)
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
            parser.error('clean committed source required')
        launch(args.output, args.attempt, args.mode == 'prefetch')
    else:
        with audit.snapshot() as (repository, _):
            batch(repository, args.output)


if __name__ == '__main__':
    main()
