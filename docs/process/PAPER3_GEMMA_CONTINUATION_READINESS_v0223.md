# Gemma continuation readiness — v0.22.3 (offline preparation)

Owner approved offline preparation/testing, not execution. A prospective rule
amendment was recorded in the notebook before any further calls. Original Gemma
A_R01 r1 and P_R01 r1 remain correct; P_R02 r1 / A000009 HTTP503 remains unchanged.
Exactly 237 untouched primary cells begin A_R02 repeat1. After these, one fresh
separately labeled full P_R02 r1 replacement is planned under the explicit new
owner amendment. No original request/cell is reissued or overwritten; a new
replacement is a different recorded episode, not a hidden retry of old evidence.

## Prospective transport policy

HTTP429/500/502/503/504, timeouts and connection resets can retry only if no model
reply bytes have been received. FIVE TOTAL attempts includes the first, so waits
before attempts2–5 are 10/30/60/120 seconds (four waits, no sixth attempt); explicit
Retry-After/reset/Google RetryInfo is honored if longer. Request body/system/full
history/defaults stay identical. Every issued generation attempt has its own
native journal/accounting closure and reserve; metadata attempts have a separate
transport/receipt ledger at $0. Unknown timeout/reset usage is not fabricated;
paid-provider reserves remain and the existing $8 cumulative stop applies before
each attempt. The eleventh distinct request needing any retry stops before its
second send; all HTTP jobs including token-count jobs count conservatively. Counts,
wait deadlines and received-byte barriers persist across resumes.

First received reply is scored regardless of quality. Malformed/refusing/unfinished
model replies are never resampled or replaced. Any received partial/native bytes
block re-sending even if later read/decoding fails. Transport stop conditions are
five failed attempts on one request or >10 requests needing retry. Existing
freeze/identity/native-usage/size/credential/budget guards still apply; these are
not bypassed by the transport amendment. Process death with an inflight/unclosed
checkpoint requires review; persistent retry state does not justify replaying an
unclosed request. Normal pre-request quota pauses remain resumable.

Each transport-lost primary keeps its original error record and may receive one
fresh same-slot full episode at the end. Failed replacements get no replacement.
An exhausted-request/run-retry safety stop halts before further originals or
pending replacements; any later continuation needs review. Original primary
failures stay in planned denominators; report replacement sensitivity separately.
Old 4-rate-error/2-consecutive and missing-reset transport stops are superseded
prospectively; original version/evidence is unchanged.

Rationale: strict no-retry was stopping on provider outages without received model
output, rather than on study behavior. This avoids selecting among observed
replies. It is not proof of zero statistical bias: a timeout/reset can conceal
server generation/usage and latency can correlate with behavior. Preserve that
uncertainty and disclose the prospective amendment. The same policy is binding
for ALL models in B/C/D before their respective freezes. Those stages/adapters
are not launched or retrospectively changed in this preparation.

## Continuation safeguards

Same original Cloud /workspace/taa-lab, Python3.11, original Gemma output directory.
All existing source files/9 closed attempts/8 valid native responses are hashed
and protected, along with 59 frozen files, original/new adapters, source plans,
other provider ledgers and Groq quota. Original controller status remains stopped;
old CLI must not restart. Continuation journals/checkpoints/status/manifests use
separate names in the same output, preserving all source files byte-for-byte.
A separate hash-bound EXECUTION approval receipt is required before credentials,
transport or new execution evidence. None was created during preparation.

Source quota event history is copied forward without trimming/reset, new quota
updates stay in continuation-quota.json; old quota remains intact. Exact complete
body countTokens preflight, <=14,400 reserved input TPM/24 HTTP RPM/12,960 HTTP RPD,
combined prompt+2048+128 <=16000 and wire <=32000 bytes remain. Failed attempts
retain their token/dollar reservations, and all retries are paced too. Shared
provider run lock spans waits. Maintenance hold prevents HTTP at attempt boundaries;
only its owner may release it. No other provider-ledger run concurrently. No Groq
calls, provider/account upgrade, frozen settings change, history trimming or P6
verdict. Study C longest-history token verification remains a gate before C freeze.

Gemma continuation projected cost $0; Google cumulative remains $0.631178075.
No model requests/probes were made in this preparation. Model identities/settings,
neutral records, completed other models and all timeout reserves remain untouched.

Plan: studies/formation-study-a-gemma31-continuation-plan-v0223.json.
Policy: studies/formation-transport-retry-policy-v0223.json.
CLI (NOT run; separate execution approval required):

```
/workspace/haiku55-runtime/venv/bin/python3 scripts/formation_study_a_gemma31_continuation.py --approved-continuation
```

Offline terminal audit: scripts/formation_study_a_gemma31_continuation_audit.py.
It verifies deterministic replay, exact histories including identical retry
payloads, first-byte barriers, request closure/counts/identity/usage, ordered
suffix and replacements, original source integrity and cumulative spending.

Proposed next approval: “Approve Gemma’s 237 untouched Study A episodes and one
fresh replacement for P_R02 repeat 1 at $0, under the reviewed five-attempt
transport retry policy; retain all original evidence and score the first received
reply.”

Final verification: all 329 unit tests pass (16 new targeted tests), plus the
historical scripted suite. Full 237-cell + one-replacement declared native fixture
and terminal audit pass; original source files are byte-identical and a completed
resume sends no duplicate requests. Approval barriers send zero requests and
create no execution evidence. All 59 freezes, adapters, ledgers/Groq quota and
Qwen evidence verified. Readiness receipt and logs are saved separately under
results/2026-10-11 v0.22.3 scripted-none gemma continuation verify. No execution
approval receipt, live request, continuation output or supervision activation.
