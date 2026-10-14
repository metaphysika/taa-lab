import sys
sys.path.insert(0,'/workspace/taa-lab')
from unittest.mock import patch
from tests.test_formation_study_c_v0239 import ExecutionTests
from formation import study_c_evaluation_v0239 as c
from formation import study_c_report_v0239 as report
x=ExecutionTests();x.setUp();(x.root/'docs/process').mkdir(parents=True)
try:
 for model in c.MODELS:
  x.run_fixture(model)
  with patch.object(c,'provider_processes',return_value=[]),patch.object(report,'provider_processes',return_value=[]):
   summary=report.model_report(x.root,model);assert summary['completed']==72
   c.snapshot_boundary(x.root,model,reported=True)
  x.run_fixture(model,after=True)
  with patch.object(c,'provider_processes',return_value=[]),patch.object(report,'provider_processes',return_value=[]):
   summary=report.model_report(x.root,model);assert summary['completed']==540
   c.snapshot_boundary(x.root,model,reported=True)
  print(model,'540 fake primaries audited and reported',flush=True)
 with patch.object(c,'provider_processes',return_value=[]),patch.object(report,'provider_processes',return_value=[]):
  result=report.final_report(x.root)
 out=x.root/report.FINAL_OUTPUT
 assert len(c.read(out/'item-breakdowns.json'))==2160
 assert len(c.read(out/'condition-breakdowns.json'))==432
 assert len(c.read(out/'theme-concentration.json'))==216
 print('Full 2160-item final report/immutable model indexes passed; no HTTP or credentials.',flush=True)
finally:x.doCleanups()
