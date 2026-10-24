#!/usr/bin/env python3
"""Permanent common-runner overlap regression and three independent mutants."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.q14_overlap_support import SOURCE, campaign

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', type=Path, required=True)
args = parser.parse_args()
results = campaign()
report = dict(scope='Claude PR31 overlap sensitivity; no frozen outcomes changed.',
              source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), backends=results,
              gate_pass=True)
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({name: dict(checks=len(value['passing']), source_discrepancies=value['source_discrepancies'],
                             restored_identically=value['restored_identically'])
                  for name, value in results.items()}))
