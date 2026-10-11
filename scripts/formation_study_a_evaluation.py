"""Approved per-model evaluation batch; checkpoints resume only unissued work."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from formation.evaluation_runner_v0218 import run_batch
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True);p.add_argument('--budget',required=True,type=float)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--approved-cost',action='store_true')
    p.add_argument('--confirm-groq-free',action='store_true');a=p.parse_args()
    s=run_batch(a.model,a.budget,a.output,a.approved_cost,a.confirm_groq_free)
    print('%s: %s, %d/%d completed; estimated $%.8f'%(a.model,s['status'],s['completed_cells'],s['planned_cells'],s['batch_estimated_dollars']))
