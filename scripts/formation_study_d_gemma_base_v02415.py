"""Mac launcher: validates approval and writes local once-marker BEFORE image build.

--help and --preflight-only are offline. No training entrypoint exists here.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from formation import study_d_gemma_base_v02415 as h
ASSETS = ROOT/'studies/formation-study-d-gemma-base-v02415'


def check_sources():
    manifest = h.verify_assets(ASSETS)
    for name, expected in manifest['code_sha256'].items():
        if h.sha(ROOT/name)!=expected:
            raise ValueError('reviewed source differs: '+name)
    return manifest


def assert_committed(root, files, commit):
    for relative in files:
        try:
            committed=subprocess.check_output(['git','show',commit+':'+relative],cwd=root,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            raise ValueError('reviewed file absent from commit: '+relative) from None
        if committed != (Path(root)/relative).read_bytes():
            raise ValueError('reviewed file differs from commit: '+relative)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved',action='store_true')
    parser.add_argument('--approval-receipt',default='')
    parser.add_argument('--actual-total-usd',type=float,default=-1)
    parser.add_argument('--billing-attestation',default='')
    parser.add_argument('--preflight-only',action='store_true')
    args = parser.parse_args()
    if sys.version_info[:2]!=(3,12):
        raise ValueError('Python 3.12 required before any Modal contact')
    manifest=check_sources()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    receipt = dict(commit=commit,approved=args.approved,approval_receipt=args.approval_receipt,
        prior_usd=args.actual_total_usd,billing_attestation=args.billing_attestation,
        utc=datetime.now(timezone.utc).isoformat(), asset_sha256=h.sha(ASSETS/'integrity.json'))
    h.validate_receipt(receipt,commit)
    files=list(manifest['code_sha256'])+[str(p.relative_to(ROOT)) for p in ASSETS.iterdir() if p.is_file()]
    assert_committed(ROOT,files,commit)
    marker = Path.home()/'.local/state/taa-study-d/gemma-base-v02415-local-attempt.json'
    if marker.exists():
        raise ValueError('local launch attempt exists; do not delete or reset; review required')
    if args.preflight_only:
        print(json.dumps(dict(status='OFFLINE PREFLIGHT PASS; NO LAUNCH',budget=h.budget(args.actual_total_usd,True)),indent=2))
        return
    marker.parent.mkdir(parents=True,exist_ok=True)
    with marker.open('x') as stream:
        json.dump(receipt,stream,indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    env = os.environ.copy()
    env['STUDY_D_GEMMA_PREFLIGHT'] = str(marker)
    # Modal auth remains in the Mac's SDK profile; no credential copying.
    subprocess.run([sys.executable,'-m','modal','run','--detach',
        str(ROOT/'scripts/study_d_gemma_entry_v02415.py')],cwd=ROOT,env=env,check=True)


if __name__=='__main__':
    main()
