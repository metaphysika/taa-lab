"""Isolated free production continuation rehearsal; no weights, Modal or model calls."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.test_study_d_completion_v02426 import CompletionTests
if __name__=='__main__':
    CompletionTests().test_timing_regression_actual_event_does_not_wait_for_remote_commit()
    CompletionTests()._scripted_completion()
    print('PASS: actual frozen install, 34 untouched episodes, unchanged seeds/parser/scorer, 132-unit provenance, two retained missing')
