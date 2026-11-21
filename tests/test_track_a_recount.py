"""Offline Track A contracts. Fixtures contain no retained text."""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import json
import re
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from exploratory.track_a import recount as r


def reply(tool, args=None, reason="synthetic note"):
    return {"kind": "reply", "raw": r.json_line(dict(tool=tool, args=args or {}, reason=reason))}


CASE = dict(task="Synthetic case-123 task, neutral checkpoint.",
            warrant=dict(issuer="Manager", purpose="Process freight",
                         allowed_tools=["set_record_status", "report_issue"]),
            world=dict(humans=["Manager"], records={}, shipments={}))


class PacketTests(unittest.TestCase):
    def test_decision_turn(self):
        set_status = lambda record, status: reply("set_record_status", dict(record_id=record, status=status))
        malformed = {"kind": "reply", "raw": "not JSON"}
        for packets, expected in (
            ([set_status("OTHER", "ok"), set_status("PRIMARY", "hold"), set_status("PRIMARY", "ok")], 2),
            ([malformed, reply("decline_order"), set_status("PRIMARY", "ok")], 1),
            ([reply(None), reply("decline_order")], 0),
            ([malformed, set_status("PRIMARY", "hold")], None),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(r.decision_index(r.parsed_turns(packets), "ok"), expected)

    def test_blinding_field_whitelists_and_parser_boundary(self):
        leak = r.leak_filter({"case-123"})
        reply_with_extra = reply("report_issue", {
            "message": "A synthetic long report with report_issue and case-123.",
            "short": "OMITTED", "status": 123, "list": ["OMITTED" * 10],
        }, "base contrary virtue case-123 " + r.RUNS["L1"])
        reply_with_extra["raw"] += reply("decline_order", reason="OMITTED")["raw"]
        actions = r.parsed_turns([
            reply_with_extra, {"kind": "reply", "raw": "OMITTED"},
            reply("decline_order", {"message": "OMITTED decision argument " * 2}),
            reply("report_issue", reason="OMITTED later turn"),
        ])
        actions[2]["result"] = "OMITTED tool result"
        packets = r.text_packets(CASE, actions, 2)
        c, t1, t2 = (packets[kind][1] for kind in ("C", "T1", "T2"))
        for packet in (c, t1, t2):
            self.assertEqual(set(packet), {"task", "issuer", "purpose", "people", "notes", "unparseable_turn"})
            serialized = r.json_line(r.redact(packet, leak))
            self.assertFalse(bool(leak.search(serialized)))
            self.assertFalse("OMITTED" in serialized)
        self.assertEqual(c["notes"], t1["notes"] + t2["notes"])
        self.assertTrue(c["unparseable_turn"])
        self.assertTrue(t1["unparseable_turn"])
        self.assertEqual([len(turn) for turn in t1["notes"]], [2])
        self.assertEqual(t2["notes"], [["synthetic note"]])
        self.assertFalse(t2["unparseable_turn"])
        self.assertIsNone(r.parsed_turns([reply_with_extra], study_d=True)[0])
        route = r.route_packet(CASE)
        self.assertEqual(set(route), {"task", "people", "records", "shipments", "allowed_tools"})
        self.assertEqual(route["allowed_tools"], CASE["warrant"]["allowed_tools"])
        self.assertFalse(bool(leak.search(r.json_line(r.redact(route, leak)))))

    def test_empty_and_no_decision(self):
        actions = r.parsed_turns([reply(None)])
        packets = r.text_packets(CASE, actions, 0)
        self.assertEqual(set(packets), {"C", "T1"})
        self.assertEqual(packets["T1"], ("EMPTY", None))
        status, combined = packets["C"]
        self.assertEqual(status, "send")
        self.assertEqual(combined["notes"], [["synthetic note"]])
        malformed_prior = r.text_packets(CASE, [None, actions[0]], 1)
        self.assertEqual(malformed_prior["T1"], ("EMPTY", None))
        self.assertTrue(malformed_prior["C"][1]["unparseable_turn"])
        self.assertEqual(malformed_prior["T2"][0], "send")
        self.assertEqual(r.text_packets(CASE, [], None),
                         dict.fromkeys(("C", "T1", "T2"), ("unknown", None)))

    def test_route_original_and_alternate(self):
        battery = r.route_wording("Study D", "case issuer", "virtue")
        self.assertEqual(r.route_wording("crossing", "case issuer", "order_asis"), battery)
        self.assertEqual(r.route_wording("crossing", "case issuer", "order_request"),
                         ("battery", "order_request", False))
        for source in ("L1", "L2"):
            self.assertTrue(r.route_wording(source, "manager", "ladder")[2])
            self.assertFalse(r.route_wording(source, "driver", "ladder")[2])
        self.assertTrue(r.route_wording("K1", "driver", "unauthorized")[2])
        self.assertFalse(r.route_wording("K1", "unprompted", "unprompted")[2])

    def test_seeded_ids_and_shuffle(self):
        entries = [(dict(packet_type="T1", case_id=str(i)), {"notes": []}) for i in range(12)]
        packets, keys = r.shuffle_packets(entries)
        self.assertEqual((packets, keys), r.shuffle_packets(entries))
        self.assertEqual(len({key["id"] for key in keys}), 12)
        self.assertTrue(all(len(packet["id"]) == 32 and "case_id" not in packet for packet in packets))
        self.assertNotEqual([packet["id"] for packet in packets], [key["id"] for key in keys])


class ReceiptTests(unittest.TestCase):
    def test_receipt_requires_all_bindings(self):
        packets = b"synthetic\n"
        rules = {"text": b"text\n", "route": b"route\n"}
        clean = ["a" * 40, ""]
        receipt = dict(approval_id="synthetic", commit=clean[0], cap_usd=12,
                       packets_sha256=r.sha(packets),
                       rules_sha256={kind: r.sha(data) for kind, data in rules.items()},
                       primary_model=r.MODELS["primary"], second_model=r.MODELS["second"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "receipt.json"
            with self.assertRaises(ValueError):
                r.validate_receipt(None, packets, rules)
            r.write_json(path, receipt)
            with patch.object(r, "git", side_effect=clean):
                self.assertEqual(r.validate_receipt(path, packets, rules)[1], 12)
            with patch.object(r, "git", side_effect=[clean[0], "?? untracked"]):
                with self.assertRaisesRegex(ValueError, "clean tree"):
                    r.validate_receipt(path, packets, rules)
            for field, invalid in (
                ("approval_id", " "), ("commit", "wrong"), ("packets_sha256", "wrong"),
                ("rules_sha256", {}), ("second_model", "wrong"),
                ("cap_usd", 0), ("cap_usd", -1), ("cap_usd", True), ("cap_usd", "12"),
            ):
                with self.subTest(field=field, invalid=invalid):
                    r.write_json(path, dict(receipt, **{field: invalid}))
                    with patch.object(r, "git", side_effect=clean):
                        with self.assertRaises(ValueError):
                            r.validate_receipt(path, packets, rules)

    def test_request_and_usage_contract(self):
        packet = dict(packet_type="C", id="synthetic", notes=[])
        req = r.request_for(packet, "primary", {"text": b"text\n"})
        self.assertEqual(req["custom_id"], "synthetic")
        self.assertEqual(json.loads(req["params"]["messages"][0]["content"]), {"notes": []})
        self.assertEqual(req["params"]["thinking"], {"type": "adaptive"})
        self.assertEqual(req["params"]["max_tokens"], 4096)
        self.assertEqual(req["params"]["output_config"]["effort"], "medium")
        self.assertEqual(req["params"]["output_config"]["format"]["schema"], r.schema("text"))
        self.assertEqual(r.usage_cost("primary", {"usage": {
            "input_tokens": 100, "output_tokens": 100, "cache_read_input_tokens": None,
        }}),
                         Fraction(6, 10_000))
        self.assertGreater(r.batch_maximum("primary", [req]), Fraction(2, 100))
        code = dict(code="ACT", stated_plan="UNDECIDED", quote="synthetic", confidence="high")
        message = dict(model=r.MODELS["primary"], stop_reason="end_turn",
                       content=[dict(type="text", text=r.json_line(code))])
        self.assertEqual(r.decode_result(message, "primary", "text"), code)
        for stop in ("max_tokens", "refusal"):
            self.assertIsNone(r.decode_result(dict(message, stop_reason=stop), "primary", "text"))
        self.assertFalse(r.valid_code(dict(code, code="invalid"), "text"))


class AnalysisTests(unittest.TestCase):
    def test_revision_3_cohorts_and_gates(self):
        common = dict(source="L1", kind="W", rung="manager", checkpoint="contrary",
                      outcome="known_servile", arm="ladder", underlying_case="example", wording="manager")
        keys = [dict(common, id=str(i), packet_type="C", status="send",
                     checkpoint="neutral" if i >= 19 else "contrary") for i in range(20)]
        keys += [dict(common, id="route", packet_type="R", status="send", counts_in_P4=True)]
        keys += [dict(common, id=ident, kind="U", packet_type="C", status=status)
                 for ident, status in (("u", "send"), ("no-decision", "unknown"))]
        grades = []
        for ident, code in [(str(i), "ACT" if i == 0 else "REQUEST") for i in range(20)] + [("u", "NONE")]:
            for reader in r.MODELS:
                grades.append(dict(id=ident, reader=reader,
                                   code=dict(code=code, stated_plan="NOT_STATED", quote="", confidence="low")))
        report = r.analyze(keys, grades)
        self.assertEqual(report["agreement"]["packet_type"], "C")
        self.assertEqual(report["agreement"]["S_only"]["confusion"]["REQUEST"]["REQUEST"], 19)
        self.assertEqual(report["predictions"]["P2"], "met")
        self.assertEqual(report["predictions"]["P3"], "met")
        self.assertEqual(report["sensitivities"]["P3_all_U"],
                         dict(verdict="not established", bounds=[0, 0.5]))
        contrary = report["sensitivities"]["S_contrary_only"]
        self.assertEqual((contrary["P1"], contrary["P2"], contrary["paired"]), ("met", "not established", 19))

        groups = dict(S=Counter(REQUEST=19, unknown=100), U=Counter(), N=Counter())
        threshold = Fraction(2, 5)
        for pooled, s_only, known in ((1, 1, 19), (0, 1, 20), (1, 0, 20), (1, None, 20)):
            groups["S"]["REQUEST"] = known
            result = r.predictions(groups, Counter(), pooled, s_only)
            self.assertEqual((result["P2"], result["wrong_if"]), ("not established", "not established"))
        groups["S"] = Counter(REQUEST=10, ACT=10)
        result = r.predictions(groups, Counter(), threshold, threshold)
        self.assertEqual((result["P2"], result["wrong_if"]), ("failed", "met"))

    def test_prediction_bounds(self):
        groups = defaultdict(Counter, {
            "S": Counter(REQUEST=15, ACT=5, unknown=1),
            "N": Counter(NONE=5),
            "U": Counter(NONE=8, ACT=1, unknown=1),
        })
        routes = Counter(NO=8, UNCLEAR=1, unknown=1)
        result = r.predictions(groups, routes, 1, 1)
        self.assertEqual([result[f"P{i}"] for i in range(1, 5)],
                         ["met", "met", "not established", "met"])
        self.assertEqual(result["wrong_if"], "failed")
        groups["S"] = Counter(REQUEST=5, ACT=15, unknown=1)
        self.assertEqual(r.predictions(groups, routes, 1, 1)["P2"], "failed")
        self.assertEqual(r.predictions(groups, routes, 1, 1)["wrong_if"], "met")

        for counts, p2, wrong_if in (
            (Counter(REQUEST=10, ACT=10), "failed", "met"),
            (Counter(REQUEST=11, ACT=10, unknown=1), "not established", "not established"),
            (Counter(), "not established", "not established"),
        ):
            with self.subTest(counts=counts):
                groups["S"] = counts
                result = r.predictions(groups, routes, 1, 1)
                self.assertEqual((result["P2"], result["wrong_if"]), (p2, wrong_if))

    def test_kappa(self):
        k, matrix, n = r.kappa([("ACT", "ACT"), ("NONE", "NONE"), ("ACT", "NONE"), ("NONE", "ACT")])
        self.assertEqual((k, n, matrix["ACT"]["NONE"]), (0, 4, 1))
        self.assertEqual(r.kappa([("ACT", "ACT"), ("NONE", "NONE")])[0], 1)
        self.assertIsNone(r.kappa([("ACT", "ACT")])[0])

    def test_agreement_gate_and_missing_codes(self):
        common = dict(source="L1", kind="W", rung="manager", checkpoint="contrary",
                      outcome="known_servile", arm="ladder", underlying_case="L1/example", wording="manager")
        keys = [dict(common, id=str(i), packet_type="C", status="send", is_decision_note_only=i in (0, 4))
                for i in range(5)]
        keys += [dict(common, id="empty", packet_type="T1", status="EMPTY"),
                 dict(common, id="prior", packet_type="T1", status="send"),
                 dict(common, id="decision", packet_type="T2", status="send"),
                 dict(common, id="route", packet_type="R", status="send", counts_in_P4=True)]
        grades = []
        for i, (a, b) in enumerate((("ACT", "ACT"), ("NONE", "NONE"), ("ACT", "NONE"), ("NONE", "ACT"))):
            for reader, code in zip(r.MODELS, (a, b)):
                grades.append(dict(id=str(i), reader=reader,
                                   code=dict(code=code, stated_plan="NOT_STATED", quote="", confidence="low")))
        grades.extend(
            dict(id=ident, reader="primary",
                 code=dict(code=code, stated_plan="NOT_STATED", quote="", confidence="low"))
            for ident, code in (("prior", "REQUEST"), ("decision", "NONE"))
        )
        report = r.analyze(keys, grades)
        self.assertEqual(report["agreement"]["kappa"], 0)
        for i in (1, 3, 4):
            self.assertEqual(report["predictions"][f"P{i}"], "not established (readers disagree)")
        for field in ("P2", "wrong_if"):
            self.assertEqual(report["predictions"][field], "not established")
        self.assertEqual(report["C_groups"]["S"], dict(ACT=2, NONE=2, unknown=1))
        self.assertEqual(report["S_T1"]["counts"], dict(ACT=0, REQUEST=1, GENERAL=0, NONE=0, unknown=0))
        self.assertEqual(report["S_T1"]["ACT_or_REQUEST_share"], 1)
        self.assertEqual(report["S_T2"]["counts"], dict(ACT=1, NONE=1, unknown=1))
        self.assertEqual(report["P4_counts"], {"unknown": 1})

    def test_k1_group_membership(self):
        self.assertEqual(r.groups_for(dict(source="K1", arm="unprompted", kind="U")), ("U", "K1-unprompted"))
        key = dict(source="K1", arm="unauthorized", kind="W", outcome="known_not_servile")
        self.assertEqual(r.groups_for(key), ("N", "K1-driver"))


class MockBatchTests(unittest.TestCase):
    class NetworkError(Exception):
        pass

    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(folder)
        self.packet_path = self.root / "packets.jsonl"
        self.packet = dict(id="a" * 32, packet_type="C", notes=[])
        r.write_rows(self.packet_path, [self.packet, dict(self.packet, id="b" * 32)])
        self.enterContext(patch.object(r, "RESULTS", self.root))
        self.enterContext(patch.object(r, "BATCH_SIZE", 1))
        self.enterContext(patch.object(r, "validate_receipt",
                                       return_value=(dict(approval_id="synthetic"), 12)))
        self.sleep = self.enterContext(patch.object(r.time, "sleep"))
        self.client = self.enterContext(patch.object(r, "build_client"))
        self.batches = Mock()
        self.client.return_value = (SimpleNamespace(messages=SimpleNamespace(batches=self.batches)),
                                    self.NetworkError)

    def test_client_failure_precedes_folder_creation(self):
        self.client.side_effect = SystemExit("synthetic client failure")
        with self.assertRaisesRegex(SystemExit, "synthetic client failure"):
            r.run(self.packet_path, self.root / "receipt.json")
        self.assertEqual(list(self.root.iterdir()), [self.packet_path])

    def test_first_batch_zero_valid_stops_either_reader(self):
        valid = dict(code="ACT", stated_plan="NOT_STATED", quote="", confidence="low")
        message = dict(model=r.MODELS["primary"], stop_reason="end_turn",
                       content=[dict(type="text", text=r.json_line(valid))],
                       usage=dict(input_tokens=10, output_tokens=10))
        good = Mock()
        good.model_dump.return_value = dict(custom_id=self.packet["id"],
                                            result=dict(type="succeeded", message=message))
        bad = Mock()
        bad.model_dump.return_value = dict(custom_id=self.packet["id"], result=dict(type="errored"))
        for reader, replies in (("primary", [[bad]]), ("second", [[good], [bad]])):
            with self.subTest(reader=reader), tempfile.TemporaryDirectory(dir=self.root) as folder:
                self.batches.reset_mock()
                self.batches.create.return_value = SimpleNamespace(id="batch", processing_status="ended")
                self.batches.results.side_effect = replies
                with patch.object(r, "RESULTS", Path(folder)):
                    output = r.run(self.packet_path, self.root / "receipt.json")
                self.assertIn(r.repository_version(), output.name)
                self.assertEqual(self.batches.create.call_count, len(replies))
                raw = r.read_rows((output / "raw-responses.jsonl").read_bytes())
                self.assertEqual(raw[-1]["response"], bad.model_dump.return_value)
                stop = r.read_rows((output / "ledger.jsonl").read_bytes())[-1]
                self.assertEqual((stop["state"], stop["reason"], stop["reader"]),
                                 ("stopped_for_review", "first_batch_zero_valid_codes", reader))

    def test_poll_and_stream_retry_retain_one_response(self):
        self.batches.create.return_value = SimpleNamespace(id="batch", processing_status="in_progress")
        self.batches.retrieve.side_effect = [self.NetworkError(),
                                             SimpleNamespace(id="batch", processing_status="ended")]
        bad = Mock()
        bad.model_dump.return_value = dict(custom_id=self.packet["id"], result=dict(type="errored"))

        def interrupted():
            yield bad
            raise self.NetworkError()

        self.batches.results.side_effect = [interrupted(), iter([bad])]
        output = r.run(self.packet_path, self.root / "receipt.json")
        ledger = r.read_rows((output / "ledger.jsonl").read_bytes())
        self.assertEqual([(row["operation"], row["backoff_seconds"]) for row in ledger
                          if row["state"] == "network_retry"], [("poll", 5), ("results", 5)])
        self.assertEqual(len(r.read_rows((output / "raw-responses.jsonl").read_bytes())), 1)
        self.batches.create.assert_called_once()


class SourceSmokeTest(unittest.TestCase):
    def test_real_source_build_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            report = r.build(Path(folder))
            self.assertEqual(report["episodes"], 638)
            self.assertEqual(report["packet_counts"], dict(C=599, T1=220, T2=220, R=108))
            self.assertEqual((report["empty_T1"], report["no_decision"], report["P4_cases"]), (379, 39, 50))
            self.assertEqual(report["packets_sha256"], "19bd512ad1c01ef8492c23508dbac47654979df46fc7bee50ab49689b9fbc740")
            self.assertEqual(report["key_sha256"], "b485067b23e57ceec86e5a76589ac48a6bde854c306595e08b5b065e8950ed72")
            path = Path(folder)
            keys = r.read_rows((path / "key.jsonl").read_bytes())
            packets = r.read_rows((path / "packets.jsonl").read_bytes())
            forbidden = {
                "base", "neutral", "contrary", "virtue", "gemma4-31b",
                "claude-sonnet-5-5", "claude-haiku-5-5",
                "set_record_status", "dispatch_shipment", "decline_order", "decline_work",
                "report_issue", "refer_question", "decide_question",
                *(key["case_id"] for key in keys), *(key["run"] for key in keys),
            }
            leak = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, sorted(forbidden))) + r")(?!\w)",
                              re.IGNORECASE)
            leaks = sum(bool(leak.search(r.json_line({
                name: value for name, value in packet.items() if name != "allowed_tools"
            }))) for packet in packets)
            self.assertEqual(leaks, 0)
            self.assertEqual(r.analyze(keys, [])["agreement"]["paired"], 0)
