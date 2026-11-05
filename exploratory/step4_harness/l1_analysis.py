"""Descriptive planned-denominator L1 counts; no thresholds or verdicts."""
from collections import Counter
from .crossing_analysis import classify
from .k1_analysis import stop_category


def key(cell):
    return tuple(cell[x] for x in ('l1_arm','issuer_rung','case_id','checkpoint','repeat'))


def difference(a,b):
    return dict(lower=a['known']-b['known']-b['unknown'],
                upper=a['known']+a['unknown']-b['known'])


def tally(cells,cases,rows):
    indexed={}
    for row in rows:
        if key(row) in indexed: raise ValueError('duplicate row')
        indexed[key(row)]=row
    if set(indexed)-{key(x) for x in cells}: raise ValueError('unplanned row')
    counts={}; quantities={}; paired={}
    for cell in cells:
        arm,rung,ident,cp,repeat=key(cell)
        row=indexed.get(key(cell)); case=cases[ident]
        cls=classify(case,row)
        group=counts.setdefault((arm,rung,cp),Counter())
        group['planned']+=1; group[cls]+=1
        positive='known_lawful_success' if case['kind']=='U' else 'known_servile'
        q=quantities.setdefault((arm,rung,cp),Counter(known=0,unknown=0,negative=0,planned=0))
        q['planned']+=1; q['unknown' if cls=='unknown' else 'known' if cls==positive else 'negative']+=1
        if arm=='ladder' and cp=='contrary': paired.setdefault((ident,repeat),{})[rung]=cls
        if arm=='ladder' and cls=='known_servile':
            group['all_servile']+=1; group[stop_category(case,row)]+=1
            if row.get('stop_turn') is not None:
                group['stop_opportunity']+=1; group['stop_issued']+=1
                if len(row.get('packets',[]))>row['stop_turn']: group['response_after_stop']+=1
    bounds={}
    for arm,rung,cp in quantities:
        if cp=='contrary' and (arm,rung,'neutral') in quantities:
            bounds[arm,rung]=difference(quantities[arm,rung,'contrary'],quantities[arm,rung,'neutral'])
    manager=quantities.get(('ladder','manager','contrary'),Counter())
    issuer_bounds={r:difference(manager,quantities.get(('ladder',r,'contrary'),Counter())) for r in ('peer','driver','anonymous')}
    return dict(counts=counts,quantities=quantities,paired_contrary=paired,
                contrary_minus_neutral_bounds=bounds,manager_minus_lower_bounds=issuer_bounds)


if __name__=='__main__':
    import argparse,json
    from . import l1
    parser=argparse.ArgumentParser()
    parser.add_argument('events'); parser.add_argument('--repeats',type=int,default=1)
    args=parser.parse_args()
    rows=[e['row'] for e in map(json.loads,open(args.events,encoding='utf-8')) if e.get('event')=='cell']
    out=tally(l1.plan(args.repeats),{x['id']:x for x in l1.c.cases()},rows)
    for name,values in out.items():
        for key,value in values.items(): print(name,key,dict(value))
