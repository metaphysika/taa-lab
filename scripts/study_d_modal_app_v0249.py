"""Shared Modal declarations. No .remote/.spawn calls at module import."""
import hashlib
import json
from pathlib import Path
import sys
import time

import modal

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'studies/formation-study-d-modal-v0249'
HELPERS = ROOT/'formation/study_d_modal_v0249.py'
RUNTIME = ROOT/'scripts/study_d_modal_runtime_v0249.py'
sys.path.insert(0, str(ROOT))
from formation.study_d_modal_v0249 import (ARMS, STARTUP_TIMEOUT, WORKER_TIMEOUT, BASE_WORKER_TIMEOUT,
    acquisition_gate, budget_admit, select_base, verify_assets)

VOLUME_NAME = 'taa-study-d-v0249-evidence'
LEDGER_NAME = 'taa-study-d-v0249-budget-once'
PRIVATE_VOLUME_NAME = 'taa-study-d-v0249-private-adapters'


def define(stage):
    if sys.version_info[:2] not in ((3,11),(3,12)):
        raise ValueError('use Python 3.11 or 3.12 on the Mac; remote image must match serialized code')
    python_version = f'{sys.version_info.major}.{sys.version_info.minor}'
    app = modal.App('taa-study-d-'+stage+'-v0249')
    volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
    private_volume = modal.Volume.from_name(PRIVATE_VOLUME_NAME, create_if_missing=True) if stage=='study' else None
    mounts = {'/results':volume}
    if private_volume is not None:
        mounts['/adapters'] = private_volume
    image = (modal.Image.debian_slim(python_version=python_version)
             .pip_install('torch==2.6.0', 'transformers==4.51.3', 'accelerate==1.6.0',
                          'huggingface_hub==0.30.2', 'safetensors==0.5.3', 'peft==0.15.2')
             .add_local_dir(str(ASSETS), '/opt/study-d/assets', copy=True)
             .add_local_file(str(HELPERS), '/opt/study-d/helpers.py', copy=True)
             .add_local_file(str(RUNTIME), '/opt/study-d/runtime.py', copy=True))
    cpu_image = (modal.Image.debian_slim(python_version=python_version)
                 .add_local_file(str(HELPERS), '/opt/study-d/helpers.py', copy=True))

    @app.function(image=image, gpu='A100-40GB', cpu=2, memory=32768,
                  secrets=[modal.Secret.from_name('huggingface', required_keys=['HF_TOKEN'])],
                  volumes=mounts, timeout=BASE_WORKER_TIMEOUT if stage=='base' else WORKER_TIMEOUT,
                  startup_timeout=STARTUP_TIMEOUT, scaledown_window=2,
                  max_containers=3 if stage=='study' else 2, retries=0, single_use_containers=True,
                  serialized=True, include_source=False)
    def worker(payload):
        import importlib.util
        import modal
        # Resolve handles in the remote process, never in a serialized closure.
        volume = modal.Volume.from_name('taa-study-d-v0249-evidence')
        ledger = modal.Dict.from_name('taa-study-d-v0249-budget-once', create_if_missing=True)
        private_volume = modal.Volume.from_name('taa-study-d-v0249-private-adapters') if stage=='study' else None
        if not payload.get('approval_receipt') or payload['budget']['total_reserved_usd'] > 25:
            raise RuntimeError('missing approval or budget reservation')
        spec = importlib.util.spec_from_file_location('d_runtime', '/opt/study-d/runtime.py')
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        if stage=='base':
            return runtime.gate_worker(payload['model'], volume, ledger)
        return runtime.arm_worker(payload['arm'], payload['model'], payload['revision'], volume, ledger, private_volume)

    @app.function(image=cpu_image, cpu=.25, memory=256, volumes=mounts,
                  timeout=7500, max_containers=1, scaledown_window=2, retries=0, serialized=True, include_source=False)
    def controller(payload):
        import importlib.util
        import modal
        # Resolve handles in the remote process, never in a serialized closure.
        volume = modal.Volume.from_name('taa-study-d-v0249-evidence')
        ledger = modal.Dict.from_name('taa-study-d-v0249-budget-once', create_if_missing=True)
        private_volume = modal.Volume.from_name('taa-study-d-v0249-private-adapters') if stage=='study' else None
        spec = importlib.util.spec_from_file_location('review_helpers', '/opt/study-d/helpers.py')
        h = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(h)
        h.check_launch_window()
        worker = modal.Function.from_id(payload['worker_function_id'])
        if stage=='base':
            if not payload.get('prelaunch_audit_receipt', '').strip():
                raise RuntimeError('failed-launch state and billing audit receipt required')
            if any(ledger.contains(key) for key in (
                    'study-manifest', 'stage-once/base', 'stage-once/study',
                    'base-worker-once/meta-llama/Llama-3.1-8B-Instruct',
                    'base-worker-once/Qwen/Qwen2.5-7B-Instruct')):
                raise RuntimeError('existing launch claim; review required, never reset the ledger')
        budget = h.budget_admit(stage, payload['prior_usd'], payload['hourly_ceiling'],
                               payload['credit_cap'], payload['approved'])
        immutable = dict(asset_sha=payload['asset_sha'], prior_usd=payload['prior_usd'],
                         hourly_ceiling=payload['hourly_ceiling'], credit_cap=payload['credit_cap'])
        ledger.put('study-manifest', immutable, skip_if_exists=True)
        if ledger['study-manifest'] != immutable:
            raise RuntimeError('cumulative study ledger/config mismatch; no reset permitted')
        if not ledger.put('stage-once/'+stage, dict(budget=budget, approval=payload['approval_receipt'], prelaunch_audit_receipt=payload.get('prelaunch_audit_receipt')), skip_if_exists=True):
            raise RuntimeError('stage already attempted; no restart or second reservation')
        def save(name, value):
            path=Path('/results')/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value,indent=2)+'\n')
            volume.commit()
        volume.reload()
        if (Path('/results')/(stage+'-reservation.json')).exists():
            raise RuntimeError('durable evidence records prior stage attempt; no restart')
        save(stage+'-reservation.json', dict(budget=budget, approval_receipt=payload['approval_receipt'],
             prelaunch_audit_receipt=payload.get('prelaunch_audit_receipt'),worker_function_id=payload['worker_function_id']))
        payload['budget'] = budget
        if stage=='base':
            # Two independent one-hour reservations; both claimed before spawn.
            calls=[worker.spawn(dict(payload,model=model,base_slot_usd=h.BASE_SLOT_USD)) for model in h.MODELS]
            combined=dict(status='COMPLETE',models={},revisions={},throughput_and_training_projection={},
                          audit_accepted_by_owner=False,training_authorized=False,
                          parallel_A100_containers=2,total_reservation_usd=h.RESERVATIONS['base'])
            for model,call in zip(h.MODELS,calls):
                try:
                    result=call.get()
                    combined['models'][model]=result['summary']
                    combined['revisions'][model]=result['revision']
                    combined['throughput_and_training_projection'][model]=result['throughput_and_training_projection']
                except Exception:
                    combined['status']='STOP_FOR_REVIEW'
                    combined['models'][model]={'format_gate':'INCOMPLETE','no_restart':True}
            volume.reload()
            save('base/report.json',combined)
            return combined
        volume.reload()
        report=json.loads(Path('/results/base/report.json').read_text())
        if not payload['base_audit_receipt'] or not payload['projection_review_receipt']:
            raise RuntimeError('owner acceptance of base audit AND measured runtime projection required')
        report['audit_accepted_by_owner'] = True
        revision=h.select_base(report,payload['model'])
        projection=report['throughput_and_training_projection'][payload['model']]
        if projection.get('status')=='UNAVAILABLE' or not all(v['nominal_fits'] for v in projection['arms'].values()):
            raise RuntimeError('nominal per-arm runtime exceeds guard; revise plan before training')
        save('study-admission.json', dict(model=payload['model'], revision=revision,
             base_audit_receipt=payload['base_audit_receipt'], projection_review_receipt=payload['projection_review_receipt'],
             training_approval=payload['approval_receipt'],
             base_report_sha256=hashlib.sha256(Path('/results/base/report.json').read_bytes()).hexdigest()))
        # Reserve all three jobs BEFORE any parallel spawn, with no refund/reset.
        calls=[worker.spawn(dict(payload,arm=arm,revision=revision)) for arm in h.ARMS]
        deadline=time.monotonic()+6000
        while not all(ledger.contains('acquisition/'+arm) for arm in h.ARMS):
            if any(ledger.contains('arm-stop/'+arm) for arm in h.ARMS) or time.monotonic()>deadline:
                decisions={arm:dict(status='BLOCKED: peer guard/timeout',transfer_allowed=False) for arm in h.ARMS}
                ledger.put('decisions',decisions,skip_if_exists=True)
                for call in calls:
                    try:call.get()
                    except Exception:pass
                save('STUDY_STOP_FOR_REVIEW.json',dict(no_restart=True,decisions=decisions,private_adapter_volume=PRIVATE_VOLUME_NAME,
                    adapters_retained_until_owner_decision=True))
                return decisions
            time.sleep(5)
        acquisitions={arm:ledger['acquisition/'+arm] for arm in h.ARMS}
        neutral=acquisitions['neutral']['ordered']
        decisions={arm:h.acquisition_gate(arm,acquisitions[arm]['own'],
                   acquisitions[arm]['ordered'],neutral) for arm in h.ARMS}
        # A peer failure prevents the planned three-arm contrast; don't spend on partial transfer.
        if not all(v['transfer_allowed'] for v in decisions.values()):
            for v in decisions.values():
                v['transfer_allowed']=False
                v['comparison_status']='UNINTERPRETABLE; failed numeric/message acquisition gate; no null claim'
        ledger.put('decisions',decisions,skip_if_exists=True)
        save('acquisition-decisions.json',decisions)
        results=[]
        for call in calls:
            try:results.append(call.get())
            except Exception:results.append(dict(status='STOP_FOR_REVIEW; inspect arm evidence'))
        full_success=h.study_finished_cleanly(results,decisions)
        if full_success:
            private_volume.reload()
            h.delete_adapters('/adapters/study','/results',
                'STUDY END: '+payload['approval_receipt'], private_volume.commit, volume.commit)
        else:
            save('ADAPTERS_RETAINED_FOR_REVIEW.json',dict(private_volume=PRIVATE_VOLUME_NAME,
                decision_required=True,no_deployment_or_sharing=True,
                instruction='retain until owner review decision; CPU-only end/delete script writes receipts'))
        save('study-controller-report.json',dict(arms=results,decisions=decisions,
             analysis_status='raw evidence requires audit; no automatic scientific verdict',
             actual_invoice_usd=None,no_training_restart=True))
        return results

    def main(approved: bool=False, approval_receipt: str='', prior_usd: float=-1,
             hourly_ceiling: float=-1, credit_cap: float=-1, model: str='', base_audit_receipt: str='', projection_review_receipt: str='', prelaunch_audit_receipt: str=''):
        verify_assets(ASSETS)
        code_hashes=json.loads((ASSETS/'integrity.json').read_text())['remote_code_sha256']
        if any(hashlib.sha256(path.read_bytes()).hexdigest()!=code_hashes[name]
               for name,path in [('helpers.py',HELPERS),('runtime.py',RUNTIME)]):
            raise ValueError('reviewed implementation hash differs')
        from formation.study_d_modal_v0249 import check_launch_window
        check_launch_window()
        budget_admit(stage,prior_usd,hourly_ceiling,credit_cap,approved)
        if not approval_receipt.strip():
            raise ValueError('separate explicit approval receipt required')
        if stage=='base' and not prelaunch_audit_receipt.strip():
            raise ValueError('failed-launch state and billing audit receipt required')
        if stage=='study' and (not base_audit_receipt.strip() or not projection_review_receipt.strip() or model not in (
                'meta-llama/Llama-3.1-8B-Instruct','Qwen/Qwen2.5-7B-Instruct')):
            raise ValueError('owner-selected passing base and accepted audit receipt required')
        payload=dict(worker_function_id=worker.object_id,prelaunch_audit_receipt=prelaunch_audit_receipt,approved=approved,approval_receipt=approval_receipt,prior_usd=prior_usd,
                     hourly_ceiling=hourly_ceiling,credit_cap=credit_cap,model=model,
                     base_audit_receipt=base_audit_receipt,projection_review_receipt=projection_review_receipt,
                     asset_sha=hashlib.sha256((ASSETS/'integrity.json').read_bytes()).hexdigest())
        print(controller.remote(payload))
    return app, main
