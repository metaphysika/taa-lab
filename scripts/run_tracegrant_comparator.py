#!/usr/bin/env python3
"""Frozen-contract TraceGrant reconstruction on all ten development inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from comparators.harness import run_suite
from comparators.tracegrant import contract
from comparators.audit import audit

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--report',type=Path,required=True)
a=p.parse_args()
sources=sorted(p for p in (ROOT/'comparators').rglob('*') if p.suffix in ('.py','.json','.md'))
source_start={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
paths=sorted((ROOT/'comparators/contracts/v0.1').glob('*.json'))
start={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
r=run_suite()
r['audits']=[{'case':episode['case'],'controller':episode['controller'],'checks':audit(episode,contract(episode['case']))} for episode in r['episodes']]
rows=[row for episode in r['audits'] for row in episode['checks']]
r['counts'].update(checks=len(rows),discrepancies=sum(row['status']!='pass' for row in rows),incomplete=0)
r['contracts_unchanged']=start=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
r['source_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
r['sources_unchanged']=r['source_hashes']==source_start
a.report.parent.mkdir(parents=True,exist_ok=True)
a.report.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r['counts']))
raise SystemExit(not r['contracts_unchanged'] or not r['sources_unchanged'] or bool(r['counts']['discrepancies']))
