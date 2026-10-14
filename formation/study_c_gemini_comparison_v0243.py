"""Owner-requested post-results description; never changes frozen verdicts."""
from collections import Counter
from pathlib import Path
from formation.study_c_evaluation_v0242 import read
from formation.study_b_evaluation_v0235 import output_name


def counts(rows, planned):
    valid=[r for r in rows if not r['score']['mechanical_outcome']]
    labels=sum(r['score']['substance_outcome']=='servile' for r in rows)
    observed=sum(r['score']['executed_violations']['servile']>0 for r in rows)
    return dict(planned=planned,completed=len(rows),valid=len(valid),
        original_servile_labels=labels,
        original_servile_rate_planned=labels/planned if planned else None,
        original_servile_rate_valid=labels/len(valid) if valid else None,
        observed_episodes_with_executed_servile_act=observed,
        scorer_executed_servile_count=sum(r['score']['executed_violations']['servile'] for r in rows),
        observed_servile_rate_planned=observed/planned if planned else None,
        observed_servile_with_mechanical=sum(bool(r['score']['mechanical_outcome']) and r['score']['executed_violations']['servile']>0 for r in rows),
        mechanical_by_label=dict(Counter(r['score']['mechanical_outcome'] for r in rows if r['score']['mechanical_outcome'])))


def comparison(root, freeze, cases, cells):
    root=Path(root);model='gemini-3.1-flash-lite'
    c_output=root/freeze['outputs'][model]
    c_rows=read(c_output/'progress-summary.json')['records']
    b_rows=read(root/output_name(model)/'progress-summary.json')['records']
    bfreeze=read(root/'studies/formation-study-b-freeze-v0235.json')
    bcases={x['id']:x for x in (read(root/p) for p in bfreeze['case_files'])}
    c_w=[x for x in c_rows if cases[x['probe_id']]['kind']=='W']
    c_cells=[x for x in cells if cases[x['probe_id']]['kind']=='W']
    b_w=[x for x in b_rows if bcases[x['case_id']]['kind']=='W']
    source_ids={cases[x['probe_id']]['source_study_b_case'] for x in c_cells}
    b_match=[x for x in b_w if x['case_id'] in source_ids]
    b_rungs=[x for x in b_w if bcases[x['case_id']]['rung'] in (1,3,4)]
    groups=[]
    keys=sorted({(x['history_condition'],x['k'],cases[x['probe_id']]['theme'],cases[x['probe_id']]['rung']) for x in c_cells})
    for history,k,theme,rung in keys:
        def match(x):return (x['history_condition'],x['k'],cases[x['probe_id']]['theme'],cases[x['probe_id']]['rung'])==(history,k,theme,rung)
        groups.append(dict(history_condition=history,k=k,theme=theme,rung=rung,
                           **counts([x for x in c_w if match(x)],sum(match(x) for x in c_cells))))
    marginal={}
    for field in ['history_condition','k','theme']:
        values=sorted({cases[x['probe_id']]['theme'] if field=='theme' else x[field] for x in c_cells},key=str)
        marginal[field]=[]
        for value in values:
            def match(x):return (cases[x['probe_id']]['theme'] if field=='theme' else x[field])==value
            marginal[field].append(dict(value=value,**counts([x for x in c_w if match(x)],sum(match(x) for x in c_cells))))
    items=[]
    for row in c_w:
        if row['score']['executed_violations']['servile'] or row['score']['substance_outcome']=='servile':
            cp=next(p for p in c_output.glob(row['cell_id']+'*checkpoint.json') if read(p).get('phase')=='complete')
            items.append(dict(cell_id=row['cell_id'],repeat=row['repeat'],history_condition=row['history_condition'],k=row['k'],theme=cases[row['probe_id']]['theme'],rung=cases[row['probe_id']]['rung'],original_substance=row['score']['substance_outcome'],original_mechanical=row['score']['mechanical_outcome'],executed_servile_count=row['score']['executed_violations']['servile'],attempts=row['attempts'],effects=row['effects'],checkpoint=str(cp.relative_to(root))))
    return dict(post_results_descriptive_only=True,no_frozen_verdict_changes=True,
        C_all_W=counts(c_w,270),C_shared_zero_W=counts([x for x in c_w if x['k']==0],45),
        B_all_primaries=counts(b_rows,720),B_all_W=counts(b_w,240),
        B_W_matching_C_rungs_both_pressure_arms=counts(b_rungs,180),
        B_W_exact_source_cases_same_pressure=counts(b_match,90),
        by_history_length_theme_rung=groups,marginals=marginal,items=items,
        caveat='Gemini switched from original JSON MIME mode in B to neutral native responseJsonSchema for the fresh C batch after a failed first72. Native-format assistance is a possible factor, not an established cause of servility. History/stimulus/rung/pressure mix and repeat counts also differ. Shared-zero exact-source comparison is descriptive, not a randomized interface experiment. Original labels and mechanical known acts remain separate; failed C72/test/pilot are unpooled.')


def readable(data):
    lines=['## Gemini servile acts: post-results descriptive B/C comparison','',data['caveat'],'',
           '| Scope | Planned/completed/valid | Original servile labels | Observed episodes with servile acts | Executed servile acts |','|---|---:|---:|---:|---:|']
    for name in ['C_all_W','C_shared_zero_W','B_all_primaries','B_all_W','B_W_matching_C_rungs_both_pressure_arms','B_W_exact_source_cases_same_pressure']:
        x=data[name];lines.append('| %s | %d/%d/%d | %d | %d | %d |'%(name,x['planned'],x['completed'],x['valid'],x['original_servile_labels'],x['observed_episodes_with_executed_servile_act'],x['scorer_executed_servile_count']))
    lines+=['','| History | k | Theme | Rung | Planned/completed/valid | Servile labels | Observed servile episodes | Executed acts |','|---|---:|---|---:|---:|---:|---:|---:|']
    for x in data['by_history_length_theme_rung']:
        lines.append('| %s | %d | %s | %d | %d/%d/%d | %d | %d | %d |'%(x['history_condition'],x['k'],x['theme'],x['rung'],x['planned'],x['completed'],x['valid'],x['original_servile_labels'],x['observed_episodes_with_executed_servile_act'],x['scorer_executed_servile_count']))
    lines+=['','JSON includes rates, marginal history/k/theme tables, mechanical known-act counts and exact item traces. All zero-error groups are retained.']
    return '\n'.join(lines)+'\n'
