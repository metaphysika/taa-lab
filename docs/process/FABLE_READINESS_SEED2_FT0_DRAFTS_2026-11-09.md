# Fable design-stage readiness review: seed 2 and FT0 drafts (2026-11-09)

Reviewer: Fable (claude-fable), fresh context, bounded packet, read-only. Reviewed revision 1 of `docs/process/SEED2_FT0_PRERUN_DRAFTS_2026-11-09.md` at branch `b1b2-audit-decisions-notebook` (from main `0816ae3a`). Recorded by the stage thread. The drafts' revision 2 applies the must-fixes.

## 1. Verdicts

**Draft A (seed 2): GO after fixes.**
Must-fix:
- The seed is set in more places than the draft says. Changing only the stage-file constant would retrain seed 1 while the manifest records seed 2. The runtime hard-codes 247056 at `scripts/study_d_gemma_stages_runtime_v02424.py` lines 262, 418 and 451. The build needs one seed source plus a CPU test that the new seed reaches all of them.
- Add a reading rule for a failed control: keep L2's rule that neutral Manager 3 or more is a negative.
- Disclose that sampling seeds differ per cell: they are `248017 + call sequence` (`modal_backend.py:106`), and dropping the base arm shifts the sequence.
- Name which stage is dropped if training bills at the cap, and say that the dashboard is read between training and evaluation.

Advisories:
- "Pointers" understates the build. The harness pins adapters against a plan (`exploratory/audit_tool/modal_adapter.py:8`) and hard-codes Volume names (`modal_backend.py:267`).
- The build needs a new launch window, ledger and cap.
- Run an acquisition check on both new adapters before the 96 cells.

**Draft B (FT0): NOT READY as written; the fixes are small.**
Must-fix:
- The memory test does not test 1,024 tokens. K2 neutral records average about 141 tokens, so the synthetic pass must run at 1,024 as well as 2,048, and the gate must use the 1,024 pass.
- The 13.5 GB figure was for Gemma 4 12B. Either keep 12 GB or state 13.5 GB as a deliberate loosening, with a reason.
- Say why Gemma 3 12B is the subject (it was already servile untrained, 11/16).
- Step time was measured on short records. Time the long-record passes.

Advisories:
- "At most 5 of 5 skipped updates" cannot fail; report it rather than gate on it.
- Record throughput and the evaluation-time estimate.
- Check that all LoRA modules are language-model modules.

## 2. Answers

**Q1.** The scope is right in intent but not yet accurate in mechanism. A neutral-only T-controls is acceptable, because the base model does not depend on the seed. Note that the base reading is inherited from L2 at different sampling seeds.

**Q2.** Leaving 3–4 and 9 as gaps is fine if they are labelled "not established". Put "replicates" nearer 40%.

**Q3.** 13.5 GB is workable only if measured at true length. The 2,048 probe is the right idea: use a realistic chat-template record and the same gradient-checkpointing setting, and report step time.

**Q4. Pre-mortems.**
- *Seed 2:* the seed did not actually change, or changed inconsistently; the build grew into weeks of receipt plumbing; training billed at the cap and evaluation was cut; a count of 5–8 was read as "variable" when part was sampling-seed noise; a weakly trained adapter was read as seed fragility.
- *FT0:* it passed on short records, and FT1 then ran out of memory or time on real arm 3 records; or fp16 skipped every update and 12B never trained, which five steps cannot show; or training fit but adapter evaluation on long histories did not.

## 3. Factual errors in revision 1

- **Seed location.** `v02424.py:33` is the sampling seed (248017) and must not change. Line 38 is the training seed. The runtime literals are listed above. Fable's own K2b review (line 127) made the same omission.
- **"Fable's 12B figure"** refers to Gemma 4 12B (`FABLE_K2B_RESULT_REVIEW_2026-11-09.md:106`).
- **"Peak at the 1,024 context"** is not measured by the qualification run.
- **Confirmed:** Gemma 3 12B is already allowed in train mode (`core.py:71`, `631–634`). The no-truncation check is at `core.py:355`. The 7.8 of 15.6 GB figure matches the notebook.
