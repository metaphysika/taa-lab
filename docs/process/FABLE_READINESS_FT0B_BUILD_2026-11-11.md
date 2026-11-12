# Fable exact-commit readiness review: FT0b build (2026-11-11)

Reviewer: Fable (claude-fable), fresh context, bounded packet (`C:\Users\lahn0\T3\briefs\ft0b-readiness\PACKET.md`), read-only. Reviewed commit `36cc26527a290ac9ad5cb18d9ee4e8ef04589ac1` on PR #136. Summarised faithfully by the stage thread (Claude); handling follows.

## Verdict: READY AFTER FIXES

**Must-fix M1. The fp16 cast moved the whole residual stream to fp16** (`ft0b.py` cast; effects on the chunked loss and on `qualify()` generation). The Gemma 3 embedding returns its table's dtype and each layer's residual add keeps it. Under FT0 PEFT's fp32 table kept the stream fp32 even under autocast (bitsandbytes `Linear4bit` returns the input dtype). As built, FT0b would run every residual add and its backward in fp16, the regime widely reported to overflow for Gemma 3 (Fable's memory, not checked here); FT0 already had NaN gradient norms on steps 1–3 with the fp32 stream. Consequences: a NaN loss fails rule 2 and aborts training before any probe (NOT ESTABLISHED); the equivalence backward has no GradScaler, so small fp16 gradients lose precision and cosine ≥ 0.99 is at risk; a pass would under-measure FT1's memory by about 0.4 GB. Not disclosed in the draft or Sol's notes. Fix: keep the table fp16 but upcast the embedding output to fp32 with a forward hook, add a forward-pre-hook casting the output layer's input to its weight dtype (otherwise un-autocast `generate` crashes, reproduced on CPU), record both, and test.

**Owner decision D1. Preflight aborts versus verdicts.** `check_internals`, `layout()` and the Trainer-normalisation guards raise before any measurement; the report would call that NOT ESTABLISHED, and the draft then stops all Kaggle fixes. The pre-run entry should say whether a guard trip before the first `equivalence` event counts as "no attempt" with one relaunch allowed.

## Q1. False pass or false fail
- **Pinned hashes:** all four equal the PyPI wheel files for transformers 5.20.2 and PEFT 0.21.2 (LF); Fable downloaded and compared. Not verified: that Kaggle installed those exact wheels unpatched. A mismatch fails closed about a minute in (D1).
- **`before_cast` fp32:** holds; PEFT upcasts every fp16/bf16 non-`Params4bit` parameter (`peft/utils/other.py:205-209`). The 12B loads bf16, so bf16 → fp32 → fp16 is essentially lossless.
- **Tied table:** the `.data` cast on one shared Parameter is safe; FT0's memory implies a single shared Parameter.
- **`lm_head`** stays a plain `nn.Linear` (excluded from quantisation).
- **Trainer normalisation correct:** `model_accepts_loss_kwargs` True, `_loss_shifts_labels` True, loss is sum/N with `num_items_in_batch` and not divided again; FT0's eight raw losses of about 0.35 sum to the logged 2.75.
- **Old versus chunked loss:** mean over shifted non-ignored positions versus sum/count; identical.
- **Softcapping:** default `None`; the real `config.json` was not inspected; non-null fails closed.
- **Gradient checkpointing** is on during equivalence (`prepare_model_for_kbit_training` enables it).
- **Gap to disclose:** neutral records average about 27 trained tokens, so every equivalence record is a single 128-position slice; multi-slice chunking is only CPU-tested.

## Q2. Probes
Faithful to a Trainer step on every point checked: same resident `AcceleratedOptimizer` and GradScaler; scaled backward; unscale then clip; `optimizer.step()` runs scaler step and update; no zeroing between micro-steps; denominator 8 × span equals the shifted label count; checkpointing still on. OOM recovery via `scaler.update(new_scale=...)` is safe. Minor: after an OOM, `value` keeps the last graph alive until the next span; add `del value`. Eight identical 1,024-token records is the worst case.

## Q3. Report
Matches the draft (rules 1–4, thresholds, slowest step, 200 raw losses, span checks, skip flag, reserved flag, 896 report-only). NOT ESTABLISHED before a rule-2 FAIL is sensible; both mean stop; state it in the entry. Advisories: non-finite probe losses/gradients are only a warning, so a PASS can coexist with every 640-span update skipped, and the entry should give such a PASS a headline caveat; report warm-up peaks; bare asserts give the uninformative reason "AssertionError"; add `torch.cuda.empty_cache()` after the cast so the `fp16_cast` reserved figure is meaningful.

## Q4. Unchanged paths
Yes. Every change is gated on `FT0B`/`--ft0b`; `core.py` and `ft0.py` unchanged; the launcher's `^FT0\s*=` substitution does not match the `FT0B` line. 94 tests passed in a scratch worktree.

## Q5. Pre-mortem
1. The fp16 stream (M1) gives NaN or low cosine, so FT0b fails on precision, not fit.
2. A guard trips on the real stack and the stop rule forbids a relaunch (D1).
3. PASS while probe gradients are non-finite; FT1 then skips most updates at long spans.
4. Time is tight: 14.6 s/step at about 141 tokens against a 115 s/step limit at about seven times the length; scaling should be sublinear but is unmeasured.
5. Equivalence passes on single-slice short records and is read as proof for 640-token multi-slice training.
6. Synthetic probes miss mixed-length fragmentation over 250 steps.

## Probabilities (Fable)
With M1 fixed: PASS 50%, PASS LIMITED 5%, FAIL 30%, NOT ESTABLISHED 15%. As built: 25 / 5 / 40 / 30. The memory rule likely passes (estimated peak 10–11e9). Could not verify: actual fp16 overflow on Gemma 3 12B, Kaggle's installed file bytes, the real tokenizer's exact-length search for the new prefix lengths, all GPU behaviour.

---

## Stage-thread handling (Claude)
- M1: fixed in `ft0b.stream_hooks` (embedding output upcast to fp32; output-layer pre-hook casts its input to the weight dtype), installed at the cast and recorded as `stream_fp32_hooks` in the `tables` event; the report requires it for rule 1. CPU test added (fp32 stream, un-autocast output layer, fp32 residual gradient).
- Advisories applied: `del value` after each span; `torch.cuda.empty_cache()` after the cast; warm-up peaks reported per span. Not applied: replacing bare asserts (cosmetic).
- D1 and the non-finite-probe caveat go to Chris in the pre-run entry.
