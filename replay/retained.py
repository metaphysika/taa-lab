"""Read retained state deltas only; never execute policy, tools or an oracle."""
from copy import deepcopy
import json


def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)


def present(mapping,key):
    return {'present':True,'value':mapping[key]} if key in mapping else {'present':False}


def apply(value,delta):
    if 'entries' in delta:
        if type(value) is not dict:raise ValueError('dictionary delta on another type')
        result=deepcopy(value)
        for key,row in delta['entries'].items():
            if canonical(present(value,key))!=canonical(row['before']):raise ValueError('retained dictionary before-value mismatch')
            if row['after']['present']:result[key]=deepcopy(row['after']['value'])
            else:result.pop(key,None)
        return result
    if delta.get('prefix_retained') is True:
        if type(value) is not list or len(value)!=delta['before_length']:raise ValueError('retained append prefix length mismatch')
        result=value+deepcopy(delta['appended'])
        if len(result)!=delta['after_length']:raise ValueError('retained append ending length mismatch')
        return result
    if canonical(value)!=canonical(delta['before']):raise ValueError('retained scalar before-value mismatch')
    return deepcopy(delta['after'])


def transitions(episode):
    initial=episode['actual_initial'];channels=deepcopy(initial['channels']);log=deepcopy(initial['event_log'])
    for t in episode['actual_transitions']:
        before=deepcopy(channels['revision'])
        for key,delta in t['actual_channels'].items():
            current=channels.get(key,{'present':False})
            if 'before' in delta and type(delta['before']) is dict and set(delta['before'])<= {'present','value'} and 'present' in delta['before']:
                if canonical(current)!=canonical(delta['before']):raise ValueError('retained channel presence mismatch')
                channels[key]=deepcopy(delta['after'])
            else:
                if not current['present']:raise ValueError('delta without retained channel')
                channels[key]={'present':True,'value':apply(current['value'],delta)}
        previous_log=log;log=apply(log,t['actual_event_log'])
        prefix=0
        while prefix<min(len(previous_log),len(log)) and canonical(previous_log[prefix])==canonical(log[prefix]):prefix+=1
        if channels['step']!={'present':True,'value':t['step']}:raise ValueError('retained transition step mismatch')
        yield dict(t,before_revision=before,after_revision=deepcopy(channels['revision']),log_change={'unchanged_prefix_count':prefix,'before_tail':previous_log[prefix:],'after_tail':log[prefix:]})


def render(episode,rows,detail,esc,duty_table):
    arm=episode['arm'];parts=['<section class="arm" data-column="'+esc(arm)+'"><h2>'+esc({'conventional':'independently implemented conventional arm','tracegrant':'TraceGrant reconstruction with fixed W0 contracts and documented adaptations'}.get(arm,arm))+'</h2>',
        '<p class="notice">Actual retained state changes and event rows. Archive checksums are verified; HMAC authentication and an independent native ending checkpoint are not verified.</p>',
        detail('Initial actual state channels and event rows',episode['actual_initial']),
        detail('Retained protocol metrics — keyed metrics are conditional',episode['metrics']),
        detail('Committed acts disallowed by the reference policy — post-v0 development only',episode['reference_policy_committed_acts'])]
    actions=iter(rows);consumed=0
    for index,t in enumerate(transitions(episode)):
        phase=t['phase'];parts+=['<article class="row" data-step="'+str(t['step'])+'"><span class="tag">observed step '+str(t['step'])+' · transition '+str(index)+'</span><h3>'+esc(phase)+'</h3>',detail('Observed revision before / after',{'before':t['before_revision'],'after':t['after_revision']})]
        if phase in ('proposal','agent_withholding','execution'):
            try:row=next(actions)
            except StopIteration:raise ValueError('more actual actions than retained observations') from None
            o=row['observation'];consumed+=1
            if row['step']!=t['step'] or o['actor']!=t['inputs']['actor'] or (o['kind']=='execution')!=(phase=='execution'):raise ValueError('actual action / observation mismatch')
            if phase!='execution' and (phase=='agent_withholding')!=o['withheld']:raise ValueError('withholding / actual phase mismatch')
            if phase!='execution' and (o['tool']!=t['inputs']['tool'] or canonical(o['args'])!=canonical(t['inputs']['arguments'])):raise ValueError('actual proposal arguments mismatch')
            parts.append(detail('Agent input and proposal origin',{'actor':o['actor'],'tool':o['tool'],'arguments':o['args'],'origin':o['key'],'retained_origin':json.loads(o['key'])[0] if o['key'] is not None else 'not bound to a proposal origin'},True))
            if phase=='agent_withholding':parts.append('<p>Agent withheld this request; the gateway was not called and no token was issued.</p>')
            if 'checks' in o['result']:parts.append(detail('Gateway checks — rules, versioned facts and dispositions',o['result']['checks'],True))
            parts.append(detail('Returned gateway result — checked by the common state audits',o['result']))
            parts.append(detail('Observed record effects',{'receipted_commit':o['committed'],'effects':o['effects']}))
            parts.append(detail('Frozen key / context assessment',{k:o[k] for k in ('semantic_label','label_source','context')}))
        else:parts.append(detail('Host inputs; events precede the duty phase',t['inputs']))
        parts.append(detail('Actual token, record, duty, report, notice and receipt changes',t['actual_channels'],bool(t['actual_channels'])))
        parts.append(detail('Actual projected log changes — ending checkpoints may be replaced; no oracle obligation is inferred as delivery',t['log_change']))
        parts.append('</article>')
    if consumed!=len(rows):raise ValueError('missing actual action transitions')
    parts.extend([detail('Final actual world',episode['final_world']),'<h3>Final common external oracle duty board — normative, not the arm’s internal ledger</h3>'+duty_table(episode['oracle_board']),
        '<p>Actual report-delivery aggregate: '+str(episode['metrics']['reports_delivered'])+'. Deliveries are retained artifacts, not inferred from this oracle board.</p>',detail('Common actual-state audits',episode['assertions']),'</section>'])
    return ''.join(parts)
