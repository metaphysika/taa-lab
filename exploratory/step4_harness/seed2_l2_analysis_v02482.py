"""L2 planned-denominator counts and bounds, without decision thresholds."""
from collections import Counter
from .crossing_analysis import classify
from .l1_analysis import difference
from .k1 import answer


def key(cell):
    return tuple(cell[x] for x in ('l2_arm','issuer_rung','case_id','checkpoint','repeat'))


def tally(cells,cases,rows):
    indexed={}
    for row in rows:
        if key(row) in indexed: raise ValueError('duplicate row')
        indexed[key(row)]=row
    if set(indexed)-{key(x) for x in cells}: raise ValueError('unplanned row')
    quantities={}
    for cell in cells:
        arm,rung,ident,cp,repeat=key(cell)
        row=indexed.get(key(cell)); case=cases[ident]
        # Knowledge is also tallied separately for W twins (answer no) and U twins (answer yes).
        groups=[(arm,rung,cp)]+([('knowledge_'+case['kind'],rung,cp)] if arm=='knowledge' else [])
        qs=[quantities.setdefault(g,Counter(known=0,negative=0,unknown=0,planned=0)) for g in groups]
        if arm=='knowledge':
            value=answer(row.get('raw')) if row and row.get('terminal_status')=='single_turn' else None
            category='unknown' if value is None else 'known' if value==case['answer_key']['knowledge_answer'] else 'negative'
        else:
            cls=classify(case,row)
            category='unknown' if cls=='unknown' else 'known' if cls==('known_lawful_success' if case['kind']=='U' else 'known_servile') else 'negative'
        for q in qs:
            q['planned']+=1; q[category]+=1
    bounds={}
    for name,a,b in [('contrary_manager_minus_driver',('ladder','manager','contrary'),('ladder','driver','contrary')),('knowledge_contrary_minus_neutral',('knowledge','manager','contrary'),('knowledge','manager','neutral')),('knowledge_contrary_minus_base',('knowledge','manager','contrary'),('knowledge','manager','base'))]:
        if a in quantities and b in quantities:
            bounds[name]=difference(quantities[a],quantities[b])
    return dict(quantities=quantities,bounds=bounds,rate_bounds={k:dict(lower=v['known']/v['planned'],upper=(v['known']+v['unknown'])/v['planned']) for k,v in quantities.items()})


if __name__=='__main__':
    import argparse,json
    from . import l2
    parser=argparse.ArgumentParser(); parser.add_argument('events'); parser.add_argument('--repeats',type=int,default=1)
    args=parser.parse_args()
    with open(args.events,encoding='utf-8') as stream:
        rows=[e['row'] for e in map(json.loads,stream) if e.get('event')=='cell']
    for name,values in tally(l2.plan(args.repeats),{x['id']:x for x in l2.cases()},rows).items():
        for group,value in values.items(): print(name,group,dict(value))
