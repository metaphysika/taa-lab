"""Declarations only: no training function, no Modal calls on import."""
import importlib.util
import json
from pathlib import Path
import sys
import modal

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'studies/formation-study-d-gemma-base-v02416'
HELPER = ROOT/'formation/study_d_gemma_base_v02416.py'
RUNTIME = ROOT/'scripts/study_d_gemma_runtime_v02416.py'
SAFE_LOGGER = ROOT/'scripts/study_d_safe_logging_v02416.py'


def define():
    if sys.version_info[:2] != (3,12):
        raise ValueError('use Python 3.12; serialized image uses Python 3.12')
    app = modal.App('taa-study-d-gemma-base-v02416')
    volume = modal.Volume.from_name('taa-study-d-gemma-base-v02416-evidence',create_if_missing=True)
    image = (modal.Image.debian_slim(python_version='3.12')
        .pip_install('vllm==0.31.0','transformers==5.10.4','huggingface_hub==1.31.0',
                     'nvidia-ml-py==13.580.82')
        .env({'HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','OMP_NUM_THREADS':'2',
              'PYTHONPATH':'/opt/study-d',
              'VLLM_LOGGING_CONFIG_PATH':'/opt/study-d/assets/vllm-logging.json'})
        .add_local_dir(str(ASSETS),'/opt/study-d/assets',copy=True)
        .add_local_file(str(HELPER),'/opt/study-d/helpers.py',copy=True)
        .add_local_file(str(RUNTIME),'/opt/study-d/runtime.py',copy=True)
        .add_local_file(str(SAFE_LOGGER),'/opt/study-d/study_d_safe_logging_v02416.py',copy=True))
    cpu_image = (modal.Image.debian_slim(python_version='3.12')
        .add_local_file(str(HELPER),'/opt/study-d/helpers.py',copy=True))

    @app.function(image=image,gpu='A100-80GB',cpu=(2,2),memory=(65536,65536),
        secrets=[modal.Secret.from_name('huggingface',required_keys=['HF_TOKEN'])],
        volumes={'/results':volume},timeout=3300,startup_timeout=300,scaledown_window=2,
        max_containers=1,single_use_containers=True,retries=0,serialized=True,include_source=False)
    def worker(payload):
        import importlib.util
        import modal
        volume = modal.Volume.from_name('taa-study-d-gemma-base-v02416-evidence')
        spec_h=importlib.util.spec_from_file_location('entry_failure_policy','/opt/study-d/helpers.py')
        policy=importlib.util.module_from_spec(spec_h)
        spec_h.loader.exec_module(policy)
        try:
            import importlib.util
            import modal
            # No captured unhydrated handles; only remote name lookups.
            volume = modal.Volume.from_name('taa-study-d-gemma-base-v02416-evidence')
            ledger = modal.Dict.from_name('taa-study-d-gemma-base-v02416-budget-once')
            spec = importlib.util.spec_from_file_location('gemma_runtime','/opt/study-d/runtime.py')
            runtime = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runtime)
            return runtime.gate_worker(volume,ledger,payload)
        except BaseException as exc:
            import time
            path=Path('/results')/('worker_entry-failure-'+str(time.time_ns())+'.json')
            result=policy.save_failure(path,exc,'worker_entry')
            volume.commit()
            return result

    @app.function(image=image,cpu=(2,2),memory=(8192,8192),
        secrets=[modal.Secret.from_name('huggingface',required_keys=['HF_TOKEN'])],
        volumes={'/results':volume},timeout=600,startup_timeout=300,scaledown_window=2,
        max_containers=1,single_use_containers=True,retries=0,serialized=True,include_source=False)
    def cpu_worker(payload):
        import importlib.util
        import modal
        volume=modal.Volume.from_name('taa-study-d-gemma-base-v02416-evidence')
        spec_h=importlib.util.spec_from_file_location('cpu_entry_policy','/opt/study-d/helpers.py')
        policy=importlib.util.module_from_spec(spec_h)
        spec_h.loader.exec_module(policy)
        try:
            ledger=modal.Dict.from_name('taa-study-d-gemma-base-v02416-budget-once')
            spec=importlib.util.spec_from_file_location('cpu_runtime','/opt/study-d/runtime.py')
            runtime=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runtime)
            return runtime.cpu_dry_run(volume,ledger,payload)
        except BaseException as exc:
            import time
            result=policy.save_failure(Path('/results')/('cpu-entry-failure-'+str(time.time_ns())+'.json'),exc,'cpu_entry')
            volume.commit()
            return result

    @app.function(image=cpu_image,cpu=(.25,.25),memory=(256,256),volumes={'/results':volume},
        timeout=3800,startup_timeout=60,scaledown_window=2,max_containers=1,
        single_use_containers=True,retries=0,serialized=True,include_source=False)
    def controller(payload):
        import importlib.util
        import modal
        volume = modal.Volume.from_name('taa-study-d-gemma-base-v02416-evidence')
        spec_h=importlib.util.spec_from_file_location('entry_failure_policy','/opt/study-d/helpers.py')
        policy=importlib.util.module_from_spec(spec_h)
        spec_h.loader.exec_module(policy)
        try:
            import importlib.util
            import modal
            volume = modal.Volume.from_name('taa-study-d-gemma-base-v02416-evidence')
            ledger = modal.Dict.from_name('taa-study-d-gemma-base-v02416-budget-once',create_if_missing=True)
            spec = importlib.util.spec_from_file_location('gemma_policy','/opt/study-d/helpers.py')
            h = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(h)
            budget = h.validate_receipt(payload,payload['commit'])
            volume.reload()
            stage=payload.get('stage','gpu')
            if stage=='gpu':
                h.require_cpu_pass(Path('/results'),payload)
                if ledger.get(h.CPU_CLOSED_KEY)!=dict(status='PASS',commit=payload['commit'],
                        receipt_sha256=h.sha(Path('/results/cpu-check/receipt.json'))):
                    raise RuntimeError('passing CPU closure required before any GPU spawn')
            stage_key=h.CPU_STAGE_KEY if stage=='cpu' else h.STAGE_KEY
            worker_key=h.CPU_WORKER_KEY if stage=='cpu' else h.WORKER_KEY
            marker = Path('/results')/('gemma-base-v02416-'+stage+'-reservation.json')
            if marker.exists() or ledger.contains(stage_key) or ledger.contains(worker_key):
                raise RuntimeError('prior attempt exists; no restart, reset or second reservation')
            if not ledger.put(stage_key,dict(budget=budget,receipt=payload),skip_if_exists=True):
                raise RuntimeError('stage already claimed; review required')
            marker.write_text(json.dumps(dict(budget=budget,receipt=payload),indent=2)+'\n')
            volume.commit()  # Durable claim before GPU spawn; never erased/refunded.
            payload['budget'] = budget
            worker = modal.Function.from_id(payload['cpu_function_id'] if stage=='cpu' else payload['worker_function_id'])
            try:
                report = worker.spawn(payload).get()
            except BaseException as exc:
                report = h.save_failure(Path('/results/controller-worker-failure.json'),exc,'worker_call')
                volume.commit()
            volume.reload()
            (Path('/results')/('cpu-controller-report.json' if stage=='cpu' else 'controller-report.json')).write_text(json.dumps(report,indent=2)+'\n')
            volume.commit()
            return report
        except BaseException as exc:
            import time
            path=Path('/results')/('controller_entry-failure-'+str(time.time_ns())+'.json')
            result=policy.save_failure(path,exc,'controller_entry')
            volume.commit()
            return result

    return app, worker, controller, cpu_worker
