"""Deterministic POEC reconstruction from Claude's published-source notes.

Local schemas/derivations are explicit adaptations. No core/reference decision,
authorization, discharge or transaction code is imported. No duty ledger exists.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
from threading import RLock

ROOT = Path(__file__).parent / 'contracts' / 'v0.1'
ROLES = {'issue_refund': {'claim', 'amount', 'to', 'basis', 'customer'},
         'message_party': {'claim', 'to', 'amount', 'template', 'cites', 'basis', 'customer', 'referred_to'},
         'close_case': {'case'}}
REQUIRED = {'issue_refund': {'claim', 'amount', 'to', 'basis'},
            'message_party': {'claim', 'to', 'template', 'amount'}, 'close_case': {'case'}}
DERIVATIONS = {'supported_amount', 'notice_amount', 'own_settlement', 'denial_record'}
TYPES = {'string': str, 'integer': int, 'array': list}
EVIDENCE_TYPES = {
    'claim': {'claimant': (str,), 'order': (str,), 'amount': (int,)},
    'payment': {'method': (str,), 'order': (str,), 'payer': (str,), 'amount': (int,)},
    'return_receipt': {'order': (str,), 'received': (bool, type(None))},
    'carrier_record': {'order': (str,), 'status': (str,), 'failed_value': (int,)},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def contract(case):
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
    if case + '.json' not in manifest['contracts']:
        raise ValueError('unknown frozen task')
    path = ROOT / (case + '.json')
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['contracts'][path.name]:
        raise ValueError('frozen contract changed')
    notes = ROOT.parents[2] / 'docs/process/TRACEGRANT_COMPARATOR_SOURCE_NOTES.md'
    if hashlib.sha256(notes.read_bytes()).hexdigest() != manifest['source_notes_sha256']:
        raise ValueError('source notes changed')
    return json.loads(path.read_text())


def static_checks(c):
    """Five named text checks (§4.2.2), never Algorithm 1's garbled line 14."""
    checks = {name: False for name in ('WellFormed', 'ControlSafe', 'FlowSafe', 'ScopeSafe', 'VerifySafe')}
    try:
        nodes, may, bindings = c['MUST'], c['MAY'], c['BIND']
        checks['WellFormed'] = bool(nodes and may and c['actor'] and all(
            n['kind'] in ('effect', 'evidence') and type(n['hard']) is bool and
            isinstance(n['depends'], list) and all(d in nodes for d in n['depends']) and
            (n['kind'] != 'effect' or n['tool'] in may and n['tool'] in ROLES) and
            (n['kind'] != 'evidence' or n.get('record') and n.get('source') and n.get('query'))
            for n in nodes.values()) and all(t in ROLES and t in bindings for t in may) and
            all(v in TYPES for v in c['argument_types'].values()))
        for tool, slots in bindings.items():
            for slot, spec in slots.items():
                wanted = TYPES[c['argument_types'][slot]]
                if 'constant' in spec and type(c['trusted_request'][spec['constant']]) is not wanted:
                    checks['WellFormed'] = False
                if 'values' in spec and (not isinstance(spec['values'], list) or any(type(v) is not wanted for v in spec['values'])):
                    checks['WellFormed'] = False
                if 'field' in spec:
                    evidence_kind = nodes[spec['evidence']]['query']['kind']
                    if wanted not in EVIDENCE_TYPES.get(evidence_kind, {}).get(spec['field'], ()):
                        checks['WellFormed'] = False
        if not checks['WellFormed']:
            return checks
        def visit(key, path):
            if key in path:
                raise ValueError('cyclic obligation graph')
            for parent in nodes[key]['depends']:
                visit(parent, path | {key})
        for key in nodes:
            visit(key, set())
        reachable = set(c['roots'])
        if not reachable <= nodes.keys() or any(nodes[k]['depends'] for k in reachable):
            raise ValueError('invalid roots')
        for _ in nodes:
            reachable |= {k for k, n in nodes.items() if n['depends'] and set(n['depends']) <= reachable}
        checks['ControlSafe'] = all(k in reachable for k, n in nodes.items() if n['hard'])
        def valid_binding(b):
            return (('constant' in b and b['constant'] in c['trusted_request']) or
                    ('evidence' in b and b['evidence'] in nodes and nodes[b['evidence']]['kind'] == 'evidence') or
                    'values' in b or b.get('derive') == 'own_settlement') and (
                    'derive' not in b or b['derive'] in DERIVATIONS)
        tools = {nodes[k]['tool'] for k in reachable if nodes[k]['kind'] == 'effect'}
        checks['FlowSafe'] = all(ROLES[t] <= bindings[t].keys() and
                                all(valid_binding(b) for b in bindings[t].values()) and
                                all(k in c['argument_types'] for k in bindings[t]) for t in tools)
        counts = Counter(n['tool'] for n in nodes.values() if n['kind'] == 'effect')
        checks['ScopeSafe'] = all(type(may[t]['budget']) is int and may[t]['budget'] >= counts[t] and
                                 may[t]['constraints']['actor'] == c['actor'] and
                                 may[t]['constraints']['claim'] == c['trusted_request']['claim'] and
                                 may[t]['constraints']['customer'] == c['trusted_request']['customer'] and
                                 type(may[t]['constraints']['amount_max']) is int and may[t]['constraints']['amount_max'] > 0
                                 for t in tools) and all(
                                     'amount' not in v or v['amount'] <= may[nodes[k]['tool']]['constraints']['amount_max']
                                     for k, v in c['VERIFY'].items())
        observable = {'issue_refund': {'kind', 'record', 'claim', 'claimant', 'order', 'amount', 'currency', 'to', 'settled'},
                      'message_party': set(c['argument_types']) | {'kind', 'actor'}, 'close_case': {'kind', 'claim'}}
        kinds = {'issue_refund': 'refund', 'message_party': 'notice', 'close_case': 'case_closed'}
        checks['VerifySafe'] = all(k in c['VERIFY'] and set(c['VERIFY'][k]) <= observable[nodes[k]['tool']] and
                                   c['VERIFY'][k].get('kind') == kinds[nodes[k]['tool']] and
                                   ('amount' not in c['VERIFY'][k] or type(c['VERIFY'][k]['amount']) is int and c['VERIFY'][k]['amount'] > 0) and c['VERIFY'][k].get('kind') in ('refund', 'notice', 'case_closed')
                                   and c['VERIFY'][k].get('claim') == c['trusted_request']['claim']
                                   for k in reachable if nodes[k]['kind'] == 'effect')
    except (KeyError, TypeError):
        checks['WellFormed'] = False
    except (ValueError, RecursionError):
        pass
    return checks


class InvalidContract(ValueError):
    pass


class DispatchFailure(ValueError):
    pass


class TraceGrant:
    def __init__(self, poec, *, certificate_key):
        self.validation = static_checks(poec)
        if not all(self.validation.values()):
            raise InvalidContract(str(self.validation))
        if not isinstance(certificate_key, bytes) or len(certificate_key) < 32:
            raise ValueError('explicit simulator certificate key required')
        self.c = deepcopy(poec)
        self._key, self._lock = certificate_key, RLock()
        self.states = {k: 'PENDING' for k in poec['MUST']}
        self.evidence, self.certificates, self.receipts, self.history = {}, {}, [], []
        self.budget = {t: rule['budget'] for t, rule in poec['MAY'].items()}
        self._activate()

    def _activate(self):
        for _ in self.states:
            for key, node in self.c['MUST'].items():
                if self.states[key] == 'PENDING' and (key in self.c['roots'] or node['depends']) and all(self.states[p] == 'VERIFIED' for p in node['depends']):
                    self.states[key] = 'ACTIVE'

    def admit(self, obligation, candidates, *, authenticated_source, query):
        """Trusted host-only admission, never an actor-callable endpoint.

        Source authentication is supplied by the simulator host, not an agent
        argument. Candidate integrity pins canonical id/version/kind/fields.
        Selection is the sole exact matching record, never first-of-many.
        """
        with self._lock:
            n = self.c['MUST'].get(obligation, {})
            if self.states.get(obligation) != 'ACTIVE' or n.get('kind') != 'evidence':
                return False
            if authenticated_source != n['source'] or query != n['query']:
                return False
            matched = []
            for row in candidates:
                body = {k: row[k] for k in ('id', 'version', 'kind', 'fields') if k in row}
                if (len(body) != 4 or type(body['version']) is not int or body['version'] < 1 or
                        not isinstance(body['fields'], dict) or body['id'] != n['record'] or
                        body['kind'] != query['kind'] or row.get('integrity') != digest(body)):
                    continue
                if all(k in body['fields'] and type(body['fields'][k]) in types for k, types in EVIDENCE_TYPES.get(body['kind'], {}).items()) and all(body['fields'].get(k) == v for k, v in query.items() if k != 'kind'):
                    matched.append(body)
            if len(matched) != 1:
                return False
            self.evidence[obligation] = deepcopy(matched[0])
            self.states[obligation] = 'VERIFIED'
            self.history.append({'type': 'evidence_admitted', 'obligation': obligation, 'record': deepcopy(matched[0]),
                                 'authenticated_source': authenticated_source, 'query': deepcopy(query)})
            self._activate()
            return True

    def _proof(self, slot, spec, value, node, args):
        requested = self.c['trusted_request']
        proof = {'slot': slot, 'value': deepcopy(value)}
        if 'values' in spec:
            return dict(proof, source='contract') if value in spec['values'] else None
        if spec.get('derive') == 'own_settlement':
            matches = [r for r in self.receipts if r['effect'].get('kind') == 'refund' and r['effect'].get('record') == str(value).split('@v')[0]]
            return dict(proof, source='receipt', receipt=matches[0]['id'], record=deepcopy(matches[0]['record_provenance'])) if len(matches) == 1 else None
        if spec.get('derive') == 'notice_amount':
            required = node.get('amount', requested['amount'])
            if value != required:
                return None
            if node.get('template') == 'refund_denied':
                row, claim = self.evidence.get('support'), self.evidence.get('claim')
                if not row or not claim:
                    return None
                f, total = row['fields'], claim['fields']['amount']
                allowed = (total if f.get('received') is False or f.get('status') == 'delivered' else
                           max(0, total - f.get('failed_value', total)) if f.get('status') == 'partial' else 0)
                return dict(proof, source='evidence', obligation='support', record=deepcopy(row)) if 0 < value <= allowed else None
            receipts = [r for r in self.receipts if r['effect'].get('kind') == 'refund' and r['effect'].get('amount', 0) >= value]
            return dict(proof, source='receipt', receipt=receipts[0]['id'], record=deepcopy(receipts[0]['record_provenance'])) if len(receipts) == 1 else None
        if 'evidence' in spec:
            row = self.evidence.get(spec['evidence'])
            if not row:
                return None
            fields = row['fields']
            if spec.get('derive') == 'supported_amount':
                supported = (requested['amount'] if fields.get('received') is True else
                             fields.get('failed_value', 0) if fields.get('status') in ('delivery_failed', 'partial') else 0)
                valid = type(value) is int and 0 < value <= supported and value == requested[spec['constant']]
            elif spec.get('derive') == 'denial_record':
                valid = (str(value).split('@v')[0] == row['id'] and
                         (fields.get('received') is False or fields.get('status') == 'delivered' or
                          fields.get('status') == 'partial' and node.get('amount', args.get('amount', 0)) <=
                          self.evidence['claim']['fields']['amount'] - fields.get('failed_value', self.evidence['claim']['fields']['amount'])))
            else:
                valid = value == fields.get(spec.get('field'))
            return dict(proof, source='evidence', obligation=spec['evidence'], record=deepcopy(row)) if valid else None
        return dict(proof, source='trusted_request') if value == requested[spec['constant']] else None

    def decide(self, actor, tool, arguments, *, risk=False):
        with self._lock:
            args = deepcopy(arguments)
            # The risk detector is inert in W0 by explicit ruling 6. This hook
            # tests the ordered decision independently outside W0, without a model.
            if risk:
                return {'decision': 'STEP_UP_AUTH'}
            may = self.c['MAY'].get(tool)
            valid_types = isinstance(args, dict) and tool in REQUIRED and REQUIRED[tool] <= args.keys() and all(
                key in self.c['argument_types'] and type(value) is TYPES[self.c['argument_types'][key]] for key, value in args.items()) and all(type(x) is str for x in args.get('asserts', []))
            if not may or not valid_types or actor != self.c['actor'] or self.budget.get(tool, 0) <= 0:
                return {'decision': 'DENY', 'reason': 'MAY/schema/budget'}
            scope = may['constraints']
            if (args.get('claim', args.get('case')) != scope['claim'] or
                    args.get('amount', 0) > scope['amount_max']):
                return {'decision': 'DENY', 'reason': 'scope'}
            nodes = [(k, n) for k, n in self.c['MUST'].items() if n['kind'] == 'effect' and n['tool'] == tool and
                     self.states[k] == 'ACTIVE' and ('template' not in n or n['template'] == args.get('template'))]
            if len(nodes) != 1:
                return {'decision': 'DENY', 'reason': 'no unique active obligation'}
            key, node = nodes[0]
            proofs, missing = [], []
            for slot in sorted(ROLES[tool] & args.keys()):
                proof = self._proof(slot, self.c['BIND'][tool][slot], args[slot], node, args)
                (proofs if proof else missing).append(proof if proof else slot)
            if missing:
                return {'decision': 'PROOF_GAP', 'missing_slots': missing}
            self.budget[tool] -= 1
            cid = 'EC' + str(len(self.certificates) + 1)
            cert = {'id': cid, 'contract': self.c['id'], 'actor': actor, 'obligation': key, 'tool': tool,
                    'arguments': args, 'proofs': proofs, 'budget_state': deepcopy(self.budget)}
            cert['authentication'] = hmac.new(self._key, canonical(cert), hashlib.sha256).hexdigest()
            self.certificates[cid] = {'certificate': deepcopy(cert), 'status': 'live'}
            self.history.append({'type': 'certificate_issued', 'certificate': deepcopy(cert)})
            return {'decision': 'ALLOW', 'certificate': cert}

    def dispatch(self, certificate, actor, tool, arguments, world, *, fault=None):
        """Consume on dispatch; observe actual world state; rollback failed effects.

        Only cited evidence freshness is checked, not global revisions or TAA
        policy. World transactions and source locks are simulator infrastructure.
        """
        with self._lock:
            row = self.certificates.get(certificate.get('id')) if isinstance(certificate, dict) else None
            if (not row or row['status'] != 'live' or canonical(certificate) != canonical(row['certificate']) or
                    actor != certificate['actor'] or tool != certificate['tool'] or
                    canonical(arguments) != canonical(certificate['arguments'])):
                return {'dispatch': 'refused', 'reason': 'certificate mismatch or replay'}
            row['status'] = 'consumed'
            node = certificate['obligation']
            old_states, old_receipts = deepcopy(self.states), deepcopy(self.receipts)
            try:
                with world.transaction():
                    if self.states[node] != 'ACTIVE':
                        raise DispatchFailure('obligation no longer active')
                    for proof in certificate['proofs']:
                        if proof['source'] in ('evidence', 'receipt') and world.current(proof['record']['id']) != proof['record']:
                            raise DispatchFailure('cited provenance superseded')
                    before = world.snapshot()
                    world.apply(tool, arguments, actor)
                    if fault == 'after_effect':
                        raise DispatchFailure('injected after actual effect')
                    effect = world.observed_effect(before, tool)
                    bound = ({k: arguments[k] for k in ('claim', 'to', 'amount')} if tool == 'issue_refund' else
                             {k: arguments[k] for k in ('claim', 'to', 'amount', 'template')} if tool == 'message_party' else
                             {'claim': arguments['case']})
                    if not all(k in effect and effect[k] == v for k, v in bound.items()):
                        raise DispatchFailure('actual effect differs from certified arguments')
                    expected = self.c['VERIFY'][node]
                    if not all(effect.get(k) == v for k, v in expected.items()):
                        raise DispatchFailure('postcondition failed')
                    receipt = {'id': 'R' + str(len(self.receipts) + 1), 'contract': self.c['id'],
                               'obligation': node, 'certificate': deepcopy(certificate), 'status': 'success',
                               'effect': effect, 'record_provenance': world.current(effect['record']) if effect['kind'] == 'refund' else None}
                    self.receipts.append(receipt)
                    self.states[node] = 'VERIFIED'
                    self._activate()
                    if fault == 'after_receipt':
                        raise DispatchFailure('injected after actual receipt')
            except Exception as error:
                self.states, self.receipts = old_states, old_receipts
                self.budget[tool] += 1
                self.history.append({'type': 'dispatch_rolled_back', 'certificate': certificate['id'], 'reason': str(error)})
                return {'dispatch': 'rolled_back', 'reason': str(error)}
            self.history.append({'type': 'receipt', 'receipt': deepcopy(receipt)})
            return {'dispatch': 'committed', 'receipt': deepcopy(receipt)}

    def final_answer(self, *, claims_success):
        missing = [k for k, n in self.c['MUST'].items() if n['hard'] and self.states[k] != 'VERIFIED']
        return {'accepted': not claims_success or not missing, 'unverified_hard': missing,
                'WAIVED_reachable': False}
