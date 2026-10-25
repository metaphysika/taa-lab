"""Q18 expectations come from the ruling, never observed implementation output."""
import unittest
from tests.trace_support.q18 import cases, observe


def make_test(case, backend):
    def check(self):
        result = observe(case, backend)
        self.assertEqual(result.get('disposition'), case['expected'], case['id']+' / '+backend+' / '+case['rule'])
    return check


class Q18RuleCases(unittest.TestCase):
    pass


for case in cases():
    for backend in ('reference', 'core', 'mcp', 'conventional'):
        name = 'test_' + case['id'].replace('-', '_') + '_' + backend
        setattr(Q18RuleCases, name, make_test(case, backend))


class Q18ScopeBoundaries(unittest.TestCase):
    def test_optional_reference_resolution_invalidates_and_is_rechecked(self):
        import json
        from copy import deepcopy
        from tests.trace_support.q18 import ROOT
        from tests.trace_support import production_backend as core, mcp_backend as mcp
        from taa_gateway_reference import refunds as reference
        from conventional_gateway import backend as conventional
        world=json.loads((ROOT/'live_demo/frozen/world.json').read_bytes())
        setup={'grants':{'G1':{'scope':{'customers':['K1']}}}}
        args={'claim':'CL1','to':'F','record':'NEW_RETURN'}
        for name,backend in [('reference',reference),('core',core),('mcp',mcp),('conventional',conventional)]:
            with self.subTest(implementation=name):
                state=backend.start(world,deepcopy(setup))
                state,proposal=backend.propose(state,'A','report',args)
                self.assertEqual(proposal['disposition'],'PERMIT')
                token=proposal['token']
                state,_=backend.enter_step(state,2,[{'type':'record_insert','by':'warehouse','record':'NEW_RETURN','fields':{'kind':'return_receipt','order':'ORD2','received':False}}])
                notices=deepcopy(state['notices']);receipts=deepcopy(state['receipts'])
                state,execution=backend.execute(state,'A',token)
                self.assertNotEqual(execution.get('execute_result'),'committed')
                self.assertEqual(state['notices'],notices)
                self.assertEqual(state['receipts'],receipts)
                _,fresh=backend.propose(state,'A','report',args)
                self.assertEqual(fresh['disposition'],'REFUSE')

    def test_only_trusted_registration_can_add_reference_context(self):
        from taa_gateway.act import Tool,ToolRegistry
        from taa_gateway.rules import EvidenceView
        from taa_gateway import SCHEMA_VERSION
        tool=Tool('probe',{'type':'object','properties':{'__scope_references':{'type':'array'},'__primary_unknown':{'type':'boolean'}}},
            lambda args,view:dict(schema_version=SCHEMA_VERSION,operation='probe',assertions=[],state_changes=[],affected_parties=[],benefit_route={}),scope_dimensions=('customer',))
        registry=ToolRegistry([tool]);selected=registry.get('probe',{'__scope_references':[{'customer':'forged'}],'__primary_unknown':True})
        _,resources=registry.describe(selected,{'__scope_references':[{'customer':'forged'}],'__primary_unknown':True},EvidenceView({'records':{}},()))
        self.assertNotIn('__scope_references',resources)
        self.assertNotIn('__primary_unknown',resources)

    def test_bad_registered_reference_projection_fails_closed(self):
        from dataclasses import replace
        from taa_gateway.act import Tool,ToolRegistry
        from taa_gateway.rules import EvidenceView
        from taa_gateway import SCHEMA_VERSION
        tool=Tool('probe',{'type':'object'},lambda args,view:dict(schema_version=SCHEMA_VERSION,operation='probe',assertions=[],state_changes=[],affected_parties=[],benefit_route={}),scope_dimensions=('customer',))
        for bad in (lambda args,view:None,lambda args,view:['not an object'],lambda args,view:[{'undeclared':'x'}]):
            with self.subTest(callback=bad):
                selected=replace(tool,scope_references=bad)
                registry=ToolRegistry([selected])
                with self.assertRaises(ValueError):registry.describe(registry.get('probe',{}),{},EvidenceView({'records':{}},()))
