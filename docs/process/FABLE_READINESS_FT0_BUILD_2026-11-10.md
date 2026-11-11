# Fable exact-commit readiness review: FT0 build (2026-11-10)

Reviewer: Fable (claude-fable), fresh context, bounded packet (`C:\Users\lahn0\T3\briefs\ft0-readiness\PACKET.md`), read-only. Reviewed commit `bb353252662d8a2048ebf2187b9d1d682ba7d310` (tree `20386db5`) on PR #132. Recorded verbatim by the stage thread (Claude), followed by how each point was handled.

---

**Verdict: READY AFTER FIXES** for an owner-approved $0 Kaggle run. I found no path to a false PASS inside the notebook or probe code. The fixes are one launch-process blocker and three small robustness changes that would otherwise waste the run.

Checked at `bb353252` (tree `20386db5`): the K2 tests pass (78 OK) from a `git archive` copy with no `keys.env`. Hosted CI has `fast`, `smoke` and `scope` green; `offline` (two jobs), `formation`, `q18`, `reference-and-foundation`, `test` and the CPU rehearsal were still pending when I looked.

## Must-fix

1. **The launch command cannot run at exactly `bb353252` (process, `launch.py:44`).** A non-plan `push` requires the commit to be an ancestor of `origin/main`, and the standing squash-merge rule produces a new SHA. Approve the squash commit on main instead, after confirming its tree is `20386db5745aea9a902828634895c7b35a4ed58b` (or at least that `exploratory/k2_kaggle/` is unchanged). `stage-repo` for that SHA must also come first; the packet's command omits it.

2. **A non-finite probe loss aborts the whole run (`ft0.py:61`).** `core.finite_scalar` raises before `backward`, nothing catches it, and the run ends as `run_failed` with no memory or time for that length. 4B produced NaN gradients on all five fp16 qualify steps, so a non-finite loss at 1,024 degenerate tokens is plausible. Retain the row with a non-finite flag, still run `backward`, and let the report decide.

3. **Only `torch.cuda.OutOfMemoryError` is caught (`ft0.py:74`).** A cuBLAS or bitsandbytes allocation failure surfaces as a plain `RuntimeError`. At 2,048, which is not gating, that would turn a valid 1,024 result into NOT ESTABLISHED. Catch `RuntimeError` whose message contains "out of memory" or "ALLOC_FAILED" as `probe_oom`.

4. **The report does not check what it ran on (`ft0.py:122-135`).** It never asserts `gpu == 'Tesla T4'`, `visible_gpus == 1`, `recipe_sha256 == core.digest(core.RECIPE)`, the approved `repo_commit`, or that each `length_probe_record` has exactly `length` ids. A run on another 16 GB card or commit would report PASS. This is offline code, so it can land after the run, but before anyone reads a verdict.

## Advisories

- **Training peak is lost (`ft0.py:57`):** the first reset wipes the five-step peak before it is retained; record `max_memory_allocated()` once before the loop.
- **Gradients are not inspected:** per pass, record how many LoRA gradients are non-None and finite. This is the only cheap evidence FT0 can give on whether fp16 survives at 1,024.
- **`use_cache` is not restored (`ft0.py:43`):** it stays False into `qualify()`'s generation. If `generate` honours it in transformers 5.20.2 (unverified), throughput and the evaluation estimate are understated and not comparable with 4B.
- **Small under-read of memory:** the probe zeroes gradients each pass, while real training holds accumulated gradients across eight micro-steps. Treat a peak above about 13.2e9 as marginal.
- **Reserved memory is not surfaced:** the gate is on allocated bytes; show `peak_reserved_bytes` in the summary and flag it above about 15.0e9.
- **No FT0 label:** the kernel slug and results folder say only "qualify-neutral"; the flag is only in `launch.json` and metadata.
- **Adapter needed for the report:** `ft0.report` requires `adapter/`, which was not committed for the 4B run. Run it on the fetched folder.

## Q1. Faithful to Draft B; any false pass?

Faithful. The probe is a real micro-step on the trainable model:
- **Autocast:** fp16, matching the Trainer.
- **Checkpointing:** re-enabled explicitly, and the input-gradient hook from `prepare_model_for_kbit_training` persists.
- **Gradients:** if they were not flowing, `backward` would raise, not pass silently.
- **Optimizer state:** still resident, because `trainer` is alive.
- **Peak reset:** placed before the forward pass and read after `backward`; timing is synchronised and excludes the deadline check.
- **Updates:** none are kept, and the adapter is saved and checked before the probes (pinned by a test).

The sliding window at 2,048 changes masks, not memory, in the implementations I know. I could not inspect transformers 5.20.2, so which attention implementation runs is unverified. It is not gating here, but it does feed FT1's context choice.

## Q2. Will it run on the T4?

- **Module naming:** the 4B run, same class and stack, recorded 238 modules named `base_model.model.model.language_model.layers.N…`. Both the new filter and `ft0.language_modules` accept these. 12B's own naming is unverified, but a mismatch fails before training.
- **`probe_record`:** the logic is sound and matches `masked_record` (same prefix and end token). I did not run it on the real Gemma tokenizer. If no unit gives one token per repeat, it raises and the run fails closed after the adapter is saved.
- **OOM handling:** a caught OOM leaves the session able to finish; `qualify` and the manifest still run. `loss` stays alive until `probes` returns, which is harmless.
- **Deadline:** an 8.5 h session against a run of minutes. The check runs before each pass.

## Q3. Is the report correct?

Yes against the pass rule:
- **Units:** decimal 13.5e9, consistent with the T4's recorded 15,636,037,632 bytes.
- **Time:** `(load + 250 × slowest pass × 8) / 3600 ≤ 8.0`.
- **Losses:** 40 is right; `compute_loss` runs once per micro-batch and probes emit no `raw_loss`.
- **Verdict logic:** FAIL beats NOT ESTABLISHED; a 1,024 OOM is FAIL, a 2,048 OOM does not gate, and an empty folder is NOT ESTABLISHED.

The evaluation estimate will look alarming and is weak. It assumes 1,024 output tokens per request and takes throughput from a 16-token generation that includes prompt prefill. At 4B's 4.9 tokens/s it would give about 28 h. It is reported only.

With FT0 off, 1B and 4B behave the same: every notebook change is behind `if FT0`, `RECIPE` and its hash are untouched, and the `core.py` filter change affects 12B only. `implementation_sha256` changes, but nothing compares it for existing adapters.

## Q4. Pre-mortem

1. **A genuine memory fail.** `prepare_model_for_kbit_training` casts non-4-bit weights to fp32 (from memory of PEFT, not verified at 0.21.2). On 12B that adds roughly 3 GB over the 7.8 GB inference peak, plus about 3 GB of logits and loss tensors at 1,024 tokens. My guess is a 1,024 peak of 13 to 14.5 GB, so I would put a pass nearer 45% than 60%, and expect 2,048 to OOM. The obvious remedies are recipe changes this entry forbids.
2. **It passed but FT1 never trains.** fp16 skips every update, as on 4B. FT0 as built records only the five-step skips.
3. **Marginal pass, later OOM.** Allocator fragmentation over 250 mixed-length steps, plus accumulated gradients, exceeds what three identical passes showed.
4. **Lost run read as a result.** A NaN probe loss or non-OOM allocation error gives NOT ESTABLISHED, which gets read as "12B doesn't fit".
5. **Wrong hardware or commit.** The report says PASS and nobody checks `metadata.gpu` or `repo_commit`.
6. **The evaluation estimate misleads FT1 planning** in either direction.

---

## Stage-thread handling (Claude)

- Must-fix 1: accepted. Chris is asked to approve the squash-merge SHA on main, with its `exploratory/k2_kaggle/` tree checked against the reviewed head, and the launch sequence includes `stage-repo` first.
- Must-fix 2: fixed. Probe losses are retained with `loss_finite`; `backward` still runs; no abort.
- Must-fix 3: fixed. `ft0.is_oom` treats `OutOfMemoryError` and RuntimeErrors containing "out of memory" or "ALLOC_FAILED" as `probe_oom`; others still raise.
- Must-fix 4: fixed. Rule 1 now checks Tesla T4, one visible GPU, recipe hash, neutral arm, exact probe-record lengths and, with `--approved-commit`, the repo commit.
- Advisories applied: training peak retained before probes; per-pass LoRA gradient present/finite counts; `use_cache` restored; reserved peak surfaced and flagged above 15e9; 1,024 peaks above 13.2e9 flagged marginal. Not applied: FT0 label in the slug (the flag is in launch.json and metadata; the results folder name will carry "ft0" when the stage thread renames it per CLAUDE.md rule 4).
- Fable's pass estimate (about 45%, against Claude's draft 60%) goes into the pre-run entry.
