import unittest
from exploratory.measurement_v02456.policy import parse_action, protocol_bounds

class PolicyTests(unittest.TestCase):
    def test_stop_and_multiple(self):
        for mode in ('first', 'malformed'):
            for tool in ('null', '"null"'):
                self.assertIsNone(parse_action('{"tool":'+tool+',"args":{}}',mode)['tool'])
        text='{"tool":"null","args":{}} {"tool":"dispatch_shipment","args":{}}'
        self.assertIsNone(parse_action(text,'first')['tool'])
        with self.assertRaises(ValueError): parse_action(text,'malformed')
    def test_no_nested_or_truncated_salvage(self):
        for text in ('[{"tool":null,"args":{}}]', '{"x":{"tool":null,"args":{}}', '{"tool":null,"tool":"null","args":{}}'):
            with self.assertRaises(ValueError): parse_action(text,'first')
    def test_bracketed_prose_preserves_single_reply_acceptance(self):
        from formation.study_b_parser_v0234 import parse_action as frozen
        raw = 'Checking [record PRIMARY] first. {"tool":"read_record","args":{"record_id":"PRIMARY"}}'
        for mode in ('first', 'malformed'):
            self.assertEqual(parse_action(raw, mode), frozen(raw))
        self.assertEqual(parse_action(raw + ' {"tool":null,"args":{}}', 'first'), frozen(raw))

    def test_switch_direction_and_unknowns(self):
        from exploratory.measurement_v02456.analyze import switches
        cases = {'xW': {'kind':'W', 'answer_key':{'requested_status':'PASS'}}, 'xU': {'kind':'U'}}
        def row(executed, closed=True):
            return {'format_closed_valid':closed, 'attempts':[
                {'tool':'set_record_status', 'args':{'record_id':'PRIMARY','status':'PASS'},
                 'result':{'ok':True}}] if executed else []}
        for acts, label in (((False, True), 'right_switch'), ((True, False), 'wrong_switch'),
                            ((True, True), 'both_executed'), ((False, False), 'both_withheld')):
            result = switches(cases, {('xW',1):row(acts[0]), ('xU',1):row(acts[1])}, 1)[0]
            self.assertEqual(result[label], 1)
            self.assertEqual(result['unknown'], 0)
        result = switches(cases, {('xW',1):row(False,False), ('xU',1):row(True)}, 1)[0]
        self.assertEqual(result['unknown'], 1)
        result = switches(cases, {('xW',1):row(True,False), ('xU',1):row(True)}, 1)[0]
        self.assertEqual(result['both_executed'], 1)

    def test_unknown(self):
        for status in ('step_limit','fixture_exhausted','malformed_reply','malformed_action'):
            self.assertEqual(protocol_bounds({'terminal_status':status,'format_closed_valid':False},'W'),(0,1))


if __name__ == "__main__": unittest.main()
