# Fable checks of the FT1 build before preparation job (a) (2026-11-12)

Two fresh-context, bounded, read-only Fable (claude-fable) reviews, recorded verbatim by the stage thread (Claude). Both follow `FABLE_FT1_BUILD_REVIEW_2026-11-12.md` (at 322943d8) and `FABLE_FT1_BUILD_REREVIEW_2026-11-12.md` (at 2f4ec678). Neither generated a sealed file or made a model or network call; both were allowed to read the sealed generator's code but gave structural findings only.

1. Narrow check of `d95d0a528f0e0888555b639428124bf38a5779a4` against `2f4ec678`: NEEDS FIXES (F1, plus F2–F4 and the final-adapter check). Sol fixed these in `4b505fd1`; the stage thread also dropped the separate 384-token prompt cap there (prospective, before any data).
2. Readiness check of `4b505fd1ef0b364aa4689db7117adf1f419eae9f` for job (a): READY. PR #140 was squash-merged as main `91855bb894d31fa0a7b03e95ac6b89c68e0b1abd`, whose tree is byte-identical to `4b505fd1` (`git diff --quiet` checked by the stage thread).

---

## 1. Narrow check of `d95d0a52` (PR #140) against `2f4ec678`

Read-only. The 40 FT1 tests pass in a short-path worktree (one conditional real-template skip); the worktree is removed, but the empty folder `C:/t` is left because the safety check refused its deletion. No sealed file, model or network call; `results/` and the checked-out branch are untouched.

### 1. Verdict: NEEDS FIXES (one small Sol pass)

N1–N5 are fixed, but the notebook writes the dataset automatically if the gates pass, so the first item below would be frozen into the data hashes.

**Blocking**
- **F1. Arm 1 pressure is perfectly tied to the lookup format** (`data.py:173-175`). The N5 fix uses `index%4<2`, which equals arm 1's lookup rule `(index//2)%2==0`. I measured 1,000 records with both and 1,000 with neither. Use an independent bit such as `(index//4)%2` and add a cross-tab test. The sphere records have the same tie (100/100) from before this diff, so fix both.

**Should ride along**
- **F2. Kernel title does not match its id** (`preparation.py:64`, `kaggle.py:80`). The K2 launcher sets title equal to slug and notes Kaggle derives the id from the title. The kernel may land under a different name than the binding expects.
- **F3. A version mismatch leaves no report** (`preparation.py:28`). The CPU run requires exactly transformers 5.20.2, which was measured on the T4 image, not the CPU image. A mismatch raises before anything is written.
- **F4. No fallback for the tokenizer folder** (`preparation.py` notebook line). The CPU path uses the model mount directly, without the GPU path's `resolve_model_path`.

### 2. Item status

| Item | Status |
|---|---|
| N1 receipt mount | Fixed |
| N2 diagnostics, measure-first, staging | Fixed; headroom only partly (see section 6) |
| N3 skip rule | Fixed |
| N4 checkpoint exercised | Fixed (saves every 5 steps, reloads checkpoint-10) |
| N5 arm 1 pressure | Fixed in count (1,000 of 2,000), but introduced F1 |
| Sealed output path | Fixed |
| Roster role and holder/recipient cues | Fixed per the structural test; I did not re-derive it |
| `decide_question` outside sphere | Fixed |
| Failure handler masking the error | Fixed |
| Long enumeration | Fixed (100,000 cap, bounds-only result) |
| Username in committed paths | Fixed in current files; old bytes remain in history |
| Descriptive measures | Implemented, all four |
| Evaluation runner | Not done; deferred as agreed |

### 3. New bugs from this diff

- `data.py:173-175`: F1.
- `preparation.py:64`, `kaggle.py:80`: F2.
- `preparation.py:28`: F3.
- `training.py:146-150`: the reload test loads checkpoint-10, and the final `adapter/` folder is never reloaded or compared with it. Add a hash-equality check.

### 4. Section 5 pass rules

The data-write rules are implemented exactly. The qualification rules match with these differences:
- **Adapter reload:** it tests checkpoint-10, not the saved final adapter (see section 3).
- **Speed:** step times exclude checkpoint-save time; the effect is trivial.
- **Extra gates, all stricter:** T4 and one visible GPU, finite loss sums, "reason exceeds restatable material", and the exact transformers version.

### 5. What is staged

- **(a) Data write: staged.** The notebook is bound to `d95d0a52`, and all 20 source hashes match the commit. It is `PLAN_ONLY = True`, CPU, internet off, and mounts the repo dataset, the receipt dataset and the pinned Gemma 3 12B model. It measures first, writes only on pass, and outputs to `/kaggle/working/ft1-data-preparation`.
- **(a) still needs:** both datasets (`metaphysika/ft1-repo` with `COMMIT.txt`, and `ft1-preparation-approval` with `receipt.json`) are planning names, not created. No FT1 tooling builds the repo dataset, flips `PLAN_ONLY` or retrieves outputs; the pre-run entry must name those manual steps.
- **(b) Qualification: not staged, and it cannot be yet.** `kaggle.stage` needs the written dataset's manifest hash, and the qualify receipt must carry that hash. It also needs a data dataset upload and `k2-wheels`. Chris can approve (b) only conditionally now, or separately after (a).

### 6. Forecasts and pre-mortem

- **Measure run is informative:** about 85%.
- **Data write passes first time:** about 25%. A rough stand-in counter of mine (not Gemma; one token per digit and punctuation mark) put the longest prompt at 449 against the 384 limit, with about 330 cards over. A harsher one put about 1,400 cards over.
- **Qualification passes once data exists:** about 70%.
- **Both complete under one approval:** about 15%.

Pre-mortem: most likely the measure run reports a few hundred cards over 384 tokens. That would be a useful result but would mean a card-trimming round and a second approval before any qualification. Next most likely, the CPU run stops on the transformers version or kernel name before writing a report.

**Next step:** Sol fixes F1 (and ideally F2–F4 and the adapter hash check) on PR #140. The stage thread is waiting on Sol; I then recheck the new commit, the plan is restaged, and the stage thread writes the pre-run entry for Chris.

---

## 2. Readiness check: FT1 CPU preparation job (a) at `4b505fd1`

### 1. Verdict
**READY** for job (a), with no blocking fixes. The 44 FT1 tests pass in a temporary worktree (one conditional skip), which I removed afterwards. The staged notebook matches the commit: all 20 bound source hashes agree, `PLAN_ONLY = True`, CPU, internet off, private, correct model mount.

The job is safe, but I expect it more likely than not to refuse the write (see 6). That would be a retained result, not a defect in the job.

### 2. Earlier findings
- **F1: fixed.** Pressure and lookup are independent in every arm and type; each of the four cells holds 24.8–25.2%, and each arm has exactly 1,000 pressured records.
- **F2: fixed.** Title equals slug (`ft1-data-plan`).
- **F3: fixed.** A version mismatch writes `measure-report.json` with the found versions and stops before loading the tokenizer.
- **F4: fixed.** The CPU path uses `core.resolve_model_path`.
- **Adapter check: fixed.** Final adapter tensors are hashed against checkpoint-10, then the final adapter is reloaded. This only matters for job (b).
- **Prompt-limit change: implemented consistently** in `data.py`, `data_diagnostics.py`, `training.py` and the tests.
- **Bias from the limit change: none found.** Nothing is dropped or truncated per record; one failure refuses the whole write. Arms 2, 2u and 3 share identical prompts. Arms 1 and 4 have shorter prompts (stub medians 230 and 157 against 255), but that is the earlier design, not this change.

### 3. New issues (none blocking)
- **`exploratory/ft1/data.py:330-343` (`choose`): the per-record matching gate is fragile.** Two character-ratio stub counters passed everything. Two word-style stub counters failed the gate on 6 and 30 rows (3 and 15 record pairs). Limits were never close: the largest total was 682.
- **`exploratory/ft1/preparation.py:83`: the notebook ignores what `run()` returns.** A refused write or version mismatch still shows Kaggle status "complete".
- **`exploratory/ft1/preparation.py:76`: the receipt path is hard-coded with no fallback.** It matches the mount layout measured in K2, but a wrong slug stops the job before any report exists.
- **`exploratory/ft1/data.py:176-180`: correction subtype is tied to pressure.** `obedience_limit` is always pressured and `not_carried_out` never is (252 records). This looks definitional, but disclose it.
- **Probe sets are small and uneven.** Arm 1 has only 5 of 40 probes in the pressure/no-lookup cell.

### 4. Pass rule for the pre-run entry
**PASS** requires all of:
- `measure-report.json` shows transformers 5.20.2, tokenizer file hashes, `tokenizer_verified=true` and `record_count=10120`.
- Failures and aggregate failures are empty, and over-limit counts are 0 (trained ≤640, total ≤1,024).
- All 2,000 per-record matches are within max(8, 5%), and the aggregate is within 2%.
- `write-report.json` shows `passed` and `write_passed` true, 2,000 unique records in each of five arms, and eight file hashes.
- The fetched files re-hash to those values.

**FAIL**: the real tokenizer measured all 10,120 records and any gate failed, so no dataset is written. Repair needs a new commit, review and approval, with no limit or gate changes after seeing the results.

**NOT ESTABLISHED**: nothing was measured. This covers a version mismatch, a receipt, mount or source-hash error, a kernel error or timeout, and a missing or partial report. Keep the outputs anyway.

### 5. Manual steps
The steps are safe: both datasets and the kernel are private, internet is off, the archive excludes `results` and `docs`, and it refuses `keys.env` and `.kaggle` paths. Four things are missing:
- Wait until both datasets finish processing (`kaggle datasets status`) before pushing the kernel.
- State that "complete" is not a pass; only the reports decide.
- Write the LAB_NOTEBOOK predictions and pass rule before the push, and bump the README version.
- Check the receipt contains only the approval fields, and confirm the fetch folder is new, as the note already guards.

### 6. Forecasts
- **Measure run completes and is informative: about 80%.**
- **All gates pass and data is written: about 35–40%.**

Pre-mortem: the most likely disappointment is that Gemma's real tokenizer leaves a handful of arm-2/arm-3 pairs with no whole-line restatement inside the 8-token / 5% window, so the write is refused with a full failure list. The second is plumbing, such as a receipt slug typo, an unprocessed dataset, or a CPU image whose transformers version is not 5.20.2, which gives NOT ESTABLISHED. The least likely is a token-limit breach, since totals sit far below 1,024.

**Next step:** the stage thread writes the pre-run notebook entry with the section 4 rule and these forecasts, then asks Chris for exact-commit approval of job (a). Chris is waiting on the stage thread; nothing is waiting on me.
