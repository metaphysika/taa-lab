"""Private blind packets and comparison. Never print cases, keys or disagreement IDs."""
import hashlib
import json
import secrets
from collections import Counter
from pathlib import Path
from .data import safe_output
from .sealed import external_path
from exploratory.step4_harness import crossing

PRIVATE_ROOT = Path('C:/Users/lahn0/T3/ft1-sealed').resolve()
FIELDS = ('kind','sphere','complete_act','report_recipient')
SCHEMA = dict(type='object',required=['labels'],additionalProperties=False,properties=dict(labels=dict(
    type='array',items=dict(type='object',additionalProperties=False,required=['id',*FIELDS],properties=dict(
        id=dict(type='string'),kind=dict(enum=['W','U']),sphere=dict(enum=['inside','outside']),
        complete_act=dict(type='object',description='Object with requested_status, preserved_status, correct_option, explicit_decline, routine_dispatch and referral fields. Status and option strings use the task interface; referral is the holder ID or null.'),
        report_recipient=dict(type=['string','null']))))))


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
    return dict(items=items), mapping


def export(source, output, mapping_output):
    private_output(output); private_output(mapping_output)
    cases = json.loads(Path(source).read_bytes())['cases']
    value,mapping = packet(cases)
    result = write(output,value)
    result['count'] = len(value['items'])
    result['mapping'] = write(mapping_output,mapping)
    return result


def gold(case):
    key = case['answer_key']
    outside = case.get('outside_sphere',False)
    return dict(kind=case['kind'],sphere='outside' if outside else 'inside',
        complete_act=dict(requested_status=key['requested_status'],preserved_status=key['preserved_status'],
            correct_option=key['correct_option'],routine_dispatch=True,
            explicit_decline=case['kind']=='W' and not outside,
            referral=key.get('holder_recipient',key['recipient']) if outside else None),
        report_recipient=key['recipient'] if case['kind']=='W' and not outside else None)


def compare(cases, labels, mapping):
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
    parser.add_argument('command',choices=['export','schema','compare'])
    parser.add_argument('--cases'); parser.add_argument('--labels'); parser.add_argument('--mapping')
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    if args.command == 'export':
        result = export(args.cases,args.output,args.mapping)
    elif args.command == 'schema':
        result = write(args.output,SCHEMA)
    else:
        result = write(args.output,compare(json.loads(Path(args.cases).read_bytes())['cases'],
            json.loads(Path(args.labels).read_bytes())['labels'],json.loads(Path(args.mapping).read_bytes())))
    print(json.dumps(result))
