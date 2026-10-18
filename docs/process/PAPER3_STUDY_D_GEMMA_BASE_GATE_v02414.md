# Study D v0.24.14 — KV-cache configuration remedy, offline review only

No relaunch or training is approved. The v02413 attempt at `ac59bcd`, app
`ap-uobB8mtcmhyi6iDkbaWfEG`, is preserved in
`studies/formation-study-d-gemma-base-audit-v02413/`. All six raw files, the original
zip and app log are retained with hashes. The old ledger, Volume, local marker,
reservation, source files and gate outputs are never reset or overwritten.

## Diagnosis and cost reconciliation

Weights loaded successfully: 58.02 GiB model memory, 448.601130 seconds including
a 432.464415-second download. vLLM then raised a ValueError in
`_check_enough_kv_cache_memory`: **13.76 GiB required > 11.88 GiB available** for
one **16,384-token** request at utilization 0.90. The parent RuntimeError obscured
this because the old recorder stored only its type. This was a KV-cache engine
configuration stop, **not a model format failure**. No episode started; the gate
is INCOMPLETE, all 34 are not run and W headroom is unresolved. There is no TPS
or training-speed measurement. The old `load_seconds=0` is an unset initializer;
complete engine readiness was never reached. Sampled device peak was **63.134583
GiB**, 9,348 samples; telemetry succeeded. Full audit has the measurement details.

Owner's dashboard total is **$2.17 credits**, a **$0.47 displayed increase** over
$1.70. All credit consumption counts; rounded totals cannot supply an exact
per-component invoice. No bill or ledger is edited. This revision also retains
the old full reservation conservatively in its cap accounting rather than
silently reclaiming unused authorization.

## Minimal serving change and preflight

Only serving memory utilization changes: **0.90 → 0.95**. Keep
`max_model_len=16384`, A100 80 GB, bf16, vLLM0.31.0, model revision
`842da3794eaa0b77d5f08bae87a17459d91ff475`, LoRA enabled/rank8 with **no active
adapter**, original defaults/chat template, 4,096 output tokens, full histories,
12 steps, 128,000-byte message guard and frozen parser/scorer. No context reduction,
quantization, precision/hardware substitution, format coaching or retry.

The frozen v0248 plan/bundle, 17 cases × two repeats, fixture keys, seeds and
thresholds are byte-identical to v02413. The 85% W headroom rule and descriptive
substance rates remain unchanged. Hosted API → open weights, LoRA-enabled vLLM,
and post-results Gemma selection remain explicit disclosures. This is an additional
prospective implementation change after a zero-episode initialization failure.

Before engine creation, write `kv-preflight-prediction.json`. Using the same
pinned stack's observed profile, the simple 0.95 prediction is
11.88 + 0.05 × 79.27246 = **15.84362 GiB** available, about **2.08362 GiB** above
the logged need. Code uses conservative rounding edges, subtracts any increase
in current baseline GPU usage and a further **0.25 GiB margin**. It predicts a
13.765 GiB upper need without changing context. If short, stop before engine
loading/generation with a saved exception. This is a prediction, not proof:
profiling overhead can differ even on identical settings.

The **unmodified vLLM constructor** still runs its exact current KV-spec memory
check before allocating a usable engine. Its native profiler/EngineCore messages
are saved to `gemma-base/vllm-engine.log` through the pinned logging-config interface,
including child-process exception messages and tracebacks. After successful
construction, require a current native available-memory log observation and check
its lower rounding bound against the conservative requirement again. Save
`kv-preflight-current.json` before any generation. Missing/short profile evidence
stops cleanly. There is no automatic fallback to the suggested 14,128 context.

## Error evidence

Every caught worker/controller Python exception writes its full message, chained
traceback, exception type and phase to the evidence Volume, followed by commit.
EngineCore uses a durable INFO/FileHandler configured in both parent and spawned
processes; this captures the child ValueError even when the parent only receives
an initialization RuntimeError. Logging redacts known token values without
truncating the remaining trace. No credential values belong in evidence.
Outer worker/controller guards also record setup/admission/call failures;
secondary stop-ledger or memory-telemetry exceptions get separate records.

On an incomplete load, new reports use `load_seconds: null` and record elapsed
load-attempt time separately. A completed engine load gets a real duration. No
failure is scored as a model reply. Uncatchable process kills or an unavailable
Volume cannot guarantee a Python traceback/commit; preserve provider logs and
available evidence, stop, and never infer an exception or restart automatically.

## Window, fresh claims and budget

New window: **2026-10-18 04:00 UTC inclusive to 2026-10-24 04:00 UTC exclusive**,
less than seven days. New app `taa-study-d-gemma-base-v02414`, Dict
`taa-study-d-gemma-base-v02414-budget-once`, evidence Volume
`taa-study-d-gemma-base-v02414-evidence`, stage/worker keys
`gemma-base-v02414/stage-once` and `gemma-base-v02414/worker-once`, and a separate
Mac local marker. Exact-commit/source/approval/billing/window checks precede image
build; atomic stage plus durable Volume claim precede the sole GPU spawn.
The existing v0249 and v02413 resources are not even looked up. No training
function, adapter Volume or executable training plan is added.

| Quantity | USD |
| --- | ---: |
| Actual dashboard total, rounded | 2.170000 |
| Old v02413 cumulative reservation retained for conservative accounting | 5.501778 |
| New gate reservation, unchanged | 3.801778 |
| Actual dashboard total + proposed new reservation | 5.971778 |
| Conservative cumulative accounting reservation used by code | **9.303556** |
| Existing cap | **25.000000** |

Before a later launch the owner must supply a current reconciled dashboard total
at least $2.17 and billing attestation. Code uses the greater of that total and
the old $5.501778 accounting reserve before adding the new $3.801778. Unknown,
stale-below-baseline, nonfinite or over-cap values refuse launch. No reservation
is automatically refunded. The new stage remains under $4 at the unchanged $3.20
whole-worker ceiling, 3,300-second execution + 300 startup + two idle seconds,
and $0.60 build/controller/storage allowance. Hardware price estimate is
$3.104208/hour for A10080GB + two physical cores + 64 GiB, with hard CPU/RAM limits.
The allowance is not a live provider invoice meter. Actual charges must be
reconciled after completion, including failures and credit consumption. The
owner-verified no-card/$30 monthly-credit backstop is distinct from the code cap.

Training remains unapproved and unimplemented. The earlier measurement/projection
requirements remain: generation wall TPS, sampled device memory/load time,
2,000-example token counts only, complete unchanged three-arm probe cost scenarios
with explicitly unmeasured training TPS. Any later cap raise spanning October and
November monthly credit needs a separate owner decision; no cumulative reset,
assumed rollover, cuts in cases/repeats or training admission is authorized here.

## Optional weights cache — priced, deferred

Not included in this minimal revision: there is **no cache Volume, warm-up job or
model download during preparation**. A later private Volume cache of the pinned
checkpoint could avoid repeating much of the **432-second download**, but not
weight loading/engine profiling or KV checks. Do not label all 448.6 seconds as
avoidable network time. No cache success is assumed in this revision's budget.

[Modal pricing](https://modal.com/pricing) lists **$0.09/GiB/month**, with the first
**1 TiB/month included**. The observed 58.25 GiB checkpoint would be **$5.2425/month
gross**, or a conservative 64 GiB allowance **$5.76/month**; incremental charge may
be $0 while total storage remains within the included allowance. Quota use and
precise prorating require billing confirmation; long-lived cache charges also
count toward Study D's cumulative cap. Cache creation, retention/deletion policy
and any budget change would need separate review. Existing evidence stays intact.

Sources: original owner app log; pinned
[vLLM KV checker](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/v1/core/kv_cache_utils.py),
[pinned logging configuration](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/logger.py),
and the v02413 reviewed specification. Mac templates are in
`studies/formation-study-d-gemma-base-v02414/MAC_COMMANDS.md`. Push/checks are for
review only. No execution approval is implied.
