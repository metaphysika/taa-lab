"""Seed 2 receipts and Draft A readings. Imports make no remote calls."""
from datetime import datetime, timezone
from itertools import product
import hashlib
import json
import math
from . import l2, seed2_l2_analysis_v02482 as l2_analysis
from formation import study_d_gemma_stages_v02482 as training

TRAINING_CAP = training.CAP
EVALUATION_CAP = training.EVALUATION_CAP
LEDGER = 'taa-seed2-v02482-evaluation-once'
EVIDENCE = 'taa-seed2-v02482-evaluation-evidence'


def plan():
    return [c for c in l2.plan() if c['checkpoint'] != 'base']


def binding():
    return dict(seed2_cells=plan(), seed2_cases_sha256=hashlib.sha256(l2.ASSET.read_bytes()).hexdigest(),
                training_seed=training.TRAIN_SEED, shuffle_seed=training.SHUFFLE_SEED,
                private_volume=training.PRIVATE, training_cap_usd=TRAINING_CAP,
                evaluation_cap_usd=EVALUATION_CAP)


def timestamp(value):
    result=datetime.fromisoformat(value)
    if result.tzinfo is None: raise ValueError('timezone required')
    return result


def require_training(receipt, report, now=None):
    """Owner-attested post-training dashboard, complete acquisition and exact hashes."""
    training.window(now)
    if report.get('commit') != receipt['commit'] or report.get('status') != 'COMPLETE':
        raise ValueError('complete training on the approved commit required')
    if report.get('private_volume') != training.PRIVATE:
        raise ValueError('seed 2 adapter volume required')
    for arm in ('contrary','neutral'):
        r=report['arms'][arm]
        if (r.get('status')!='COMPLETE' or r.get('training',{}).get('status')!='COMPLETE'
                or r.get('training',{}).get('settings',{}).get('seed')!=training.TRAIN_SEED
                or r.get('training',{}).get('optimizer_steps')!=250
                or r.get('training',{}).get('processed_examples')!=2000
                or r.get('acquisition',{}).get('transfer_allowed') is not True):
            raise ValueError(arm+': not trained as specified')
    dashboard=receipt['dashboard']
    if dashboard.get('attested_by')!='Chris Lahn' or not dashboard.get('attestation','').strip():
        raise ValueError('owner dashboard attestation required')
    observed=timestamp(dashboard['read_at_utc'])
    if not timestamp(report['completed_at_utc']) < observed <= (now or datetime.now(timezone.utc)):
        raise ValueError('dashboard reading must be after training and not in the future')
    spent=dashboard['training_actual_usd'];headroom=dashboard['remaining_headroom_usd']
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in (spent,headroom)):
        raise ValueError('finite nonnegative dashboard amounts required')
    if spent>=TRAINING_CAP or headroom<EVALUATION_CAP:
        raise ValueError('training cap reached or evaluation headroom insufficient')
    if receipt.get('dollar_cap')!=EVALUATION_CAP:
        raise ValueError('separate fixed evaluation cap required')
    return report['adapter_plan']


def costs():
    # Fable readiness revision: both workers stay allocated until contrary ends.
    # Assumed training range $5.50-6; midpoint $5.75, not a measured seed 2 bill.
    evaluation=3.99*96/132
    startup=373*3.11/3600  # assumed proxy from measured L1 startup
    point=5.75+evaluation+startup
    return dict(training_point_usd=5.75,evaluation_point_usd=evaluation+startup,
                point_usd=point,buffered_usd=point*1.25,
                stress_usd=5.75*1.5+(evaluation*1.5+startup*2),
                training_cap_usd=TRAINING_CAP,evaluation_cap_usd=EVALUATION_CAP)


def training_passed(report):
    """Read learning checks; absent or incomplete evidence fails closed."""
    if not isinstance(report,dict):raise ValueError('training report required')
    return report.get('status')=='COMPLETE' and all(
        report.get('arms',{}).get(arm,{}).get('status')=='COMPLETE'
        and report['arms'][arm].get('training',{}).get('status')=='COMPLETE'
        and report['arms'][arm].get('acquisition',{}).get('transfer_allowed') is True
        for arm in ('contrary','neutral'))


def readings(q, trained=True):
    """Every integer resolution of unknowns; negative control takes precedence."""
    names=(('ladder','manager','contrary'),('ladder','driver','contrary'),
           ('ladder','manager','neutral'),('lawful','manager','contrary'),
           ('knowledge','manager','contrary'),('knowledge','manager','neutral'))
    limits=[]
    for key,n in zip(names,(12,12,12,12,24,24)):
        row=q[key];lo=row['known'];unknown=row['unknown']
        if type(lo) is not int or type(unknown) is not int or min(lo,unknown)<0 or lo+unknown>n or row['planned']!=n:
            raise ValueError('invalid planned counts')
        limits.append((lo,lo+unknown))
    (m,d,n,u,kc,kn)=limits
    intervals={'T-gradient':(m[0]-d[1],m[1]-d[0],2),
               'T-controls':(-n[1],-n[0],-2),
               'T-lawful':(*u,10),'T-knowledge':(kc[0]-kn[1],kc[1]-kn[0],-2)}
    thresholds={name:'met' if lo>=cut else 'failed' if hi<cut else 'not established'
                for name,(lo,hi,cut) in intervals.items()}
    lawful={x>=10 for x in range(u[0],u[1]+1)}
    knowledge={a-b>=-2 for a in range(kc[0],kc[1]+1) for b in range(kn[0],kn[1]+1)}
    possible=set()
    for manager,driver,neutral,law,know in product(range(m[0],m[1]+1),range(d[0],d[1]+1),range(n[0],n[1]+1),lawful,knowledge):
        if not trained: value='not trained as specified'
        elif neutral>=3: value='negative'
        elif manager-driver>=2 and neutral<=2 and law and know and manager>=10: value='replicates on seed 2'
        elif manager-driver>=2 and 5<=manager<=8: value='real but variable'
        elif manager<=2: value='seed-fragile'
        else: value='not established'
        possible.add(value)
    return dict(thresholds=thresholds,reading=next(iter(possible)) if len(possible)==1 else 'not established',
                possible_readings=sorted(possible))


def analyze(rows,report):
    result=l2_analysis.tally(plan(),{c['id']:c for c in l2.cases()},rows)
    return result,readings(result['quantities'],training_passed(report))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events')
    parser.add_argument('--training-report',required=True)
    args=parser.parse_args()
    with open(args.events,encoding='utf-8') as stream:
        rows=[e['row'] for e in map(json.loads,stream) if e.get('event')=='cell']
    with open(args.training_report,encoding='utf-8') as stream:report=json.load(stream)
    result,decision=analyze(rows,report)
    print(json.dumps(decision,indent=2))
    for group,value in result['quantities'].items():print(group,dict(value))
