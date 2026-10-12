"""Offline readiness only: no provider transport, key files, or model probes."""
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation.study_b_evaluation_v0233 import check, output_name, read, SLUGS
from scripts.formation_study_a_gate3 import verify_freeze

def readiness():
    f,a,cases,schedule=check(ROOT,True)
    lock=ROOT/'results/formation-spending-v021/run.lock'
    if lock.exists():raise ValueError('shared run lock present; no new run')
    hold=Path('/workspace/haiku55-runtime/study-b-maintenance.hold')
    if hold.exists():raise ValueError('maintenance hold present; never clear automatically')
    existing=[output_name(m) for m in SLUGS if (ROOT/output_name(m)).exists()]
    if existing:raise ValueError('existing B evaluation output; must review closed status before any action')
    active=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            command=(p/'cmdline').read_bytes().split(b'\0')
            # Never print arbitrary process arguments, which may contain credentials.
            if any(b'scripts/formation_study_' in arg and b'.py' in arg and not b'readiness' in arg for arg in command) and any(arg in (b'--approved-study-b',b'--approved-continuation',b'--approved-gemma-free',b'--approved-luna-pilot',b'--confirm-groq-free') for arg in command):active.append(int(p.name))
        except (OSError,PermissionError):pass
    if active:raise ValueError('approved provider runner active; no concurrent ledger run')
    ledgers={p:read(ROOT/('results/formation-spending-v021/%s.json'%p))['estimated_api_dollars'] for p in ('openai','claude','google','groq')}
    if any(abs(ledgers[p]-f['ledger_start'][p])>1e-12 for p in ledgers):raise ValueError('starting cumulative ledger differs')
    available={n:bool(os.environ.get(n)) for n in ('TAA_OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY')}
    if not all(available.values()):raise ValueError('required configured API binding unavailable; no credentials displayed')
    policy=read('/etc/codex/network-policy.json')
    configured={x['host'] for x in policy['http_network_policy']['egress_rules']}
    network={host:host in configured for host in ('api.anthropic.com','api.openai.com','generativelanguage.googleapis.com')}
    if not all(network.values()):raise ValueError('API destination not configured; no probe')
    return {'status':'offline_readiness_passed','root':str(ROOT),'python':sys.version.split()[0],'original_A_freeze_verified':verify_freeze(),'B_frozen_files':len(f['files_sha256']),'protected_evidence_verified':len(f['protected_evidence_sha256']),'conditions':len(cases),'episodes_per_model':len(schedule),'ledger_dollars':ledgers,'API_bindings_available_without_values':available,'configured_HTTPS_POST_destinations_without_probe':network,'model_calls_or_probes':0,'active_provider_runners':active,'run_lock_present':False,'existing_evaluation_outputs':existing,'first_launch':'Haiku5.5 repeat1 only; stop/report72 mechanical labels'}
if __name__=='__main__':print(json.dumps(readiness(),indent=2))
