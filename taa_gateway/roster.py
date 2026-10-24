"""H1 authenticated roster inbox for explicitly enabled regression worlds.

The core owns authentication and field-limited writes. No caller-supplied
sender field can confer authority, and no roster update creates a grant.
"""
from taa_gateway.records import Write
from taa_gateway.serialization import copy_json


class RosterInbox:
    def __init__(self, store, auth, gateway, *, enabled=False):
        self.store, self.auth, self.gateway, self.enabled = store, auth, gateway, enabled

    def receive(self, envelope):
        if not self.enabled:
            raise ValueError('roster_change is not declared in this world overlay')
        env = self.auth.verify(envelope)
        if (env['message_kind'] != 'roster_change' or env['recipient'] != 'gateway_roster' or
                env['step'] != self.store.step):
            raise ValueError('roster envelope outside this service/step')
        payload = env['content']
        keys = ('add_jurisdictions', 'remove_jurisdictions', 'add_may_receive', 'remove_may_receive')
        valid = (type(payload) is dict and not set(payload) - {'party', *keys} and
                 type(payload.get('party')) is str and
                 all(type(payload.get(k, [])) is list and
                     all(type(v) is str and v for v in payload.get(k, [])) for k in keys))
        reason = None
        if env['authenticated_sender'] != 'party:company':
            reason = 'root principal required'
        elif not valid:
            reason = 'malformed roster change'
        if reason:
            self.store.audit('rejected_roster_change', {'envelope': env, 'reason': reason})
            return {'roster_rejected': True, 'reason': reason}
        result = {}
        def change(state, events):
            if env['step'] != state['step']:
                raise ValueError('roster envelope is no longer current')
            rid = 'party:' + payload['party']
            history = state['records'].get(rid, [])
            if not history or history[-1]['kind'] != 'party':
                result.update(roster_rejected=True, reason='unknown party')
                events.append((state['step'], 'rejected_roster_change', {'envelope': env, **result}))
                return
            fields = copy_json(history[-1]['fields'])
            for field in ('jurisdictions', 'may_receive'):
                wanted = (set(fields[field]) - set(payload.get('remove_' + field, []))) | set(payload.get('add_' + field, []))
                fields[field] = [x for x in fields[field] if x in wanted]
                for x in payload.get('add_' + field, []):
                    if x not in fields[field]:
                        fields[field].append(x)
            # Membership is semantic; adding an existing member is a no-op.
            if fields == history[-1]['fields']:
                events.append((state['step'], 'roster_change_noop', {'envelope': env}))
            else:
                self.store.append_write(state, events, self.gateway, 'roster_change', Write(rid, 'party', fields))
                events.append((state['step'], 'roster_change_accepted', {'envelope': env}))
        self.store.gateway_mutation(self.gateway, 'roster_change', change)
        return result
