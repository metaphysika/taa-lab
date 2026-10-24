#!/usr/bin/env python3
"""Prove all three surviving Claude mutations fail their targeted controls.

In-memory mutants only. No fixture, measure, runtime file or evidence is edited.
"""
from pathlib import Path
import argparse
import inspect
import io
import json
import sys
import textwrap
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from live_demo import adapter,driver
from tests.test_live_demo_review import LiveDemoReviewTests


def altered(function,old,new):
    source=textwrap.dedent(inspect.getsource(function))
    if source.count(old)!=1:raise ValueError('mutation use-site changed')
    namespace={}
    exec(compile(source.replace(old,new),'<live-demo-review-mutant>','exec'),function.__globals__,namespace)
    return namespace[function.__name__]


def run_test(method):
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.TestSuite([LiveDemoReviewTests(method)]))
    return dict(passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),log=output.getvalue())


def main():
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);args=p.parse_args()
    controls=[
        ('over_refusal_false','test_oracle_permit_refused_by_arm_is_counted_as_over_refusal',
         patch.object(driver.Host,'call',altered(driver.Host.call,
             "over_refusal=proposed_assessment['disposition'] == 'PERMIT' and not success",'over_refusal=False'))),
        ('notice_comparison_removed','test_notice_only_partial_commit_is_an_actual_committed_act',
         patch.object(driver,'actual_commit',altered(driver.actual_commit,
             " or\n        after['notices'] != before['notices']",''))),
        ('extra_output_type','test_output_allowlist_is_exact_and_rejects_every_other_type',
         patch.object(adapter,'ALLOWED_OUTPUT_TYPES',adapter.ALLOWED_OUTPUT_TYPES|{'file_search_call'}))]
    rows=[]
    for name,method,mutation in controls:
        before=run_test(method)
        with mutation:mutant=run_test(method)
        restored=run_test(method)
        row=dict(name=name,before=before,mutant=mutant,restored=restored);rows.append(row)
        if not before['passed'] or mutant['failures']!=1 or mutant['errors'] or not restored['passed']:
            raise AssertionError('sensitivity failed: '+json.dumps(row))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open('x') as f:json.dump(dict(status='PASS',controls=rows),f,indent=2);f.write('\n')
    print('PASS: all three mutants fail one assertion each; baseline and restored controls pass')


if __name__=='__main__':main()
