"""FT1 plan-only entry point; no launcher and no backend imports."""
import json
import random
from exploratory.k2_kaggle import core

SEEDS = (247056, 247057, 247058)
MODELS = [('base', None)] + [(a, s) for a,n in [('1',2),('2',3),('2u',2),('3',3),('4',2)] for s in SEEDS[:n]]


def order(seed):
    indices=list(range(2000))
    random.Random(seed).shuffle(indices)
    return indices



def format_cases():
    # Read development-exposed IDs only; never score their conduct.
    from exploratory.k2_kaggle.core import manager_cases
    cases=manager_cases()
    return [c['id'] for k in ('W','U') for c in [x for x in cases if x['kind']==k][:4]]


def plan():
    return dict(approved=False, model='google/gemma-3-12b-it', recipe=core.RECIPE,
                memory_layout='exploratory.k2_kaggle.ft0b: fp16 tables, fp32 residual, chunked trained-position loss',
                training=[dict(arm=a,seed=s,order=order(s),steps=250,max_skipped=25) for a,s in MODELS[1:]],
                evaluation=[dict(arm=a,training_seed=s,case_index=i,branch=b,repeat=1,
                                 sampling_seed=248017+i*12,reply_cap=1024,max_steps=12)
                            for a,s in MODELS for i in range(48) for b in ('action','knowledge')],
                format_evaluation=[dict(arm=a,training_seed=s,case_id=cid,branch='format_only',repeat=1,
                       sampling_seed=348017+i*12,reply_cap=1024,max_steps=12)
                       for a,s in MODELS for i,cid in enumerate(format_cases())],
                protocol=dict(acquisition=40,development_k2={'W':4,'U':4},conduct='never score or report'),
                throughput=dict(min_generated_tokens=200,measure='tokens/seconds on first shard; recheck schedule'),
                turn_log_fields=['reply_tokens','cap_hit','malformed'],
                stop_authority='Compliance Director after executed wrongful entry')


def trained(skipped_steps):
    if len(set(skipped_steps)) != len(skipped_steps) or any(type(s)!=int or not 1<=s<=250 for s in skipped_steps):
        raise ValueError('invalid skipped steps')
    return len(skipped_steps)<=25


def split_loss(model, inputs, reason_mask, retain, num_items_in_batch=None):
    """FT0b objective unchanged; diagnostic sums detached, not two averaged objectives.

    reason_mask aligns labels and marks JSON reason value tokens only. Caller must
    derive it from tokenizer offsets on the final assistant string, not text search
    over the prompt. End token and JSON syntax belong to action.
    """
    import torch
    from exploratory.k2_kaggle import ft0b
    base, _, head = ft0b.layout(model)
    hidden = base.model(input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'],
                        use_cache=False, return_dict=True)[0]
    labels=inputs['labels'][...,1:].reshape(-1)
    selected=labels!=-100
    states=hidden[...,:-1,:].reshape(-1,hidden.shape[-1])[selected]
    targets=labels[selected]
    mask=reason_mask[...,1:].reshape(-1)[selected].bool()
    sums={'reason':0.,'action':0.}
    counts={'reason':0,'action':0}
    with torch.no_grad():
        for i in range(0,len(targets),128):
            losses=torch.nn.functional.cross_entropy(head(states[i:i+128]).float(),targets[i:i+128],reduction='none')
            for name, m in [('reason',mask[i:i+128]),('action',~mask[i:i+128])]:
                sums[name]+=losses[m].sum().item()
                counts[name]+=m.sum().item()
    retain(dict(event='loss_split',sums=sums,counts=counts))
    return ft0b.chunked_loss(hidden,head,inputs['labels'],num_items_in_batch)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--plan',action='store_true',required=True)
    p.parse_args()
    print(json.dumps(plan(),indent=2))
