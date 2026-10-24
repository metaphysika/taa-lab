"""Offline MCP stdio front, pinned to protocol 2025-06-18.

A trusted host supplies an already authenticated SimulatorAuthority.Session.
The wire cannot select another identity or administer the world. This is local
simulator authentication, not remote authentication/OAuth or a production host.
All decisions, capabilities and effects use the unchanged core runtime.
"""
import argparse
import json
from pathlib import Path
import secrets
import sys

from taa_gateway.serialization import canonical,copy_json,parse_json
from taa_gateway.executor import ExecutionRefused

PROTOCOL='2025-06-18'
MAX_FRAME=1024*1024
CONTROL_TOOLS=('taa_propose','taa_execute','taa_withdraw')
LOG_URI='taa://session/decision-log'


class ProtocolError(ValueError):
    def __init__(self,code,message):
        super().__init__(message);self.code=code


def exact(value,allowed,required=()):
    if type(value) is not dict or set(value)-set(allowed) or not set(required)<=set(value):
        raise ProtocolError(-32602,'Invalid parameters')


class Server:
    def __init__(self,runtime,session,tools,event_log,*,test_fault=None):
        actor,channel=runtime.authority.identity(session,'propose')
        runtime.authority.identity(session,'execute')
        if channel!='agent':raise ValueError('MCP front requires a bound agent session')
        self.__runtime,self.__session,self.__log=runtime,session,event_log
        self.actor=actor
        self.__tools=tuple(tools)
        if set(t.name for t in self.__tools)&set(CONTROL_TOOLS):raise ValueError('registered tool collides with MCP control name')
        self.__phase='new';self.__sequences=set()
        # Trusted host fault injection only; never accepted from a wire argument.
        self.__fault=test_fault

    def _reject(self,code,message):
        raise ProtocolError(code,message)

    def _call(self,params):
        exact(params,('name','arguments','_meta'),('name',))
        if type(params['name']) is not str:self._reject(-32602,'Tool name must be a string')
        name=params['name'];args=params.get('arguments',{})
        if type(args) is not dict:self._reject(-32602,'Tool arguments must be an object')
        metadata=params.get('_meta',{})
        exact(metadata,('order_reference','claimed_purpose','claimed_grant','claimed_reasons'))
        start=len(self.__log.events())
        try:
            if name=='taa_propose':
                if metadata:self._reject(-32602,'Full proposals carry their own core metadata')
                result=self.__runtime.propose(self.__session,args)
            elif name=='taa_execute':
                exact(args,('token_id','tool','arguments'),('token_id',))
                if type(args['token_id']) not in (str,type(None)) or ('tool' in args and type(args['tool']) is not str) or ('arguments' in args and type(args['arguments']) is not dict):self._reject(-32602,'Invalid execution binding')
                if metadata:self._reject(-32602,'Execution does not accept proposal metadata')
                result=self.__runtime.execute(self.__session,args['token_id'],
                    **{k:args[k] for k in ('tool','arguments') if k in args},fault=self.__fault)
            elif name=='taa_withdraw':
                exact(args,('token_id',),('token_id',))
                if type(args['token_id']) is not str:self._reject(-32602,'Invalid withdrawal token')
                if metadata:self._reject(-32602,'Withdrawal does not accept proposal metadata')
                try:
                    self.__runtime.withdraw(self.__session,args['token_id']);result={'withdraw_result':'withdrawn'}
                except ExecutionRefused as error:
                    self.__runtime.store.audit('withdrawal_refused',{'actor':self.actor,'token':args['token_id'],'reason':str(error)})
                    result={'withdraw_result':str(error)}
            else:
                # Including an unknown name: the core rejects/audits it, rather
                # than a transport-only check suppressing the decision log.
                result=self.__runtime.propose(self.__session,dict(metadata,tool=name,arguments=args))
        finally:self.__sequences.update(range(start,len(self.__log.events())))
        return {'content':[{'type':'text','text':canonical(result).decode()}],
                'structuredContent':copy_json(result),'isError':str(result.get('call_result','')).startswith('rejected_')}

    def _dispatch(self,method,params):
        if method=='initialize':
            if self.__phase!='new':self._reject(-32600,'Already initialized')
            exact(params,('protocolVersion','capabilities','clientInfo'),('protocolVersion','capabilities','clientInfo'))
            if params['protocolVersion']!=PROTOCOL:self._reject(-32602,'Supported protocol: '+PROTOCOL)
            if type(params['capabilities']) is not dict or type(params['clientInfo']) is not dict:self._reject(-32602,'Invalid client initialization')
            self.__phase='initializing'
            return {'protocolVersion':PROTOCOL,'capabilities':{'tools':{'listChanged':False},'resources':{'subscribe':False,'listChanged':False}},
                    'serverInfo':{'name':'taa-offline-gateway','version':'0.1'},
                    'instructions':'Registered tools propose only. Execute returned capabilities with taa_execute. Identity is bound by the trusted stdio host.'}
        if method=='notifications/initialized':
            exact(params,())
            if self.__phase!='initializing':self._reject(-32600,'Unexpected initialized notification')
            self.__phase='ready';return None
        if method=='ping':exact(params,());return {}
        if self.__phase!='ready':self._reject(-32002,'Initialize the session first')
        if method=='tools/list':
            exact(params,())
            tools=[{'name':t.name,'description':'Propose '+t.name+' through the existing gateway; no effect until taa_execute.',
                    'inputSchema':copy_json(t.arguments_schema)} for t in sorted(self.__tools,key=lambda t:t.name)]
            tools.extend([
                {'name':'taa_propose','description':'Full core proposal. Claimed identity, reasons, grant and purpose confer no authority.',
                 'inputSchema':{'type':'object','properties':{'tool':{'type':'string'},'arguments':{'type':'object'},'order_reference':{'type':['string','null']},'claimed_purpose':{},'claimed_grant':{},'claimed_reasons':{'type':'array'}},'required':['tool','arguments']}},
                {'name':'taa_execute','description':'Execute an existing actor-bound one-use capability through the atomic runtime.',
                 'inputSchema':{'type':'object','properties':{'token_id':{'type':['string','null']},'tool':{'type':'string'},'arguments':{'type':'object'}},'required':['token_id'],'additionalProperties':False}},
                {'name':'taa_withdraw','description':'Withdraw this session actor’s live token through the runtime.',
                 'inputSchema':{'type':'object','properties':{'token_id':{'type':'string'}},'required':['token_id'],'additionalProperties':False}}])
            return {'tools':tools}
        if method=='tools/call':return self._call(params)
        if method=='resources/list':
            exact(params,());return {'resources':[{'uri':LOG_URI,'name':'This session’s existing core decision/event entries','mimeType':'application/json'}]}
        if method=='resources/read':
            exact(params,('uri',),('uri',))
            if params['uri']!=LOG_URI:self._reject(-32602,'Unknown session resource')
            events=[e for e in self.__log.events() if e['sequence'] in self.__sequences]
            value={'actor':self.actor,'events':events,'scope':'Events produced during this bound session’s calls; not a complete authenticated chain.'}
            return {'contents':[{'uri':LOG_URI,'mimeType':'application/json','text':canonical(value).decode()}]}
        self._reject(-32601,'Method not found')

    def handle(self,request):
        identity=None
        try:
            if type(request) is not dict or set(request)-{'jsonrpc','id','method','params'} or not {'jsonrpc','method'}<=set(request):raise ProtocolError(-32600,'Invalid JSON-RPC request')
            identity=request.get('id')
            if request['jsonrpc']!='2.0' or type(request['method']) is not str or ('id' in request and type(identity) not in (str,int)):
                raise ProtocolError(-32600,'Invalid JSON-RPC request')
            notification='id' not in request
            if notification and not request['method'].startswith('notifications/'):
                self._reject(-32600,'Only notifications may omit an id')
            if not notification and request['method'].startswith('notifications/'):
                self._reject(-32600,'Notifications must omit id')
            result=self._dispatch(request['method'],request.get('params',{}))
            return None if notification else {'jsonrpc':'2.0','id':identity,'result':result}
        except ProtocolError as error:
            self.__runtime.store.audit('mcp_request_rejected',{'actor':self.actor,'code':error.code,'reason':str(error)})
            if type(request) is dict and 'id' not in request:return None
            return {'jsonrpc':'2.0','id':identity,'error':{'code':error.code,'message':str(error)}}

    def handle_line(self,line):
        try:request=parse_json(line)
        except (ValueError,TypeError):
            self.__runtime.store.audit('mcp_request_rejected',{'actor':self.actor,'code':-32700,'reason':'Invalid finite JSON'})
            return canonical({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Invalid finite JSON'}}).decode()
        result=self.handle(request)
        return None if result is None else canonical(result).decode()

    def serve(self,reader,writer):
        while True:
            line=reader.readline(MAX_FRAME+1)
            if not line:return
            if len(line.encode('utf-8'))>MAX_FRAME:
                self.__runtime.store.audit('mcp_request_rejected',{'actor':self.actor,'code':-32600,'reason':'Frame too large'})
                writer.write(canonical({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Frame too large; connection closed'}}).decode()+'\n');writer.flush();return
            answer=self.handle_line(line)
            if answer is not None:writer.write(answer+'\n');writer.flush()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--world',type=Path,required=True);p.add_argument('--actor',required=True);p.add_argument('--setup',type=Path)
    p.add_argument('--log',type=Path);p.add_argument('--checkpoint',type=Path)
    a=p.parse_args(argv)
    if bool(a.log)!=bool(a.checkpoint):p.error('--log and --checkpoint must be supplied together')
    if a.log and (a.log==a.checkpoint or a.log.exists() or a.checkpoint.exists()):p.error('log/checkpoint paths must be distinct and new')
    import yaml
    from taa_gateway.refunds import RefundWorld
    setup=json.loads(a.setup.read_text()) if a.setup else {}
    context=RefundWorld(yaml.safe_load(a.world.read_text()),secrets.token_bytes(32),setup=setup)
    if a.actor not in context.sessions:p.error('unknown trusted host actor')
    context.store.publish(context.gateway,'advance_clock',step=1);context.engine.reconcile()
    server=Server(context.runtime,context.sessions[a.actor],context.tools,context.log)
    server.serve(sys.stdin,sys.stdout)
    if a.log:
        checkpoint=context.log.seal()
        with a.log.open('xb') as f:f.write(context.log.jsonl())
        with a.checkpoint.open('xb') as f:f.write(canonical(checkpoint)+b'\n')

if __name__=='__main__':main()
