"""Separate seed 2 L2 launcher. Preview is offline; execution needs an owner receipt."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
import zipfile
import time
from . import seed2_v02482 as s, modal_backend as m, seed2_l2_v02482 as l2
from .guard import LaunchGuard, inventory_hash, verify_execution_commit, weight_verification
from exploratory.audit_tool.modal_adapter import ROOT, verify_checkpoint
from exploratory.audit_tool.step4 import WEIGHTS_VOLUME, launch_guard
from exploratory.audit_tool import audit

Journal=m.Journal


def checkpoints(report):
    entries=report['adapter_plan']['checkpoints']
    if sorted(r['arm'] for r in entries)!=['contrary','neutral']:
        raise ValueError('exact contrary/neutral adapter pair required')
    return {r['arm']:dict(model=s.training.MODEL,revision=s.training.REVISION,
                         available=True,adapter=r) for r in entries}


def expected(commit,report,report_bytes):
    return dict(s.binding(),commit=commit,block='l2',inventory_sha256=inventory_hash(checkpoints(report)),
                training_report_sha256=hashlib.sha256(report_bytes).hexdigest(),
                backend_settings=m.settings(s.EVALUATION_CAP,'l2'))


def validate(receipt,report,report_bytes,commit,now=None):
    if receipt.get('approved_by')!='Chris Lahn' or not isinstance(receipt.get('approval_id'),str) or not receipt['approval_id'].strip():
        raise ValueError('explicit owner exact-commit approval required')
    if any(receipt.get(k)!=v for k,v in expected(commit,report,report_bytes).items()):
        raise ValueError('seed 2 receipt binding mismatch')
    return s.require_training(receipt,report,now)


def execute(receipt,source_commit,run_id,journal,clock=time.monotonic):
    started=clock();raw=Path('/opt/training-report.json').read_bytes();report=json.loads(raw)
    pinned=validate(receipt,report,raw,source_commit)
    if weight_verification('/weights') is not None:raise ValueError('pinned weights unavailable')
    cps=checkpoints(report)
    paths={arm:verify_checkpoint('/adapters',arm,pinned) for arm in cps}
    guard=LaunchGuard(receipt,expected(source_commit,report,raw),cps,
        lambda rows:journal(dict(event='attempt_ledger',attempts=rows)),owner_approved=True)
    config=m.settings(s.EVALUATION_CAP,'l2')
    guard.before_cell=lambda:m.may_start(clock()-started,config)
    runtime=audit.module(ROOT/'scripts/study_d_gemma_runtime_v02416.py','seed2_serving_template')
    from vllm import LLM
    from vllm.lora.request import LoRARequest
    backend=m.Backend(LLM(**s.training.ENGINE),runtime,paths,journal,LoRARequest)
    def verify(commit):
        if commit!=source_commit:raise ValueError('source archive commit mismatch')
    try:
        return l2.run(cps,guard,backend,lambda row:journal(dict(event='cell',row=row)),1,verify)
    finally:
        journal(dict(event='stage_end',run_id=run_id,reserved=guard.reserved,elapsed=clock()-started))


def submit(app,worker,ledger,receipt,run_id,output):
    fingerprint=hashlib.sha256(json.dumps(receipt,sort_keys=True,allow_nan=False).encode()).hexdigest()
    with app.run(detach=True):
        # One evaluation for this version, even if a different approval id is supplied.
        if not ledger.put('evaluation/once',dict(run_id=run_id,fingerprint=fingerprint,reserved=s.EVALUATION_CAP),skip_if_exists=True):
            raise ValueError('seed 2 evaluation already attempted; no resume or rerun')
        call=worker.spawn(receipt,run_id)
        with Path(output).open('x',encoding='utf-8') as f:
            json.dump(dict(run_id=run_id,app_id=app.app_id,function_call_id=call.object_id),f)


def launch(receipt,archive,output,training_report):
    import modal
    image=(modal.Image.debian_slim(python_version='3.12')
        .pip_install('vllm==0.31.0','transformers==5.10.4','huggingface_hub==1.31.0',
                     'nvidia-ml-py==13.580.82','peft==0.21.2','accelerate==1.15.0')
        .env({'HF_HUB_DISABLE_TELEMETRY':'1','VLLM_NO_USAGE_STATS':'1',
              'VLLM_USE_FLASHINFER_SAMPLER':'0','OMP_NUM_THREADS':'2',
              'HF_HOME':'/weights','HF_HUB_OFFLINE':'1'})
        .add_local_file(str(archive),'/opt/source.zip',copy=True)
        .add_local_file(str(training_report),'/opt/training-report.json',copy=True))
    app=modal.App('taa-seed2-v02482-evaluation')
    evidence=modal.Volume.from_name(s.EVIDENCE,create_if_missing=True)
    private=modal.Volume.from_name(s.training.PRIVATE).read_only()
    weights=modal.Volume.from_name(WEIGHTS_VOLUME).read_only()
    config=m.settings(s.EVALUATION_CAP,'l2')
    @app.function(image=image,gpu='A100-80GB',cpu=(2,2),memory=(65536,65536),
        timeout=config['timeout'],startup_timeout=m.STARTUP_SECONDS,scaledown_window=m.IDLE,
        retries=0,max_containers=1,single_use_containers=True,
        volumes={'/weights':weights,'/adapters':private,'/results':evidence},serialized=True)
    def worker(payload,run_id):
        import sys
        if hashlib.sha256(Path('/opt/source.zip').read_bytes()).hexdigest()!=payload['archive_sha256']:
            raise ValueError('source archive mismatch')
        with zipfile.ZipFile('/opt/source.zip') as source:source.extractall('/opt/repo')
        sys.path.insert(0,'/opt/repo')
        from exploratory.step4_harness.seed2_backend_v02482 import Journal,execute
        journal=Journal(Path('/results')/run_id,evidence.commit)
        journal(dict(event='launch',receipt=payload,run_id=run_id))
        try:execute(payload,payload['commit'],run_id,journal)
        except BaseException as exc:
            journal(dict(event='failure',error=type(exc).__name__));raise
        finally:evidence.commit()
    ledger=modal.Dict.from_name(s.LEDGER,create_if_missing=True)
    submit(app,worker,ledger,receipt,uuid.uuid4().hex,output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-report',type=Path)
    parser.add_argument('--receipt',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--confirm-owner-approval',action='store_true')
    args=parser.parse_args()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if not args.training_report:
        print(json.dumps(dict(approved=False,binding=s.binding(),cost=s.costs()),indent=2));return
    raw=args.training_report.read_bytes();report=json.loads(raw)
    print(json.dumps(expected(commit,report,raw),indent=2))
    if not args.receipt:return
    if not args.confirm_owner_approval or not args.output or args.output.exists():
        parser.error('explicit operator trust and fresh output required')
    receipt=json.loads(args.receipt.read_bytes())
    validate(receipt,report,raw,commit)
    verify_execution_commit(commit);launch_guard(True,os.environ)
    with tempfile.TemporaryDirectory() as temporary:
        archive=Path(temporary)/'source.zip'
        subprocess.run(['git','archive','--format=zip','-o',str(archive),commit],cwd=ROOT,check=True)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=receipt.get('archive_sha256'):
            raise ValueError('approved archive SHA256 required')
        launch(receipt,archive,args.output,args.training_report)


if __name__=='__main__':main()
