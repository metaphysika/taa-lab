import importlib.util,sys,unittest
sys.path.insert(0,'/workspace/taa-live-demo-results-review')
import tests.trace_support
tests.trace_support.__path__.append('/workspace/taa-gateway-q18/tests/trace_support')
spec=importlib.util.spec_from_file_location('new_q18_tests','/workspace/taa-gateway-q18/tests/test_gateway_q18.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
suite=unittest.TestSuite([m.Q18ScopeBoundaries('test_optional_reference_resolution_invalidates_and_is_rechecked')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert len(result.failures)==4 and not result.errors
