#!/usr/bin/env python3
"""Read-only compatibility proof; never rerun the retained scored experiment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from live_demo import config
from tests.trace_support.bundle import verify_bundle

BASE = '436fbf002d3e0f9e84a41206fe3c4c43b0d71ed7'


Q18_POLICY_FILES = frozenset((
    'taa_gateway/act.py', 'taa_gateway/grants.py', 'taa_gateway/refunds.py',
    'taa_gateway_reference/refunds.py', 'conventional_gateway/policy.py',
))


def policy_delta(record_path, root=ROOT):
    """Explicit, hash-bound Q18 exception; never a launch approval.

    Without this option the original Q17 source-equality check is unchanged.
    Scientific inputs, source expectations, scoring and host code are never
    eligible for the policy exception.
    """
    if record_path is None:
        return {}
    record = json.loads(Path(record_path).read_bytes())['q18_policy_delta']
    if (record.get('owner') != 'Chris' or record.get('ruling') != 'Q18' or
            record.get('frozen_acceptance_pass') is not True or
            record.get('comparison_pass') is not True or type(record.get('changed_scores')) is not int or record.get('changed_scores') != 0):
        raise ValueError('missing successful Q18 acceptance/comparison record')
    hashes = record['source_sha256']
    if set(hashes) != Q18_POLICY_FILES:
        raise ValueError('Q18 exception must name exactly the five policy files')
    if any(hashlib.sha256((Path(root)/name).read_bytes()).hexdigest() != digest
           for name, digest in hashes.items()):
        raise ValueError('Q18 policy source does not match recorded verification')
    return hashes


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--policy-change-record',type=Path,help='Explicit pinned Q18 delta; default retains strict Q17 source equality')
    args=p.parse_args()
    verify_bundle(); config.verify()
    # All old policy, host, reference, comparator and permanent source fixtures
    # must be byte-identical to the approved Q17 merge. New harness is separate.
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'--',
        'taa_gateway','taa_gateway_reference','conventional_gateway','comparators','worlds/refunds',
        'tests/expected_traces','tests/regression_scenarios','tests/trace_support',
        'docs/process/evidence/gateway-cross-arm-scoring-v02','docs/process/evidence/gateway-q17-verification'],
        cwd=ROOT,text=True).splitlines()
    hashes={}; changes={}
    authorized_delta=policy_delta(args.policy_change_record)
    for name in names:
        # Explicit allowlist of repository source/evidence paths; never keys.env.
        original=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)
        actual=(ROOT/name).read_bytes()
        if actual!=original:
            if authorized_delta.get(name)!=hashlib.sha256(actual).hexdigest():
                raise ValueError('protected file changed: '+name)
            changes[name]=dict(before=hashlib.sha256(original).hexdigest(),after=hashlib.sha256(actual).hexdigest())
        hashes[name]=hashlib.sha256(actual).hexdigest()
    with ZipFile(ROOT/'docs/process/evidence/gateway-cross-arm-scoring-v02/acceptance.zip') as archive:
        hasher=hashlib.sha256();count=0
        with archive.open('episodes.jsonl') as stream:
            for line in stream:
                hasher.update(line);count+=1
        if count!=320 or hasher.hexdigest()!='4f96fa81efdb5362fa385ce5ab0a550f9faa7ddb1057e25c0432e049b653776a':
            raise ValueError('retained v0.2 scored journal changed')
    comparison=json.loads((ROOT/'docs/process/evidence/gateway-q17-verification/metric-verification.json').read_bytes())
    if any(c['changed'] for c in comparison['protocol_cells']):raise ValueError('score changed')
    report=dict(status='PASS',scope='Preservation of approved runtime and retained scoring; no scored rerun',
                base=BASE,protected_hashes=hashes,episodes=count,journal_sha256=hasher.hexdigest(),
                explicit_q18_policy_delta=changes,policy_change_record=str(args.policy_change_record) if args.policy_change_record else None)
    if changes:
        report['scope']='Frozen science/evidence preserved; explicit owner-requested Q18 policy delta pinned; no scored rerun'
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(status='PASS',protected_files=len(hashes),retained_episodes=count)))


if __name__=='__main__':main()
