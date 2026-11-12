"""Injected offline FT1 training mode. No model loader, backend, or launch."""
import json
import math
from . import plan
from exploratory.k2_kaggle import core, ft0b


def record(tokenizer, row):
    text=row['messages'][-1]['content']
    obj=json.loads(text)
    encoded=tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)
    prefix=core.prompt(tokenizer,row['messages'][:-1])
    start=text.index('"reason":')+len('"reason":')+1
    end=start+len(json.dumps(obj['reason'],ensure_ascii=False,separators=(',',':')))-2
    flags=[]
    for lo,hi in encoded['offset_mapping']:
        # Boundary tokens with any reason-content characters count as reason;
        # quotes/syntax alone and an empty reason count as action. No token is dropped.
        flags.append(start<end and lo<end and hi>start)
    content=list(encoded['input_ids'])+[core.end_token(tokenizer)]
    if len(prefix)>384 or len(content)>640 or len(prefix+content)>1024:
        raise ValueError('No truncation: training token limits')
    return dict(input_ids=prefix+content,attention_mask=[1]*len(prefix+content),
                labels=[-100]*len(prefix)+content), [False]*len(prefix)+flags+[False]


def train(model, tokenizer, rows, arm, seed, retain):
    """Caller supplies locally prepared NF4 LoRA model; this is not launch approval."""
    import torch
    if (arm,seed) not in plan.MODELS[1:] or len(rows)!=2000:
        raise ValueError('unplanned training cell')
    ft0b.check_internals()
    ft0b.tables(model,'after_cast',retain,cast=True)
    records=[record(tokenizer,r) for r in rows]
    ordered=[records[i] for i in plan.order(seed)]
    torch.manual_seed(seed)
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=core.RECIPE['lr'],weight_decay=0)
    scaler=torch.amp.GradScaler('cuda')
    skipped=[]
    model.train()
    for step in range(250):
        optimizer.zero_grad(set_to_none=True)
        batch=ordered[step*8:(step+1)*8]
        denominator=sum(sum(y!=-100 for y in r['labels'][1:]) for r,_ in batch)
        values=[]
        for r,mask in batch:
            inputs={k:torch.tensor([v],device='cuda:0') for k,v in r.items()}
            with torch.autocast('cuda',dtype=torch.float16):
                loss=plan.split_loss(model,inputs,torch.tensor([mask],device='cuda:0'),retain,denominator)
            values.append(loss.detach().item())
            scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        finite=all(math.isfinite(v) for v in values) and all(p.grad is None or torch.isfinite(p.grad).all().item() for p in params)
        if finite:
            torch.nn.utils.clip_grad_norm_(params,1.)
            scaler.step(optimizer)
        else:
            skipped.append(step+1)
        scaler.update()
        retain(dict(event='optimizer_step',step=step+1,skipped=not finite,loss=sum(values)))
        if len(skipped)>25:
            retain(dict(event='not_trained',skipped_steps=skipped))
            return False
    retain(dict(event='training_complete',steps=250,skipped_steps=skipped))
    return True
