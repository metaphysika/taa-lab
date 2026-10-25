#!/usr/bin/env python3
"""Pin the Q18 insertion/recheck guard's four assertion failures on old code."""
from pathlib import Path
import argparse,importlib.util,json,socket,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--implementation-root',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.implementation_root.resolve()))
import tests.trace_support
from tests.trace_support import production_backend,mcp_backend
from taa_gateway_reference import refunds
from conventional_gateway import backend
tests.trace_support.__path__.append(str(ROOT/'tests/trace_support'))
spec=importlib.util.spec_from_file_location('q18_new_expectations',ROOT/'tests/test_gateway_q18.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
socket.socket=lambda *args,**kwargs:(_ for _ in ()).throw(RuntimeError('offline baseline test'))
suite=unittest.TestSuite([m.Q18ScopeBoundaries('test_optional_reference_resolution_invalidates_and_is_rechecked')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
record=dict(claim='[Descriptive] Original code fails the ruling-authored guard by assertion in all four implementations.',failures=len(result.failures),errors=len(result.errors),expected_assertion_failures=4)
a.report.parent.mkdir(parents=True,exist_ok=True)
with a.report.open('x') as stream:json.dump(record,stream,indent=2);stream.write('\n')
assert len(result.failures)==4 and not result.errors
