"""Free deterministic controls. These are not model evidence."""
from copy import deepcopy


class Scripted:
    def __init__(self, host, mode):
        if mode not in ('obedient', 'careful'):
            raise ValueError('stand-in must be obedient or careful')
        self.host, self.mode, self.finished = host, mode, False

    def request(self):
        if self.finished:
            return []
        self.finished = True
        data = self.host.case
        if self.mode == 'careful' and data['twin'] == 'W':
            return []
        return [dict(id='scripted-act', **deepcopy(data['required']))]

    def results(self, results):
        pass
