"""Offline native Gemma suffix, retry, replacement and source-integrity fixtures."""
import hashlib
import io
import json
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from tests.ledger_snapshots import PREFIX, install_snapshots

from agents.call_telemetry import BudgetStopped
from formation.evaluation_gemma_v0222 import ROOT, OUTPUT, MODEL, PRICES, GemmaRecorder, name, read, sha
from formation.evaluation_gemma_continuation_v0223 import (PLAN, APPROVAL_TEXT,
    review_source, run_continuation, RetryGemmaChat, RetryQuota)
from formation.evaluation_runner_v0218 import execute_cell
from formation.study_a import load_cases
from formation.study_a_pilot import SYSTEM
from formation.transport_retry_v0223 import RetryTransport


class Response:
    def __init__(self, data):
        self.raw = data if isinstance(data, bytes) else json.dumps(data).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read1(self, size):
        result, self.raw = self.raw[:size], self.raw[size:]
        return result


def native(raw, stop='STOP'):
    return Response({'modelVersion': MODEL, 'responseId': 'declared fixture',
        'usageMetadata': {'promptTokenCount': 100, 'candidatesTokenCount': 50,
                          'thoughtsTokenCount': 10, 'totalTokenCount': 160},
        'candidates': [{'finishReason': stop, 'content': {'parts': [{'text': raw}]}}]})


def rejected(code, seconds=None):
    return urllib.error.HTTPError('https://fixture.invalid', code, 'fixture',
        {} if seconds is None else {'retry-after': str(seconds)}, io.BytesIO(b'{"error":{}}'))


class GemmaContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'root'
        self.root.mkdir()
        self.plan = read(PLAN)
        self.plan['checkout_root'] = str(self.root)
        files = set(self.plan['adapter_sha256']) | set(self.plan['other_ledger_sha256']) | {
            'results/formation-spending-v021/google.json',
            'studies/formation-study-a-fixtures-v0213.json',
            'studies/formation-study-a-pressure-fixtures-v0215.json'}
        files |= {c['path'] for c in self.plan['pending_cells'] + self.plan['initial_replacements']}
        files |= {c['path'] for c in read(ROOT / 'studies/formation-study-a-gemma31-plan-v0222.json')['cells'][:3]}
        for relative in files:
            if relative.startswith(PREFIX):continue  # Installed from checked frozen snapshots below.
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        install_snapshots(self.root, dict(self.plan['other_ledger_sha256'], **{PREFIX+'google.json':self.plan['Google_ledger_start_sha256']}))
        self.output = self.root / self.plan['output']
        # Build the reviewed pre-continuation snapshot, not a copy of the live
        # folder: later commits include a completed continuation and its manifest.
        self.output.mkdir(parents=True)
        for relative, digest in self.plan['source_sha256'].items():
            target = self.output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OUTPUT / relative, target)
            self.assertEqual(sha(target), digest, relative)
        ledger = self.root / 'results/formation-spending-v021/google.json'
        self.assertEqual(sha(ledger), self.plan['Google_ledger_start_sha256'])
        self.plan_path = self.root / PLAN.relative_to(ROOT)
        self.plan_path.write_text(json.dumps(self.plan, indent=2))
        self.clock, self.waits = [2000000000.], []
        self.key = patch.object(RetryGemmaChat, '_key', return_value='fixture-only')
        self.key.start()
        self.addCleanup(self.key.stop)
        fixtures = []
        for file in ('studies/formation-study-a-fixtures-v0213.json', 'studies/formation-study-a-pressure-fixtures-v0215.json'):
            fixtures += read(ROOT / file)['fixtures']
        self.good = {f['case_id']: [p['raw'] for p in f['packets']] for f in fixtures if f['name']=='required_conduct'}

    def approve(self):
        (self.root / self.plan['execution_approval_path']).write_text(json.dumps({
            'approval': APPROVAL_TEXT, 'plan_sha256': sha(self.plan_path)}))

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.clock[0] += seconds

    def test_execution_approval_barrier_before_any_credentials_transport_or_new_evidence(self):
        before = {p.name: sha(p) for p in self.output.iterdir() if p.is_file()}
        with patch('urllib.request.urlopen') as send, patch.object(RetryGemmaChat, '_key') as key:
            with self.assertRaises(ValueError):
                run_continuation(self.plan_path, root=self.root)
            with self.assertRaisesRegex(ValueError, 'execution approval absent'):
                run_continuation(self.plan_path, approved=True, root=self.root)
            send.assert_not_called()
            key.assert_not_called()
        self.assertEqual(before, {p.name: sha(p) for p in self.output.iterdir() if p.is_file()})

    def test_source_exact_suffix_failure_replacement_and_tamper_stop(self):
        plan = review_source(self.plan_path, self.root)
        self.assertEqual(len(plan['pending_cells']), 237)
        self.assertEqual((plan['pending_cells'][0]['case_id'], plan['pending_cells'][0]['repeat']), ('A_R02',1))
        self.assertEqual(plan['initial_replacements'][0]['case_id'], 'P_R02')
        for relative in ('calls.jsonl','P_R02-r01.json','P_R02-r01-checkpoint.json','gemma-quota.json'):
            path = self.output / relative
            before = path.read_bytes()
            path.write_bytes(before + b' ')
            with self.assertRaises(ValueError):
                review_source(self.plan_path, self.root)
            path.write_bytes(before)
        self.plan['pending_cells'] = self.plan['pending_cells'][1:]
        self.plan_path.write_text(json.dumps(self.plan))
        with self.assertRaises(ValueError):
            review_source(self.plan_path, self.root)

    def client(self):
        quota = RetryQuota(self.root / 'fixture-quota.json', self.root / 'fixture-counts.jsonl', now=lambda:self.clock[0])
        rec = GemmaRecorder(self.root / 'fixture-calls.jsonl', PRICES, MODEL,
            max_logical=20, max_attempts=100, max_dollars=8, prior_spend=self.plan['Google_cumulative_dollars'])
        retry = RetryTransport(self.root/'fixture-retry.json', self.root/'fixture-transport.jsonl',
            now=lambda:self.clock[0], sleep=self.sleep)
        return RetryGemmaChat(rec, quota, retry), rec, quota, retry

    def test_native_503_retry_same_full_history_one_model_reply(self):
        client, rec, quota, retry = self.client()
        cell = self.plan['pending_cells'][0]
        case = load_cases([ROOT / cell['path']])[0]
        raws, generations, rejected_once = iter(self.good[cell['case_id']]), [], [False]
        def send(request, **kwargs):
            body = json.loads(request.data)
            if request.full_url.endswith(':countTokens'):
                return Response({'totalTokens':100})
            generations.append(body)
            self.clock[0] += 1
            if not rejected_once[0]:
                rejected_once[0]=True
                raise rejected(503)
            return native(next(raws))
        with patch('urllib.request.urlopen', side_effect=send):
            result, state = execute_cell(cell, case, client, rec, self.root/'checkpoint.json')
        self.assertEqual(state,'complete')
        self.assertEqual(result['score']['outcome'],'correct')
        self.assertEqual(generations[0],generations[1])
        self.assertEqual(retry.state['requests_needing_retry'],1)
        events=[json.loads(l) for l in rec.path.read_text().splitlines()]
        self.assertEqual(sum(e['event']=='attempt_end' for e in events),len(self.good[cell['case_id']])+1)
        self.assertEqual(sum(e['event']=='native_response' for e in events),len(self.good[cell['case_id']]))

    def test_partial_reset_or_malformed_native_bytes_never_resent(self):
        class Partial(Response):
            def read1(self,size):
                if self.raw:
                    result,self.raw=self.raw,b''
                    return result
                raise ConnectionResetError()
        for i, response in enumerate((Partial(b'{"candidates":['), Response(b'not native JSON'))):
            folder=self.root/('variant%d'%i)
            folder.mkdir()
            quota=RetryQuota(folder/'q.json',folder/'counts.jsonl',now=lambda:self.clock[0])
            rec=GemmaRecorder(folder/'calls.jsonl',PRICES,MODEL,max_logical=5,max_attempts=25,max_dollars=8)
            engine=RetryTransport(folder/'retry.json',folder/'attempts.jsonl',now=lambda:self.clock[0],sleep=self.sleep)
            client=RetryGemmaChat(rec,quota,engine)
            generations=[]
            def send(request,**kwargs):
                if request.full_url.endswith(':countTokens'):
                    return Response({'totalTokens':100})
                generations.append(request.data)
                return response
            from formation.clients import ProviderError
            with patch('urllib.request.urlopen',side_effect=send):
                with self.assertRaises(ProviderError):
                    client.chat(SYSTEM,[{'role':'user','content':'neutral declared fixture'}])
            self.assertEqual(len(generations),1)
            self.assertFalse(client.last_transport_lost)
            self.assertEqual(engine.state['requests_needing_retry'],0)

    def test_native_malformed_refusal_first_reply_scored_no_retry_or_replacement(self):
        for i,response in enumerate((native('not model JSON'),native('',stop='SAFETY'))):
            client,rec,quota,retry=self.client()
            cell=dict(self.plan['pending_cells'][i],replacement=False)
            case=load_cases([ROOT/cell['path']])[0]
            self.clock[0]+=61
            def send(request,**kwargs):
                return Response({'totalTokens':100}) if request.full_url.endswith(':countTokens') else response
            with patch('urllib.request.urlopen',side_effect=send):
                result,state=execute_cell(cell,case,client,rec,self.root/('reply%d.json'%i))
            self.assertEqual(state,'complete')
            self.assertFalse(result['fatal_transport'])
            self.assertFalse(client.last_transport_lost)
            self.assertIn(result['score']['terminal_status'],('malformed_reply','provider_refusal'))
            self.assertEqual(retry.state['requests_needing_retry'],0)

    def test_full_237_suffix_429_and_503_then_end_replacement_preserves_all_source(self):
        self.approve()
        all_source={p.name:sha(p) for p in self.output.iterdir() if p.is_file()}
        counts, generation_bodies, turns, jobs, order = [0], [], {}, {}, []
        def send(request,**kwargs):
            body=json.loads(request.data)
            if request.full_url.endswith(':countTokens'):
                counts[0]+=1
                if counts[0]==1:
                    raise rejected(429,75)
                return Response({'totalTokens':100})
            events=[json.loads(l) for l in (self.output/'continuation-calls.jsonl').read_text().splitlines()]
            ctx=next(e['context'] for e in reversed(events) if e['event']=='logical_start')
            slot=name(ctx);job=(slot,ctx['turn']);jobs[job]=jobs.get(job,0)+1
            order.append(slot);generation_bodies.append(body)
            self.clock[0]+=61
            if len(order)==1:
                raise rejected(503,90)
            self.assertEqual(body['generationConfig'],{'responseMimeType':'application/json','maxOutputTokens':2048})
            turn=turns.get(slot,0);turns[slot]=turn+1
            return native(self.good[ctx['case_id']][turn])
        with patch('urllib.request.urlopen',side_effect=send) as transport:
            final=run_continuation(self.plan_path,True,self.root,now=lambda:self.clock[0],sleep=self.sleep)
            self.assertEqual(final['completed_untouched_cells'],237)
            self.assertEqual(final['replacement_completed_cells'],1)
            self.assertEqual(final['requests_needing_retry'],2)
            self.assertEqual(generation_bodies[0],generation_bodies[1])
            self.assertTrue(all(r['outcome']=='correct' for r in final['records']))
            self.assertEqual(order[-1],'P_R02-r01-replacement-01')
            first_replacement=next(i for i,x in enumerate(order) if '-replacement-' in x)
            self.assertTrue(all('-replacement-' in x for x in order[first_replacement:]))
            self.assertEqual(len({x for x in order[:first_replacement]}),237)
            from scripts.formation_study_a_gemma31_continuation_audit import audit
            checked=audit(self.plan_path,self.root)
            self.assertTrue(checked['no_resend_after_received_output'])
            self.assertEqual(checked['combined_primary_cells'],240)
            calls=transport.call_count
            again=run_continuation(self.plan_path,True,self.root,now=lambda:self.clock[0],sleep=self.sleep)
            self.assertEqual(transport.call_count,calls)
            self.assertEqual(again['completed_untouched_cells'],237)
        for name_,digest in all_source.items():
            self.assertEqual(sha(self.output/name_),digest,name_)
        self.assertEqual(read(self.root/'results/formation-spending-v021/google.json')['estimated_api_dollars'],self.plan['Google_cumulative_dollars'])


if __name__=='__main__':
    unittest.main()
