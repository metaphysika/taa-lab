"""Mechanical failures never receive conduct labels."""
import gc

class MechanicalUnknown(RuntimeError):
    status = 'mechanical_unknown'
    def __init__(self, prompt_tokens, turn=0):
        super().__init__(self.status)
        self.prompt_tokens = prompt_tokens
        self.turn = turn

class MechanicalOOM(MechanicalUnknown):
    status = 'mechanical_oom'

class ContextLimit(MechanicalUnknown):
    status = 'context_limit'
    def __init__(self, prompt_tokens, turn=0, rule=None):
        super().__init__(prompt_tokens,turn)
        self.rule = rule

class GateDecisionRequired(RuntimeError):
    pass

def is_oom(exc):
    return isinstance(exc,RuntimeError) and (type(exc).__name__ == 'OutOfMemoryError' or
        any(text in str(exc).lower() for text in ('out of memory','cublas_status_alloc_failed','cudnn_status_alloc_failed')))

def snapshot():
    import torch
    return dict(memory_allocated=torch.cuda.memory_allocated(), memory_reserved=torch.cuda.memory_reserved(),
                total_device_memory=torch.cuda.get_device_properties(0).total_memory)

def cleanup():
    import torch
    gc.collect()
    torch.cuda.empty_cache()

class Tracker:
    limit = 3
    def __init__(self, retain):
        self.retain = retain
        self.total = self.consecutive = 0
        self.counts = dict(mechanical_oom=0,context_limit=0)
        self.last_oom = self.last_unknown = self.stopped = False
    def call(self, call, turn, identity):
        self.last_oom = self.last_unknown = False
        try:
            result = call()
        except MechanicalUnknown as exc:
            self.total += 1
            self.counts[exc.status] += 1
            self.last_unknown = True
            self.last_oom = exc.status == 'mechanical_oom'
            self.consecutive = self.consecutive+1 if self.last_oom else self.consecutive
            self.stopped = self.consecutive >= self.limit
            rule = dict(rule=exc.rule) if isinstance(exc,ContextLimit) else {}
            details = identity if isinstance(identity,dict) else dict(identity=identity)
            self.retain(dict(event=exc.status,status=exc.status,prompt_tokens=exc.prompt_tokens,
                turn=exc.turn if turn is None else turn,consecutive=self.consecutive,stopped=self.stopped,**rule,**details))
            return None
        self.consecutive = 0
        return result
