"""Free regression checks for pressure delivery and preserved moral distinctions."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from formation.clients import OpenAIChat
from formation.study_a import ROOT, load_cases, replay_episode
from formation.study_a_pressure import pressure_view, replay_pressure
from scripts.formation_study_a_pressure_scripted import MANIFEST, run_pressure_fixtures

class PressureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text())
        cls.cases={c['id']:c for c in load_cases([ROOT/p for p in cls.manifest['scenario_paths']])}
        cls.baselines={c['id']:c for c in load_cases()}
        cls.fixtures=json.loads((ROOT/cls.manifest['fixture_file']).read_text())['fixtures']

    def good(self,cid):
        return next(f['packets'] for f in self.fixtures if f['case_id']==cid and f['name']=='required_conduct')

    def test_preserved_baseline_evidence_authority_and_pairing(self):
        self.assertEqual(len(self.cases),12)
        self.assertEqual(len(self.baselines),12)
        for cid,c in self.cases.items():
            b=self.baselines[c['baseline_case_id']]
            self.assertEqual(c['baseline_sha256'],hashlib.sha256((ROOT/'scenarios/formation'/ (b['id']+'.json')).read_bytes()).hexdigest())
            self.assertEqual(c['warrant'],b['warrant'])
            self.assertEqual(c['world']['records'],b['world']['records'])
            self.assertEqual(c['world']['questions'],b['world']['questions'])
            for k in ('preserve_records','unresolved_questions','withheld_shipments'):
                self.assertEqual(c['requirements'][k],b['requirements'][k])
            self.assertEqual(c['requirements']['effects'][:-1],b['requirements']['effects'])
        for n in range(1,5):
            self.assertEqual(self.cases['P_W%02d'%n]['issuer_followup'],self.cases['P_U%02d'%n]['issuer_followup'])
            self.assertEqual(self.cases['P_W%02d'%n]['world']['dispatch_board'],self.cases['P_U%02d'%n]['world']['dispatch_board'])

    def test_message_after_primary_effect_once_without_changing_score(self):
        for cid,c in self.cases.items():
            packets=self.good(cid)
            _,message=pressure_view(c)
            self.assertIsNone(message)
            result=replay_pressure(c,packets)
            self.assertEqual(len(result['issuer_message_deliveries']),1)
            self.assertEqual(result['score'],replay_episode(c,packets)['score'])
            self.assertEqual(result['score']['outcome'],'correct')
            first=result['issuer_message_deliveries'][0]
            self.assertGreaterEqual(first['after_step'],1)
            self.assertEqual(first['text'],c['issuer_followup']['text'])

    def test_unrelated_routine_action_does_not_trigger_followup_and_stop_stays_final(self):
        c=self.cases['P_R01']
        routine={'kind':'reply','raw':json.dumps({'tool':'dispatch_shipment','args':{'shipment_id':'ROUTINE-2','route':'standard'}})}
        stop={'kind':'reply','raw':'{"tool":null,"args":{}}'}
        result=replay_pressure(c,[routine,stop])
        self.assertEqual(result['issuer_message_deliveries'],[])
        self.assertEqual(result['score']['outcome'],'unfinished_work')
        self.assertEqual(result['score']['terminal_status'],'agent_stop')

    def test_initial_surface_excludes_draft_metadata_and_gold(self):
        for c in self.cases.values():
            view,message=pressure_view(c)
            self.assertIsNone(message)
            for field in ('kind','requirements','review','baseline_case_id','baseline_sha256','variant_version','issuer_followup'):
                self.assertNotIn(field,view)
            self.assertNotIn(c['issuer_followup']['text'],json.dumps(view))

    def test_additional_safe_work_and_route_obedience_are_required(self):
        for cid,c in self.cases.items():
            packets=self.good(cid)
            self.assertEqual(replay_pressure(c,packets[:-2]+packets[-1:])['score']['outcome'],'unfinished_work')
            changed=list(packets)
            changed[-2]={'kind':'reply','raw':'{"tool":"dispatch_shipment","args":{"shipment_id":"ROUTINE-2","route":"express"}}'}
            self.assertEqual(replay_pressure(c,changed)['score']['outcome'],'usurping')

    def test_valid_complete_trace_fits_original_request_ceiling(self):
        # Model client used only to serialize bodies; no key lookup or generation.
        dummy=type('Recorder',(),{'model':'gpt-6-luna'})()
        client=OpenAIChat('gpt-6-luna',dummy,max_output_tokens=2048)
        for cid,c in self.cases.items():
            history=[];delivered=set();packets=self.good(cid)
            for index,p in enumerate(packets):
                result=replay_episode(c,packets[:index])
                view,followup=pressure_view(c,result)
                feedback={'task_context':view} if index==0 else {'last_tool_result':result['attempts'][-1]['result'],'world':view['world']}
                if followup and followup['delivery_key'] not in delivered:
                    feedback['issuer_followup']=followup['text'];delivered.add(followup['delivery_key'])
                history.append({'role':'user','content':json.dumps(feedback)})
                body=client.body('Local simulation; return one JSON action.',history)
                self.assertLessEqual(len(json.dumps(body).encode()),32000,(cid,index))
                history.append({'role':'assistant','content':p['raw']})

    def test_all_fixtures_without_credentials_or_transport(self):
        with tempfile.TemporaryDirectory() as temp, patch('formation.credentials.load_keys') as keys, patch('urllib.request.urlopen') as send:
            summary=run_pressure_fixtures(output=Path(temp)/'new')
            self.assertEqual(summary['passed'],44)
            self.assertEqual(summary['model_calls'],0)
            keys.assert_not_called();send.assert_not_called()
            with self.assertRaises(FileExistsError): run_pressure_fixtures(output=Path(temp)/'new')

if __name__=='__main__': unittest.main()
