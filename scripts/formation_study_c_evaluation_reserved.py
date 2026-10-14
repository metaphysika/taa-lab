"""Owner-approved Gemma received-reply adoption and Luna; original root only."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formation.study_c_evaluation_v0244 import run

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--model',required=True,choices=['gemma-4-31b-it','gpt-6-luna'])
    p.add_argument('--approved-study-c',action='store_true')
    p.add_argument('--after-passed-checkpoint',action='store_true')
    p.add_argument('--adopt-approved-received-reply',action='store_true')
    a=p.parse_args()
    result=run(a.model,approved=a.approved_study_c,after_checkpoint=a.after_passed_checkpoint,adopt_received=a.adopt_approved_received_reply)
    print('Study C %s: %s;%d scheduled closed'%(a.model,result['status'],result['primary_closed']))
