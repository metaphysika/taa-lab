"""Declared native-envelope fixtures only: no credentials, no network, no models."""
import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from formation.evaluation_runner_v0218 import execute_cell
from formation.evaluation_transport_v0218 import QuotaRecorder,GroqSlots,make_client
from formation.study_a import load_cases
from tests.test_formation_evaluation_v0218 import Response

if __name__=='__main__':
    output=ROOT/'results/2026-10-10 v0.21.8 scripted-none r1 native adapter verify'
    output.mkdir(parents=True,exist_ok=False)
    plan=json.loads((ROOT/'studies/formation-study-a-evaluation-plan-v0217.json').read_text())
    prices=json.loads((ROOT/plan['price_file']).read_text())['models']
    fixtures=[]
    for path in ('studies/formation-study-a-fixtures-v0213.json','studies/formation-study-a-pressure-fixtures-v0215.json'):
        fixtures+=json.loads((ROOT/path).read_text())['fixtures']
    rows=[];mocked=0
    with tempfile.TemporaryDirectory() as temporary:
        temp=Path(temporary)
        for item in plan['models']:
            model,provider=item['model'],item['provider'];clock=[1000.0]
            quota=GroqSlots(temp/'groq-rate.json',now=lambda:clock[0]) if provider=='groq' else None
            rec=QuotaRecorder(temp/(provider+model.replace('/','_')+'.jsonl'),prices,model,
                max_logical=288,max_attempts=288,max_dollars=8,quota=quota)
            client=make_client(model,provider,rec,quota)
            for cell in (c for c in plan['cells'] if c['model']==model and c['repeat']==1):
                packets=next(f['packets'] for f in fixtures if f['case_id']==cell['case_id'] and f['name']=='required_conduct')
                raws=iter(p['raw'] for p in packets)
                def send(*args,**kwargs):
                    clock[0]+=61
                    return Response(model,provider,next(raws))
                keys={name:'declared-fixture-only' for name in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','GROQ_API_KEY')}
                with patch.dict('os.environ',keys),patch('urllib.request.urlopen',side_effect=send) as transport:
                    case=load_cases([ROOT/cell['path']])[0]
                    result,status=execute_cell(cell,case,client,rec,temp/(model.replace('/','_')+cell['case_id']+'.json'))
                    mocked+=transport.call_count
                assert status=='complete' and result['score']['outcome']=='correct'
                result.update(phase='DECLARED NATIVE-RESPONSE FIXTURE; no model observation',model_calls=0,api_cost_dollars=0)
                (output/(model.replace('/','_')+'-'+cell['case_id']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
                rows.append({'model_transport':model,'case':cell['case_id'],'passed':True})
    summary={'fixture_episodes':len(rows),'passed':len(rows),'mocked_requests':mocked,'actual_network_requests':0,'model_calls':0,'api_cost_dollars':0,'declared_fixtures':rows}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('120/120 declared native fixtures passed; actual model calls 0; API cost $0')
