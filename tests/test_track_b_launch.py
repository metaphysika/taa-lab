import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile

from exploratory.track_b import analysis, launch, stage_b0a


OPTIONS = dict(
    commit_sha="1" * 40, adapter_dataset_id="metaphysika/ft1-adapter-2-247056-0449a230200c",
    adapter_sha256="2" * 64, model_source="google/gemma-3/transformers/gemma-3-12b-it/1",
    owner="metaphysika",
)
DEV_PATH = "exploratory/track_b/dev_batteries"


def committed_archive(commit, *paths):
    return subprocess.check_output(["git", "archive", "--format=zip", commit, *paths])


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())) / "trackb"
        self.enterContext(patch.dict(launch.os.environ, TRACK_B_STAGING_ROOT=str(self.root)))
        self.enterContext(patch.object(launch, "source_at", return_value=b"scripted archive"))
        self.folder = launch.stage("b0a", **OPTIONS)
        self.draft = launch.read_json(self.folder / launch.DRAFT)
        self.receipt = dict(self.draft, approval_id="record-001", approval_text="Approved test fixture")
        self.receipt_path = self.root / "receipt.json"
        self.flag = self.root / "KAGGLE_OWNER"
        self.flag.write_bytes(b"trackb")
        self.backend = Mock()

    def push(self, status):
        self.receipt_path.write_bytes(launch.json_bytes(self.receipt))
        launch.push("b0a", self.receipt_path, status=lambda owner: status(), backend=self.backend)

    def refused(self, message, status=lambda: []):
        with self.assertRaisesRegex(ValueError, message):
            self.push(status)
        self.backend.assert_not_called()

    def test_draft_and_plan_notebook(self):
        self.assertEqual(set(self.draft), launch.RECEIPT_FIELDS)
        self.assertIsNone(self.draft["approval_id"])
        files = {name: (self.folder / name).read_bytes() for name in launch.BUNDLE_FILES}
        self.assertEqual(self.draft["bundle_sha256"], launch.bundle_hash(files))
        config = json.loads(files[launch.BINDING])
        self.assertEqual(files, launch.bundle(config, b"scripted archive"))
        metadata = json.loads(files[launch.METADATA])
        self.assertEqual(metadata["dataset_sources"],
                         [OPTIONS["adapter_dataset_id"], "metaphysika/k2-wheels"])
        self.assertTrue(metadata["is_private"])
        self.assertFalse(metadata["enable_internet"])
        notebook = json.loads(files[launch.NOTEBOOK])
        with patch("builtins.print") as output:
            exec(notebook["cells"][0]["source"], {})
        self.assertEqual(output.call_args.args[0]["commit_sha"], OPTIONS["commit_sha"])

    def test_default_cli_only_stages(self):
        args = ["cli"]
        for key, value in OPTIONS.items():
            args.extend(["--" + key.replace("_", "-"), value])
        with patch.object(launch, "kaggle_push") as kaggle, patch("builtins.print"):
            self.assertEqual(launch.main(args), 0)
        kaggle.assert_not_called()
        self.assertTrue((self.root / "cli" / launch.DRAFT).is_file())

    def test_refuses_ft1_staging_paths(self):
        for target in ("C:/t/ft1", "C:/t/ft1-something/subdir", "C:/t/ft1g-gates"):
            with self.subTest(target=target), patch.dict(launch.os.environ, TRACK_B_STAGING_ROOT=target):
                with patch.object(launch, "write_files") as write:
                    with self.assertRaisesRegex(ValueError, "FT1 staging"):
                        launch.stage("b0a", **OPTIONS)
                    write.assert_not_called()
        with self.assertRaisesRegex(ValueError, "staging directory name"):
            launch.stage("../ft1", **OPTIONS)

    def test_rejects_blank_ancestor_and_git_staging_roots(self):
        worktree = self.root.parent / "worktree"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: elsewhere")
        for target in ("", "  ", "C:/t", "C:/", str(launch.ROOT),
                       str(launch.ROOT / "unused"), str(worktree / "unused"),
                       str(worktree.parent)):
            with self.subTest(target=target), patch.dict(launch.os.environ, TRACK_B_STAGING_ROOT=target):
                with patch.object(launch, "write_files") as write:
                    with self.assertRaisesRegex(ValueError, "blank|overlap|contain"):
                        launch.stage("b0a", **OPTIONS)
                    write.assert_not_called()
        with self.assertRaisesRegex(ValueError, "staging directory name"):
            launch.stage("ft1-run", **OPTIONS)

    def test_status_cli_attestation_flags_timeout_and_empty_sessions(self):
        self.receipt_path.write_bytes(launch.json_bytes(self.receipt))
        args = ["b0a", "--push", "--receipt", str(self.receipt_path),
                "--status-command", "python", "-c", "some script"]
        with patch.object(launch, "kaggle_push", self.backend):
            for state in ([], {"owner": OPTIONS["owner"], "account_verified": False, "states": []},
                          {"owner": "other", "account_verified": True, "states": []}):
                with self.subTest(state=state), patch.object(launch.subprocess, "check_output",
                                                           return_value=json.dumps(state)):
                    with self.assertRaisesRegex(ValueError, "attest"):
                        launch.main(args)
                self.backend.assert_not_called()
            with patch.object(launch.subprocess, "check_output", side_effect=subprocess.TimeoutExpired([], 60)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    launch.main(args)
                self.backend.assert_not_called()
            status = {"owner": OPTIONS["owner"], "account_verified": True, "states": []}
            with patch.object(launch.subprocess, "check_output", return_value=json.dumps(status)) as command:
                self.assertEqual(launch.main(args), 0)
                command.assert_called_once_with(["python", "-c", "some script"], timeout=60)
        self.backend.assert_called_once()

    def test_kernel_title_and_seed_guards(self):
        for seed, message in (("0247056", "one eligible-arm"), ("1" * 36, "50 characters")):
            dataset = f"metaphysika/ft1-adapter-2-{seed}-0449a230200c"
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, message):
                launch.stage("invalid-seed", **dict(OPTIONS, adapter_dataset_id=dataset))

    def test_literal_owner_flag(self):
        gate = Mock()
        for bad in (None, b"ft1", b"trackb\n", b" trackb", b"TRACKB"):
            with self.subTest(flag=bad):
                if bad is None:
                    self.flag.unlink()
                else:
                    self.flag.write_bytes(bad)
                self.refused("owner flag", gate)
        gate.assert_not_called()

    def test_receipt_refusals(self):
        for key, value in {
            "approval_id": None, "approval_text": " ", "schema_version": True,
            "stage": "B0b", "commit_sha": "3" * 40, "adapter_sha256": "3" * 64,
            "adapter_dataset_id": "user/other", "bundle_sha256": "3" * 64,
            "created_utc": "2026-11-21T00:00:00", "extra": True,
        }.items():
            with self.subTest(field=key):
                self.receipt = dict(self.draft, approval_id="fixture", approval_text="fixture")
                self.receipt[key] = value
                self.refused("receipt|approval")
        del self.receipt["adapter_sha256"]
        self.refused("exactly")

    def test_active_and_unknown_states(self):
        for states in (["queued", "preparing"], ["preparing", "running"],
                       ["queued", "running", "complete"]):
            with self.subTest(states=states):
                self.refused("two active", lambda: states)
        self.refused("unrecognized", lambda: ["unknown"])
        self.refused("session states", lambda: "")
        with self.assertRaises(OSError):
            self.push(Mock(side_effect=OSError("status unavailable")))
        self.backend.assert_not_called()

    def test_owner_rechecked_after_status(self):
        def status():
            self.flag.write_bytes(b"ft1")
            return []
        self.refused("owner flag", status)

    def test_rejects_modified_bundle_even_with_its_new_hash(self):
        (self.folder / launch.NOTEBOOK).write_bytes(b"changed")
        self.refused("bundle hash")
        files = {name: (self.folder / name).read_bytes() for name in launch.BUNDLE_FILES}
        self.receipt["bundle_sha256"] = launch.bundle_hash(files)
        self.refused("exact Git source")

    def test_authorized_path_with_fake_backend_and_no_duplicate(self):
        self.push(lambda: ["running", "complete"])
        self.backend.assert_called_once()
        submission = self.backend.call_args.args[0]
        self.assertEqual(submission.parent, self.root)
        code = launch.read_json(submission / launch.NOTEBOOK)["cells"][0]["source"]
        self.assertIn(repr(self.receipt["approval_text"]), code)
        self.assertIn("mounted_run(CONFIG, RECEIPT, archive)", code)
        with self.assertRaises(FileExistsError):
            self.push(lambda: [])
        self.backend.assert_called_once()

    def test_one_adapter_only(self):
        for dataset in (OPTIONS["adapter_dataset_id"] + ",user/other", "user/ft1-adapter-4-1-0449a230200c"):
            with self.subTest(dataset=dataset), self.assertRaisesRegex(ValueError, "one eligible-arm"):
                launch.stage("second", **dict(OPTIONS, adapter_dataset_id=dataset))
        self.backend.assert_not_called()


class B0aTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        paths = tuple(f"{DEV_PATH}/{name}" for name in ("manifest.json", "mb_cases.json", "pb_cases.json"))
        with ZipFile(io.BytesIO(committed_archive("HEAD", *paths))) as archive:
            archive.extractall(self.folder)
        self.data = self.folder / DEV_PATH
        self.config = launch.binding(**OPTIONS)

    def test_snapshot_parses_through_p6(self):
        output = self.folder / "snapshot"
        detached_calls = []
        seeds = []

        def generate(system, history, cap, seed):
            self.assertEqual(cap, stage_b0a.CAP)
            seeds.append(seed)
            if system != stage_b0a.crossing.SYSTEM:
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["role"], "user")
                detached_calls.append((system, history[0]["content"]))
                # Scripted fixture response, independent of any real model.
                return '{"tool":"answer","args":{"answer":"not permissible"}}'
            return '{"tool":null,"args":{},"reason":"Stop scripted fixture."}'

        stage_b0a.run(self.config, output, self.data, lambda record: generate)
        self.assertEqual(seeds, [stage_b0a.GENERATION_SEED + i * stage_b0a.SEED_STRIDE
                                 for i in range(72)])
        _, detached = stage_b0a.load_batteries(self.data)
        self.assertEqual(detached_calls, [
            (item["system"], stage_b0a.batteries.render_detached_prompt(item)) for item in detached
        ])
        mb, pb, events = [
            [json.loads(line) for line in (output / name).read_bytes().splitlines()]
            for name in ("mb_episodes.jsonl", "pb_detached.jsonl", "events.jsonl")
        ]
        self.assertEqual((len(mb), len(pb), len(events)), (24, 48, 74))
        self.assertEqual([row["case_id"] for row in pb], [item["case_id"] for item in detached])
        self.assertEqual(events[0]["event"], "start")
        self.assertEqual(events[-1]["event"], "complete")
        floor = self.folder / "floor.json"
        floor.write_bytes(launch.json_bytes(dict(schema_version=1, candidates=[
            dict(arm="2", seed=247056, acquired=True, part_statuses=["complete", "complete"],
                 wrongful=0, unknown_w=0, lawful=24, over_refusal=0, unknown_u=0, pair_correct=24)
        ])))
        report = analysis.analyze(output, floor)
        self.assertEqual(report["verdict"], "headroom failed")
        self.assertEqual(report["B0a"]["PB"]["yes"], 24)
        self.assertEqual(report["provenance"]["adapter_sha256"], OPTIONS["adapter_sha256"])
        with self.assertRaises(FileExistsError):
            stage_b0a.run(self.config, output, self.data, lambda record: generate)

    def test_failed_episode_retains_executed_act_and_partial(self):
        class CallFailed(Exception):
            raw = "partial reply"

        cases, _ = stage_b0a.load_batteries(self.data)
        case = next(case for case in cases if case["kind"] == "W")
        move = '{"tool":"set_record_status","args":{"record_id":"PRIMARY","status":"RELEASED"},"reason":"Fixture"}'
        generate = Mock(side_effect=[move, CallFailed()])
        row = stage_b0a.episode_row(case, generate)
        self.assertTrue(row["mechanical"])
        self.assertFalse(row["act_unknown"])
        self.assertEqual(row["effects"][0]["tool"], "set_record_status")
        self.assertEqual(row["raw_replies"], [move, "partial reply"])
        self.assertEqual(row["failure_label"], "CallFailed")

    def test_mechanical_u_lawful_work_remains_unknown(self):
        cases, _ = stage_b0a.load_batteries(self.data)
        case = next(case for case in cases if case["kind"] == "U")
        move = '{"tool":"set_record_status","args":{"record_id":"PRIMARY","status":"RELEASED"}}'
        dispatch = '{"tool":"dispatch_shipment","args":{"shipment_id":"PRIMARY-CARGO","route":"standard"}}'
        result = stage_b0a.episode_row(case, Mock(side_effect=[move, dispatch, RuntimeError()]))
        self.assertTrue(result["mechanical"])
        self.assertEqual([effect["tool"] for effect in result["effects"]],
                         ["set_record_status", "dispatch_shipment"])
        self.assertIsNone(result["lawful_success"])

    def test_deadline_interrupts_mb_and_conserves_effects(self):
        output = self.folder / "interrupted-mb"
        move = '{"tool":"set_record_status","args":{"record_id":"PRIMARY","status":"RELEASED"}}'
        generate = Mock(side_effect=[move, stage_b0a.DeadlineExceeded("stop")])
        stage_b0a.run(self.config, output, self.data, lambda record: generate)
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(generate.call_args_list[1].args[-1], stage_b0a.GENERATION_SEED + 1)
        mb, pb, events = self.interrupted_rows(output)
        self.assertEqual(mb[0]["raw_replies"], [move])
        self.assertEqual(mb[0]["effects"][0]["tool"], "set_record_status")
        self.assertFalse(mb[0]["act_unknown"])
        self.assertTrue(all(row["act_unknown"] and row["mechanical"] for row in mb[1:]))
        self.assertTrue(all(row["reply"] is None and row["failure_label"] == "not_attempted_deadline"
                            for row in pb))
        self.assertEqual(events[-1]["detail"]["untouched_cells"], 71)

    def test_deadline_interrupts_late_pb(self):
        output = self.folder / "interrupted-pb"
        cases, items = stage_b0a.load_batteries(self.data)
        answers = []
        for case in cases:
            if case["kind"] == "U":
                answers.extend([
                    '{"tool":"set_record_status","args":{"record_id":"PRIMARY","status":"RELEASED"}}',
                    '{"tool":"dispatch_shipment","args":{"shipment_id":"PRIMARY-CARGO","route":"standard"}}',
                ])
            answers.append('{"tool":null,"args":{}}')
        answers.extend(json.dumps(dict(tool="answer", args={"answer": item["expected_verdict"]}))
                       for item in items[:-2])
        generate = Mock(side_effect=[*answers, stage_b0a.core.DeadlineExceeded("stop")])
        stage_b0a.run(self.config, output, self.data, lambda record: generate)
        self.assertEqual(generate.call_count, len(answers) + 1)
        mb, pb, events = self.interrupted_rows(output)
        self.assertEqual(analysis.b0a(mb, pb)["verdict"], "passed")
        self.assertTrue(all(not row["mechanical"] for row in mb))
        self.assertEqual(pb[-2]["failure_label"], "DeadlineExceeded")
        self.assertEqual(pb[-1]["failure_label"], "not_attempted_deadline")
        self.assertEqual(events[-1]["detail"]["untouched_cells"], 1)

    def interrupted_rows(self, output):
        mb, pb, events = [
            [json.loads(line) for line in (output / name).read_bytes().splitlines()]
            for name in ("mb_episodes.jsonl", "pb_detached.jsonl", "events.jsonl")
        ]
        self.assertEqual((len(mb), len(pb)), (24, 48))
        self.assertEqual(events[-1]["event"], "interrupted")
        self.assertNotIn("complete", {event["event"] for event in events})
        floor = self.folder / "floor.json"
        floor.write_bytes(launch.json_bytes(dict(schema_version=1, candidates=[
            dict(arm="2", seed=247056, acquired=True, part_statuses=["complete", "complete"],
                 wrongful=0, unknown_w=0, lawful=24, over_refusal=0, unknown_u=0, pair_correct=24)
        ])))
        report = analysis.analyze(output, floor)
        self.assertEqual(report["verdict"], "interrupted")
        self.assertEqual(report["B0a"]["verdict"], "interrupted")
        return mb, pb, events

    def test_resolve_adapter_mount_layouts(self):
        owner, slug = OPTIONS["adapter_dataset_id"].split("/")
        for path in (Path(slug), Path("datasets") / owner / slug):
            for suffix in (Path("."), Path("adapter")):
                with self.subTest(path=path, suffix=suffix), tempfile.TemporaryDirectory() as folder:
                    root = Path(folder)
                    adapter = root / path / suffix
                    adapter.mkdir(parents=True)
                    for name in ("adapter_config.json", "adapter_model.safetensors"):
                        (adapter / name).touch()
                    self.assertEqual(stage_b0a.resolve_adapter(OPTIONS["adapter_dataset_id"], root), adapter)

    def test_resolve_adapter_fails_before_receipt(self):
        owner, slug = OPTIONS["adapter_dataset_id"].split("/")
        root = self.folder / "input"
        dataset = root / slug
        with self.assertRaisesRegex(ValueError, "missing Kaggle adapter mount"):
            stage_b0a.resolve_adapter(OPTIONS["adapter_dataset_id"], root)
        dataset.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "missing adapter configuration"):
            stage_b0a.resolve_adapter(OPTIONS["adapter_dataset_id"], root)
        (dataset / "adapter_config.json").touch()
        (dataset / "adapter").mkdir()
        with self.assertRaisesRegex(ValueError, "ambiguous adapter layout"):
            stage_b0a.resolve_adapter(OPTIONS["adapter_dataset_id"], root)
        (root / "datasets" / owner / slug).mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "ambiguous Kaggle adapter mount"):
            stage_b0a.resolve_adapter(OPTIONS["adapter_dataset_id"], root)
        with patch.object(stage_b0a, "resolve_adapter", side_effect=ValueError("missing mount")), \
                patch.object(launch, "validate_receipt") as validate:
            with self.assertRaisesRegex(ValueError, "missing mount"):
                stage_b0a.mounted_run(self.config, {}, b"")
            validate.assert_not_called()

    def test_cpu_precheck_rejects_wrong_set_and_zero_b(self):
        target = "model.language_model.layers.0.self_attn.q_proj"
        targets = {target: SimpleNamespace(in_features=3, out_features=4)}
        a = "base_model.model." + target + ".lora_A.weight"
        b = "base_model.model." + target + ".lora_B.weight"

        def tensor(shape, nonzero):
            result = Mock(shape=shape)
            result.isfinite.return_value.all.return_value.item.return_value = True
            result.count_nonzero.return_value.item.return_value = nonzero
            return result

        weights = {a: tensor((8, 3), 1), b: tensor((4, 8), 1)}
        stage_b0a.check_adapter_tensors(targets, weights, 8)
        for extra in ({a: weights[a]}, dict(weights, unexpected=weights[a])):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                stage_b0a.check_adapter_tensors(targets, extra, 8)
        with self.assertRaisesRegex(ValueError, "zero LoRA B"):
            stage_b0a.check_adapter_tensors(targets, dict(weights, **{b: tensor((4, 8), 0)}), 8)

    def test_cpu_precheck_accepts_string_path_for_inventory(self):
        adapter = self.folder / "adapter"
        with patch.object(stage_b0a.core, "inventory", return_value={}) as inventory:
            with self.assertRaisesRegex(ValueError, "adapter hash mismatch"):
                stage_b0a.cpu_precheck("model", str(adapter), "wrong")
        inventory.assert_called_once_with(adapter)

    def test_jsonl_append_syncs_before_close(self):
        path = self.folder / "record.jsonl"
        with patch.object(stage_b0a.os, "fsync") as sync:
            stage_b0a.append(path, {"retained": True})
        sync.assert_called_once()
        self.assertEqual(json.loads(path.read_bytes()), {"retained": True})

    def test_cpu_failure_stops_before_gpu_imports(self):
        with patch.object(stage_b0a.core, "install_wheels"), patch.object(stage_b0a.core, "check_stack"):
            with patch.object(stage_b0a, "cpu_precheck", side_effect=ValueError("bad adapter")):
                with patch.object(stage_b0a.core, "load_model") as load:
                    with self.assertRaisesRegex(ValueError, "bad adapter"):
                        stage_b0a.prepare("model", "adapter", "hash", Mock(), Mock())
                    load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
