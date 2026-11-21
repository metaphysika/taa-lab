import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from exploratory.track_a import recount as r


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.output = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.packets = [dict(id=f"{i:032x}", packet_type="C", notes=[]) for i in range(3)]
        self.packet_path = self.output / "packets.jsonl"
        self.receipt_path = self.output / "resume.json"
        r.write_rows(self.packet_path, self.packets)
        self.rules = r.rules_data()
        for kind, data in self.rules.items():
            (self.output / r.RULES[kind].name).write_bytes(data)
        self.original = dict(approval_id="original", commit="a" * 40, cap_usd=12,
                             packets_sha256=r.sha(self.packet_path.read_bytes()),
                             rules_sha256={kind: r.sha(data) for kind, data in self.rules.items()},
                             primary_model=r.MODELS["primary"], second_model=r.MODELS["second"])
        self.receipt = dict(self.original, commit="b" * 40, resumes_folder=str(self.output),
                            resume_approval_id="continuation")
        r.write_json(self.output / "receipt.json", self.original)
        r.write_json(self.receipt_path, self.receipt)
        self.git = self.enterContext(patch.object(r, "git", side_effect=self.fake_git))
        self.enterContext(patch.object(r, "BATCH_SIZE", 1))
        self.enterContext(patch.object(r.time, "sleep"))
        self.batches = Mock()
        self.client = self.enterContext(patch.object(r, "build_client", return_value=(
            SimpleNamespace(messages=SimpleNamespace(batches=self.batches)), ConnectionError)))
        self.batches.create.side_effect = self.create
        self.batches.retrieve.side_effect = [ConnectionError(), self.batch("in-flight", "in_progress"),
                                             self.batch("in-flight")]
        self.batches.results.side_effect = self.results
        self.submitted = {}
        self.zero_reader = None
        for name in ("requests", "raw-responses", "codes", "ledger"):
            self.write(name, [])
        self.write("codes", [dict(id=self.packets[0]["id"], reader=reader, code=None)
                             for reader in r.MODELS])
        self.record = dict(reader="primary", start=1, reserved_usd=0.5)
        self.write("requests", [dict(self.record, requests=[
            r.request_for(self.packets[1], "primary", self.rules)])])
        self.history = [
            dict(self.record, state="reserved", spent_usd=1.18),
            dict(self.record, state="submitted", spent_usd=1.18, batch_id="in-flight"),
        ]
        self.write("ledger", self.history)

    def fake_git(self, command, *_):
        return self.receipt["commit"] if command == "rev-parse" else ""

    def write(self, name, rows):
        r.write_rows(self.output / f"{name}.jsonl", rows)

    def rows(self, name):
        return r.retained_rows(self.output, name)

    @staticmethod
    def batch(ident, status="ended"):
        return SimpleNamespace(id=ident, processing_status=status)

    def raw(self, reader, ident):
        result = dict(type="errored")
        if reader != self.zero_reader:
            code = dict(code="ACT", stated_plan="NOT_STATED", quote="", confidence="low")
            result = dict(type="succeeded", message=dict(
                model=r.MODELS[reader], stop_reason="end_turn",
                usage=dict(input_tokens=10, output_tokens=10),
                content=[dict(type="text", text=r.json_line(code))]))
        return dict(custom_id=ident, result=result)

    def create(self, *, requests):
        ident = f"new-{len(self.submitted)}"
        self.submitted[ident] = requests[0]
        return self.batch(ident)

    def results(self, batch_id):
        if batch_id == "in-flight":
            raw = self.raw("primary", self.packets[1]["id"])
        else:
            req = self.submitted[batch_id]
            reader = next(reader for reader, model in r.MODELS.items() if model == req["params"]["model"])
            raw = self.raw(reader, req["custom_id"])
        return [Mock(model_dump=Mock(return_value=raw))]

    def resume(self):
        return r.resume(self.output, self.packet_path, self.receipt_path)

    def test_reconstruct_retrieve_and_append_only(self):
        by_id = {packet["id"]: packet for packet in self.packets}
        spent, coded, recovery = r.resume_state(self.output, "continuation", by_id)
        self.assertEqual(float(spent), 1.18)
        self.assertEqual(coded, {reader: {self.packets[0]["id"]} for reader in r.MODELS})
        self.assertEqual([record["batch_id"] for record, *_ in recovery], ["in-flight"])
        paths = [self.output / f"{name}.jsonl" for name in ("ledger", "raw-responses", "codes", "requests")]
        before = {path: path.read_bytes() for path in paths}
        self.assertEqual(self.resume(), self.output)
        self.assertTrue(all(path.read_bytes().startswith(data) for path, data in before.items()))
        self.assertEqual([call.args for call in self.batches.retrieve.call_args_list], [("in-flight",)] * 3)
        self.assertEqual(self.batches.results.call_args_list[0].args, ("in-flight",))
        self.assertEqual([(req["custom_id"], req["params"]["model"]) for req in self.submitted.values()],
                         [(self.packets[i]["id"], r.MODELS[reader])
                          for i, reader in ((1, "second"), (2, "primary"), (2, "second"))])
        self.assertEqual(len(self.rows("codes")), 6)
        self.assertEqual(self.rows("ledger")[-1], dict(state="resume-end", outcome="complete",
                                                      resume_approval_id="continuation"))
        with self.assertRaisesRegex(ValueError, "already been used"):
            self.resume()

    def test_partial_batch_write_is_reconciled_once(self):
        ident = self.packets[1]["id"]
        self.write("raw-responses", [dict(batch_id="in-flight", reader="primary",
                                         response=self.raw("primary", ident))])
        codes = self.rows("codes")
        self.write("codes", [*codes, dict(id=ident, reader="primary", code=None)])
        self.resume()
        self.assertEqual(sum(row["batch_id"] == "in-flight" for row in self.rows("raw-responses")), 1)
        self.assertEqual(sum(row["id"] == ident and row["reader"] == "primary"
                             for row in self.rows("codes")), 1)
        charge = next(row for row in self.rows("ledger") if row["state"] == "response")
        self.assertEqual(charge["spent_usd"], 1.18006)

    def test_recorded_charge_is_not_added_again(self):
        ident = self.packets[1]["id"]
        self.write("raw-responses", [dict(batch_id="in-flight", reader="primary",
                                         response=self.raw("primary", ident))])
        self.write("codes", [*self.rows("codes"), dict(id=ident, reader="primary", code=None)])
        charged = dict(self.history[-1], state="response", id=ident, spent_usd=1.18006)
        self.write("ledger", [*self.history, charged])
        self.resume()
        rows = [row for row in self.rows("ledger") if row.get("batch_id") == "in-flight"]
        self.assertEqual([row for row in rows if row["state"] == "response"], [charged])
        self.assertEqual(rows[-1]["spent_usd"], 1.18006)

    def test_concurrent_resume_refuses_before_contacting_provider(self):
        with r.lock_resume(self.output), self.assertRaisesRegex(ValueError, "resume lock"):
            self.resume()
        self.client.assert_not_called()

    def test_prior_spend_and_retrieval_count_toward_cap(self):
        self.write("ledger", [dict(row, spent_usd=11.9999) for row in self.history])
        self.resume()
        self.batches.results.assert_called_once_with("in-flight")
        self.batches.create.assert_not_called()
        self.assertEqual(self.rows("ledger")[-2]["spent_usd"], 11.99996)
        self.assertEqual(self.rows("ledger")[-1]["outcome"], "cap_stop")

    def test_first_new_batch_guard_ignores_retrieved_batch(self):
        self.zero_reader = "primary"
        self.resume()
        self.assertEqual(len(self.submitted), 2)
        stop = self.rows("ledger")[-2]
        self.assertEqual((stop["reader"], stop["start"], stop["reason"]),
                         ("primary", 2, "first_batch_zero_valid_codes"))

    def test_binding_and_dirty_tree_refusals(self):
        for mutation, message in (
            (dict(resumes_folder=str(self.output / "other")), "folder mismatch"),
            (dict(cap_usd=13), "original receipt"),
            (dict(resume_approval_id="original"), "distinct"),
            (dict(packets_sha256="wrong"), "packet hash"),
        ):
            with self.subTest(mutation=mutation):
                r.write_json(self.receipt_path, dict(self.receipt, **mutation))
                with self.assertRaisesRegex(ValueError, message):
                    self.resume()
        r.write_json(self.receipt_path, self.receipt)
        self.git.side_effect = ["b" * 40, "?? untracked"]
        with self.assertRaisesRegex(ValueError, "clean tree"):
            self.resume()
        self.client.assert_not_called()
        self.assertEqual(self.rows("ledger"), self.history)

    def test_uncertain_submission_refuses_without_contacting_provider(self):
        self.write("ledger", self.history[:1])
        with self.assertRaisesRegex(ValueError, "Uncertain submission"):
            self.resume()
        self.client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
