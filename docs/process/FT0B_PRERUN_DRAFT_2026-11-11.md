# FT0b: memory-layout training-fit check for FT1, draft (2026-11-11)

Status: **draft for build, not a pre-run entry.** The pre-run entry goes into `LAB_NOTEBOOK.md` after Sol's build passes Fable's exact-commit readiness review. Nothing runs without Chris's exact-commit approval. Exploratory, non-scientific, $0.

Basis: FT0 failed rule 2 (out of memory at 1,024 tokens; `LAB_NOTEBOOK.md`, 2026-11-11). Fable's options review (`docs/process/FABLE_FT1_OPTIONS_REVIEW_2026-11-11.md`) recommended this check; Chris agreed on 2026-11-11.

## Question

Can Gemma 3 12B IT be LoRA-trained on one Kaggle T4 at FT1's record lengths when two memory costs are removed, and the training math stays the same? The two costs are the fp32 copy of the frozen vocabulary table and the full-vocabulary scores at every position.

## Proposed FT1 record lengths (Chris approves these with this draft)

- **Total length:** at most 1,024 tokens per record (the K2 recipe context; no truncation, unchanged).
- **Trained part (assistant reasoning and action):** at most **640 tokens**. That is roughly 450 words of step-by-step reasons, corrections and the final action, for arm 3. Arm 2 uses the same cases with the action only.
- **Prompt part (system, case, records, history):** the remainder, at least 384 tokens.
- How arms 2 and 3 are matched on trained tokens stays FT1's separate decision, fixed before any FT1 data is written.

FT0b gates on the 640-token trained span. If 640 fails but 384 passes, the result is **PASS LIMITED**, and Chris decides whether FT1 can live with 384.

## What changes (all behind a new `FT0B` flag; default off; 1B, 4B, FT0 and K2 paths unchanged)

1. **Vocabulary table stays fp16.** After `prepare_model_for_kbit_training`, any frozen fp32 embedding or output-layer weight is cast back to fp16. The run records dtype, bytes and whether input and output share one tensor, before and after.
2. **Chunked loss on trained positions only.** The model returns final hidden states, not logits. The output layer and the cross-entropy run only on positions whose next-token label is not -100, in slices of 128 positions, each slice recomputed in backward (checkpointed), so no full logit tensor is ever held. Normalisation must be identical to the Trainer's default causal-LM loss, including how it divides across the eight accumulated micro-steps (`num_items_in_batch`), and any final logit soft-capping in the model config must be applied.
3. **Allocator setting:** `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, set before torch loads.

The recipe (`core.RECIPE` and its hash), records, LoRA targets, rank, optimizer, fp16 compute, batch and accumulation are unchanged.

## Design

One `MODE='qualify'` run with `FT0B=True`, K2 neutral records, training seed 247056, one visible T4.

1. **Itemised memory:** allocated and reserved bytes after load, after kbit preparation, after the fp16 cast, after the LoRA wrap, after Trainer creation, and after training.
2. **Equivalence check, before training** (no optimizer state yet, short records, so the old path fits as it did in FT0): on the first 8 records in the training order, compute the loss and LoRA gradients with the old setup (fp32 table, standard full-logit loss), then with the FT0b setup (fp16 table, chunked loss), same weights.
3. **Training: 25 optimizer steps** (200 micro-steps) on the neutral records with the chunked loss, recording every raw loss, skipped (non-finite) update and step time.
4. **Existing qualify checks:** template and mask probes, adapter save, finite tensors, reload, switch, disable.
5. **Generation speed:** on the reloaded adapter, 200 new tokens greedy from the qualification prompt, timed (replaces the 16-token figure for evaluation planning).
6. **Full-step probes on the trainable model** after the adapter is saved: for trained spans of 128, 384 and 640 tokens (each record exactly 1,024 tokens, built from the chat template like FT0's probes), one warm-up optimizer step and then two measured optimizer steps. Each step is eight accumulated micro-steps plus the optimizer update, gradients not zeroed between micro-steps. A span of 896 is run last, report-only. Updates are not kept (the adapter is already saved). An out-of-memory error is retained, and the run still finishes.

## Pass rule (to be fixed in the pre-run entry; proposed)

1. **Artifacts and identity:** as FT0 rule 1 (Tesla T4, one visible GPU, recipe hash, neutral records, approved commit, language-model LoRA modules, exact probe lengths), plus `ft0b` metadata, `qualification_complete` with 25 steps and 200 finite raw losses, and the fp16 table recorded.
2. **Same math.** Over the 8 equivalence records: every per-record loss differs by at most 0.02 nats and the median by at most 0.005; for each record, the cosine similarity between the old and new LoRA gradient vectors is at least 0.99. Failing this is FAIL, whatever the memory.
3. **Memory:** peak allocated over a full optimizer step at the 640-token trained span is at most 13.5e9 bytes.
4. **Time:** load + 250 × (slowest measured 640-span optimizer step) is at most 8.0 h.
5. **Reported, not gating:** the 128, 384 and 896 spans; reserved memory (flag above 15.0e9); skipped updates in 25 steps (flag if more than 3 of the last 20); itemised memory; generation tokens per second over 200 tokens.

**Verdicts.** PASS needs rules 1–4 at 640. PASS LIMITED: rules 1–2 pass and rules 3–4 pass at 384 but not at 640. FAIL: rule 2 fails, or rules 3–4 fail at 384. NOT ESTABLISHED: rule 1 cannot be verified.

**On FAIL or NOT ESTABLISHED:** stop. No further Kaggle memory fixes (Fable's fix-on-fix warning); the next step is pricing a 24 GB Modal GPU for Chris.

## Expectations (Claude, before any build)

PASS about 55%, PASS LIMITED about 15%, FAIL about 30%. The most likely failure is time, not memory: 14.6 s per step at about 141 tokens may grow past the 115 s per step that 8 h allows at 1,024 tokens. Fable's estimates go in the pre-run entry after its readiness review.

## Cost

$0. About 1 to 1.5 Kaggle T4 GPU-hours of the weekly ~30.

## Limits

- Feasibility only. A pass does not show that FT1's arms will learn or transfer.
- 25 steps on short neutral records show whether fp16 updates land early; they do not show it for long records. FT1 keeps the 25-of-250 rule per arm.
- Probe records are synthetic; allocator fragmentation over 250 mixed-length steps is not captured.
- Transformers 5.20.2 and PEFT 0.21.2 internals are unverified offline; the build must fail closed where its assumptions do not hold.
