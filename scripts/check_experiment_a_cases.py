#!/usr/bin/env python3
"""Offline structural checks and one retained lawful-controller campaign.

Explicit sealed input is allowed ONLY for owner-approved feasibility validation;
experiment_a.run has no H loader/unseal switch. No model transport is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiment_a import config
from experiment_a.cases import pair_check,sealed_digest
from experiment_a.lawful_controller import complete
from live_demo.evidence import Evidence


def blocked(*args,**kwargs):raise RuntimeError('network disabled for feasibility validation')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sealed-validation-root',type=Path,required=True)
    p.add_argument('--structure-only',action='store_true')
    a=p.parse_args()
    socket.socket=blocked;socket.create_connection=blocked
    config.verify()
    a.output.mkdir(parents=True,exist_ok=False)
    sealed=a.sealed_validation_root.resolve()
    if sealed.is_relative_to(config.ROOT):raise ValueError('sealed inputs must stay outside checkout')
    seal=sealed_digest(sealed)
    if seal!=(config.INPUTS/'H.sha256').read_text().strip():raise ValueError('sealed hash mismatch')
    pairs={'P':config.load('P-pairs.json'),'H':json.loads((sealed/'pairs.json').read_bytes())}
    structure={group:pair_check(config.INPUTS/'P' if group=='P' else sealed,items) for group,items in pairs.items()}
    report=dict(status='STRUCTURE_PASS',claim='[Descriptive] Offline feasibility, no model or expected key',
                structure=structure,H_sha256=seal,controllers=[],requested_controller_cells=36,source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'experiment_a').rglob('*.py'))})
    if not a.structure_only:
        # All detailed H evidence remains within the external sealed tree.
        h_evidence=sealed.parent/('feasibility-'+seal)
        h_evidence.mkdir(exist_ok=False)
        for group in ('P','H'):
            directory=config.INPUTS/'P' if group=='P' else sealed
            for pair in pairs[group]:
                identity=pair['pair'][1]
                prog=json.loads((directory/(identity+'.json')).read_bytes())
                for arm in config.ARMS:
                    parent=a.output if group=='P' else h_evidence
                    row=complete(identity,arm,prog,Evidence(parent/(identity+'-'+arm)))
                    report['controllers'].append(row)
                    if not row['lawful_completion']:
                        report['status']='STOP_NO_LAWFUL_COMPLETION'
                        (a.output/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
                        print(json.dumps(report,indent=2));return 1
        report['status']='PASS'
    # Program data must remain byte-identical throughout this campaign.
    config.verify()
    if sealed_digest(sealed)!=seal:raise ValueError('sealed input changed during campaign')
    (a.output/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
