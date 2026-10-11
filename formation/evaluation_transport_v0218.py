"""New accounting/quota adapters; frozen clients and prompts remain untouched."""
import json
import os
import time
from pathlib import Path
from agents.call_telemetry import BudgetStopped
from formation.clients import OpenAIChat, ClaudeChat, GeminiChat, GroqChat
from formation.limits import FreeTierLimiter, RatePaused
from formation.telemetry import FormationRecorder


class EvaluationRecorder(FormationRecorder):
    def __init__(self,*args,**kwargs):
        self.last_reply=None
        self.last_identity_valid=False
        super().__init__(*args,**kwargs)
        self.pending=False
        if self.path.exists():
            started=set();ended=set()
            for line in self.path.read_text().splitlines():
                e=json.loads(line)
                if e['event']=='attempt_start':started.add(e['id'])
                if e['event']=='attempt_end':
                    ended.add(e['id'])
                    self.last_identity_valid=(e.get('model_returned')==self.model and not e.get('model_mismatch') and not e.get('usage_missing'))
            self.pending=bool(started-ended)

    def _write(self,record):
        super()._write(record)
        with self.path.open('a') as out:os.fsync(out.fileno())

    def before_attempt(self,body):
        if self.pending:raise BudgetStopped('uncertain prior attempt; no new request')
        if len(json.dumps(body).encode())>32000:raise BudgetStopped('frozen 32,000-byte limit exceeded')
        output=body.get('max_completion_tokens',body.get('max_tokens',body.get('generationConfig',{}).get('maxOutputTokens')))
        if body.get('model',self.model)!=self.model or output!=2048:
            raise BudgetStopped('frozen model or output ceiling differs')
        original=self.prices
        price=original[self.model]
        maximum=max(price['input_per_million'],price.get('cache_write_per_million',0))
        self.prices={self.model:dict(price,input_per_million=maximum)}
        try:return super().before_attempt(body)
        finally:self.prices=original

    def raw_reply(self,text,parsed=None,error=None):
        self.last_reply=text
        super().raw_reply(text,parsed=parsed,error=error)


class GroqSlots(FreeTierLimiter):
    """Reserve a whole minute's quota; never treat JSON bytes as exact tokens.

One slot per 61 seconds, 1,000 rolling requests/day, 200,000 rolling tokens/day.
Server limits remain authoritative. An individually oversized request may be
rejected by the provider and must not be retried as a replacement episode.
"""
    def __init__(self,path,now=time.time):
        super().__init__(path,now=now)
        self.last_event=None

    def before(self,ignored_byte_hint):
        now=self.now()
        state=json.loads(self.path.read_text()) if self.path.exists() else {}
        if now<state.get('paused_until',0):raise RatePaused('provider reset pending')
        events=[e for e in state.get('events',[]) if now-e[0]<86400]
        if events and now-events[-1][0]<61:raise RatePaused('one full minute slot reserved; resume after 61 seconds')
        if len(events)>=1000 or sum(e[1] for e in events)+8000>200000:
            raise RatePaused('rolling free daily quota reserved; resume after reset')
        events.append([now,8000]);self.last_event=now
        self._save({'events':events})

    def settle(self,response):
        u=response.get('usage') or {};d=u.get('prompt_tokens_details') or {}
        if 'prompt_tokens' not in u or 'completion_tokens' not in u:return
        actual=u['prompt_tokens']-d.get('cached_tokens',0)+u['completion_tokens']
        if actual<0:raise BudgetStopped('invalid Groq usage')
        state=json.loads(self.path.read_text())
        for e in reversed(state['events']):
            if e[0]==self.last_event:e[1]=max(actual,0);break
        self._save(state)
        if actual>8000:
            self.pause(86400)
            raise BudgetStopped('reported uncached usage exceeded reserved free slot; inspect limits')


class QuotaRecorder(EvaluationRecorder):
    def __init__(self,*args,quota=None,**kwargs):
        self.quota=quota
        super().__init__(*args,**kwargs)

    def finish_native(self,aid,response,provider,status=200):
        super().finish_native(aid,response,provider,status)
        self.last_identity_valid=True
        if self.quota:self.quota.settle(response)


def make_client(model,provider,recorder,quota=None):
    cls={'openai':OpenAIChat,'claude':ClaudeChat,'google':GeminiChat,'groq':GroqChat}[provider]
    options={'max_output_tokens':2048}
    if provider=='groq':options.update(free_tier_confirmed=True,limiter=quota)
    return cls(model,recorder,**options)
