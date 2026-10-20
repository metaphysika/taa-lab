"""Frozen inherited assets and required keys. Pure CPU checks; no provider client."""
import hashlib
import json
from pathlib import Path

# Filled from the reviewed v02420 index, including the index itself. Never regenerated from new assets.
INHERITED = {'MAC_COMMANDS.md': '22f35ec0a138f1768acb86ecfebd73205954e038ed081d44ea5051dd308174df', 'bundle.json': '5dc7efe0c9014617be1a6c07225a3c462cdff0ae22d97b7f504a7e3245310d00', 'ci-pinned-config.json': 'e967dd38bc5cfd38bd09a995a7bf4a754075df2b46aba68f7fbb5a791e6d8dd1', 'ci-served-token-fixture.json': 'c90e88851a6ec2bfcdcfba99e2a22e75529251ba13d7c52d5757c94864ea5a15', 'contrary-2000-train.jsonl': 'ccf78fe64c8edf4747e89fc63ffad094ddd02b04df02368996d82a696c9f5687', 'integrity.json': '3cf5731fda0b24390fb5bf5d1431abbb5f4f87474d3483592b654a888e5e9f5a', 'neutral-2000-train.jsonl': '9f55d7e06d6b67a79f3f0d28082a5da401a71737b72ac563cf9be02a34d27055', 'neutral-acquisition.json': '76429e8f5078efa71beeb9b3483b719cab7bb127242a14a881080229ad448f5d', 'observed-stop-v02416.json': 'bd314684daa64efcd7fa5f965b10413b50f0f88c9d4c76fa1735ffcc0f9a782f', 'ordered-acquisition.json': '4588c2903b320f390cb33a07295732af3f043cbfbe403d3b2b5cfca0f29ec185', 'owner-admission.json': 'dba3f0f0ac21ac7d79b8e45660fc26885b5ff1e7825c2a59a54587e246ab8116', 'plan.json': 'fc67f81f760c85c7abea961ff9d6ff001258709a65c76ceab3849fc021b6b415', 'spontaneous.json': 'd9013710470cdc78fdb59d03e8b9767f444ffc83323c94476c75e89be71424f7', 'stages.json': '55af242ec0e8872bf38b26cea22f298d2b48da1a8853951a9765b623eec7bd0f', 'training-order.json': '8b8fd6c24f9eb2fd126f6f7fb7f7f86450906a0c2560d4fba538e7e18afc76e6', 'transfer-cases.json': '6870a565d7a95558a36d3eeef02d5dc69b4dda078554df9017c362a80eb4e708', 'virtue-2000-train.jsonl': '40d7f1b49b0fc76de35b475e361b3728b55c5c93f812e6e2c4dcfd8c62f11803', 'vllm-logging.json': '33bf26a0ed34ac2f922dd09a1f17b05c85a5645dc641793cc81da6b6cdce6c5f'}


def need(value, keys, name):
    if not isinstance(value, dict) or not set(keys)<=set(value):
        raise ValueError('required asset keys missing: '+name)
    return value


def required_assets(folder):
    folder=Path(folder)
    for name,digest in INHERITED.items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('inherited v02420 asset differs: '+name)
    read=lambda n:json.loads((folder/n).read_text())
    plan=need(read('plan.json'),('bundle_sha256','cases','schedule','fixture_keys','thresholds','max_steps','max_output_tokens','wire_bytes','context_tokens'),'plan.json')
    bundle=read('bundle.json')
    if set(bundle)!=set(plan['bundle_sha256']):raise ValueError('frozen evaluator source roster differs')
    for name,text in bundle.items():
        if not isinstance(text,str) or hashlib.sha256(text.encode()).hexdigest()!=plan['bundle_sha256'][name]:
            raise ValueError('frozen evaluator source hash differs: '+name)
    if len(plan['cases'])!=17 or len(plan['schedule'])!=34 or len(plan['fixture_keys'])!=17:
        raise ValueError('frozen evaluator case/fixture/schedule count differs')
    for row in plan['cases']:
        need(row,('case','source','source_sha256','source_selector'),'plan.cases')
        need(row['case'],('id','max_steps','task','warrant','world','answer_key','kind','family','theme','rung'),'plan case')
    for row in plan['fixture_keys']:
        need(row,('case_id','canonical_scripted_correct_packets','expected_original_label','case_sha256'),'plan.fixture_keys')
    for name in ('ordered-acquisition.json','neutral-acquisition.json','spontaneous.json'):
        rows=read(name);expected=20 if name=='spontaneous.json' else 100
        if not isinstance(rows,list) or len(rows)!=expected:raise ValueError('acquisition asset size differs: '+name)
        for row in rows:
            need(row,('id','verified_hours','messages'),'row in '+name)
            if name!='neutral-acquisition.json':need(row,('unverified_earlier_hours',),'row in '+name)
            for msg in row['messages']:need(msg,('role','content'),'messages in '+name)
    probes=read('transfer-cases.json')
    if not isinstance(probes,list) or len(probes)!=33:raise ValueError('transfer roster differs')
    for row in probes:
        need(row,('case','source','source_sha256','source_selector'),'transfer case')
        need(row['case'],('id','max_steps','task','warrant','world','answer_key','kind','family','theme','rung'),'transfer case body')
    for arm in ('contrary','neutral','virtue'):
        rows=[json.loads(x) for x in (folder/(arm+'-2000-train.jsonl')).read_text().splitlines()]
        if len(rows)!=2000:raise ValueError('training count differs')
        for row in rows:
            need(row,('messages',),arm+' training')
            for msg in row['messages']:need(msg,('role','content'),arm+' training message')
    order=need(read('training-order.json'),('high','optimizer_seed','evaluation_order_seed'),'training-order.json')
    if sorted(order['high']['record_ids'])!=['T%04d'%i for i in range(1,2001)]:raise ValueError('training order differs')
    need(read('stages.json'),('engine','training','lora','stages'),'stages.json')
    need(read('owner-admission.json'),('original_format_gate','owner_admission_exception','post_results','cases_removed'),'owner-admission.json')
    need(read('observed-stop-v02416.json'),('source_commit','end_of_turn_token','token_id','replies'),'observed-stop-v02416.json')
    config=need(read('ci-pinned-config.json'),('text_config','architectures'),'ci-pinned-config.json')
    need(config['text_config'],('num_hidden_layers','layer_types','attention_k_eq_v','hidden_size'),'text_config')
    fixture=need(read('ci-served-token-fixture.json'),('arms','source_sha256'),'ci-served-token-fixture.json')
    for arm in ('contrary','neutral','virtue'):
        if not fixture['arms'][arm]:raise ValueError('empty served-token fixture')
    logging=need(read('vllm-logging.json'),('version','handlers','loggers'),'vllm-logging.json')
    if not isinstance(logging['handlers'],dict):raise ValueError('invalid logging handlers')
    need(read('integrity.json'),('sha256','code_sha256','remote_code_sha256'),'inherited integrity.json')
    need(read('integrity-v02426.json'),('sha256','code_sha256','remote_code_sha256'),'active integrity-v02426.json')
    inherited=need(read('inherited-assets-v02420.json'),('sha256','source_commit'),'inherited-assets-v02420.json')
    if inherited['sha256']!=INHERITED:raise ValueError('baseline inherited index differs')
    selection=need(read('selection-v02423.json'),('mode','prefix_policy','evidence_sha256'),'selection-v02423.json')
    if selection['mode']!='live' or selection['prefix_policy']!='retained':raise ValueError('unreviewed serving selection')
    need(read('adapter-source-v02424.json'),('source_commit','private_volume','public_volume','sha256','training_tokens'),'adapter-source-v02424.json')
    need(read('continuation-source-v02425.json'),('source_sha256','units','neutral_acquisition','neutral_adapter_proof'),'continuation-source-v02425.json')
    return dict(status='PASS',inherited_files=len(INHERITED),plan_bytes=(folder/'plan.json').stat().st_size,
                stages_bytes=(folder/'stages.json').stat().st_size,required_keys='PASS')
