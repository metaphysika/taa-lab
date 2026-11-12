# FT0b implementation notes (2026-11-11)

Offline build against `docs/process/FT0B_PRERUN_DRAFT_2026-11-11.md` and `FABLE_FT1_OPTIONS_REVIEW_2026-11-11.md` on `origin/b1b2-ft0b-design`. No notebook pre-run entry or execution approval is supplied here.

The build inspected the Python sources inside the Transformers 5.20.2 and PEFT 0.21.2 wheels, without importing either package or loading weights. FT0b pins the inspected Trainer, causal-loss, Gemma3-model and PEFT-preparation file hashes and refuses source drift.

Trainer counts `labels[..., 1:] != -100` over all eight micro-batches and supplies that total as `num_items_in_batch`. The causal loss sums cross-entropy and divides by that total; Trainer does not divide by accumulation again when `model_accepts_loss_kwargs` is true. FT0b checks that property, the causal-loss shift property, and an actual eight-record denominator before training. Its override returns the sum of checkpointed position-slice losses divided by the supplied denominator. Probe steps use eight copies of the same record, hence denominator `8 * trained_span`.

The inspected conditional-generation forward calls `model` for final hidden states and then `lm_head`. Its text-only model path creates the same causal/sliding masks without labels. Unlike Gemma3ForCausalLM, this conditional-generation class does not apply final logit softcapping. FT0b therefore rejects a non-null final cap on this class; the standalone chunked-loss primitive implements and tests softcapping. This prevents claiming equivalence where the stock class and requested softcapping disagree.

Choices where the draft left implementation details open:

- Wrap LoRA before the equivalence check, measure all eight old records first, then cast frozen vocabulary tables and measure the eight new records. Cast precedes Trainer construction. The memory event for LoRA wrap therefore precedes the cast event.
- Retain old gradients on CPU for comparison, avoiding eight resident GPU gradient copies. No optimizer exists during equivalence. Both sides use training mode, zero LoRA dropout, identical weights, and fp16 autocast.
- Probe optimizer steps reuse the Trainer's resident AcceleratedOptimizer, GradScaler and maximum gradient norm. Only the already-saved adapter is used for reload; probe updates are not saved. Restore the previous train/eval state and top-level cache setting even on a probe exception.
- Generate exactly 200 new tokens with greedy decoding (`min_new_tokens=max_new_tokens=200`) to make the throughput sample length explicit. Keep the original 16-token check separately.
- Probe records search complete rendered chat prefixes and independently encoded assistant text for exact lengths. Incompatible tokenizers fail rather than trimming or padding ids.

Unverified offline: real Gemma tokenizer exact-length construction, actual 12B table sharing and module layout, GPU autocast/checkpoint behavior, bitsandbytes memory use, Accelerate/GradScaler execution on a T4, memory/time and loss/gradient equivalence on the real model. Runtime guards and retained measurements are required; CPU math tests and source inspection do not establish these outcomes. No model/API calls, Kaggle push, GPU run or workflow dispatch occurred.

Validation: all 136 `test_k2*.py` tests passed; the explicit FT0/FT0b pair passed 80 tests; `scripts/run_fast_checks.py` passed 644 tests and all scripted scenarios (133.368 seconds). CPU torch 2.15.0+cpu exercised chunked loss and hidden-state gradients, including masking, a supplied accumulation denominator and softcapping. Tests use no GPU or model weights. The CPU torch installation emitted a missing-NumPy warning; the tests passed. `core.py` and `ft0.py` have no diff; the recipe digest remains `407a4eefb077bfc280ac5f50b4ba921bf21c1e643482ce59e6d2744ea8ab1be1`.
