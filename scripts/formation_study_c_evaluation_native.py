"""Original-root Study C: owner-approved one-time native-format Gemini rerun."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formation.study_c_evaluation_v0242 import run, compatibility_call, MODELS

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True,choices=MODELS)
    p.add_argument('--approved-study-c',action='store_true')
    p.add_argument('--after-passed-checkpoint',action='store_true')
    p.add_argument('--compatibility-check',action='store_true')
    a=p.parse_args()
    if a.compatibility_check:
        if a.model!='gemini-3.1-flash-lite' or a.after_passed_checkpoint:p.error('one neutral Gemini compatibility check only')
        result=compatibility_call(approved=a.approved_study_c)
        print('Neutral native-schema compatibility passed;1attempt;notstudydata;$%.9f'%result['cost'])
    else:
        result=run(a.model,approved=a.approved_study_c,after_checkpoint=a.after_passed_checkpoint)
        print('StudyC %s: %s;%d/540;$%.9f'%(a.model,result['status'],result['primary_completed'],result['model_dollars']))
