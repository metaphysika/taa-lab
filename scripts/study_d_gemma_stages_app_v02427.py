"""Offline declarations. Named remote resources are resolved inside remote bodies."""
from pathlib import Path
import sys
import modal
ROOT=Path(__file__).resolve().parents[1]


def define(stage):
    if sys.version_info[:2]!=(3,12):raise ValueError('Python 3.12 required')
    sys.path.insert(0,str(ROOT))
    from formation import study_d_gemma_stages_v02427 as h
    if stage not in h.STAGES:raise ValueError('unplanned stage')
    assets=ROOT/'studies/formation-study-d-gemma-stages-v02427'
    app=modal.App('taa-study-d-gemma-'+stage+'-v02427')
    evidence=modal.Volume.from_name(h.VOLUME,create_if_missing=True)
    private=(modal.Volume.from_name(h.SOURCE_PRIVATE).read_only() if stage=='neutral-completion'
             else modal.Volume.from_name(h.PRIVATE,create_if_missing=True))
    copies={'assets_check.py':'scripts/study_d_gemma_assets_v02427.py',
        'legacy_policy.py':'formation/study_d_gemma_stages_v02420.py',
        'sampler_guard.py':'scripts/study_d_gemma_sampler_v02422.py',
        'stages_policy.py':'formation/study_d_gemma_stages_v02427.py',
        'runtime.py':'scripts/study_d_gemma_stages_runtime_v02427.py',
        'base_runtime.py':'scripts/study_d_gemma_runtime_v02416.py',
        'base_policy.py':'formation/study_d_gemma_base_v02416.py',
        'acquisition.py':'formation/study_d_modal_v0249.py',
        'study_d_safe_logging_v02416.py':'scripts/study_d_safe_logging_v02416.py',
        'provenance.py':'scripts/study_d_gemma_provenance_v02427.py'}
    prior_cpu=modal.Volume.from_name('taa-study-d-gemma-v02420-evidence').read_only()
    prior_speed=modal.Volume.from_name('taa-study-d-gemma-v02422-speed-evidence').read_only()
    prior_pair=modal.Volume.from_name(h.SOURCE_PUBLIC).read_only()
    prior_completion=modal.Volume.from_name('taa-study-d-gemma-v02426-evidence').read_only()
    image=(modal.Image.debian_slim(python_version='3.12')
        .pip_install('vllm==0.31.0','transformers==5.10.4','huggingface_hub==1.31.0',
                     'nvidia-ml-py==13.580.82','peft==0.21.2','accelerate==1.15.0')
        .env({'HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1','VLLM_USE_FLASHINFER_SAMPLER':'0','OMP_NUM_THREADS':'2','PYTHONPATH':'/opt/study-d'})
        .add_local_dir(str(assets),'/opt/study-d/assets',copy=True))
    for dest,source in copies.items():image=image.add_local_file(str(ROOT/source),'/opt/study-d/'+dest,copy=True)
    cpu_image=modal.Image.debian_slim(python_version='3.12')
    cpu_image=cpu_image.add_local_dir(str(assets),'/opt/study-d/assets',copy=True)
    for dest in ('stages_policy.py','legacy_policy.py','base_policy.py','acquisition.py','assets_check.py','provenance.py'):
        cpu_image=cpu_image.add_local_file(str(ROOT/copies[dest]),'/opt/study-d/'+dest,copy=True)
    @app.function(image=image,gpu=None if stage=='cpu' else 'A100-80GB',cpu=(2,2),
        memory=(16384,16384) if stage=='cpu' else (65536,65536),
        secrets=[modal.Secret.from_name('huggingface',required_keys=['HF_TOKEN'])],
        volumes={'/results':evidence,'/adapters':private},timeout=h.STAGES[stage]['timeout'],
        startup_timeout=120,scaledown_window=2,max_containers=1,
        single_use_containers=True,retries=0,serialized=True,include_source=False)
    def worker(payload):
        import importlib.util
        import modal
        spec=importlib.util.spec_from_file_location('stages_runtime','/opt/study-d/runtime.py')
        r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02427-evidence')
        private=(modal.Volume.from_name('taa-study-d-gemma-v02424-private-adapters').read_only() if payload['stage']=='neutral-completion'
                 else modal.Volume.from_name('taa-study-d-gemma-v02427-private-adapters'))
        ledger=modal.Dict.from_name('taa-study-d-gemma-v02427-budget-once')
        if payload['stage']=='cpu':return r.cpu_dataset_worker(evidence,ledger,payload)
        return r.arm_worker(evidence,private,ledger,payload)

    @app.function(image=cpu_image,cpu=(.25,.25),memory=(256,256),
        volumes={'/results':evidence,'/adapters':private,'/prior-cpu':prior_cpu,'/prior-speed':prior_speed,'/prior-training-public':prior_pair,'/prior-completion':prior_completion},timeout=h.STAGES[stage]['timeout']+450,startup_timeout=60,
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
        evidence=modal.Volume.from_name('taa-study-d-gemma-v02427-evidence')
        private=(modal.Volume.from_name('taa-study-d-gemma-v02424-private-adapters').read_only() if payload['stage']=='neutral-completion'
                 else modal.Volume.from_name('taa-study-d-gemma-v02427-private-adapters'))
        ledger=modal.Dict.from_name('taa-study-d-gemma-v02427-budget-once',create_if_missing=True)
        stage=payload['stage'];root=Path('/results');folder=root/stage;report=None
        def save(name,value):
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps(value,indent=2)+'\n');evidence.commit()
        try:
            budget=h.validate(payload);evidence.reload()
            manifest=h.verify_assets(Path('/opt/study-d/assets'))
            if h.sha(Path('/opt/study-d/assets/integrity-v02427.json'))!=payload['asset_sha256']:raise ValueError('reviewed asset index differs')
            for name in ('stages_policy.py','legacy_policy.py','base_policy.py','acquisition.py','assets_check.py','provenance.py'):
                if h.sha(Path('/opt/study-d')/name)!=manifest['remote_code_sha256'][name]:raise ValueError('controller source differs: '+name)
            if folder.exists() or ledger.contains(stage+'/once'):
                raise ValueError('stage evidence/once marker already exists; review, never restart')
            # CPU-only admission: copy pinned completed source from a READ-ONLY mount.
            binding=h.completion_binding()
            source_ledger=modal.Dict.from_name('taa-study-d-gemma-v02426-budget-once')
            source_closure=source_ledger.get('pair/closed')
            if source_closure!=dict(status='COMPLETE',report_sha256=binding['source_composite_sha256']):
                raise ValueError('source composite durable closure absent or changed')
            for name,digest in binding['source_sha256'].items():
                source=Path('/prior-completion')/name
                if h.stream_sha(source)!=digest:raise ValueError('pinned v02426 source differs: '+name)
                dest=root/('source-composite-v02426.json' if name=='pair/report.json' else name)
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
            repair=module('provenance','provenance.py')
            original=json.loads((root/'source-composite-v02426.json').read_text())
            composite=repair.repair_composite(root,original,h.continuation_binding())
            save('../pair/report.json',composite)
            if h.sha(root/'pair/report.json')!=binding['repaired_composite_sha256']:
                raise ValueError('CPU repaired composite hash differs from review')
            ledger.put('pair/closed',dict(status='COMPLETE',report_sha256=h.sha(root/'pair/report.json')),skip_if_exists=True)
            if stage!='cpu':h.require_cpu(root,payload,modal.Dict.from_name('taa-study-d-gemma-v02420-budget-once') if stage=='neutral-completion' else None)
            h.require_previous(root,payload,ledger)
            if ledger.contains('STOP_FOR_REVIEW'):raise ValueError('review stop exists; no further stage')
            if stage=='neutral-completion':
                for arm in h.STAGES[stage]['arms']:
                    save('adapter-provenance/'+arm+'.json',h.verify_reused_adapter(root,arm,published=h.continuation_binding()['neutral_adapter_proof']))
                # Hashes are durable public evidence BEFORE reservation or GPU submission.
                evidence.commit()
            if (folder/'reservation.json').exists() or ledger.contains(stage+'/once'):
                raise ValueError('stage already attempted; never reset, delete, refund or relaunch')
            if not ledger.put(stage+'/once',dict(payload=payload,budget=budget),skip_if_exists=True):
                raise ValueError('stage already claimed')
            save('reservation.json',dict(payload=payload,budget=budget))
            worker=modal.Function.from_id(payload['worker_function_id'])
            # One worker for this separately approved stage; two engine sequences remain frozen.
            calls={arm:worker.spawn(dict(payload,arm=arm,budget=budget)) for arm in h.STAGES[stage]['arms']}
            if stage=='virtue':
                required=h.STAGES[stage]['arms'];deadline=time.monotonic()+h.STAGES[stage]['software']
                while not all(ledger.contains(stage+'/acquisition/'+arm) for arm in required):
                    if ledger.contains('STOP_FOR_REVIEW') or time.monotonic()>deadline:
                        raise RuntimeError('acquisition interrupted or deadline; no transfer')
                    time.sleep(2)
                neutral_ordered=None
                if stage=='virtue':
                    evidence.reload()
                    pair=json.loads((root/'pair/report.json').read_text())
                    neutral_ordered=pair['arms']['neutral']['neutral_ordered']
                decisions=h.acquisition_decisions(ledger,stage,a,neutral_ordered)
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
            if stage=='neutral-completion' and complete:
                contrary=json.loads((root/'prior-pair/pair/contrary/report.json').read_text())
                composite=dict(status='COMPLETE',commit=payload['commit'],engine=h.ENGINE,
                    arms=dict(contrary=contrary,neutral=results['neutral']),
                    budget=budget,completion_worker_seconds=results['neutral']['software_wall_seconds'],
                    source_v02425_report_sha256=h.sha(root/'prior-pair/pair/report.json'),
                    original_pair_status='STOP_FOR_REVIEW',owner_review_required=True,
                    disclosure='Composite scheduled closure includes two retained missing neutral episodes; no replacements. Per-event vs batched commits disclosed.')
                save('../pair/report.json',composite)
                ledger.put('pair/closed',dict(status='COMPLETE',report_sha256=h.sha(root/'pair/report.json')),skip_if_exists=True)
            save('controller-report.json' if stage=='cpu' else 'report.json',report)
            # Pair adapters must survive until the separately approved virtue/review decision.
            if stage=='virtue' and complete:
                report['source_pair_adapter_deletion']='Pending separate owner-reviewed cleanup of read-only v02424 private Volume; retention remains private'
                save('report.json',report)
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
