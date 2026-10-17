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
from formation.study_d_modal_v0249 import (ARMS, STARTUP_TIMEOUT, WORKER_TIMEOUT,
    acquisition_gate, budget_admit, select_base, verify_assets)

VOLUME_NAME = 'taa-study-d-v0249-evidence'
LEDGER_NAME = 'taa-study-d-v0249-budget-once'


def define(stage):
    if sys.version_info[:2] not in ((3,11),(3,12)):
        raise ValueError('use Python 3.11 or 3.12 on the Mac; remote image must match serialized code')
    python_version = f'{sys.version_info.major}.{sys.version_info.minor}'
    app = modal.App('taa-study-d-'+stage+'-v0249')
    volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
    ledger = modal.Dict.from_name(LEDGER_NAME, create_if_missing=True)
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
                  volumes={'/results':volume}, timeout=WORKER_TIMEOUT,
                  startup_timeout=STARTUP_TIMEOUT, scaledown_window=2,
                  max_containers=3 if stage=='study' else 1, retries=0, serialized=True, include_source=False)
    def worker(payload):
        import importlib.util
        if not payload.get('approval_receipt') or payload['budget']['total_reserved_usd'] > 25:
            raise RuntimeError('missing approval or budget reservation')
        spec = importlib.util.spec_from_file_location('d_runtime', '/opt/study-d/runtime.py')
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        if stage=='base':
            return runtime.gate_worker(volume, ledger)
        return runtime.arm_worker(payload['arm'], payload['model'], payload['revision'], volume, ledger)

    @app.function(image=cpu_image, cpu=.25, memory=256, volumes={'/results':volume},
                  timeout=7500, max_containers=1, scaledown_window=2, retries=0, serialized=True, include_source=False)
    def controller(payload):
        import importlib.util
        spec = importlib.util.spec_from_file_location('review_helpers', '/opt/study-d/helpers.py')
        h = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(h)
        h.check_launch_window()
        budget = h.budget_admit(stage, payload['prior_usd'], payload['hourly_ceiling'],
                               payload['account_cap'], payload['approved'])
        immutable = dict(asset_sha=payload['asset_sha'], prior_usd=payload['prior_usd'],
                         hourly_ceiling=payload['hourly_ceiling'], account_cap=payload['account_cap'])
        ledger.put('study-manifest', immutable, skip_if_exists=True)
        if ledger['study-manifest'] != immutable:
            raise RuntimeError('cumulative study ledger/config mismatch; no reset permitted')
        if not ledger.put('stage-once/'+stage, dict(budget=budget, approval=payload['approval_receipt']), skip_if_exists=True):
            raise RuntimeError('stage already attempted; no restart or second reservation')
        def save(name, value):
            path=Path('/results')/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value,indent=2)+'\n')
            volume.commit()
        volume.reload()
        if (Path('/results')/(stage+'-reservation.json')).exists():
            raise RuntimeError('durable evidence records prior stage attempt; no restart')
        save(stage+'-reservation.json', dict(budget=budget, approval_receipt=payload['approval_receipt']))
        payload['budget'] = budget
        if stage=='base':
            return worker.remote(payload)
        volume.reload()
        report=json.loads(Path('/results/base/report.json').read_text())
        if not payload['base_audit_receipt']:
            raise RuntimeError('separate owner acceptance of base audit required')
        report['audit_accepted_by_owner'] = True
        revision=h.select_base(report,payload['model'])
        save('study-admission.json', dict(model=payload['model'], revision=revision,
             base_audit_receipt=payload['base_audit_receipt'], training_approval=payload['approval_receipt'],
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
                save('STUDY_STOP_FOR_REVIEW.json',dict(no_restart=True,decisions=decisions))
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
                v['comparison_status']='UNINTERPRETABLE OR PENDING CODING; no transfer/null claim'
        ledger.put('decisions',decisions,skip_if_exists=True)
        save('acquisition-decisions.json',decisions)
        results=[]
        for call in calls:
            try:results.append(call.get())
            except Exception:results.append(dict(status='STOP_FOR_REVIEW; inspect arm evidence'))
        save('study-controller-report.json',dict(arms=results,decisions=decisions,
             analysis_status='raw evidence requires audit; no automatic scientific verdict',
             actual_invoice_usd=None,no_training_restart=True))
        return results

    def main(approved: bool=False, approval_receipt: str='', prior_usd: float=-1,
             hourly_ceiling: float=-1, account_cap: float=-1, model: str='', base_audit_receipt: str=''):
        verify_assets(ASSETS)
        code_hashes=json.loads((ASSETS/'integrity.json').read_text())['remote_code_sha256']
        if any(hashlib.sha256(path.read_bytes()).hexdigest()!=code_hashes[name]
               for name,path in [('helpers.py',HELPERS),('runtime.py',RUNTIME)]):
            raise ValueError('reviewed implementation hash differs')
        from formation.study_d_modal_v0249 import check_launch_window
        check_launch_window()
        budget_admit(stage,prior_usd,hourly_ceiling,account_cap,approved)
        if not approval_receipt.strip():
            raise ValueError('separate explicit approval receipt required')
        if stage=='study' and (not base_audit_receipt.strip() or model not in (
                'meta-llama/Llama-3.1-8B-Instruct','Qwen/Qwen2.5-7B-Instruct')):
            raise ValueError('owner-selected passing base and accepted audit receipt required')
        payload=dict(approved=approved,approval_receipt=approval_receipt,prior_usd=prior_usd,
                     hourly_ceiling=hourly_ceiling,account_cap=account_cap,model=model,
                     base_audit_receipt=base_audit_receipt,
                     asset_sha=hashlib.sha256((ASSETS/'integrity.json').read_bytes()).hexdigest())
        print(controller.remote(payload))
    return app, main
