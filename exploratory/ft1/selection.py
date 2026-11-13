"""Same-cell candidate refusal, preserving the original selection ordering."""
import json
from pathlib import Path
from . import data

CANDIDATE_STOP = 110000


def cell(index, kind):
    """All structural case-mix fields, including controls and the chosen turn."""
    keys=('type','theme','evidence_type','lookup','correction','outside_sphere','pressure','holder')
    result=[]
    for mode,partition in ((kind,'train'),('refusal','train-1'),('routine','train-4')):
        messages,target,_,lines,meta=data.card(index,mode,partition)
        # Normalize concrete IDs and randomly assigned recipient names.
        step=meta['step']
        for value in (*meta['ids'].values(),meta['recipient']): step=step.replace(value,'#')
        result.append(tuple(meta[k] for k in keys)+(step,target['tool'],
            tuple(sorted(target['args'].keys())),
            any('lower fees' in line for line in lines)))
    return tuple(result)


def units():
    """Lawful/wrongful twins and sphere twins are indivisible units."""
    seen=set()
    for i,kind in enumerate(data.MIX):
        if i in seen: continue
        pair=([i,i+600] if i<500 else [i,i+1] if kind=='sphere' and i%2==0 else [i])
        seen.update(pair)
        yield pair


def select_training(counter):
    originals={}; balances={}; refused=[]; balance=0
    for i,kind in enumerate(data.MIX):
        card=data.card(i,kind)
        balances[i]=balance
        try:
            choice=data.choose(counter,*card[:4],balance)
            originals[i]=(i,card,choice)
            balance+=choice[2]-choice[3]
        except data.InfeasibleCandidate as exc:
            originals[i]=None
            refused.append(i)
            # This is never emitted or accepted as training data. It preserves
            # 91855bb8's deterministic ordering for subsequent untouched slots.
            balance+=exc.reference_delta
    selected=dict(originals); replacements=[]; used=set(range(2000))
    for unit in units():
        if all(originals[i] is not None for i in unit): continue
        wanted=[cell(i,data.MIX[i]) for i in unit]
        offsets=[i-unit[0] for i in unit]
        rejected=[]
        for start in range(10000,CANDIDATE_STOP):
            indices=[start+offset for offset in offsets]
            if any(i in used for i in indices): continue
            if [cell(j,data.MIX[i]) for i,j in zip(unit,indices)]!=wanted: continue
            candidates=[]
            for i,j in zip(unit,indices):
                card=data.card(j,data.MIX[i])
                try: choice=data.choose(counter,*card[:4],balances[i])
                except data.InfeasibleCandidate:
                    rejected.append(j)
                    break
                candidates.append((j,card,choice))
            else:
                for i,candidate in zip(unit,candidates):
                    selected[i]=candidate
                    replacements.append(dict(slot=i,refused=i if i in refused else None,
                        replacement=candidate[0],unit=unit,rejected_candidates=list(rejected)))
                used.update(indices)
                break
        else:
            raise ValueError('same-cell feasible candidate pool exhausted; stop for owner review')
    return selected,replacements,refused


def selection_rows(output):
    rows=[]
    for two,three in zip(output['2'],output['3']):
        index=int(three['id'].rsplit('-',1)[1])
        _,_,reasons,lines,_=data.card(index,three['type'])
        reason=json.loads(three['messages'][-1]['content'])['reason']
        rest=json.loads(two['messages'][-1]['content'])['reason']
        rows.append([three['id'],reasons.index(reason),len(rest.splitlines()),
                     two['trained_tokens'],three['trained_tokens']])
    return rows


def verify_expected(report):
    """Job (a) compares its own counts/choices; no tolerance or fallback."""
    expected=json.loads(Path(__file__).with_name('selection_expected.json').read_bytes())
    actual=report['training']
    if actual['selection']!=expected['selection'] or actual['replacements']!=expected['replacements'] or actual['refused']!=expected['refused']:
        # Say which rows differ, so a failed job (a) leaves usable evidence (IDs and numbers only).
        a,e=actual['selection'],expected['selection']
        differing=[x[0] for x,y in zip(a,e) if x!=y]
        raise ValueError('FT1 real-tokenizer selection/expected-count table mismatch: '
                         f'selection rows {len(a)} vs expected {len(e)}; {len(differing)} differing rows; '
                         f'first differing IDs {differing[:10]}; '
                         f"replacements match {actual['replacements']==expected['replacements']}; "
                         f"refused match {actual['refused']==expected['refused']}")
