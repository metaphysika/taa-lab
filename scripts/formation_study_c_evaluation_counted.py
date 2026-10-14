"""Original-root Study C: approved Gemma count recovery, then Luna."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formation.study_c_evaluation_v0243 import run, MODELS

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True,choices=MODELS[2:])
    p.add_argument('--approved-study-c',action='store_true')
    p.add_argument('--after-passed-checkpoint',action='store_true')
    a=p.parse_args()
    result=run(a.model,approved=a.approved_study_c,after_checkpoint=a.after_passed_checkpoint)
    print('StudyC %s: %s;%d/540;$%.9f'%(a.model,result['status'],result['primary_completed'],result['model_dollars']))
