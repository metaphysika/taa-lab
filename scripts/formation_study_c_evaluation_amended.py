"""Original-root owner-approved frozen Study C; one model and closed block only."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formation.study_c_evaluation_v0241 import run, MODELS

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True,choices=MODELS)
    p.add_argument('--approved-study-c',action='store_true')
    p.add_argument('--after-passed-checkpoint',action='store_true')
    p.add_argument('--resume-approved-pre-send-guard',action='store_true')
    args = p.parse_args()
    result = run(args.model,approved=args.approved_study_c,after_checkpoint=args.after_passed_checkpoint,resume_guard=args.resume_approved_pre_send_guard)
    print('StudyC %s: %s; %d/540; $%.9f' % (args.model,result['status'],result['primary_completed'],result['model_dollars']))
