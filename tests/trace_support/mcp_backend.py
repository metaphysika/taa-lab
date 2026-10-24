"""Actual JSON-RPC round trips over the unchanged production test host.

Only the trusted test host delivers clock/events and injects transaction faults.
The MCP wire has no host-event or identity-changing method. Normalization and
all state audits remain those of the existing common production adapter.
"""
import json
import io
from unittest.mock import patch
from taa_gateway.mcp_server import Server,PROTOCOL
from taa_gateway.serialization import canonical
from tests.trace_support import production_backend as core


class ScriptedClient:
    def __init__(self,send):
        self.send=send;self.serial=0
        self.request('initialize',{'protocolVersion':PROTOCOL,'capabilities':{},'clientInfo':{'name':'offline-scripted-client','version':'0.1'}})
        result=self.send(canonical({'jsonrpc':'2.0','method':'notifications/initialized'}).decode())
        if result is not None:raise ValueError('notification unexpectedly responded')

    @classmethod
    def framed(cls,server):
        def send(frame):
            writer=io.StringIO();server.serve(io.StringIO(frame+'\n'),writer)
            lines=writer.getvalue().splitlines()
            if len(lines)>1:raise ValueError('unexpected extra protocol output')
            return lines[0] if lines else None
        return cls(send)

    def request(self,method,params):
        self.serial+=1
        answer=self.send(canonical({'jsonrpc':'2.0','id':self.serial,'method':method,'params':params}).decode())
        result=json.loads(answer)
        if result.get('id')!=self.serial or 'error' in result:raise ValueError('MCP request failed: '+str(result))
        return result['result']

    def call(self,name,args,metadata=None):
        params={'name':name,'arguments':args}
        if metadata:params['_meta']=metadata
        answer=self.request('tools/call',params)
        if json.loads(answer['content'][0]['text'])!=answer['structuredContent']:raise ValueError('MCP content disagrees with structured result')
        return answer['structuredContent']


start=core.start
apply_event=core.apply_event
reconcile=core.reconcile
incomplete_assertion=core.incomplete_assertion
inject_hidden_state=core.inject_hidden_state


def propose(before,actor,tool,args,order_reference=None):
    context=core._context(before)
    server=Server(context.runtime,context.sessions[actor],context.tools,context.log)
    client=ScriptedClient.framed(server)
    raw=client.call(tool,args,{'order_reference':'order:'+order_reference} if order_reference else None)
    result=core._format(raw)
    result['cited_reference_rejected']=bool(order_reference and order_reference not in result.get('associated_orders',[]))
    return core._describe(before,core._project(context,before),result)


def execute(before,actor,token_id=None,fault=None):
    context=core._context(before)
    server=Server(context.runtime,context.sessions[actor],context.tools,context.log,test_fault=fault)
    result=ScriptedClient.framed(server).call('taa_execute',{'token_id':token_id})
    return core._describe(before,core._project(context,before),core._format(result))


def enter_step(before,step,events=(),*,event_observer=None):
    # Preserve the existing hidden-record mutation hook in the common harness.
    with patch.object(core,'apply_event',apply_event):
        return core.enter_step(before,step,events,event_observer=event_observer)


def advance(before,step):
    for at in range(before['step']+1,step+1):before=enter_step(before,at)[0]
    return before
