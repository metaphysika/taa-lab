"""Offline policy and pacing tests; no network or changes to study evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agents.call_telemetry import BudgetStopped
from formation import study_c_usage_proposal_v0244 as p
from formation.study_b_parser_v0234 import parse_action
from formation.transport_retry_v0223 import RetryTransport


class UsageProposalTests(unittest.TestCase):
    def response(self):
        return dict(modelVersion=p.MODEL, responseId='fixture', candidates=[
            {'content': {'parts': [{'text': '{"tool":null,"args":{}}'}]}}],
            usageMetadata=dict(promptTokenCount=2452, totalTokenCount=2452))

    def test_exact_reserve_separate_from_native_usage(self):
        response=self.response();before=copy.deepcopy(response)
        booking=p.conservative_booking(p.MODEL,response,2452)
        self.assertEqual(booking['output_tokens_booked'],4096)
        self.assertIsNone(booking['output_tokens_native'])
        self.assertEqual(booking['label'],'usage missing; conservative reserve booked')
        self.assertEqual(response,before)

    def test_paid_models_cannot_use_missing_usage_exception(self):
        for model in ['claude-haiku-5-5','gemini-3.1-flash-lite','gpt-6-luna']:
            with self.subTest(model=model),self.assertRaises(BudgetStopped):
                p.conservative_booking(model,self.response(),2452)

    def test_identity_and_independent_guards_not_waived(self):
        for key,value in [('promptTokenCount',True),('promptTokenCount',3000),
                          ('thoughtsTokenCount',4097),('cachedContentTokenCount',2453),
                          ('totalTokenCount',100),('totalTokenCount',7000)]:
            response=self.response();response['usageMetadata'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(BudgetStopped):
                p.conservative_booking(p.MODEL,response,2452)
        response=self.response();response['modelVersion']='different'
        with self.assertRaises(BudgetStopped):p.conservative_booking(p.MODEL,response,2452)
        with self.assertRaises(BudgetStopped):p.conservative_booking(p.MODEL,self.response(),11777)

    def test_present_output_usage_stays_with_strict_existing_validator(self):
        response=self.response();response['usageMetadata']['candidatesTokenCount']=-1
        self.assertIsNone(p.conservative_booking(p.MODEL,response,2452))

    def test_thought_tokens_are_not_added_twice(self):
        response=self.response();response['usageMetadata'].update(thoughtsTokenCount=100,totalTokenCount=2552)
        self.assertEqual(p.conservative_booking(p.MODEL,response,2452)['output_tokens_booked'],4096)

    def test_persisted_count_includes_stopped_reply_and_sixth_stops(self):
        state={};booking=p.conservative_booking(p.MODEL,self.response(),2452)
        for i in range(1,7):
            before=copy.deepcopy(state);new=p.book_once(state,'A%06d'%i,booking)
            self.assertEqual(state,before)
            state=json.loads(json.dumps(new))  # Persistent state across controllers.
            self.assertEqual(state['missing_usage_count'],i)
            self.assertEqual(state['review_required'],i>5)
            if i <= 5:p.require_calls_allowed(state)
            else:
                with self.assertRaises(BudgetStopped):p.require_calls_allowed(state)
        self.assertEqual(p.book_once(state,'A000006',booking),state)
        with self.assertRaises(BudgetStopped):p.book_once(state,'A000006',dict(booking,label='different'))

    def test_received_generation_job_never_resent(self):
        with tempfile.TemporaryDirectory() as directory:
            retry=RetryTransport(Path(directory)/'state.json',Path(directory)/'journal.jsonl')
            body={'fixture':'immutable'}
            from formation.evaluation_gemma_v0222 import body_hash
            retry.state['jobs']['received']=dict(body_sha256=body_hash(body),attempts=1,received=True,phase='complete',ready_at=0,counted_retry=False)
            begin=Mock();send=Mock();failed=Mock()
            with self.assertRaises(BudgetStopped):retry.execute('received',body,begin,send,failed)
            begin.assert_not_called();send.assert_not_called();failed.assert_not_called()

    def test_booking_does_not_change_parser_or_malformed_labels(self):
        response=self.response();p.conservative_booking(p.MODEL,response,2452)
        self.assertEqual(parse_action(response['candidates'][0]['content']['parts'][0]['text'])['tool'],None)
        with self.assertRaises(ValueError):parse_action('[{"tool":null,"args":{}}]')

    def test_maximum_single_context_waits_but_is_not_excluded(self):
        events=p.reserve_combined([],11776,0,'first')
        self.assertEqual(events[0]['tokens'],16000)
        self.assertEqual(p.combined_ready_at(events,0,1),61)
        self.assertEqual(p.reserve_combined(events,11776,61,'second')[-1]['tokens'],16000)

    def test_every_61second_window_with_full_output_reserves(self):
        events=[];now=0.
        for i in range(1000):
            count=[0,1028,2452,8000,11776][i%5]
            now=p.combined_ready_at(events,count,now)
            events=p.reserve_combined(events,count,now,str(i))
            self.assertLessEqual(sum(e['tokens'] for e in events if now-e['at']<61),16000)
            now+=.01
        self.assertGreater(now,61)

    def test_invalid_or_duplicate_pacing_history_stops(self):
        events=p.reserve_combined([],2452,0,'one')
        with self.assertRaises(BudgetStopped):p.reserve_combined(events,2452,0,'one')
        with self.assertRaises(BudgetStopped):p.combined_ready_at([dict(at=2,tokens=100)],0,1)


if __name__=='__main__':unittest.main()
