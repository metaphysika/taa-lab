# v02418 GPU smoke returned evidence — 2026-10-18

Record only; further diagnosis belongs to Claude and any fix or execution awaits
owner review. Preserve the original three uploads and all 16 ZIP files unchanged.
The Modal app log was reportedly empty (0 bytes) and could not be uploaded;
no app-log file is present or fabricated here. The returned ZIP does contain the
separate training subprocess log, which is preserved.

Commit `a63ebb191c00a9db4119c87d5386db350bb6bb58`.
App `ap-LCNwU55kRyQBOlCCXVgXer`.
Call `fc-01M58M1Z90A22KVZ2XJ10SBSPA`.
Both local receipts match the returned commit. Submission was acknowledged;
result_waited_for is false. Owner reports one submission, no rerun and no
pair/virtue launches; no live Modal state was queried for this intake.

Returned smoke status: STOP_FOR_REVIEW, no_restart true, excluded_from_science
true, next_stage_approved false. Worker software wall time: 441.370564091 s
(7.36 minutes). Child TypeError: `Object of type set is not JSON serializable`.
Saved traceback locates the exception in runtime.py training_process(), writing
training-load.json through json.dumps(); worker wraps it as RuntimeError
`training subprocess failed; see private adapter and full training failure`.
Committed source places this write after weight loading but before LoRA creation
and training. Zero training steps and transfer episodes ran. Record incomplete
engineering smoke due to software serialization failure, not scientific null,
acquisition failure or base-format failure. Sampled device-wide peak memory:
62,706,745,344 bytes; this GPU attempt used resources.

ZIP also preserves CPU PASS evidence: 2,000 examples per arm; contrary 326,496
input / 54,488 supervised tokens, max 171; virtue 363,524 / 91,516, max 190;
neutral 298,272 / 54,848, max 150. All five CPU evidence hashes and the
smoke-bound CPU receipt hash verify; GPU-built data summaries match the CPU
receipt. CPU stage reports no GPU, weights, generation or training.

Pre-smoke billing attestation in local receipt/reservation: $4.33 cumulative used,
$25.67 credit left. This supersedes the previously recorded $4.31/$25.69 only as
the pre-smoke boundary (including CPU/build); it is not a post-smoke total.
Smoke reservation $1.9695555555555555 is not actual billed spend. Returned invoice
fields are null; post-smoke actual charge/cumulative total remain unverified.
No refund, reset, ledger deletion or reservation release is inferred or performed.

No source changes, fix preparation, model downloads, launches, training or new
spending occurred in this recording task. Prior evidence and ledgers remain
unchanged. Await Claude's diagnosis and owner review before further work.
