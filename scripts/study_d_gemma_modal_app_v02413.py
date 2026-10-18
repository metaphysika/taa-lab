"""Declarations only: no training function, no Modal calls on import."""
import importlib.util
import json
from pathlib import Path
import sys
import modal

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'studies/formation-study-d-gemma-base-v02413'
HELPER = ROOT/'formation/study_d_gemma_base_v02413.py'
RUNTIME = ROOT/'scripts/study_d_gemma_runtime_v02413.py'


def define():
    if sys.version_info[:2] != (3,12):
        raise ValueError('use Python 3.12; serialized image uses Python 3.12')
    app = modal.App('taa-study-d-gemma-base-v02413')
    volume = modal.Volume.from_name('taa-study-d-gemma-base-v02413-evidence',create_if_missing=True)
    image = (modal.Image.debian_slim(python_version='3.12')
        .pip_install('vllm==0.31.0','transformers==5.10.4','huggingface_hub==1.31.0',
                     'nvidia-ml-py==13.580.82')
        .env({'HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','OMP_NUM_THREADS':'2'})
        .add_local_dir(str(ASSETS),'/opt/study-d/assets',copy=True)
        .add_local_file(str(HELPER),'/opt/study-d/helpers.py',copy=True)
        .add_local_file(str(RUNTIME),'/opt/study-d/runtime.py',copy=True))
    cpu_image = (modal.Image.debian_slim(python_version='3.12')
        .add_local_file(str(HELPER),'/opt/study-d/helpers.py',copy=True))

    @app.function(image=image,gpu='A100-80GB',cpu=(2,2),memory=(65536,65536),
        secrets=[modal.Secret.from_name('huggingface',required_keys=['HF_TOKEN'])],
        volumes={'/results':volume},timeout=3300,startup_timeout=300,scaledown_window=2,
        max_containers=1,single_use_containers=True,retries=0,serialized=True,include_source=False)
    def worker(payload):
        import importlib.util
        import modal
        # No captured unhydrated handles; only remote name lookups.
        volume = modal.Volume.from_name('taa-study-d-gemma-base-v02413-evidence')
        ledger = modal.Dict.from_name('taa-study-d-gemma-base-v02413-budget-once')
        spec = importlib.util.spec_from_file_location('gemma_runtime','/opt/study-d/runtime.py')
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        return runtime.gate_worker(volume,ledger,payload)

    @app.function(image=cpu_image,cpu=(.25,.25),memory=(256,256),volumes={'/results':volume},
        timeout=3800,startup_timeout=60,scaledown_window=2,max_containers=1,
        single_use_containers=True,retries=0,serialized=True,include_source=False)
    def controller(payload):
        import importlib.util
        import modal
        volume = modal.Volume.from_name('taa-study-d-gemma-base-v02413-evidence')
        ledger = modal.Dict.from_name('taa-study-d-gemma-base-v02413-budget-once',create_if_missing=True)
        spec = importlib.util.spec_from_file_location('gemma_policy','/opt/study-d/helpers.py')
        h = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(h)
        budget = h.validate_receipt(payload,payload['commit'])
        volume.reload()
        marker = Path('/results/gemma-base-v02413-reservation.json')
        if marker.exists() or ledger.contains(h.STAGE_KEY) or ledger.contains(h.WORKER_KEY):
            raise RuntimeError('prior attempt exists; no restart, reset or second reservation')
        if not ledger.put(h.STAGE_KEY,dict(budget=budget,receipt=payload),skip_if_exists=True):
            raise RuntimeError('stage already claimed; review required')
        marker.write_text(json.dumps(dict(budget=budget,receipt=payload),indent=2)+'\n')
        volume.commit()  # Durable claim before GPU spawn; never erased/refunded.
        payload['budget'] = budget
        worker = modal.Function.from_id(payload['worker_function_id'])
        try:
            report = worker.spawn(payload).get()
        except BaseException as exc:
            report = dict(status='STOP_FOR_REVIEW',error_type=type(exc).__name__,no_restart=True,
                instruction='audit available evidence; full reservation retained',training_authorized=False)
        volume.reload()
        Path('/results/controller-report.json').write_text(json.dumps(report,indent=2)+'\n')
        volume.commit()
        return report

    return app, worker, controller
