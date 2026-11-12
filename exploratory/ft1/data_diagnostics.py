"""Complete FT1 data diagnostics. Failure reports never discard later records."""
import statistics
from . import data


class DataBuildError(ValueError):
    def __init__(self,report):
        self.report=report
        super().__init__('FT1 data refused: '+str(len(report['failures']))+' record failures; see report')


def distribution(values):
    values=[v for v in values if v is not None]
    return dict(count=len(values),min=min(values) if values else None,
                median=statistics.median(values) if values else None,max=max(values) if values else None)


def generate(counter,partition='train',count=2000,arms=data.ARMS):
    if partition=='train' and count!=2000: raise ValueError('training requires 2000 records')
    output={a:[] for a in data.ARMS}; measurements=[]; table=[]; balance=0
    def emit(arm,mm,target,meta,extra=()):
        failures=list(extra); p=t=None
        try:
            data.validate_roles(mm+[dict(role='assistant',content=data.dump(target))])
            render=getattr(counter,'render_record',None)
            if render: render(mm+[dict(role='assistant',content=data.dump(target))])
            p=counter.prompt(mm)
        except Exception as exc: failures.append('template: '+str(exc))
        try: t=counter.trained(data.dump(target))
        except Exception as exc: failures.append('trained encoding: '+str(exc))
        if p is not None and p>384: failures.append('prompt exceeds 384')
        if t is not None and t>640: failures.append('trained exceeds 640')
        total=p+t if p is not None and t is not None else None
        if total is not None and total>1024: failures.append('total exceeds 1024')
        row=dict(id=meta['id'],arm=arm,partition=partition,prompt=p,trained=t,total=total,failures=failures)
        measurements.append(row)
        output[arm].append(dict(meta,messages=mm+[dict(role='assistant',content=data.dump(target))],
                                prompt_tokens=p,trained_tokens=t))
        return row
    for i in range(count):
        kind=data.MIX[i] if partition=='train' else ('wrongful','lawful','recipient','sphere','correction')[i%5]
        index=i if partition=='train' else i*43+i//4
        if partition!='train' and kind=='sphere': index=2000+(i//5)*22+(i//5)%2
        mm,target,reasons,lines,meta=data.card(index,kind,partition)
        if '2' in arms or '3' in arms:
            error=[]
            try: reason,rest,t2,t3=data.choose(counter,mm,target,reasons,lines,balance,strict=False)
            except Exception as exc:
                error=['matching: '+str(exc)]; reason=reasons[0]; rest='\n'.join(l for l in lines if not data.BANNED.search(l))
            pair={}
            for arm,value in [('2',dict(target,reason=rest)),('3',dict(target,reason=reason))]:
                if arm in arms: pair[arm]=emit(arm,mm,value,meta,error)
            if set(pair)=={'2','3'}:
                a,b=pair['2']['trained'],pair['3']['trained']
                if a is not None and b is not None:
                    delta=a-b; balance+=delta
                    table.append(dict(id=meta['id'],arm2=a,arm3=b,difference=delta))
                    if abs(delta)>max(8,.05*b):
                        for r in pair.values(): r['failures'].append('per-record matching gate')
                    try:
                        if counter.trained(reason)>counter.trained('\n'.join(l for l in lines if not data.BANNED.search(l))):
                            pair['3']['failures'].append('reason exceeds restatable material')
                    except Exception as exc: pair['3']['failures'].append('restatable encoding: '+str(exc))
        if '2u' in arms: emit('2u',mm,target,meta)
        for arm,mode in [('1','refusal'),('4','routine')]:
            if arm in arms:
                cm,ct,_,_,cmta=data.card(index,mode,partition+'-'+arm)
                emit(arm,cm,ct,cmta)
    aggregate=[]
    if table:
        a,b=(sum(r[k] for r in table) for k in ('arm2','arm3'))
        if abs(a-b)>.02*b: aggregate.append('aggregate matching exceeds 2%')
    else: a=b=0
    report=dict(rows=measurements,failures=[r for r in measurements if r['failures']],
                aggregate_failures=aggregate,distributions={arm:{k:distribution(r[k] for r in measurements if r['arm']==arm)
                    for k in ('prompt','trained','total')} for arm in arms},
                matching=dict(per_record=table,difference=distribution(r['difference'] for r in table),
                              arm2_total=a,arm3_total=b,aggregate_difference=a-b),
                tokenizer_verified=isinstance(counter,data.Counter))
    report['passed']=not report['failures'] and not aggregate and all(len(output[a])==count for a in arms)
    manifest=dict(partition=partition,token_table=table,totals={a:sum(r['trained_tokens'] or 0 for r in rr) for a,rr in output.items()},
                  tokenizer_verified=isinstance(counter,data.Counter),
                  record_tokens={a:[dict(id=r['id'],prompt=r['prompt_tokens'],trained=r['trained_tokens']) for r in rr] for a,rr in output.items()})
    return output,manifest,report


def prepare(counter):
    output,manifest,train=generate(counter)
    probes,_,probe=generate(counter,'heldout',40,('1','2u','4'))
    report=dict(passed=train['passed'] and probe['passed'],tokenizer_verified=isinstance(counter,data.Counter),
                training=train,probes=probe,record_count=len(train['rows'])+len(probe['rows']),
                failures=train['failures']+probe['failures'],
                aggregate_failures=train['aggregate_failures']+probe['aggregate_failures'])
    report['unique_records']={a:len({r['id'] for r in rows}) for a,rows in output.items()}
    report['template_records']=dict(training=10000,probes=120)
    if any(n!=2000 for n in report['unique_records'].values()):
        report['aggregate_failures'].append('training uniqueness gate')
        report['passed']=False
    return output,probes,manifest,report
