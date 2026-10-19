"""No CUDA imports: fail-closed sampler configuration and native-log attestation."""
import hashlib
import os

VARIABLE = 'VLLM_USE_FLASHINFER_SAMPLER'
DISABLED = 'FlashInfer top-p/top-k sampling disabled via VLLM_USE_FLASHINFER_SAMPLER=0'
ENABLED = 'Using FlashInfer for top-p & top-k sampling'


def child_env(parent):
    env = dict(parent)
    env[VARIABLE] = '0'
    return env


def configure():
    os.environ[VARIABLE] = '0'


def check_log(text):
    if ENABLED in text:
        raise RuntimeError('FlashInfer fused sampler enabled; STOP before generation')
    if DISABLED not in text:
        raise RuntimeError('native sampler-disabled attestation missing; STOP before generation')
    return dict(status='PASS',environment={VARIABLE:'0'},native_disabled_line=DISABLED,
                log_sha256=hashlib.sha256(text.encode()).hexdigest())
