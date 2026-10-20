"""Offline declarations. Named remote resources are resolved inside remote bodies."""
from pathlib import Path
import sys
import modal
ROOT=Path(__file__).resolve().parents[1]


def define(stage):
    if sys.version_info[:2]!=(3,12):raise ValueError('Python 3.12 required')
    sys.path.insert(0,str(ROOT))
    from formation import study_d_gemma_stages_v02429 as h
    if stage not in h.STAGES:raise ValueError('unplanned stage')
    assets=ROOT/'studies/formation-study-d-gemma-stages-v02429'
    app=modal.App('taa-study-d-gemma-'+stage+'-v02429')
    evidence=modal.Volume.from_name(h.VOLUME,create_if_missing=True)
    private=modal.Volume.from_name(h.SOURCE_PRIVATE).read_only()
    copies={'assets_check.py':'scripts/study_d_gemma_assets_v02429.py',
        'legacy_policy.py':'formation/study_d_gemma_stages_v02420.py',
        'sampler_guard.py':'scripts/study_d_gemma_sampler_v02422.py',
        'stages_policy.py':'formation/study_d_gemma_stages_v02429.py',
        'runtime.py':'scripts/study_d_gemma_stages_runtime_v02429.py',
        'base_runtime.py':'scripts/study_d_gemma_runtime_v02416.py',
        'base_policy.py':'formation/study_d_gemma_base_v02416.py',
        'acquisition.py':'formation/study_d_modal_v0249.py',
        'study_d_safe_logging_v02416.py':'scripts/study_d_safe_logging_v02416.py',
        'provenance.py':'scripts/study_d_gemma_provenance_v02429.py',
        'admission.py':'scripts/study_d_gemma_admission_v02429.py'}
    prior_cpu=modal.Volume.from_name('taa-study-d-gemma-v02420-evidence').read_only()
    prior_speed=modal.Volume.from_name('taa-study-d-gemma-v02422-speed-evidence').read_only()
    prior_virtue=modal.Volume.from_name(h.SOURCE_PUBLIC).read_only()
    prior_completion=modal.Volume.from_name('taa-study-d-gemma-v02426-evidence').read_only()
    image=(modal.Image.debian_slim(python_version='3.12')
        .pip_install('vllm==0.31.0','transformers==5.10.4','huggingface_hub==1.31.0',
                     'nvidia-ml-py==13.580.82','peft==0.21.2','accelerate==1.15.0')
        .env({'HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','VLLM_USE_FLASHINFER_SAMPLER':'0','OMP_NUM_THREADS':'2','PYTHONPATH':'/opt/study-d'})
        .add_local_dir(str(assets),'/opt/study-d/assets',copy=True))
    for dest,source in copies.items():image=image.add_local_file(str(ROOT/source),'/opt/study-d/'+dest,copy=True)
    cpu_image=modal.Image.debian_slim(python_version='3.12')
    cpu_image=cpu_image.add_local_dir(str(assets),'/opt/study-d/assets',copy=True)
    for dest in ('stages_policy.py','legacy_policy.py','base_policy.py','acquisition.py','assets_check.py','provenance.py','admission.py'):
        cpu_image=cpu_image.add_local_file(str(ROOT/copies[dest]),'/opt/study-d/'+dest,copy=True)
    @app.function(image=image,gpu=None if stage=='cpu' else 'A100-80GB',cpu=(2,2),
        memory=(65536,65536),
        secrets=[modal.Secret.from_name('huggingface',required_keys=['HF_TOKEN'])],
        volumes={'/results':evidence,'/adapters':private},timeout=h.STAGES[stage]['timeout'],
        startup_timeout=120,scaledown_window=2,max_containers=1,
        single_use_containers=True,retries=0,serialized=True,include_source=False)
    def worker(payload):
        import importlib.util
        import modal
        spec=importlib.util.spec_from_file_location('stages_runtime','/opt/study-d/runtime.py')
        r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02429-evidence')
        private=modal.Volume.from_name('taa-study-d-gemma-v02428-private-adapters').read_only()
        ledger=modal.Dict.from_name('taa-study-d-gemma-v02429-budget-once')
        return r.arm_worker(evidence,private,ledger,payload)

    @app.function(image=cpu_image,cpu=(h.CONTROLLER_CPU,h.CONTROLLER_CPU),memory=(h.CONTROLLER_MEMORY_MB,h.CONTROLLER_MEMORY_MB),
        volumes={'/results':evidence,'/adapters':private,'/prior-cpu':prior_cpu,'/prior-speed':prior_speed,'/prior-virtue':prior_virtue,'/prior-completion':prior_completion},timeout=600,startup_timeout=60,
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
        h=module('stages_policy','stages_policy.py');errors=module('base_policy','base_policy.py')
        a=module('acquisition','acquisition.py')
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02429-evidence')
        ledger=modal.Dict.from_name('taa-study-d-gemma-v02429-budget-once',create_if_missing=True)
        stage=payload['stage'];root=Path('/results');folder=root/stage;report=None
        def save(name,value):
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(value,indent=2)+'\n');evidence.commit()
        try:
            evidence.reload()
            admission=module('cpu_admission','admission.py')
            source_ledger=modal.Dict.from_name('taa-study-d-gemma-v02426-budget-once')
            budget=admission.admit(h,root,Path('/prior-completion'),Path('/opt/study-d/assets'),
                payload,ledger,source_ledger.get('pair/closed'),evidence.commit,Path('/prior-virtue'))
            if not ledger.put(stage+'/once',dict(payload=payload,budget=budget),skip_if_exists=True):
                raise ValueError('stage already claimed')
            save('reservation.json',dict(payload=payload,budget=budget))
            worker=modal.Function.from_id(payload['worker_function_id'])
            # Submit once, persist acknowledgement, return. Never wait for acquisition/results.
            call=worker.spawn(dict(payload,arm='virtue',budget=budget))
            report=dict(status='SUBMITTED',stage=stage,commit=payload['commit'],
                worker_call_id=call.object_id,budget=budget,worker_owns_acquisition_and_closure=True,
                next_stage_approved=False)
            save('worker-submission.json',report)
        except BaseException as exc:
            report=errors.failure_record(exc,'stage_controller');report.update(stage=stage,commit=payload['commit'],failure_classification=h.failure_classification(exc),no_restart=True)
            ledger.put('STOP_FOR_REVIEW',dict(stage=stage,classification=h.failure_classification(exc)),skip_if_exists=True)
            save('controller-failure-'+str(time.time_ns())+'.json',report)
            # Do not cancel/restart ambiguous workers; shared review stop blocks later requests.
        return report
    return app,worker,controller
