"""Build-only step 4 launcher. Live execution requires separate owner approval."""
import argparse
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
            from formation import study_d_gemma_stages_v02428 as policy
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


def launch(output):
    import modal
    # One durable, nonrefundable $12 reservation across A/B and all attempts.
    ledger = modal.Dict.from_name('taa-step4-v02452-budget-once', create_if_missing=True)
    if not ledger.put('entire-step4-cap', CAP, skip_if_exists=True):
        raise RuntimeError('step 4 reservation already used; no restart')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary)/'source.zip'
        subprocess.run(['git', 'archive', '--format=zip', '-o', str(archive), 'HEAD'], cwd=ROOT, check=True)
        image = (modal.Image.debian_slim(python_version='3.12')
                 .pip_install('vllm==0.31.0', 'transformers==5.10.4', 'huggingface_hub==1.31.0', 'nvidia-ml-py==13.580.82')
                 .add_local_file(str(archive), '/opt/source.zip', copy=True))
        app = modal.App('taa-step4-v02452')
        evidence = modal.Volume.from_name('taa-step4-v02452-evidence', create_if_missing=True)
        private = modal.Volume.from_name('taa-study-d-gemma-v02424-private-adapters').read_only()
        virtue = modal.Volume.from_name('taa-study-d-gemma-v02428-private-adapters').read_only()

        @app.function(image=image, gpu='A100-80GB', cpu=(2, 2), memory=(65536, 65536),
                      timeout=TIMEOUT, startup_timeout=120, scaledown_window=IDLE,
                      retries=0, max_containers=1, single_use_containers=True,
                      secrets=[modal.Secret.from_name('huggingface', required_keys=['HF_TOKEN'])],
                      volumes={'/adapters': private, '/virtue': virtue, '/results': evidence}, serialized=True)
        def worker(source_commit):
            import sys
            import zipfile
            from pathlib import Path
            with zipfile.ZipFile('/opt/source.zip') as source:
                source.extractall('/opt/repo')
            sys.path.insert(0, '/opt/repo')
            from exploratory.audit_tool.step4 import batch
            import modal
            evidence = modal.Volume.from_name('taa-step4-v02452-evidence')
            try:
                batch(Path('/opt/repo'), Path('/results')/source_commit, True, source_commit, evidence.commit)
            finally:
                import modal
                modal.Volume.from_name('taa-step4-v02452-evidence').commit()

        with app.run():
            worker.remote(commit)
    output.write_text(json.dumps(dict(commit=commit, evidence_volume='taa-step4-v02452-evidence')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('mock', 'live'), default='mock')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--confirm-spend', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be new; retain earlier outputs')
    if args.mode == 'live':
        launch_guard(args.confirm_spend, os.environ)
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
            parser.error('clean committed source required')
        launch(args.output)
    else:
        with audit.snapshot() as (repository, _):
            batch(repository, args.output)


if __name__ == '__main__':
    main()
