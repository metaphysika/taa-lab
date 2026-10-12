"""Offline transport/ledger fixtures. No actual provider requests or credentials."""
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from agents.call_telemetry import BudgetStopped, CallRecorder
from formation.transport_retry_v0223 import RetryTransport, RetryExhausted, RetryRunLimit, ReplyReceivedFailure


def http_error(code, retry=None, data=None):
    headers = {} if retry is None else {'retry-after': str(retry)}
    return urllib.error.HTTPError('https://fixture.invalid', code, 'declared fixture', headers,
                                  io.BytesIO(json.dumps(data or {}).encode()))


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.clock = [1000.]
        self.waits, self.starts, self.failures = [], [], []
        self.engine = self.restore()

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.clock[0] += seconds

    def restore(self):
        return RetryTransport(self.folder / 'state.json', self.folder / 'attempts.jsonl',
                              now=lambda: self.clock[0], sleep=self.sleep)

    def begin(self):
        self.starts.append(self.clock[0])
        return len(self.starts)

    def failed(self, token, meta, output, reply):
        self.failures.append((token, meta, output, reply))

    def test_503_then_success_identical_body_two_ledger_attempts(self):
        sends = []
        def send(received):
            sends.append('same request')
            if len(sends) == 1:
                raise http_error(503)
            received()
            return {'native': 'first reply'}
        result = self.engine.execute('request', {'full': 'history'}, self.begin, send, self.failed)
        self.assertEqual(result, {'native': 'first reply'})
        self.assertEqual(self.starts, [1000., 1010.])
        self.assertEqual(len(self.failures), 1)
        self.assertEqual(self.engine.state['requests_needing_retry'], 1)
        events = [json.loads(l) for l in self.engine.journal.read_text().splitlines()]
        self.assertEqual(sum(e['event'] == 'transport_attempt_start' for e in events), 2)
        self.assertEqual(sum(e['event'] == 'transport_attempt_end' for e in events), 2)

    def test_429_honors_retry_after_and_google_retry_info(self):
        for i, error in enumerate((http_error(429, 75), http_error(429, data={'error': {'details': [{
                '@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '91s'}]}}))):
            count = [0]
            at = self.clock[0]
            def send(received):
                count[0] += 1
                if count[0] == 1:
                    raise error
                received()
                return {}
            self.engine.execute('rate-%d' % i, {}, self.begin, send, self.failed)
            self.assertEqual(self.clock[0] - at, (75, 91)[i])

    def test_all_retryable_transport_classes_and_no_arbitrary_unknown_errors(self):
        for i, error in enumerate([http_error(c) for c in (429,500,502,503,504)] + [
                ConnectionResetError(), TimeoutError(), urllib.error.URLError(TimeoutError())]):
            calls = [0]
            def send(received):
                calls[0] += 1
                if calls[0] == 1:
                    raise error
                return {'received': True}
            self.engine.execute('eligible-%d' % i, {}, self.begin, send, self.failed)
            self.assertEqual(calls[0], 2)
        for i, error in enumerate((http_error(401), http_error(400), ValueError())):
            calls = [0]
            def send(received):
                calls[0] += 1
                raise error
            with self.assertRaises(type(error)):
                self.engine.execute('ineligible-%d' % i, {}, self.begin, send, self.failed)
            self.assertEqual(calls[0], 1)

    def test_five_total_attempts_then_stop_increasing_waits(self):
        def send(received):
            raise http_error(503)
        with self.assertRaises(RetryExhausted):
            self.engine.execute('outage', {}, self.begin, send, self.failed)
        self.assertEqual(len(self.starts), 5)
        self.assertEqual(self.starts, [1000,1010,1040,1100,1220])
        self.assertEqual(len(self.failures), 5)
        self.assertEqual(self.engine.state['stop'], 'five_attempts_exhausted')
        with self.assertRaises(BudgetStopped):
            self.restore().execute('outage', {}, self.begin, send, self.failed)
        self.assertEqual(len(self.starts), 5)

    def test_eleventh_retry_needed_request_stops_before_second_attempt_persisted(self):
        for i in range(11):
            calls = [0]
            def send(received):
                calls[0] += 1
                if calls[0] == 1:
                    raise http_error(502)
                received()
                return {}
            self.engine = self.restore()
            if i == 10:
                with self.assertRaises(RetryRunLimit):
                    self.engine.execute('job-%d' % i, {}, self.begin, send, self.failed)
                self.assertEqual(calls[0], 1)
            else:
                self.engine.execute('job-%d' % i, {}, self.begin, send, self.failed)
        self.assertEqual(len(self.starts), 21)
        self.assertEqual(self.restore().state['requests_needing_retry'], 11)

    def test_any_partial_reply_blocks_resend_on_timeout_and_reset(self):
        for i, error in enumerate((TimeoutError(), ConnectionResetError(), ValueError())):
            before = len(self.starts)
            def send(received):
                received()
                raise error
            with self.assertRaises(ReplyReceivedFailure):
                self.engine.execute('partial-%d' % i, {}, self.begin, send, self.failed)
            self.assertEqual(len(self.starts), before + 1)
            self.assertTrue(self.failures[-1][2])
            with self.assertRaises(BudgetStopped):
                self.restore().execute('partial-%d' % i, {}, self.begin, send, self.failed)
        self.assertEqual(self.engine.state['requests_needing_retry'], 0)

    def test_model_reply_on_http_error_is_never_retried(self):
        def send(received):
            raise http_error(503, data={'candidates': [{'content': {'parts': [{'text': 'fixture reply'}]}}]})
        with self.assertRaises(ReplyReceivedFailure):
            self.engine.execute('received-on-error', {}, self.begin, send, self.failed)
        self.assertEqual(len(self.starts), 1)
        self.assertTrue(self.failures[0][2])
        self.assertIsNotNone(self.failures[0][3])

    def test_received_malformed_refusing_or_empty_reply_is_not_resampled(self):
        for i, reply in enumerate(('not JSON', {'refusal': True}, '')):
            result = self.engine.execute('reply-%d' % i, {}, self.begin, lambda mark: reply, self.failed)
            self.assertEqual(result, reply)
            with self.assertRaises(BudgetStopped):
                self.restore().execute('reply-%d' % i, {}, self.begin, lambda mark: 'better reply', self.failed)
        self.assertEqual(len(self.starts), 3)

    def test_resume_pending_backoff_same_body_and_no_unclosed_restart(self):
        class Interrupted(BaseException):
            pass
        calls = [0]
        def send(mark):
            calls[0] += 1
            if calls[0] == 1:
                raise http_error(503)
            mark()
            return {}
        self.engine.sleep = lambda seconds: (_ for _ in ()).throw(Interrupted())
        with self.assertRaises(Interrupted):
            self.engine.execute('resume', {'same': True}, self.begin, send, self.failed)
        with self.assertRaises(BudgetStopped):
            self.restore().execute('resume', {'same': False}, self.begin, send, self.failed)
        restored = self.restore()
        restored.execute('resume', {'same': True}, self.begin, send, self.failed)
        self.assertEqual(calls[0], 2)
        self.assertEqual(restored.state['requests_needing_retry'], 1)
        def crash(mark):
            raise Interrupted()
        with self.assertRaises(Interrupted):
            restored.execute('inflight', {}, self.begin, crash, self.failed)
        with self.assertRaises(BudgetStopped):
            self.restore().execute('inflight', {}, self.begin, send, self.failed)

    def test_paid_timeout_reserve_retained_and_budget_blocks_retry(self):
        ledger = self.folder / 'paid.json'
        rec = CallRecorder(self.folder / 'paid-calls.jsonl', {
            'fixture': {'input_per_million': 1, 'output_per_million': 1}}, 'fixture',
            max_logical=1, max_attempts=5, max_dollars=8, prior_spend=7.998, ledger_path=ledger)
        rec.logical('fixture', 'fixture')
        body = {'messages': [{'content': 'fixture'}], 'max_tokens': 1500}
        sends = [0]
        def begin():
            return rec.before_attempt(body)
        def send(mark):
            sends[0] += 1
            raise TimeoutError()
        def failed(aid, meta, output, reply):
            rec.finish_attempt(aid, error=meta['error_class'])
        with self.assertRaises(BudgetStopped):
            self.engine.execute('paid', body, begin, send, failed)
        self.assertEqual(sends[0], 1)
        self.assertGreater(json.loads(ledger.read_text())['estimated_api_dollars'], 7.998)
        closed = [json.loads(l) for l in rec.path.read_text().splitlines() if json.loads(l)['event']=='attempt_end']
        self.assertTrue(closed[0]['reserve_retained'])


if __name__ == '__main__':
    unittest.main()
