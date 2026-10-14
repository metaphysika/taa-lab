"""Offline closed-boundary Study C report; no model calls."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formation.study_c_report_v0239 import model_report,final_report
from formation.study_c_evaluation_v0239 import MODELS

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',choices=MODELS)
    p.add_argument('--final',action='store_true')
    a=p.parse_args()
    if bool(a.model)==a.final:p.error('choose model boundary or final analysis')
    result=final_report() if a.final else model_report(model=a.model)
    print('Saved StudyC report:',result.get('report',result.get('report_path')))
