"""Sealed-adjacent blind packet checks, excluded from agent-safe runs."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from exploratory.ft1 import blind
from exploratory.step4_harness import crossing

class BlindTests(unittest.TestCase):
    def test_blind_synthetic(self):
        cases = copy.deepcopy(crossing.cases()[:2])
        for case in cases:
            case['difficulty_group']='synthetic'
            case['answer_key']['recipient']='synthetic-recipient'
            case['answer_key']['private_marker']='SECRET_MARKER'
        packet,mapping = blind.packet(cases)
        serialized = json.dumps(packet)
        for forbidden in ('answer_key','difficulty_group','private_marker','SECRET_MARKER','pair_id','evidence_type'):
            self.assertNotIn(forbidden,serialized)
        self.assertEqual(set(packet['items'][0]),{'id','system','history'})
        roster = {c['id']:c for c in cases}
        labels = [dict(id=bid,**blind.gold(roster[cid])) for bid,cid in mapping.items()]
        result = blind.compare(cases,labels,mapping)
        self.assertEqual(result['agreement']['all']['all_fields']['rate'],1)
        labels[0]['kind']='U' if labels[0]['kind']=='W' else 'W'
        result = blind.compare(cases,labels,mapping)
        self.assertEqual(result['disagreeing_ids'],[labels[0]['id']])
        self.assertEqual(result['agreement']['all']['kind']['rate'],.5)
        with self.assertRaises(ValueError): blind.compare(cases,labels[:1],mapping)


    def test_label_schema_and_leak_detection(self):
        cases = copy.deepcopy(crossing.cases()[:2])
        packet,mapping = blind.packet(cases)
        packet['leak']=cases[0]['id']
        self.assertFalse(blind.self_check(cases,packet)['passed'])
        labels = [dict(id=f'item-{i+1:03d}',**blind.gold(case)) for i,case in enumerate(cases)]
        schema = blind.schema_for(cases)
        self.assertTrue(blind.validate_labels(dict(labels=labels),schema)['passed'])
        labels[0]['complete_act']['requested_status']='invalid'
        report = blind.validate_labels(dict(labels=labels),schema)
        self.assertFalse(report['passed'])
        self.assertNotIn('invalid',json.dumps(report))
        self.assertEqual(report['errors'][0]['field'],'file.labels.complete_act.requested_status')


    def test_neutral_definitions_cover_fields_and_instruction_leaks(self):
        cases = copy.deepcopy(crossing.cases()[:2])
        packet,_ = blind.packet(cases)
        text = packet['instructions']['definitions']
        for field in ('id:','kind:','sphere:','complete_act:','complete_act.requested_status:',
                      'complete_act.preserved_status:','complete_act.correct_option:',
                      'complete_act.explicit_decline:','complete_act.referral:','report_recipient:'):
            self.assertIn(field,text)
        self.assertIn('W means',text)
        self.assertIn('U means',text)
        self.assertIn('Label required acts only',text)
        self.assertIn('not an unknown answer',text)
        packet['instructions']['definitions'] += cases[0]['answer_key']['rationale']
        self.assertFalse(blind.self_check(cases,packet)['passed'])


    def test_status_gloss_tracks_schema_enum(self):
        schema = copy.deepcopy(blind.SCHEMA)
        properties = schema['properties']['labels']['items']['properties']['complete_act']['properties']
        for field in ('requested_status','preserved_status'):
            properties[field]['enum']=['PENDING']
        self.assertEqual(set(blind.status_glosses(schema)),{'PENDING'})
        text = blind.definitions_for(schema)
        self.assertIn('PENDING means',text)
        self.assertNotIn('RELEASED',text)
        self.assertNotIn('UNRESTRICTED_PASS',text)
        properties['requested_status']['enum']=['UNREVIEWED_SYNTHETIC_STATUS']
        with self.assertRaises(ValueError): blind.definitions_for(schema)


    def test_export_and_self_check_bind_exact_bytes(self):
        import hashlib
        cases = copy.deepcopy(crossing.cases()[:2])
        for index,case in enumerate(cases):
            case.update(id=f'fixture-case-{index}',pair_id='fixture-pair',difficulty_group='fixture-category')
            case['answer_key']['rationale']='fixture-secret-rationale'
        with tempfile.TemporaryDirectory() as tmp,patch.object(blind,'PRIVATE_ROOT',Path(tmp).resolve()):
            root = Path(tmp)
            source = root/'cases.json'
            source.write_bytes((json.dumps(dict(cases=cases),indent=4)+'\n\n').encode('utf-8'))
            result = blind.export(source,root/'packet.json',root/'mapping.json')
            raw = (root/'packet.json').read_bytes()
            self.assertTrue(result['self_check']['passed'])
            self.assertEqual(result['packet_sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(result['cases_sha256'],hashlib.sha256(source.read_bytes()).hexdigest())
            audit = blind.self_check(cases,json.loads(raw),raw,source.read_bytes())
            self.assertEqual(audit,result['self_check'])
            self.assertEqual(audit['hash_basis'],'exact_file_bytes')
            spaced = raw+b'\n'
            other = blind.self_check(cases,json.loads(raw),spaced,source.read_bytes())
            self.assertNotEqual(other['packet_sha256'],audit['packet_sha256'])
            changed = json.loads(raw); changed['items'][0]['id']='changed'
            with self.assertRaises(ValueError): blind.self_check(cases,changed,raw,source.read_bytes())

