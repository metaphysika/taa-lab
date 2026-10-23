"""C4 simulator routing metadata; no authorization or expected-outcome logic.

The fixture's explicit token labels identify source proposal entries. Their
numbers never identify an arm's issuance sequence. Construct one table per arm,
before controller expansion. Controllers see origins but no token answer keys.
"""
from copy import deepcopy


def prepare(case):
    """Preserve zero-based source step-entry indices before inserting actions."""
    source = deepcopy(case)
    for index, entry in enumerate(source['trace']['steps']):
        if 'propose' in entry:
            entry['proposal_origin'] = [case['id'], index]
    return source, TokenBindings(source)


class TokenBindings:
    def __init__(self, source):
        self.labels = {}
        self.observed = {}
        self.last = None
        for entry in source['trace']['steps']:
            if 'propose' not in entry:
                continue
            label = entry.get('expect', {}).get('token')
            if isinstance(label, str) and label != 'none':
                # Repeated cached proposals may name the same original token.
                self.labels.setdefault(label, tuple(entry['proposal_origin']))

    def record(self, entry, token):
        self.last = deepcopy(token)  # A refusal clears the dynamic reference.
        origin = entry.get('proposal_origin')
        if origin is not None:
            origin = tuple(origin)
            if origin in self.observed:
                raise ValueError('source proposal origin executed twice')
            self.observed[origin] = deepcopy(token)

    def resolve(self, label):
        # No fallback to an arm's native ordinal or any other proposal.
        return deepcopy(self.observed.get(self.labels.get(label)))

    def execution(self, entry):
        if 'token_from' in entry:
            if entry['token_from'] != 'last_proposal' or 'token' in entry:
                raise ValueError('invalid dynamic token reference')
            return deepcopy(self.last)
        return self.resolve(entry.get('token'))

    def expectation(self, key, value):
        """Resolve token assertions only; never translate a policy outcome."""
        if key in ('token', 'same_revision_as') and value in self.labels:
            return self.resolve(value) or 'unissued:' + value
        if key == 'token_state':
            return {self.resolve(label) or 'unissued:' + label: state for label, state in value.items()}
        return value
