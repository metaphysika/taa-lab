# v02419 CPU rehearsal — STOP_FOR_REVIEW

Recorded October 18, 2026 (America/Chicago); submitted October 19, 2026 UTC.
This is an evidence intake only. No fix preparation, diagnosis beyond verifying
the supplied stop, live Modal call, model execution, or launch is authorized.
Await further instructions from Claude and owner review.

Preserve the four original uploads byte for byte: 20-file ZIP, app log and both
local receipts. All 20 files are extracted without alteration. This includes
the tiny randomly initialized checkpoint and tokenizer; these are archival
artifacts, not a trained scientific adapter or downloaded pretrained weights.
No tensor file is executed or loaded during this intake. Hashes are indexed.

Commit: `59082c45e365aeb056e67496e4e0c6c565786933`.
App: `ap-6Q32CjQGQ1jQfvgCDShxwr`.
Call: `fc-01M58QPB9CM78JZ4TD78GK16N9`.
Receipt submission acknowledged at 2026-10-19T00:06:29.502094+00:00;
result_waited_for false. Receipts, returned source commit and frozen asset
manifest hash agree. Owner reports submitted once; no rerun.

Controller/worker STOP_FOR_REVIEW, no_restart true, next_stage_approved false.
Saved child failure: RuntimeError `each of seven LoRA targets must match every
text layer`, at lora_coverage() before get_peft_model() and optimizer training.
Owner attributes this to attention_k_eq_v true and absent v_proj in some layers.
The saved tiny configuration confirms attention_k_eq_v true. No further
architectural diagnosis or workaround is prepared here.

The strict JSON fix held: training-load.json was successfully persisted with
all four loading-info collections represented as empty JSON lists. It reports
5.113761785999998 seconds for its local tiny-model loading path, not a measured
full-model GPU load. All three 2,000-example data summaries match both the
rehearsal rebuild and the prior v02418 CPU proof (identical dataset digests).
Nine decoded first-example artifacts remain preserved. Data building succeeded,
but the overall rehearsal did NOT PASS and no CPU PASS receipt exists in this
return. No two-step training, callbacks, adapter save/reload or vLLM handoff was
completed. Treat as an incomplete CPU engineering rehearsal due to LoRA coverage,
not an acquisition failure, base-format result or scientific null.

Returned reports record no GPU allocated, no pretrained weights downloaded,
no model generation, and zero optimizer/training steps. The random tiny base
was constructed/saved/loaded locally by the approved CPU attempt. GPU smoke and
scientific pair/virtue remain blocked; no new execution approval is inferred.

The local receipt/reservation attests $4.72 used/$25.28 credit left BEFORE this
CPU attempt, superseding the older $4.64/$25.36 pre-launch accounting boundary.
The $0.08 difference is a prior-charge reconciliation, not an assigned CPU cost.
CPU reservation $0.22852777777777777 is not actual billed spend. Returned invoice
fields are null; no post-CPU dashboard total was supplied. Preserve all existing
ledger entries, reservations, evidence, app records and once markers unchanged.
No reset, deletion, refund, reservation release or new spending performed here.
