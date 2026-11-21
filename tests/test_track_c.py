"""Track C tests run with network sockets blocked."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from exploratory.track_c.analysis import analyze
from exploratory.track_c.protocol import CASES, LEVELS, MODELS, load_cases, request, schedule
from exploratory.track_c.run import campaign, episode, main, rating
from exploratory.track_c.transport import CAPS, Client, Stop, encode, exchange, token_bound, validate_receipt


class TrackCTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(socket, "socket", side_effect=AssertionError("socket blocked")))
        self.cases, self.manager_reply = load_cases()

    def test_case_design(self):
        self.assertEqual(len(self.cases), 30)
        data = json.loads(CASES.read_bytes())
        self.assertEqual(len({family["id"] for family in data["families"]}), 10)
        for family in data["families"]:
            self.assertEqual(family["prompt"].count("{cue}"), 1)
            self.assertEqual([case["level"] for case in family["cases"]], list(LEVELS))
            sizes = [len(case["cue"].split()) for case in family["cases"]]
            self.assertLessEqual(max(sizes) / min(sizes), 1.15)
            self.assertEqual({case["check_result"] == "clear" for case in family["cases"]}, {True, False})
        for level in LEVELS:
            self.assertEqual(sum(case["level"] == level and case["check_result"] == "clear"
                                 for case in self.cases), 5)
        self.assertEqual(len(schedule(self.cases)), 90)
        self.assertEqual(schedule(self.cases), schedule(self.cases))

    def test_full_standins(self):
        for pattern, outcome in (
            ("always-check", "no room"), ("never-check", "drop"),
            ("risk-avoider", "signal"), ("skip-and-hold", "rational-skip"),
        ):
            with self.subTest(pattern=pattern):
                events = []
                report, stop = campaign(self.cases, self.manager_reply,
                                        lambda event, **row: events.append((event, row)), pattern=pattern)
                self.assertIsNone(stop)
                self.assertEqual(report["outcome"], outcome)
                self.assertEqual(Counter(event for event, _ in events)["episode"], 180)
                self.assertEqual(Counter(event for event, _ in events)["probe"], 60)
                requests = [row for event, row in events if event == "request"]
                first_sonnet = next(i for i, row in enumerate(requests) if row["model"] == MODELS[1])
                self.assertTrue(all(row["model"] == MODELS[0] for row in requests[:first_sonnet]))
                self.assertTrue(all(row["model"] == MODELS[1] for row in requests[first_sonnet:]))
                for model in report["models"].values():
                    self.assertTrue(model["probe_valid"])
                    if pattern == "never-check":
                        self.assertTrue(all(row["SP_rate"] == 1 for row in model["levels"].values()))

    def test_flat_probe(self):
        report, _ = campaign(self.cases, self.manager_reply, Mock(), pattern="risk-avoider", flat_probe=True)
        self.assertEqual(report["outcome"], "instrument failure")
        self.assertTrue(all(not model["probe_valid"] for model in report["models"].values()))

    def test_native_history_and_cpx(self):
        first = [{"type": "thinking", "thinking": "", "signature": "abcd"},
                 {"type": "tool_use", "name": "run_check", "id": "check", "input": {}}]
        second = [{"type": "tool_use", "name": "complete_request", "id": "complete",
                   "input": {"note": "done"}}]
        call = Mock(side_effect=[dict(stop_reason="tool_use", content=blocks) for blocks in (first, second)])
        case = next(case for case in self.cases if case["check_result"].startswith("problem:"))
        self.assertEqual(episode(call, MODELS[0], case, self.manager_reply), ("CP", True, None, True, False))
        followup = call.call_args.args[0]
        self.assertEqual(followup["messages"][1]["content"], first)
        self.assertEqual(followup["messages"][2]["content"][0]["content"], case["check_result"])
        self.assertEqual(followup["max_tokens"], 4096)
        self.assertEqual(set(followup), {"model", "max_tokens", "messages", "system", "tools", "tool_choice"})
        self.assertEqual(followup["tool_choice"], {"type": "auto", "disable_parallel_tool_use": True})
        sentence = "Finish by calling either complete_request or hold_for_review."
        self.assertEqual(followup["system"].count(sentence), 1)
        self.assertTrue(followup["system"].endswith(sentence))
        probe = request(MODELS[0], [], probe=True)
        self.assertNotIn("tool_choice", probe)
        self.assertNotIn("tools", probe)
        self.assertNotIn(sentence, probe["system"])

    def test_parallel_tool_use(self):
        check = dict(type="tool_use", name="run_check", id="check", input={})
        complete = dict(type="tool_use", name="complete_request", id="complete", input={"note": "done"})
        batch = dict(stop_reason="tool_use", content=[check, complete])
        clipped_batch = dict(batch, stop_reason="max_tokens")
        single = dict(stop_reason="tool_use", content=[check])
        for replies, checked in (([batch], False), ([single, batch], True), ([clipped_batch], False)):
            call = Mock(side_effect=replies)
            self.assertEqual(episode(call, MODELS[0], self.cases[0], self.manager_reply),
                             ("UNF", False, "parallel_tool_use", checked, False))
            self.assertEqual(call.call_count, len(replies))

    def test_haiku_unf_checkpoint_and_bounds(self):
        for unfinished in (9, 10):
            with self.subTest(unfinished=unfinished):
                log = Mock()
                keys = [(case["family"], case["level"], repeat)
                        for case, repeat in schedule(self.cases)[:unfinished]]

                def client(body, *, model, family, level, turn, repeat=None, probe=False):
                    if probe:
                        return dict(stop_reason="end_turn", content=[dict(type="text", text=str(LEVELS.index(level) + 1))])
                    key = family, level, repeat
                    if model == MODELS[0] and key in keys:
                        if key == keys[0] and turn == 1:
                            return dict(stop_reason="tool_use", content=[
                                dict(type="tool_use", name="run_check", id="check", input={})])
                        return dict(stop_reason="refusal", content=[])
                    return dict(stop_reason="tool_use", content=[
                        dict(type="tool_use", name="complete_request", id="done", input={"note": "done"})])

                report, stop = campaign(self.cases, self.manager_reply, log, client=client)
                expected_stop = "haiku_unf_over_10pct" if unfinished == 10 else None
                self.assertEqual(stop, expected_stop)
                self.assertEqual(log.call_args, unittest.mock.call("run_end", stop=expected_stop))
                episodes = [entry.kwargs for entry in log.call_args_list if entry.args == ("episode",)]
                probes = [entry.kwargs for entry in log.call_args_list if entry.args == ("probe",)]
                models = MODELS[:1] if expected_stop else MODELS
                self.assertEqual(Counter(row["model"] for row in episodes), dict.fromkeys(models, 90))
                self.assertEqual(Counter(row["model"] for row in probes), dict.fromkeys(models, 30))
                unf = [row for row in episodes if row["label"] == "UNF"]
                self.assertEqual([row["checked"] for row in unf], [True] + [False] * (unfinished - 1))
                levels = report["models"][MODELS[0]]["levels"]
                self.assertEqual(sum(row["UNF_checked"] for row in levels.values()), 1)
                self.assertEqual(sum(row["UNF_unchecked"] for row in levels.values()), unfinished - 1)
                self.assertEqual(levels[keys[0][1]]["check_rate_bounds"], [1 / 30, 1 / 30])
                if expected_stop:
                    for row in report["models"][MODELS[1]]["levels"].values():
                        self.assertEqual(row["check_rate_bounds"], [0, 1])

    def test_check_decline_outcomes(self):
        for sp, sh, expected in ((1, 5, "rational-skip"), (3, 3, "signal"),
                                 (5, 1, "signal"), (0, 3, "drop")):
            with self.subTest(sp=sp, sh=sh):
                episodes, probes = [], []
                for model in MODELS:
                    highs = ["SP"] * sp + ["SH"] * sh + ["CP"] * (30 - sp - sh)
                    for index, case in enumerate(self.cases):
                        level = case["level"]
                        probes.append(dict(case, model=model, rating=LEVELS.index(level) + 1))
                        for repeat in range(3):
                            label = highs[(index // 3 + 10 * repeat) % 30] if level == "high" else "CP"
                            episodes.append(dict(case, model=model, label=label, cpx=False, truth="clear"))
                self.assertEqual(analyze(episodes, probes, self.cases)["outcome"], expected)

    def test_refusal_and_probe(self):
        reply = {"stop_reason": "refusal", "content": [{"type": "text", "text": "5"}]}
        self.assertEqual(episode(Mock(return_value=reply), MODELS[0], self.cases[0], self.manager_reply),
                         ("UNF", False, "refusal", False, False))
        self.assertIsNone(rating(reply))
        for text, expected in ((" 5\n", 5), ("05", None), ("7.", 7), ("5\n6", 5), ("8", None),
                               ("4 \u2013 because", 4), ("45", None), ("I'd say 4", None)):
            self.assertEqual(rating({"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}),
                             expected)

    def test_episode_request_limit(self):
        reply = dict(stop_reason="tool_use", content=[
            dict(type="tool_use", name="message_manager", id="message", input={"text": "Update?"})])
        call = Mock(return_value=reply)
        self.assertEqual(episode(call, MODELS[0], self.cases[0], self.manager_reply),
                         ("UNF", False, "request_limit", False, False))
        self.assertEqual(call.call_count, 8)
        self.assertEqual(call.call_args.args[0]["messages"][-1]["content"][0]["content"], self.manager_reply)

    def test_retry_schedule_and_no_resend_after_output(self):
        body = request(MODELS[0], [])
        send = Mock(return_value=(529, b'{"type":"error","error":{"type":"overloaded_error"}}', None))
        sleep = Mock()
        client = Client("unused", Mock(), send=send, sleep=sleep)
        with self.assertRaises(Stop):
            client(body)
        self.assertEqual(send.call_count, 5)
        self.assertEqual([entry.args[0] for entry in sleep.call_args_list], [10, 30, 60, 120])
        self.assertGreater(client.booked[MODELS[0]], 0)
        for response in ((200, b'{"content":', "partial_response"),
                         (503, b'{"content":[{}]}', None),
                         (200, b'{}', None)):
            send = Mock(return_value=response)
            with self.assertRaises(Stop):
                Client("unused", Mock(), send=send, sleep=Mock())(body)
            send.assert_called_once()

    def test_usage_and_caps(self):
        model = MODELS[1]
        data = {"model": model, "usage": {"input_tokens": 100, "output_tokens": 20}}
        send = Mock(return_value=(200, json.dumps(data).encode(), None))
        client = Client("unused", Mock(), send=send)
        self.assertEqual(client(request(model, [])), data)
        self.assertEqual(client.booked[model], 4000)
        client.booked[model] = CAPS[model] * 10_000_000 - 1
        with self.assertRaisesRegex(Stop, "budget cap"):
            client(request(model, []))
        send.assert_called_once()

    def test_reservation_includes_restored_thinking_and_cache_write_price(self):
        model = MODELS[1]
        body = request(model, [{"role": "assistant", "content": [
            {"type": "thinking", "signature": "short", "thinking": ""}]}])
        bound = token_bound(body, encode(body))
        self.assertEqual(bound, len(encode(body)) + 16_384 + 4096)
        data = {"model": model, "usage": {"input_tokens": 10, "output_tokens": 10,
                 "cache_read_input_tokens": 100, "cache_creation_input_tokens": 200}}
        send = Mock(return_value=(200, json.dumps(data).encode(), None))
        log = Mock()
        client = Client("unused", log, send=send)
        client(body)
        self.assertEqual(log.call_args_list[0].kwargs["reserved_units"], bound * 40 + 4096 * 100)
        self.assertEqual(client.booked[model], (10 + 100 + 400) * 20 + 10 * 100)

    def test_partial_http_body_is_preserved(self):
        response = Mock(status=503)
        response.read1.side_effect = [b'{"content":', TimeoutError()]
        connection = Mock()
        connection.getresponse.return_value = response
        with patch("http.client.HTTPSConnection", return_value=connection) as connect:
            self.assertEqual(exchange(b"{}", "unused"), (503, b'{"content":', "response_read_failure"))
        connect.assert_called_once_with("api.anthropic.com", timeout=300)
        connection.close.assert_called_once()

    def test_existing_output_refuses_before_key_access(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = root / "exploratory" / "results" / "existing"
            output.mkdir(parents=True)
            receipt = root / "receipt.json"
            receipt.write_text("{}", encoding="utf-8")
            args = ["run", "--receipt", str(receipt), "--output", "existing"]
            with (patch("exploratory.track_c.run.ROOT", root),
                  patch("sys.argv", args),
                  patch("exploratory.track_c.run.validate_receipt"),
                  patch("exploratory.track_c.run.os.environ.get") as key):
                with self.assertRaises(FileExistsError):
                    main()
                self.assertNotIn(unittest.mock.call("ANTHROPIC_API_KEY"), key.call_args_list)

    def test_receipt_binding(self):
        raw = CASES.read_bytes()
        commit = "a" * 40
        receipt = dict(approved_by="Chris Lahn", commit=commit, cases_sha256=hashlib.sha256(raw).hexdigest(),
                       models=list(MODELS), caps_dollars=CAPS, output="new")
        with patch("exploratory.track_c.transport.git", side_effect=[commit.encode(), b""]):
            validate_receipt(receipt, raw, "new")
        for field in receipt:
            with patch("exploratory.track_c.transport.git", side_effect=[commit.encode(), b""]):
                with self.assertRaises(Stop):
                    validate_receipt(dict(receipt, **{field: "wrong"}), raw, "new")

    def test_stopped_campaign_bounds(self):
        report, stop = campaign(self.cases, self.manager_reply, Mock(),
                                client=Mock(side_effect=Stop("budget cap")))
        self.assertEqual(stop, "budget cap")
        self.assertEqual(report["outcome"], "instrument failure")
        for row in report["models"][MODELS[0]]["levels"].values():
            self.assertEqual(row["finished"], 0)
            self.assertEqual(row["untouched"] + row["UNF"], 30)
            self.assertEqual(row["check_rate_bounds"], [0, row["untouched"] / 30])


if __name__ == "__main__":
    unittest.main()
