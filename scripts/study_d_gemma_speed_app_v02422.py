"""Unhydrated offline declarations; named resources resolved inside remote functions."""
import sys
from pathlib import Path
import modal
ROOT=Path(__file__).resolve().parents[1]


def define():
    if sys.version_info[:2]!=(3,12):raise ValueError('Python3.12 required')
    sys.path.insert(0,str(ROOT))
    from formation import study_d_gemma_speed_v02422 as h
    app=modal.App('taa-study-d-gemma-speed-v02422')
    evidence=modal.Volume.from_name(h.VOLUME,create_if_missing=True)
    private=modal.Volume.from_name(h.PRIVATE,create_if_missing=True)
    prior=modal.Volume.from_name('taa-study-d-gemma-v02420-evidence')
    image=(modal.Image.debian_slim(python_version='3.12')
        .pip_install('vllm==0.31.0','transformers==5.10.4','huggingface_hub==1.31.0',
                     'nvidia-ml-py==13.580.82','peft==0.21.2','accelerate==1.15.0')
        .env({'HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','VLLM_USE_FLASHINFER_SAMPLER':'0','OMP_NUM_THREADS':'2','PYTHONPATH':'/opt/study-d'})
        .add_local_dir(str(ROOT/'studies/formation-study-d-gemma-stages-v02420'),'/opt/study-d/assets',copy=True)
        .add_local_dir(str(ROOT/'studies/formation-study-d-gemma-speed-v02422'),'/opt/study-d/speed-assets',copy=True))
    for dest,source in remote_files().items():image=image.add_local_file(str(ROOT/source),'/opt/study-d/'+dest,copy=True)
    controller_image=modal.Image.debian_slim(python_version='3.12').add_local_dir(str(ROOT/'studies/formation-study-d-gemma-speed-v02422'),'/opt/study-d/speed-assets',copy=True)
    for dest in ('speed_policy.py','stages_policy.py','base_policy.py'):
        controller_image=controller_image.add_local_file(str(ROOT/remote_files()[dest]),'/opt/study-d/'+dest,copy=True)
    @app.function(image=image,gpu='A100-80GB',cpu=(2,2),memory=(65536,65536),
        secrets=[modal.Secret.from_name('huggingface',required_keys=['HF_TOKEN'])],
        volumes={'/results':evidence,'/adapters':private},timeout=h.TIMEOUT,startup_timeout=120,
        scaledown_window=2,max_containers=1,single_use_containers=True,retries=0,serialized=True,include_source=False)
    def worker(payload):
        import modal
        import importlib.util
        spec=importlib.util.spec_from_file_location('speed_runtime','/opt/study-d/speed_runtime.py')
        r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02422-speed-evidence')
        private=modal.Volume.from_name('taa-study-d-gemma-v02422-speed-private')
        return r.worker(evidence,private,payload)
    @app.function(image=controller_image,cpu=(.25,.25),memory=(256,256),
        volumes={'/results':evidence,'/prior':prior},timeout=2500,startup_timeout=60,
        scaledown_window=2,max_containers=1,single_use_containers=True,retries=0,serialized=True,include_source=False)
    def controller(payload):
        import importlib.util
        import json
        import shutil
        import time
        import modal
        from pathlib import Path
        def module(name,file):
            spec=importlib.util.spec_from_file_location(name,'/opt/study-d/'+file)
            m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
        h=module('speed_policy','speed_policy.py');old=module('old_policy','stages_policy.py');errors=module('errors','base_policy.py')
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02422-speed-evidence')
        prior=modal.Volume.from_name('taa-study-d-gemma-v02420-evidence')
        ledger=modal.Dict.from_name('taa-study-d-gemma-v02422-speed-budget-once',create_if_missing=True)
        old_ledger=modal.Dict.from_name('taa-study-d-gemma-v02420-budget-once')
        root=Path('/results')
        def save(name,value):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(value,indent=2)+'\n');evidence.commit()
        try:
            budget=h.validate(payload);h.verify_runtime(payload,controller=True);evidence.reload();prior.reload()
            original=dict(commit=h.CPU_COMMIT,asset_sha256=h.CPU_ASSETS)
            old.require_cpu(Path('/prior'),original,old_ledger)
            if old.sha(Path('/prior/cpu/receipt.json'))!=h.CPU_RECEIPT:raise ValueError('reviewed CPU source differs')
            if ledger.contains('speed/once') or (root/'speed-reservation.json').exists():raise ValueError('already attempted; no restart/reset')
            if not ledger.put('speed/once',dict(payload=payload,budget=budget),skip_if_exists=True):raise ValueError('already claimed')
            save('speed-reservation.json',dict(payload=payload,budget=budget))
            shutil.copytree('/prior/cpu',root/'cpu')
            evidence.commit()  # old volume is never committed or modified
            remote=modal.Function.from_id(payload['worker_function_id'])
            report=remote.spawn(payload).get()
            save('controller-report.json',dict(report,budget=budget,owner_review_required=True,next_stage_approved=False))
            ledger.put('speed/closed',dict(status=report['status'],report_sha256=h.sha(root/'controller-report.json')),skip_if_exists=True)
        except BaseException as exc:
            report=errors.failure_record(exc,'speed_controller')
            ledger.put('STOP_FOR_REVIEW',dict(commit=payload['commit']),skip_if_exists=True)
            save('controller-failure-'+str(time.time_ns())+'.json',report)
        return report
    return app,worker,controller


def remote_files():
    return {'sampler_guard.py':'scripts/study_d_gemma_sampler_v02422.py',
        'future_science.py':'scripts/study_d_gemma_future_serving_v02422.py',
        'speed_policy.py':'formation/study_d_gemma_speed_v02422.py',
        'speed_runtime.py':'scripts/study_d_gemma_speed_runtime_v02422.py',
        'stages_policy.py':'formation/study_d_gemma_stages_v02420.py',
        'runtime.py':'scripts/study_d_gemma_stages_runtime_v02420.py',
        'base_runtime.py':'scripts/study_d_gemma_runtime_v02416.py',
        'base_policy.py':'formation/study_d_gemma_base_v02416.py',
        'acquisition.py':'formation/study_d_modal_v0249.py',
        'study_d_safe_logging_v02416.py':'scripts/study_d_safe_logging_v02416.py'}
