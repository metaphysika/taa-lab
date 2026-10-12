"""Unchanged B world/scoring with the owner-amended parser and full histories."""
import copy
import json
from formation.study_a import StudyAWorld, make_gate
from formation.study_b_v0227 import score, MECHANICAL, visible
from formation.study_b_parser_v0234 import parse_action

def replay(case,packets):
    world=StudyAWorld(case);gate=make_gate(case,world);attempts=[];terminal='fixture_exhausted'
    for packet in packets[:case['max_steps']]:
        if packet['kind']!='reply':
            terminal=packet['kind']
            if terminal not in MECHANICAL:raise ValueError('unknown mechanical fixture')
            break
        try:action=parse_action(packet['raw'])
        except ValueError as e:terminal=str(e);break
        if action['tool'] is None:terminal='agent_stop';break
        world.step+=1
        tool=action['tool'];args=action['args']
        try:result=gate.request(tool,args)
        except (TypeError,KeyError):result={'ok':False,'error_kind':'invalid_arguments'}
        attempts.append(dict(tool=tool,args=copy.deepcopy(args),result=result))
    else:
        if len(packets)>=case['max_steps']:terminal='step_limit'
    return {'score':score(case,world,attempts,terminal),'terminal_status':terminal,
            'attempts':attempts,'effects':world.effects,'final_world':world.observe()}


def history_for(case,packets):
    history=[]
    for turn in range(len(packets)+1):
        prior=replay(case,packets[:turn])
        if prior['terminal_status'] not in ('fixture_exhausted','step_limit'):break
        view=visible(case);view['world']=prior['final_world'];view['world']['step']=turn+1
        feedback={'task_context':view} if not history else {'last_tool_result':prior['attempts'][-1]['result'],'world':view['world']}
        history.append({'role':'user','content':json.dumps(feedback,ensure_ascii=False)})
        if turn<len(packets):
            if packets[turn]['kind']!='reply':break
            history.append({'role':'assistant','content':packets[turn]['raw']})
    return history
