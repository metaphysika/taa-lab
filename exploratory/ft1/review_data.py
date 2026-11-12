"""Reproduce public TRAINING-ONLY review samples and counts with a character stub."""
import json
import statistics
from collections import Counter
from . import data

SAMPLES=(3,614,829,1100,1101,1306,1507,1528,1561,1602)

def render():
    rows,manifest=data.build(data.CharacterCounter())
    spans=[r['trained_tokens'] for r in rows['3']]
    reason_spans=[data.CharacterCounter().trained(json.loads(r['messages'][-1]['content'])['reason']) for r in rows['3']]
    text=['# FT1 training-only review material','',
          'Reproduce with python -m exploratory.ft1.review_data --output NEW_PATH.',
          'Counts use the character stub (~one token per four characters), not the Gemma tokenizer.',
          'No test generator is called by this report.',
          'Prospective limits: trained <=640 and total <=1024. Prompt length is descriptive; there is no separate prompt cap.','',
          f"Arm 3 trained tokens min/median/max: {min(spans)}/{statistics.median(spans):g}/{max(spans)}.",
          f"Reason content stub tokens min/median/max: {min(reason_spans)}/{statistics.median(reason_spans):g}/{max(reason_spans)}.",
          f"Maximum prompt tokens: {max(r['prompt_tokens'] for r in rows['3'])}.",
          f"Arm 2 minus arm 3 aggregate trained-token difference: {sum(r['difference'] for r in manifest['token_table'])}.",'',
          '## Theme × evidence × record-type counts','',
          'Arms 2, 2u and 3 share the following table.','',
          '| Theme | Evidence | Wrongful | Lawful | Sphere | Recipient | Correction |',
          '|---|---|---:|---:|---:|---:|---:|']
    counts=Counter((r['theme'],r['evidence_type'],r['type']) for r in rows['3'])
    for theme in data.THEMES:
        for evidence in data.EVIDENCE[:4]:
            text.append('| '+theme+' | '+evidence+' | '+' | '.join(str(counts[theme,evidence,k]) for k in ('wrongful','lawful','sphere','recipient','correction'))+' |')
    text+=['','Arm 1 refusal and arm 4 routine counts use the same theme/evidence pool:','',
           '| Theme | Evidence | Arm 1 refusal | Arm 4 routine |','|---|---|---:|---:|']
    for theme in data.THEMES:
        for evidence in data.EVIDENCE[:4]:
            cc=[sum(r['theme']==theme and r['evidence_type']==evidence for r in rows[a]) for a in ('1','4')]
            text.append(f'| {theme} | {evidence} | {cc[0]} | {cc[1]} |')
    text+=['','Held-out acquisition: 40 decision points across all ten themes, using supporting_receipt only.',
           'No training arm contains that theme × evidence combination.','']
    for arm in data.ARMS:
        text+=['## Ten samples: arm '+arm,'','Full compact prompts, action-only histories and trained targets follow.','']
        for index in SAMPLES:
            text+=[chr(96)*3+'json',json.dumps(rows[arm][index],ensure_ascii=False,indent=2),chr(96)*3,'']
    return '\n'.join(text)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args()
    path=data.safe_output(a.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(render(),encoding='utf-8')
