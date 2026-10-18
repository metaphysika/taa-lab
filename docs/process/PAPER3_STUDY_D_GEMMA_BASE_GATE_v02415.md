# Study D v0.24.15 — acknowledged detached submission, review only

No relaunch, training or GPU execution is approved by this preparation. The owner
reports that v02414 at `792af7a`, app `ap-WrodYkbRNemYTIwokXBJoL`, finished with
$0.00, zero containers, no controller/worker activity and an empty evidence Volume.
The Mac local attempt receipt exists. Record **attempted launch, no execution,
$0 incremental spend**, with provenance in
`studies/formation-study-d-gemma-submission-attempt-v02414/`.

The screenshot, original Terminal log and receipt were not accessible in the
message received by this agent; the Dict-check response is still a placeholder.
The no-execution disposition is owner-reported, not an independently audited
server trace. StreamTerminatedError alone cannot prove the server never accepted
an invocation. Keep the original receipt, app record, empty Volume and any Dict;
no deletion, reset, re-use, refund or live Modal inspection is performed here.
Last supplied actual total remains $2.17 if the reported $0 increment is complete.

## Minimal change: acknowledge submission before closing the laptop

The v02414 local entrypoint calls `controller.remote()`, waiting for a result.
Its `--detach` app option does not make this local Python statement return before
result delivery. v02415 instead calls **`controller.spawn(payload)` once**. In
pinned Modal SDK 1.6.2, spawn awaits `_Invocation.create` / FunctionMap and accepted
pipelined input, or FunctionPutInputs if needed, then returns a hydrated
FunctionCall carrying the server call ID. It does not wait for the function result.
This is stronger than merely seeing an app ID/image-build completion.

Before spawn, write an exclusive separate local submission record with
SUBMISSION_IN_PROGRESS. After spawn returns a valid `fc-...` call ID, save and
fsync the acknowledged record (including `ap-...`, commit and call ID), then print
and flush exactly:

```text
SUBMITTED — safe to close laptop | app_id=ap-... | call_id=fc-...
```

The entrypoint immediately returns without `.get()` or `.remote()` on the client.
`modal run --detach` keeps the accepted controller running remotely; the remote
controller may wait for its worker as before. Submission confirmation is not a
completed/passing scientific gate.

A lost acknowledgement, missing/invalid call ID or local receipt write error
never prints the safe line. Save the full exception and retain both markers;
stop for review without resubmission. Acceptance may have occurred even if the
client cannot confirm it. A disk/OS failure may prevent error-file persistence;
the earlier original attempt marker must still be retained. No automatic retry,
result polling, second spawn, marker deletion or reconstruction is added.

Mac launch is prefixed with **`caffeinate -dis`**. Keep the lid open, power/network
available until the exact line with real app/call IDs appears. Image built, app
created or a dashboard URL is insufficient. After the line, the submitted work
runs on Modal independently of the laptop. All commands and failure instructions
are in `studies/formation-study-d-gemma-base-v02415/MAC_COMMANDS.md`.

## Science and engine unchanged

Same `google/gemma-4-31B-it`, pinned revision
`842da3794eaa0b77d5f08bae87a17459d91ff475`, vLLM0.31.0, bf16 A10080GB, LoRA-enabled
serving without an active adapter, **utilization 0.95 and max_model_len 16,384**.
The entire runtime is byte-identical to v02414 after namespace substitution.
Predictive/native KV preflights, current profile admission, full parent/EngineCore
error messages/tracebacks and redaction are retained. No extra format instruction,
context reduction, request resend, precision change or alternative engine.

The plan, bundle, 17 frozen cases × two repeats, fixture keys, seeds, original
parser/scorer, thresholds and **85% W headroom rule** are unchanged byte-for-byte.
Substantive rates remain descriptive. Original hosted-API → weights/vLLM and
post-results model-selection disclosures remain. No format verdict follows from
a no-execution attempt. The full three-arm training remains unapproved and absent
from this revision; frozen 2,000-example files are for tokenizer projection only.
Optional persistent weights caching stays deferred and retains the v02414 price
analysis; no cache, model download or warm-up is created during preparation.

## Fresh window, once-only claims and cumulative cap

Window: **October 18, 2026 01:00 CDT inclusive to October 24 01:00 CDT exclusive**
(**2026-10-18 06:00 UTC to 2026-10-24 06:00 UTC**), shorter than the Dict TTL.
Fresh app `taa-study-d-gemma-base-v02415`, evidence Volume
`taa-study-d-gemma-base-v02415-evidence`, Dict
`taa-study-d-gemma-base-v02415-budget-once`, stage/worker keys
`gemma-base-v02415/stage-once` / `gemma-base-v02415/worker-once`.
New local original marker is `gemma-base-v02415-local-attempt.json`; new sibling
submission record is `gemma-base-v02415-local-attempt.submission.json`.
Old v0249/v02413/v02414 resources are never looked up or altered by this code.
Exact-commit source/approval/billing/window checks precede build; original local
claim precedes image build, and remote durable reservation precedes sole GPU spawn.

| Quantity | USD |
| --- | ---: |
| Last supplied actual Study D total | 2.170000 |
| New incremental v02414 usage reported | 0.000000 |
| All earlier accounting reservation retained | 9.303556 |
| New v02415 gate reservation, unchanged | 3.801778 |
| Actual total plus new reserve (if dashboard total remains $2.17) | 5.971778 |
| Conservative cumulative accounting used by code | **13.105333** |
| Unchanged Study D cap | **25.000000** |

No automatic refund is assumed from the reported empty run. Code uses the greater
of the supplied current actual total and $9.303556 before adding $3.801778. Unknown,
nonfinite, stale-below-$2.17 or over-cap inputs refuse launch. Same $3.20/hour
whole-worker ceiling (public estimate $3.104208), 3,300 execution + 300 startup +
two idle seconds and $0.60 build/controller/storage allowance: gate reserve stays
under $4. This bounds reserved work, not an exact live invoice meter. No-card/$30
monthly credit remains a separate provider backstop; no new month resets the $25
cumulative cap. Actual failures/build costs must be reconciled after any later run.
Training/cap changes still need a separate decision after a completed base audit.

## Offline validation scope

Tests cover the acknowledgement-before-safe-line order, saved app/call IDs,
no client result wait, connection ambiguity/no resubmit, invalid IDs, local-write
failure, durable once-only guards and actual SDK serialization without hydration.
Runtime/scientific/engine equality to v02414 is checked. Full unit and scripted
checks precede commit; both exact-commit GitHub checks must pass before review
handoff. No live Modal backend, GPU, model/tokenizer download or spending is used.

Source: installed pinned Modal1.6.2 `_Function.spawn`, `_Invocation.create`,
`App.app_id` and detached runner lifecycle; [spawn documentation](https://modal.com/docs/reference/modal.Function#spawn).
