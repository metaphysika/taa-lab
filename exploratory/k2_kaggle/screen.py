"""K2b screen plumbing. No model loading or remote operations on import."""
from copy import deepcopy
from collections import Counter
import hashlib
import json
from . import core
from exploratory.step4_harness import l2, l1, k1, crossing as c

LONG_INPUT_TOKENS = 8000  # above the longest retained requests: 12B K2 3518, 31B L2 4829
L2_SAMPLING = dict(do_sample=True, temperature=1.0, top_k=64, top_p=0.95)


def plan():
    rows=[]
    for case in l2.cases():
        rows.append(dict(case_id=case['id'], group='W' if case['id'].endswith('W') else 'U'))
        rows.append(dict(case_id=case['id'], group='knowledge'))
    return rows


def run(generate, retain, check_deadline=lambda: None):
    roster={x['id']:x for x in l2.cases()}; rows=[]; sequence=0
    for cell in plan():
        check_deadline()
        def call(system, history, cap):
            nonlocal sequence
            seed=248017+sequence; sequence+=1
            return generate(system,history,cap,seed,'base')
        case=deepcopy(roster[cell['case_id']])
        if cell['group']=='knowledge':
            lines=case['task'].splitlines()
            lines=[k1.WORDINGS[0]+' The primary act is entering PRIMARY as '+case['answer_key']['requested_status']+'.']+[
                x for x in lines[1:] if not x.startswith(('Issuer:','Authenticated issuer:','If you identify a problem'))]
            case['task']='\n'.join(lines)
            system=c.SYSTEM+'\nFor this call only, answer using {"tool":"answer","args":{"answer":"yes"|"no"}}. Do not execute actions.'
            try:
                raw=call(system,c.history_for(case,[],'l2'),1024)
                row=dict(terminal_status='single_turn', raw=raw, answer=k1.answer(raw))
            except Exception as exc:
                row=dict(terminal_status='generation_failed',error=type(exc).__name__)
        else:
            row=l1.action_episode(l2.rewrite(case,'manager'),call,stop=cell['group']=='W')
        row=dict(cell,**row); rows.append(row); retain(dict(event='l2_screen_cell',**row))
    return rows


def summary(rows):
    result={}
    for group in ('W','U','knowledge'):
        selected=[r for r in rows if r['group']==group]
        planned=24 if group=='knowledge' else 12
        roster={x['id']:x for x in l2.cases()}
        from exploratory.step4_harness.crossing_analysis import classify
        categories=Counter()
        for row in selected:
            if group=='knowledge':
                value=row.get('answer')
                category='unknown' if value not in ('yes','no') else 'correct' if value==roster[row['case_id']]['answer_key']['knowledge_answer'] else 'incorrect'
            else: category=classify(roster[row['case_id']],row)
            categories[category]+=1
        unknown=categories['unknown']
        result[group]=dict(planned=planned, attempted=len(selected), unknown=planned-len(selected)+unknown,
                           classes=dict(categories), terminal_statuses=dict(Counter(r['terminal_status'] for r in selected)),
                           answers=dict(Counter(r.get('answer') for r in selected)) if group=='knowledge' else {})
    return result


def probe_messages(tokenizer, model):
    ready=[dict(role='user',content='Reply with READY.')]
    neutral=[dict(role='system',content='Answer with one JSON object and nothing else.'),dict(role='user',content='Return only this tool-style JSON object: {"tool":"catalog","args":{"item":"blue pebble","count":3}}')]
    # Assistant turn in the history, as in a real episode: shows how this candidate's template renders it.
    second=neutral+[dict(role='assistant',content='{"tool":"catalog","args":{"item":"blue pebble","count":3}}'),dict(role='user',content='Now return the same object with count 4.')]
    prefix='Remember the neutral marker: silver acorn.\n'
    suffix='\nWhat marker did the opening line give? Return only a JSON object with key marker.'
    count=LONG_INPUT_TOKENS
    while True:
        long=[dict(role='user',content=prefix+'Neutral archive entry. '*count+suffix)]
        size=len(core.prompt(tokenizer,long,model=model))
        if size<=LONG_INPUT_TOKENS: break
        count=int(count*LONG_INPUT_TOKENS/size*.99)
    # A short "long" probe would report a misleadingly small memory peak, so fail instead.
    if size<LONG_INPUT_TOKENS*.9: raise ValueError('long-context probe too short: '+str(size))
    return [('ready',ready),('json',neutral),('second_turn',second),('long_context',long)]


def format_audit(rows):
    counts=Counter()
    for row in rows:
        if row.get('event')=='native_tokens':
            counts['replies']+=1
            counts['stop_token']+=bool(row.get('stopped_on_turn') or row.get('stopped_on_eos'))
            counts['stopped_on_eos']+=bool(row.get('stopped_on_eos'))
            counts['hit_cap']+=bool(row.get('hit_cap'))
            reply=row.get('decoded_reply','')
            counts['special_tokens_in_reply']+=('<|' in reply or '|>' in reply)
            counts['leading_thought']+=reply.lstrip().startswith('thought')
        if row.get('event') in ('cell','l2_screen_cell'):
            counts['generation_failures']+=row.get('terminal_status')=='generation_failed'
            counts['parser_failures']+=(row.get('terminal_status')=='malformed' or (row.get('group')=='knowledge' and row.get('terminal_status')=='single_turn' and row.get('answer') is None))
    return dict(counts)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(__doc__); parser.add_argument('events')
    args=parser.parse_args()
    print(json.dumps(format_audit([json.loads(x) for x in open(args.events,encoding='utf8')]),indent=2))
