"""Only an explicitly approved, reviewed timeout continuation; no replacement cells."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from formation.evaluation_continuation_v0220 import run_continuation
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--approved-continuation',action='store_true');p.add_argument('--reviewed-timeout',action='store_true')
    a=p.parse_args();s=run_continuation(a.source,a.output,a.approved_continuation,a.reviewed_timeout)
    print('%s: %s, %d/%d completed; estimated $%.8f'%(s['model'],s['status'],s['completed_cells'],s['planned_cells'],s['batch_estimated_dollars']))
