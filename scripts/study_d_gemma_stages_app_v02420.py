"""Offline declarations. Named remote resources are resolved inside remote bodies."""
from pathlib import Path
import sys
import modal
ROOT=Path(__file__).resolve().parents[1]


def define(stage):
    if sys.version_info[:2]!=(3,12):raise ValueError('Python 3.12 required')
    sys.path.insert(0,str(ROOT))
    from formation import study_d_gemma_stages_v02420 as h
    if stage not in h.STAGES:raise ValueError('unplanned stage')
    assets=ROOT/'studies/formation-study-d-gemma-stages-v02420'
    app=modal.App('taa-study-d-gemma-'+stage+'-v02420')
    evidence=modal.Volume.from_name(h.VOLUME,create_if_missing=True)
    private=modal.Volume.from_name(h.PRIVATE,create_if_missing=True)
    copies={'stages_policy.py':'formation/study_d_gemma_stages_v02420.py',
        'runtime.py':'scripts/study_d_gemma_stages_runtime_v02420.py',
        'base_runtime.py':'scripts/study_d_gemma_runtime_v02416.py',
        'base_policy.py':'formation/study_d_gemma_base_v02416.py',
        'acquisition.py':'formation/study_d_modal_v0249.py',
        'study_d_safe_logging_v02416.py':'scripts/study_d_safe_logging_v02416.py'}
    image=(modal.Image.debian_slim(python_version='3.12')
        .pip_install('vllm==0.31.0','transformers==5.10.4','huggingface_hub==1.31.0',
                     'nvidia-ml-py==13.580.82','peft==0.21.2','accelerate==1.15.0')
        .env({'HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','OMP_NUM_THREADS':'2','PYTHONPATH':'/opt/study-d'})
        .add_local_dir(str(assets),'/opt/study-d/assets',copy=True))
    for dest,source in copies.items():image=image.add_local_file(str(ROOT/source),'/opt/study-d/'+dest,copy=True)
    cpu_image=modal.Image.debian_slim(python_version='3.12')
    for dest in ('stages_policy.py','base_policy.py','acquisition.py'):
        cpu_image=cpu_image.add_local_file(str(ROOT/copies[dest]),'/opt/study-d/'+dest,copy=True)
    @app.function(image=image,gpu=None if stage=='cpu' else 'A100-80GB',cpu=(2,2),
        memory=(16384,16384) if stage=='cpu' else (65536,65536),
        secrets=[modal.Secret.from_name('huggingface',required_keys=['HF_TOKEN'])],
        volumes={'/results':evidence,'/adapters':private},timeout=h.STAGES[stage]['timeout'],
        startup_timeout=120,scaledown_window=2,max_containers=2 if stage=='pair' else 1,
        single_use_containers=True,retries=0,serialized=True,include_source=False)
    def worker(payload):
        import importlib.util
        import modal
        spec=importlib.util.spec_from_file_location('stages_runtime','/opt/study-d/runtime.py')
        r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02420-evidence')
        private=modal.Volume.from_name('taa-study-d-gemma-v02420-private-adapters')
        ledger=modal.Dict.from_name('taa-study-d-gemma-v02420-budget-once')
        if payload['stage']=='cpu':return r.cpu_dataset_worker(evidence,ledger,payload)
        return r.arm_worker(evidence,private,ledger,payload)

    @app.function(image=cpu_image,cpu=(.25,.25),memory=(256,256),
        volumes={'/results':evidence,'/adapters':private},timeout=6650,startup_timeout=60,
        scaledown_window=2,max_containers=1,single_use_containers=True,retries=0,serialized=True,include_source=False)
    def controller(payload):
        import importlib.util
        import json
        import time
        import modal
        from pathlib import Path
        def module(name,file):
            spec=importlib.util.spec_from_file_location(name,'/opt/study-d/'+file)
            m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
        h=module('stages_policy','stages_policy.py');errors=module('base_policy','base_policy.py')
        a=module('acquisition','acquisition.py')
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02420-evidence')
        private=modal.Volume.from_name('taa-study-d-gemma-v02420-private-adapters')
        ledger=modal.Dict.from_name('taa-study-d-gemma-v02420-budget-once',create_if_missing=True)
        stage=payload['stage'];root=Path('/results');folder=root/stage;report=None
        def save(name,value):
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(value,indent=2)+'\n');evidence.commit()
        try:
            budget=h.validate(payload);evidence.reload()
            if stage!='cpu':h.require_cpu(root,payload,ledger if stage=='smoke' else None)
            h.require_previous(root,payload)
            if ledger.contains('STOP_FOR_REVIEW'):raise ValueError('review stop exists; no further stage')
            if (folder/'reservation.json').exists() or ledger.contains(stage+'/once'):
                raise ValueError('stage already attempted; never reset, delete, refund or relaunch')
            if not ledger.put(stage+'/once',dict(payload=payload,budget=budget),skip_if_exists=True):
                raise ValueError('stage already claimed')
            save('reservation.json',dict(payload=payload,budget=budget))
            worker=modal.Function.from_id(payload['worker_function_id'])
            # Both pair workers are submitted before any get: two concurrent GPU inputs.
            calls={arm:worker.spawn(dict(payload,arm=arm,budget=budget)) for arm in h.STAGES[stage]['arms']}
            if stage not in ('cpu','smoke'):
                required=h.STAGES[stage]['arms'];deadline=time.monotonic()+6000
                while not all(ledger.contains(stage+'/acquisition/'+arm) for arm in required):
                    if ledger.contains('STOP_FOR_REVIEW') or time.monotonic()>deadline:
                        raise RuntimeError('acquisition interrupted or deadline; no transfer')
                    time.sleep(2)
                values={arm:ledger[stage+'/acquisition/'+arm] for arm in required}
                if stage=='pair':neutral=values['neutral']
                else:
                    evidence.reload()
                    pair=json.loads((root/'pair/report.json').read_text())
                    neutral=dict(ordered=pair['arms']['neutral']['neutral_ordered'])
                decisions={arm:a.acquisition_gate(arm,values[arm]['own'],values[arm]['ordered'],neutral['ordered']) for arm in required}
                if stage=='pair' and not decisions['neutral']['transfer_allowed']:
                    decisions['contrary'].update(transfer_allowed=False,status='BLOCKED',interpretation='neutral acquisition failed')
                save('decisions.json',decisions)
                if not ledger.put(stage+'/decisions',decisions,skip_if_exists=True):raise RuntimeError('decisions already set')
            results={arm:call.get() for arm,call in calls.items()}
            evidence.reload()
            complete=all(r['status']==('PASS' if stage=='cpu' else 'COMPLETE') for r in results.values())
            report=(dict(results['tokenizer' if stage=='cpu' else 'smoke']) if stage in ('cpu','smoke') else dict(status='COMPLETE' if complete else 'STOP_FOR_REVIEW',
                arms=results,commit=payload['commit'],engine=h.ENGINE))
            report.update(budget=budget,actual_invoice_usd=None,
                cpu_receipt_sha256=h.sha(root/'cpu/receipt.json') if stage!='cpu' else None,
                owner_review_required=True,next_stage_approved=False,all_adapters_private=True)
            save('controller-report.json' if stage=='cpu' else 'report.json',report)
            # Pair adapters must survive until the separately approved virtue/review decision.
            if stage=='virtue' and complete:
                private.reload()
                a.delete_adapters(Path('/adapters/science'),folder/'deletion','clean complete three-arm study end',private.commit,evidence.commit)
            ledger.put(stage+'/closed',dict(status=report['status'],report_sha256=h.sha(folder/'report.json')),skip_if_exists=True)
        except BaseException as exc:
            report=errors.failure_record(exc,'stage_controller');report.update(stage=stage,commit=payload['commit'])
            ledger.put('STOP_FOR_REVIEW',dict(stage=stage),skip_if_exists=True)
            save('controller-failure-'+str(time.time_ns())+'.json',report)
            # Do not cancel/restart ambiguous workers; shared review stop blocks later requests.
        return report
    return app,worker,controller
