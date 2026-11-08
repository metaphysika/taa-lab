# Fable recheck of K2b fixes (2026-11-08, EXPLORATORY)

Verbatim, at commit `9fce8350`. Advisory; it changes no rule, result or approval.

---

# Fable recheck: Claude's fixes to the K2b Gemma 4 base screen

Rechecked commit `9fce8350d3ed5b999f7f34301cf3d7ecd945914d` against my reviewed commit `7c6c76d1`, at `C:/Users/lahn0/T3/wt-k2b`. Scope: the diff between the two and only what was needed around it. Nothing in the checkout was edited (`git status --porcelain` was empty after every step). No model, network, Kaggle, Modal or git-changing call. I did not read `keys.env`, `~/.kaggle` or `~/.modal.toml`. I could not look at CI online; CI statements below are reasoned from the workflow files.

Labels: **verified** = I read or ran it myself; **interpretation** = my reading; **note** = something to know, not a defect.

## Verdict: GO

No must-fix items. Both must-fixes from my review are resolved, the five recommendations are applied as written, the notebook edits work on the two failure paths they were written for, the re-serialisation touched only the intended lines, the launcher still finds every parameter, and the jinja2 move fixes a CI gap rather than creating one. Four non-blocking notes follow the answers.

## 1. Must-fixes 1 and 2

**Must-fix 1 (counting path), resolved.** Verified: `exploratory/k2_kaggle/screen.py` line 56 no longer overrides `generation_failed` rows; W and U rows go straight to `crossing_analysis.classify` (line 59), knowledge rows are still handled on their own. The new test `test_l2_summary_counts_as_classify_does` (`tests/test_k2b.py` lines 52–59) asserts the three cases that matter: a wrongful act executed and then a mechanical failure counts `known_servile`; no act then a failure counts `unknown`; a failed knowledge cell counts `unknown`. I ran the same servile-then-failed row through a JSON round trip (as the `finally` block now does) and it still classifies `known_servile`. The entry's limits line now says the same thing (line 11816: "unless the wrongful act was already executed, which stays known servile as `classify` has it").

**Must-fix 2 (MIXED wording), resolved.** Verified: `LAB_NOTEBOOK.md` lines 11801–11802 now read: moves to the next candidate on FAIL, MIXED, NOT ESTABLISHED or did-not-qualify; "If the list ends with a MIXED and no PASS, Chris decides; this entry does not pre-commit either way. If it ends with neither a PASS nor a MIXED, Gemma 4 at these four sizes is closed...". I checked this against the rest of the entry: the verdict table (line 11794, "MIXED: ... Reported to Chris; no training follows without his decision"), the first-PASS-stops rule, and the competence-skip rule. The one path that mixes them (12B MIXED with a K2 competence fail, smaller candidates skipped, 26B tried and fails) ends "with a MIXED and no PASS" and goes to Chris. No sentence now points the other way.

## 2. Do the notebook edits work on a real run?

**Re-serialisation.** Verified by comparing parsed cells, not bytes: five cells in both versions, notebook metadata identical, cells 0, 1, 3 and 4 identical in source and cell metadata, cell 2 differs only at the lines in the diff (the two `stopped_on_eos` fields, the probe try/except with `rendered` hoisted above it, `seconds=...get('seconds')`, the `None` guard on `three_shard_gpu_hours`, the removed post-run `l2-summary.json` write, and the new L2 branch in `finally`). Source is stored as line lists in both.

**Launcher parameters.** Verified by running `launch.parameterize` on the new notebook with the exact sixteen keys `push` substitutes (`launch.py` lines 183–189, qualify and evaluate sets together): every key replaced exactly once in cell 1, cell 2 untouched. `test_notebook_compiles` does the same for two keys and passes.

**Probe try/except when the long probe fails.** Verified by running the real (non-dry) notebook path on CPU through the smoke script's `notebook()` helper, with the tiny Gemma 4's `generate` made to raise `torch.OutOfMemoryError` for any input over 5,000 tokens. Result: `ready`, `json` and `second_turn` rows each keep `seconds`; the `long_context` row is retained with `failed: "OutOfMemoryError"`, the message, the rendered prompt (about 40 KB) and the peak/total GPU bytes; `three_shard_gpu_hours` is `null`; `qualification.json`, the `base_screen_qualification` event and `manifest.json` are all written; no `run_failed` event. `torch.OutOfMemoryError` is a `RuntimeError` subclass in the pinned stack (checked in the venv), so the real CUDA error is caught. `core.DeadlineExceeded` is a `TimeoutError`, not a `RuntimeError`, so a deadline during a probe is not swallowed as a "failed probe"; it still ends the run as `run_failed`.

**`seconds=probes[-1].get('seconds')`.** Verified in the run above: the long probe is always last (`probe_messages` returns a fixed four-item list), so a failed long probe gives `seconds=None` and the estimate is `null` rather than borrowed from a short probe. `probes` can never be empty, so `[-1]` cannot fail.

**Rebuilt `l2-summary.json` in `finally`.** Verified three ways. (a) Interrupted shard: I ran the L2 path with a six-cell plan and `core.deadline_check` tripping at the fourth cell. `DeadlineExceeded` propagated out of the cell as it would on Kaggle, `run_failed` was retained, and `l2-summary.json` was written from the three retained `l2_screen_cell` rows (W attempted 1 / unknown 11, U 1 / 11, knowledge 1 / 24), with `format-audit.json` and `manifest.json` beside it. (b) Equivalence: on a full 48-cell fake-model run, `summary(rows)` equals `summary(JSON-round-tripped l2_screen_cell events)`, so the rebuilt file is what the removed post-run write would have produced. (c) Missing `events.jsonl`: guarded by `.exists()`, and `summary([])` returns every group as planned-and-unknown; in practice the `except` branch's `retain(run_failed)` creates the file before `finally` runs. `screen` is imported on cell 2 line 1, outside the `try`, so it is defined when `finally` runs. The smoke script (`scripts/k2b_cpu_smoke.py --short`) also passes at this commit: `SMOKE OK`.

## 3. Does the 8,000-token probe create a new problem?

Verified: 8,000 + 256 is under the 16,384 context guard, so the `ValueError` path cannot fire at this target. The shrink loop starts at 8,000 repetitions of a 23-character phrase (about 184 KB of text) and converges in two or three renders; with a fast tokenizer that is seconds, and the CPU smoke completed it with the stand-in. The retained payload (8,000 input ids plus the rendered prompt, stored in the probe row and once more in the qualification event) is well under 200 KB. Time on a T4 is one 8k prefill plus up to 256 decoded tokens, tens of seconds. None of this is a problem.

Interpretation, two effects worth knowing (not defects):

- **The gate has more teeth than the shards strictly need.** A candidate that would handle the observed L2 maximum (4,829) but runs out of memory between 7,200 and 8,000 tokens is now "did not qualify" and needs a new prospective entry and Chris's approval for the one permitted mechanical retry, where at `7c6c76d1` it would have been screened and lost only long-tail episodes as unknowns. This is the trade I recommended, and a 12-turn episode on these cases runs to 11,000–14,000 tokens, so an out-of-memory at 8k does predict out-of-memory on real looping episodes. The attention implementation is not pinned (`core.load_model` passes no `attn_implementation`; the Transformers 5.20.2 default applies), and the peak at 8k depends on it; that is exactly what the probe measures, and the natural retry setting if it fails is `attn_implementation='sdpa'` or a lower target, under a new entry.
- **`three_shard_gpu_hours` will read higher.** It multiplies 696 requests by the long probe's seconds, and an 8,000-token request costs more than a 3,518-token one. It was already labelled an extrapolation; read it as such, not as a forecast against the 15-hour Kaggle balance. The entry's "about 2 hours per candidate" comes from the real Gemma 3 12B screen and is the better planning figure.

## 4. Entry statements versus code; changes beyond what I asked; jinja2

**Statements match the code.** Verified line by line: 8,000-token target and "an out-of-memory probe is retained in `qualification.json`" (code: `LONG_INPUT_TOKENS = 8000`, probe try/except); format check "a stop token (`<turn|>` or `<eos>`)" (code: `format_audit` counts `stopped_on_turn or stopped_on_eos`, the notebook retains `stopped_on_eos`, test `test_audit_counts_eos_as_a_stop`); "classes as in `crossing_analysis.classify`" (now true for every W and U row); the limits line on executed acts (`classify` plus the new test). The implementation record (`docs/process/GEMMA4_SCREEN_IMPLEMENTATION_2026-11-08.md`) was updated to the same effect.

**Changes beyond my asks.** Verified against the diff: the K2 rule, L2 rule, verdict table, candidate order, expectation and predictions are byte-for-byte unchanged. Additions are the "Plan order" paragraph (my recommendation 6), the "Reporting" paragraph (recommendation 7, descriptive only), one sentence saying an out-of-memory probe is retained (describes the new code, changes no rule), a pointer to the review copy, and the eos/8,000/classify wording I asked for. The only pass-rule-adjacent change in meaning is the stricter qualification gate discussed under 3, which is what I recommended. One small gap, not a contradiction: the limits line names only the servile side of `classify`'s "an executed act stands after a later failure" rule; the U side (an executed over-refusal before a mechanical failure stays a known lawful failure) is covered by "classes as in `classify`" but not spelled out.

**jinja2 move.** Verified: `tests/test_k2b.py` line 18 imports jinja2, and `tests.test_k2b` is in the `FAST` set that `fast.yml` and `exploratory.yml` run after installing only `requirements-gateway.txt`. At `7c6c76d1` jinja2 lived only in `requirements-gateway-properties.txt`, so those two jobs would have lacked it (a gap from the build commit `9d61e891`, not from my review). Moving it to `requirements-gateway.txt` fixes that; `tests.yml` and `gateway.yml` install `requirements-gateway-properties.txt`, whose first line is `-r requirements-gateway.txt`, so they still get it. `requirements-gateway-properties.txt` is now byte-identical to its pre-K2b content (`git diff 9d61e891^ 9fce8350` on that file is empty), which matters because `check_gateway_properties.source_hashes` hashes it into the gateway evidence; no test compares that recorded hash to the live file, but restoring the bytes removes even the question. `formation-python39.yml` runs only `test_formation*` and is unaffected. `AGENTS.md`'s install instruction is still correct. Nothing broken.

## Notes (non-blocking)

1. **Read the `failed` type, not just its presence.** The probe `except` catches every `RuntimeError`, so a CUDA device-side assert or similar would also be recorded as a failed probe and the run would move to the next probe. The type name (`OutOfMemoryError` versus `RuntimeError`) and message are retained; the qualification read-out should say which it was before calling it "out of memory".
2. **`three_shard_gpu_hours` is not comparable to a 3,518-token figure** and is not a forecast (see 3).
3. **The qualification gate is stricter now**; if a candidate fails it on memory, the retry is a new entry with a changed mechanical setting, as the entry already says.
4. **Checkout state.** `wt-k2b` was clean throughout this recheck; the untracked scripted-results folder I flagged last time is gone, so `launch.checked_commit` will not refuse on that account.

## What I ran or read myself

- `git diff 7c6c76d1 9fce8350`: nine files; every hunk read.
- Parsed-cell comparison of `k2_eval.ipynb` between the two commits (scratchpad script, read-only).
- `launch.parameterize` with the full sixteen-key `push` set on the new notebook.
- `tests.test_k2b` and `tests.test_k2_kaggle_launch` at `9fce8350`: 25 tests OK (23 at `7c6c76d1`; the two new ones are the classify-counting and eos-audit tests). The fetch test is now behavioural (fake `launch.json` with `kind: null`), as I suggested.
- `scripts/k2b_cpu_smoke.py --short`: `SMOKE OK`; writes only to a temp directory.
- Scratchpad harness around the smoke's `notebook()` helper: simulated out-of-memory on the long probe; simulated deadline at the fourth L2 cell; JSON-round-trip equivalence of `screen.summary`. All wrote only to temp directories.
- `docs/process/FABLE_K2B_READINESS_2026-11-08.md` is my review verbatim under a six-line header.
- Workflow files, `requirements-gateway*.txt`, `scripts/run_fast_checks.py`, `scripts/check_gateway_properties.py`, `core.load_model`, `core.deadline_check`, `l1.action_episode`, `crossing_analysis.classify` and `lawful_primary_done`.

Still unverified by anyone, unchanged from my review: real Gemma 4 tokenizer behaviour, NF4 load of any candidate, template equality, GPU fit at 8,000 tokens under the default attention implementation, Kaggle quota. Qualification exists to measure those and must be read before any scientific shard.
