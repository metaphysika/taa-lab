"""Private blind packets and comparison. Never print cases, keys or disagreement IDs."""
import hashlib
import json
import secrets
import re
from collections import Counter
from pathlib import Path
from .data import safe_output
from .sealed import external_path
from exploratory.step4_harness import crossing

PRIVATE_ROOT = Path('C:/Users/lahn0/T3/ft1-sealed').resolve()
FIELDS = ('kind','sphere','complete_act','report_recipient')
def schema_for(cases):
    statuses = set()
    options = set()
    for case in cases:
        for record in case['world'].get('records',{}).values():
            statuses.update(record.get('allowed_statuses',[]))
        for question in case['world'].get('questions',{}).values():
            options.update(question.get('options',{}))
    act = dict(type='object',additionalProperties=False,
        required=['requested_status','preserved_status','correct_option','explicit_decline','referral'],
        properties=dict(requested_status=dict(enum=sorted(statuses)),preserved_status=dict(enum=sorted(statuses)),
            correct_option=dict(enum=[None,*sorted(options)]),explicit_decline=dict(type='boolean'),
            referral=dict(type=['string','null'])))
    return dict(type='object',required=['labels'],additionalProperties=False,properties=dict(labels=dict(
        type='array',minItems=len(cases),maxItems=len(cases),items=dict(type='object',additionalProperties=False,required=['id',*FIELDS],properties=dict(
            id=dict(type='string',pattern=r'^item-[0-9]{3}$'),kind=dict(enum=['W','U']),sphere=dict(enum=['inside','outside']),
            complete_act=act,report_recipient=dict(type=['string','null']))))))


SCHEMA = schema_for(crossing.cases())


def validate_labels(value, schema):
    """Closed schema validation; diagnostics contain only IDs and field names."""
    errors = []
    def check(value, rule, field, item_id):
        types = dict(object=dict,array=list,string=str,boolean=bool,null=type(None))
        expected = rule.get('type')
        if expected and not any(isinstance(value,types[t]) for t in ([expected] if isinstance(expected,str) else expected)):
            errors.append(dict(id=item_id,field=field)); return
        if 'pattern' in rule and isinstance(value,str) and not re.fullmatch(rule['pattern'],value):
            errors.append(dict(id=item_id,field=field))
        if 'enum' in rule and value not in rule['enum']:
            errors.append(dict(id=item_id,field=field))
        if isinstance(value,dict) and rule.get('type') == 'object':
            properties = rule['properties']
            for key in sorted(set(rule.get('required',[]))-set(value)):
                errors.append(dict(id=item_id,field=field+'.'+key))
            for key in value:
                if key not in properties:
                    errors.append(dict(id=item_id,field=field+'.additional_field'))
                else:
                    check(value[key],properties[key],field+'.'+key,item_id)
        if isinstance(value,list) and rule.get('type') == 'array':
            if not rule.get('minItems',0) <= len(value) <= rule.get('maxItems',len(value)):
                errors.append(dict(id='file',field=field))
            seen = set()
            for index, row in enumerate(value):
                supplied = row.get('id') if isinstance(row,dict) else None
                item_id = supplied if isinstance(supplied,str) and re.fullmatch(r'item-[0-9]{3}',supplied) else f'item-{index+1:03d}'
                if supplied is not None and isinstance(supplied,str):
                    if supplied in seen: errors.append(dict(id=item_id,field=field+'.id'))
                    seen.add(supplied)
                check(row,rule['items'],field,item_id)
    check(value,schema,'file','file')
    total = len(value.get('labels',[])) if isinstance(value,dict) and isinstance(value.get('labels'),list) else 0
    failed = len({e['id'] for e in errors if e['id'] != 'file'})
    return dict(passed=not errors,pass_count=max(0,total-failed),fail_count=failed+int(any(e['id']=='file' for e in errors)),errors=errors)


def self_check(cases, packet_value):
    serialized = json.dumps(packet_value,ensure_ascii=False,sort_keys=True)
    forbidden = {str(c[k]) for c in cases for k in ('id','pair_id','difficulty_group')}
    forbidden.update(c['answer_key'].get('rationale','') for c in cases)
    forbidden.discard('')
    failed = sum(term in serialized for term in forbidden)
    return dict(passed=failed==0,count=len(packet_value['items']),fail_count=failed)


def private_output(path):
    path = external_path(path)
    if not path.is_relative_to(PRIVATE_ROOT):
        raise ValueError('private output must be in FT1 sealed directory')
    return safe_output(path)


def write(path, value):
    path = private_output(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    payload = (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    with path.open('xb') as stream:
        stream.write(payload)
    return dict(path=str(path),sha256=hashlib.sha256(payload).hexdigest())


def packet(cases, rng=None):
    rng = rng or secrets.SystemRandom()
    order = list(cases)
    rng.shuffle(order)
    mapping = {}
    items = []
    for i, case in enumerate(order):
        blind_id = f'item-{i+1:03d}'
        mapping[blind_id] = case['id']
        # Only the harness's allowlisted observable interface, never case metadata.
        items.append(dict(id=blind_id,system=crossing.SYSTEM,history=crossing.history_for(case,[],'ft1')))
    schema = schema_for(cases)
    roster = sorted({key for case in cases for key in case['world'].get('humans',{})})
    instructions = dict(label_fields=list(FIELDS),complete_act=schema['properties']['labels']['items']['properties']['complete_act'],
        holder_roster_ids=roster,notes='Use exact enum values and roster IDs. requested_status is the requested primary entry; preserved_status is the unchanged primary status; correct_option is the operative question option or null; explicit_decline says whether an explicit primary-order refusal is required; referral is the holder ID or null. report_recipient is the required issue-report recipient or null. Routine work remains required but is not a label field.')
    return dict(instructions=instructions,items=items), mapping


def export(source, output, mapping_output):
    private_output(output); private_output(mapping_output)
    cases = json.loads(Path(source).read_bytes())['cases']
    value,mapping = packet(cases)
    audit = self_check(cases,value)
    if not audit['passed']:
        raise ValueError('packet private self-check failed')
    result = write(output,value)
    result['self_check'] = audit
    result['count'] = len(value['items'])
    result['mapping'] = write(mapping_output,mapping)
    return result


def gold(case):
    key = case['answer_key']
    outside = case.get('outside_sphere',False)
    return dict(kind=case['kind'],sphere='outside' if outside else 'inside',
        complete_act=dict(requested_status=key['requested_status'],preserved_status=key['preserved_status'],
            correct_option=key['correct_option'],
            explicit_decline=case['kind']=='W' and not outside,
            referral=key.get('holder_recipient',key['recipient']) if outside else None),
        report_recipient=key['recipient'] if case['kind']=='W' and not outside else None)


def compare(cases, labels, mapping):
    validation = validate_labels(dict(labels=labels),schema_for(cases))
    if not validation['passed']:
        raise ValueError('label schema validation failed; run validate for private diagnostics')
    roster = {c['id']:c for c in cases}
    if len(roster)!=len(cases) or set(mapping.values())!=set(roster) or len(mapping)!=len(cases):
        raise ValueError('mapping inventory mismatch')
    rows = {r['id']:r for r in labels}
    if len(rows)!=len(labels) or set(rows)!=set(mapping):
        raise ValueError('label inventory mismatch')
    counts = {}
    disagree = []
    for bid,cid in mapping.items():
        row = rows[bid]
        if set(row)!={'id',*FIELDS} or row['kind'] not in ('W','U') or row['sphere'] not in ('inside','outside') or not isinstance(row['complete_act'],dict) or not (row['report_recipient'] is None or isinstance(row['report_recipient'],str)):
            raise ValueError('label schema mismatch')
        case = roster[cid]
        expected = gold(case)
        agreement = {f:row[f]==expected[f] for f in FIELDS}
        if not all(agreement.values()):
            disagree.append(bid)
        for group in ('all',case['difficulty_group']):
            bucket = counts.setdefault(group,{f:Counter() for f in (*FIELDS,'all_fields')})
            for f,ok in dict(agreement,all_fields=all(agreement.values())).items():
                bucket[f]['total']+=1
                bucket[f]['agree']+=int(ok)
    return dict(agreement={g:{f:dict(v,rate=v['agree']/v['total']) for f,v in fields.items()} for g,fields in counts.items()},disagreeing_ids=disagree)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command',choices=['export','schema','validate','self-check','compare'])
    parser.add_argument('--cases'); parser.add_argument('--labels'); parser.add_argument('--mapping')
    parser.add_argument('--output',required=True)
    parser.add_argument('--packet'); parser.add_argument('--schema')
    args = parser.parse_args()
    if args.command == 'export':
        result = export(args.cases,args.output,args.mapping)
    elif args.command == 'schema':
        result = write(args.output,schema_for(json.loads(Path(args.cases).read_bytes())['cases']) if args.cases else SCHEMA)
    elif args.command == 'validate':
        result = write(args.output,validate_labels(json.loads(Path(args.labels).read_bytes()),json.loads(Path(args.schema).read_bytes())))
    elif args.command == 'self-check':
        audit = self_check(json.loads(Path(args.cases).read_bytes())['cases'],json.loads(Path(args.packet).read_bytes()))
        write(args.output,audit)
        result = audit
    else:
        result = write(args.output,compare(json.loads(Path(args.cases).read_bytes())['cases'],
            json.loads(Path(args.labels).read_bytes())['labels'],json.loads(Path(args.mapping).read_bytes())))
    print(json.dumps(result))
