"""Representation controls from Claude's PR32 review; v0 remains immutable."""
from copy import deepcopy
import unittest
import hashlib
from pathlib import Path
from comparators.business import Backend
from comparators.duty_oracle import Oracle
from comparators.observed_world import context, legacy_context, context_payload
from tests.trace_support import production_backend as native
from tests.trace_support.bundle import world
from conventional_gateway import backend as sql


class ContextCanonicalizationTests(unittest.TestCase):
    def states(self):
        values=[]
        for name,b in [('taa',native),('conventional',sql),('floor',Backend('floor')),('static',Backend('static'))]:
            s=b.start(world(),{'records':{'RET1':{'received':True}}});o=Oracle(s);o.clock(1);o.reconcile(s)
            for tool,args in [('issue_refund',dict(claim='CL1',amount=120,to='K1_card',basis='return')),
                              ('message_party',dict(claim='CL1',to='K1',template='refund_issued',amount=120,cites='REF1'))]:
                s,p=b.propose(s,'A',tool,args);s,r=b.execute(s,'A',p.get('execution_intent',p.get('token')))
                self.assertEqual(r['execute_result'],'committed');o.committed('A',tool,args,s)
            values.append((name,s,o))
        return values

    def test_four_hosts_same_refund_world_match_and_v0_does_not(self):
        values=self.states();current=[];old=[]
        source=(Path(__file__).parent/'fixtures/context_v0_source.py.txt').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),'5c0ed9c39378592f38f375102843c12153d7f45fbb17c807c384513068cc45ab')
        namespace={'__name__':'v0_context_fixture'};exec(compile(source,'<pinned v0 context>','exec'),namespace)
        for name,s,o in values:
            snapshot=deepcopy(s);board=o.board()
            current.append(context(s,o));old.append(namespace['context'](s,o))
            self.assertEqual(old[-1],legacy_context(s,o))
            self.assertEqual(s,snapshot);self.assertEqual(o.board(),board)
            self.assertEqual('allocated_to' in s['records']['REF1'][-1]['fields'],name=='taa')
        self.assertEqual(len(set(current)),1)
        self.assertNotEqual(old[0],old[1]);self.assertEqual(len(set(old[1:])),1)

    def test_only_schema_neutral_nulls_are_erased(self):
        _,s,o=self.states()[1];base=context(s,o)
        for value in ('D_refund(other,120)',False,0,[],{}):
            changed=deepcopy(s);changed['records']['REF1'][-1]['fields']['allocated_to']=value
            self.assertNotEqual(context(changed,o),base)
        changed=deepcopy(s);changed['records']['REF1'][-1]['fields']['allocated_to']=None
        self.assertEqual(context(changed,o),base)
        for key in ('received','signed','failed_value','amount','currency','evidence'):
            a=deepcopy(s);b=deepcopy(s);a['records']['RET1'][-1]['fields'].pop(key,None);b['records']['RET1'][-1]['fields'][key]=None
            self.assertNotEqual(context(a,o),context(b,o),key)

    def test_unknown_condition_and_no_parent_are_schema_neutral(self):
        _,s,o=self.states()[1]
        a=deepcopy(s);b=deepcopy(s)
        a['records']['RET1'][-1]['fields'].pop('condition',None);b['records']['RET1'][-1]['fields']['condition']=None
        self.assertEqual(context(a,o),context(b,o))
        a['world']['grants']['G0'].pop('parent',None);b['world']['grants']['G0']['parent']=None
        self.assertEqual(context(a,o),context(b,o))
