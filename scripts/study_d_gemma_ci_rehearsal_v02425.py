"""Free CI-only tiny-model rehearsal. No Modal, HF credential, pretrained weights or generation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO=Path(__file__).resolve().parents[1]
ASSETS=REPO/'studies/formation-study-d-gemma-stages-v02425'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def main():
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--output',type=Path,required=True);opt=args.parse_args()
    if sys.version_info[:2]!=(3,12):raise RuntimeError('pinned CI Python3.12 required')
    output=opt.output.resolve();output.mkdir(parents=True,exist_ok=False)
    evidence=output/'evidence';evidence.mkdir();bundle=output/'runtime';bundle.mkdir()
    copies={'assets_check.py':'scripts/study_d_gemma_assets_v02425.py',
        'sampler_guard.py':'scripts/study_d_gemma_sampler_v02422.py',
        'legacy_policy.py':'formation/study_d_gemma_stages_v02420.py',
        'runtime.py':'scripts/study_d_gemma_stages_runtime_v02425.py',
        'stages_policy.py':'formation/study_d_gemma_stages_v02425.py',
        'base_runtime.py':'scripts/study_d_gemma_runtime_v02416.py',
        'base_policy.py':'formation/study_d_gemma_base_v02416.py'}
    for target,source in copies.items():shutil.copyfile(REPO/source,bundle/target)
    runtime=load('ci_runtime',bundle/'runtime.py');h=load('ci_policy',bundle/'stages_policy.py')
    h.verify_assets(ASSETS)
    report=dict(status='INCOMPLETE',scope='CI_ONLY; not a Modal CPU PASS or scientific result',
        gpu=False,pretrained_weights_downloaded=False,model_generation=False,hf_secret_used=False,
        real_tokenizer_rerun=False,modal_cpu_gate_pass=False,vllm_adapter_load_tested=False)
    start=time.monotonic()
    try:
        import torch
        from transformers import Gemma4Config,Gemma4ForConditionalGeneration
        if torch.cuda.device_count()!=0:raise RuntimeError('CPU-only CI; no CUDA device allowed')
        torch.set_num_threads(2)
        config=json.loads((ASSETS/'ci-pinned-config.json').read_text())
        real=runtime.expected_lora_architecture(config['text_config'],h.LORA)
        if (real['layers'],real['full_attention_layers'],real['matched_module_count'],real['expected_trainable_parameters'])!=(60,10,410,61214720):
            raise RuntimeError('real-model expected architecture differs')
        runtime.write(evidence/'architecture-expected-real-model.json',real)
        tiny=Gemma4Config.from_dict(runtime.tiny_config_values(config));torch.manual_seed(247056)
        model=Gemma4ForConditionalGeneration(tiny).float()
        base=evidence/'random-base';model.save_pretrained(base,safe_serialization=True);del model
        fixture=ASSETS/'ci-served-token-fixture.json'
        summaries={a:runtime.data_summary(runtime.ci_tensor_data(a,fixture)) for a in ('contrary','neutral','virtue')}
        runtime.write(evidence/'data-proof.json',dict(summaries=summaries,disclosure='three real-tokenizer examples/arm repeated to18 diagnostic rows; not 2000-example arm'))
        payload=dict(stage='ci_cpu_rehearsal',cpu_rehearsal=True,ci_cpu_rehearsal=True,arm='smoke',
            folder=str(evidence),adapter=str(evidence/'adapter'),tiny_checkpoint=str(base),
            ci_fixture=str(fixture),dataset_proof=str(evidence/'data-proof.json'),deadline=time.monotonic()+h.CPU_SOFTWARE)
        runtime.write(evidence/'input.json',payload)
        env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',OMP_NUM_THREADS='2')
        with (evidence/'process.log').open('w') as log:
            child=subprocess.run([sys.executable,str(bundle/'runtime.py'),'train',str(evidence/'input.json')],
                stdout=log,stderr=subprocess.STDOUT,env=env,timeout=h.CPU_SOFTWARE)
        if child.returncode:raise RuntimeError('actual training_process failed; see evidence/process.log and training-failure.json')
        training=json.loads((evidence/'training.json').read_text())
        coverage=json.loads((evidence/'lora-coverage.json').read_text())
        reload=json.loads((evidence/'adapter-reload.json').read_text())
        if training['optimizer_steps']!=2 or coverage['trainable_parameters']!=7808 or reload['status']!='PASS':
            raise RuntimeError('incomplete two-step training/coverage/reload')
        for path in (evidence/'adapter').glob('*/checkpoint-integrity.json'):
            for name,digest in json.loads(path.read_text())['sha256'].items():
                if h.sha(path.parent/name)!=digest:raise RuntimeError('checkpoint integrity failed')
        report.update(status='PASS',optimizer_steps=2,trainable_parameters=7808,
            adapted_modules=13,fixture_sha256=h.sha(fixture),package_versions=json.loads((evidence/'packages.json').read_text()),
            callbacks_and_checkpoints_verified=True,adapter_reload_verified=True,
            seconds=time.monotonic()-start,disclosure='CPU torch2.13.0+cpu build; same pinned training releases, frozen real-tokenizer IDs; no retokenization or vLLM import')
    except BaseException as exc:
        policy=load('ci_errors',bundle/'base_policy.py')
        report.update(policy.failure_record(exc,'ci_cpu_rehearsal'))
        raise
    finally:
        runtime.write(output/'report.json',report)
        # Ephemeral tiny diagnostic weights are never uploaded/shared/deployed.
        deleted=[]
        for folder in (evidence/'random-base',evidence/'adapter'):
            if folder.exists():
                files={str(p.relative_to(output)):h.sha(p) for p in folder.rglob('*') if p.is_file()}
                deleted.append(dict(path=str(folder.relative_to(output)),sha256=files))
                shutil.rmtree(folder)
        runtime.write(output/'deletion.json',dict(scope='ephemeral CI random tiny models only; no Modal/scientific adapter',deleted=deleted))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
