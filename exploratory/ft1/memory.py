"""Mechanical failures never receive conduct labels."""
import gc

class MechanicalOOM(RuntimeError):
    def __init__(self, prompt_tokens, turn=0):
        super().__init__('generation out of memory')
        self.prompt_tokens = prompt_tokens
        self.turn = turn

def is_oom(exc):
    return isinstance(exc, RuntimeError) and ('out of memory' in str(exc).lower() or type(exc).__name__ == 'OutOfMemoryError')

def cleanup():
    import torch
    gc.collect()
    torch.cuda.empty_cache()

class Tracker:
    limit = 3
    def __init__(self, retain):
        self.retain = retain
        self.total = self.consecutive = 0
        self.last_oom = self.stopped = False
    def call(self, call, turn, identity):
        self.last_oom = False
        try:
            result = call()
        except MechanicalOOM as exc:
            self.total += 1
            self.consecutive += 1
            self.last_oom = True
            self.stopped = self.consecutive >= self.limit
            self.retain(dict(event='mechanical_oom',status='mechanical_oom',prompt_tokens=exc.prompt_tokens,
                turn=exc.turn if turn is None else turn,identity=identity,consecutive=self.consecutive,stopped=self.stopped))
            return None
        self.consecutive = 0
        return result
