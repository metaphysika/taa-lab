"""Exercise actual conventional proposal/SQL path on reconstructed case snapshots.
This is a same-state offline adjudication, never an episode or model call.
"""
from pathlib import Path
from copy import deepcopy as cp
import json,socket,sys
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parents[1]))
from conventional_gateway.world import World
from conventional_gateway.policy import Policy
from conventional_gateway.ledger import Ledger
from live_demo.evidence import encoded,digest


def main():
 spec=__import__('importlib.util',fromlist=['util']).spec_from_file_location('build_review',P/'build_review.py');m=__import__('importlib.util',fromlist=['util']).module_from_spec(spec);spec.loader.exec_module(m)
 socket.socket=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('offline only'))
 records=[]
 for p in sorted((P/'internal-adjudication').glob('*.json')):
  case=json.loads(p.read_bytes());s=case['stored_assessment']['pre_commit_state'];snap=m.sql_snapshot(s)
  # Initialize a fresh SQL host with no business rows, then hydrate EXACT
  # observed version histories and independent duty relations. No historical
  # conventional trajectory, source fixture or scenario rule is modified.
  definition=cp(s['world']);definition['records']={};definition['grants']={}
  host=World(definition);host.definition=cp(s['world']);host.policy=Policy(host.definition);host.ledger=Ledger(host.policy)
  with host.store.transaction():
   host.store.append('configuration','world',host.definition,relevant=False)
   for relation in ('records','grants','duties','allocations','orders','reports','notices','cases'):
    for rid,history in snap[relation].items():
     for payload in history:host.store.append(relation,rid,payload,relevant=False)
  host.store.clock(s['step'])
  actual=host.store.snapshot()
  for rel in ('records','grants','duties','allocations','orders','reports','notices','cases'):assert actual[rel]==snap[rel],rel
  assert actual['step']==snap['step']
  result=host.propose('A',case['call']['tool'],case['call']['args'])
  assert result['disposition']==case['replay']['conventional']['disposition'],'native conventional differs from detached policy'
  # Check notices and all business state channels of the reference assessment.
  assert [n['args'] for n in s['notices']]==__import__('comparators.observed_world',fromlist=['view']).view(case['replay']['native_pre_state'])['notices']
  records.append({'claim':'[Descriptive] Actual native conventional SQL proposal; no execute, no episode. Hydrated logical pre-state; own epoch/token namespace.','id':case['id'],'logical_pre_state_sha256':digest(encoded(snap)),'all_hydrated_relations_equal':True,'sql_pre_state':actual,'result':result})
  host.store._db.close()
 (P/'native-conventional-replays.json').write_text(json.dumps(records,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'native_SQL_proposals':len(records),'dispositions':[r['result']['disposition'] for r in records],'all_match_detached_policy':True}))
if __name__=='__main__':main()
