"""Authenticated-session binding, unchanged core calls and actual stdio controls."""
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from taa_gateway.envelopes import Session
from taa_gateway.mcp_server import Server,MAX_FRAME,LOG_URI
from taa_gateway.serialization import canonical
from tests.trace_support import production_backend as core,mcp_backend
from tests.trace_support.bundle import world,cases,BUNDLE
from tests.trace_support.reference_runner import run

ARGS={'claim':'CL1','amount':120,'to':'K1_card','basis':'return'}


class MCPTests(unittest.TestCase):
    def setup_server(self,actor='A'):
        state=core.start(world(),{'records':{'RET1':{'received':True}}})
        context=core._context(state)
        server=Server(context.runtime,context.sessions[actor],context.tools,context.log)
        client=mcp_backend.ScriptedClient(server.handle_line)
        return context,server,client

    def test_registered_tools_only_propose_then_existing_atomic_runtime_executes(self):
        c,s,client=self.setup_server();before=c.store.snapshot()
        names={t['name'] for t in client.request('tools/list',{})['tools']}
        self.assertEqual(names,{t.name for t in c.tools}|{'taa_propose','taa_execute','taa_withdraw'})
        p=client.call('issue_refund',ARGS);self.assertEqual(p['disposition'],'PERMIT')
        self.assertEqual(c.store.snapshot()['receipts'],before['receipts'])
        self.assertEqual(c.store.snapshot()['records'],before['records'])
        r=client.call('taa_execute',{'token_id':p['token']});self.assertEqual(r['execute_result'],'committed')
        self.assertEqual(len(c.store.snapshot()['receipts']),1)
        again=client.call('taa_execute',{'token_id':p['token']});self.assertNotEqual(again['execute_result'],'committed')
        log=json.loads(client.request('resources/read',{'uri':LOG_URI})['contents'][0]['text'])
        actual=c.log.events();self.assertTrue(log['events'])
        self.assertTrue(all(e==actual[e['sequence']] for e in log['events']))
        self.assertNotIn('seed',{e['type'] for e in log['events']})

    def test_wire_claimed_identity_cannot_change_actor_and_forged_session_is_rejected(self):
        c,s,client=self.setup_server('B')
        before=c.store.snapshot()
        r=client.call('taa_propose',dict(tool='issue_refund',arguments=ARGS,acting_party='party:A',claimed_grant='grant:G1'))
        self.assertEqual(r['disposition'],'REFUSE');self.assertIsNone(r['token'])
        self.assertEqual(c.store.snapshot()['records'],before['records'])
        with self.assertRaises(ValueError):Server(c.runtime,Session('party:A','agent',('propose','execute')),c.tools,c.log)
        c2,s2,client2=self.setup_server('A');token=client2.call('issue_refund',ARGS)['token']
        b=Server(c2.runtime,c2.sessions['B'],c2.tools,c2.log)
        denied=mcp_backend.ScriptedClient(b.handle_line).call('taa_execute',{'token_id':token})
        self.assertEqual(denied['execute_result'],'refused_wrong_actor')
        self.assertEqual(c2.store.snapshot()['receipts'],[])

    def test_unknown_tools_bad_business_schema_and_protocol_host_methods_are_logged_without_revision(self):
        c,s,client=self.setup_server();revision=c.store.revision
        rejected=client.request('tools/call',{'name':'not_registered','arguments':{}})
        self.assertTrue(rejected['isError']);self.assertEqual(rejected['structuredContent']['call_result'],'rejected_unregistered_tool')
        self.assertEqual(client.call('issue_refund',{'amount':'bad'})['call_result'],'rejected_arguments')
        for method,params in [('world/write',{}),('tools/call',{'name':'taa_execute','arguments':{'token_id':{},'fault':'during_effect_commit'}})]:
            r=s.handle({'jsonrpc':'2.0','id':99,'method':method,'params':params});self.assertIn('error',r)
        self.assertEqual(c.store.revision,revision)
        kinds=[e['type'] for e in c.log.events()]
        self.assertIn('rejected_proposal',kinds);self.assertIn('mcp_request_rejected',kinds)

    def test_withdraw_and_argument_mismatch_remain_runtime_conditions(self):
        c,s,client=self.setup_server();t=client.call('issue_refund',ARGS)['token']
        denied=client.call('taa_execute',{'token_id':t,'tool':'issue_refund','arguments':dict(ARGS,amount=1)})
        self.assertNotEqual(denied['execute_result'],'committed')
        self.assertEqual(client.call('taa_withdraw',{'token_id':t})['withdraw_result'],'withdrawn')
        self.assertNotEqual(client.call('taa_execute',{'token_id':t})['execute_result'],'committed')
        self.assertEqual(c.store.snapshot()['receipts'],[])

    def test_malformed_json_batches_and_frame_limit_never_execute(self):
        c,s,client=self.setup_server();before=c.store.snapshot()
        for text in ('{"jsonrpc":"2.0","id":1,"id":2}', '{"x":NaN}', '[]'):
            self.assertIn('error',json.loads(s.handle_line(text)))
        output=io.StringIO();s.serve(io.StringIO('x'*(MAX_FRAME+1)+'\n'),output)
        self.assertIn('Frame too large',output.getvalue())
        self.assertEqual(c.store.snapshot(),before)

    def test_frozen_cases_cross_actual_json_rpc_and_common_state_audits(self):
        for case in [c for c in cases() if c['id'] in ('T02','T03','T23','T39')]:
            rows=run(case,backend=mcp_backend)
            self.assertFalse([r for r in rows if r['status']!='pass'],case['id'])

    def test_real_subprocess_stdio_handshake_dynamic_token_and_no_unsolicited_stdout(self):
        import sys,selectors
        with tempfile.TemporaryDirectory() as directory:
            log=Path(directory)/'episode.jsonl';cp=Path(directory)/'checkpoint.json';setup=Path(directory)/'setup.json'
            setup.write_text(json.dumps({'records':{'RET1':{'received':True}}}))
            process=subprocess.Popen([sys.executable,'-m','taa_gateway.mcp_server','--world',str(BUNDLE/'world_W0.yaml'),'--actor','A','--setup',str(setup),'--log',str(log),'--checkpoint',str(cp)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
            def send(frame):
                process.stdin.write(frame+'\n');process.stdin.flush()
                if 'id' not in json.loads(frame):return None
                if not selector.select(15):raise AssertionError('stdio response timeout')
                return process.stdout.readline().rstrip('\n')
            try:
                client=mcp_backend.ScriptedClient(send)
                self.assertTrue(client.request('tools/list',{})['tools'])
                p=client.call('issue_refund',ARGS);self.assertEqual(p['disposition'],'PERMIT')
                result=client.call('taa_execute',{'token_id':p['token']})
                self.assertEqual(result['execute_result'],'committed')
                process.stdin.close();self.assertEqual(process.wait(timeout=15),0)
                self.assertEqual(process.stdout.read(),'');self.assertEqual(process.stderr.read(),'')
            finally:
                selector.close()
                if process.poll() is None:process.terminate();process.wait(timeout=10)
                for stream in (process.stdout,process.stderr):stream.close()
            self.assertTrue(log.read_bytes().endswith(b'\n'))
            self.assertEqual(json.loads(log.read_bytes().splitlines()[-1]),json.loads(cp.read_text()))
