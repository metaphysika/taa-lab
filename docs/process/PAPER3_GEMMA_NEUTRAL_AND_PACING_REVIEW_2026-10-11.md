# Gemma neutral check and prospective quota plan — 2026-10-11 America/Phoenix

The one approved neutral request reached `gemma-4-31b-it` (HTTP 200 and exact native
model identity), but did not produce the required final JSON. Its 64-token output
ceiling ended with `MAX_TOKENS`, after reasoning only. Native usage reports 56
prompt tokens, 61 thought tokens and 117 total tokens; `candidatesTokenCount` is
absent. Zero final-answer tokens can be inferred arithmetically, but were not
reported as a native field. The unchanged recorder rejected this omission and
stopped with `BudgetStopped`. This was not a rate limit or authentication failure.
The response accepted system instructions and multi-turn contents, but the neutral
marker check did not pass. No second request, retry, or Study A episode was issued.
Original journal and summary remain unchanged; supplemental review distinguishes
native usage from the inferred zero count.

Gemma accounted charge is $0. Google cumulative accounted spending remains
$0.631178075, including Gemini Study A $0.615495025 and earlier $0.01568305.
The $8 cumulative automatic stop leaves $7.368821925; the owner's $10 ceiling leaves
$9.368821925. These are accounting estimates, not a check of billing credit balance.
Published Gemma input/output pricing is free:
https://ai.google.dev/gemini-api/docs/pricing . No new provider/account is proposed.

## Owner quotas and prospective rules

Owner reports AI Studio values of 30 RPM, 16,000 TPM and 14,400 RPD for both Gemma
models. Proposed safety budgets are 24 HTTP RPM, 14,400 reserved input TPM, and
12,960 HTTP RPD. Count token-preflight HTTP conservatively in request budgets.
Google documents TPM as input tokens; nonetheless every generation must also pass
an input + normal 2,048 completion allowance + 128 framing buffer <=16,000 check.
Use actual full-body model-specific countTokens or a verified exact local tokenizer,
cache counts bound to request hashes, and reserve input + buffer in a sliding
60-second window. No byte-to-token assumption, trimming or changed histories.
Google limits: https://ai.google.dev/gemini-api/docs/rate-limits .

Preserve each issued 429 as a failed episode. Wait for its actual Retry-After/reset
or Google RetryInfo before continuing untouched primaries; missing reliable reset
information stops for review. Never use an arbitrary 24-hour pause. Stop and report
on the fourth rate-limit error in a run or two consecutive rate-limit errors;
counters persist across resumes and include replacement failures. At the end,
run at most one fresh, separately labeled full replacement for each primary episode
lost to HTTP 429, in the same scenario/repeat slot. A failed replacement is never
replaced again. Other errors/refusals/malformed replies receive original outcome
labels and no replacement. Originals are never erased or overwritten. These rules
were recorded before any Gemma study episode. Original-episode analysis retains
failures; replacement-filled analysis is separately labeled sensitivity. P6
amendment/verdict review remains pending, and historical frozen P6 is unchanged.
Policy: studies/formation-gemma-rate-replacement-policy-2026-10-11.json.

## Updated A–D planning estimate

These are illustrative workloads, not freezes or promises. Measured Gemini A has
928 requests and 2,143,735 prompt tokens (maximum prompt 4,856); other completed
models suggest average uncached prompts around 2,310–3,734 tokens. Gemma's exact
counts and behavior are unmeasured. Below uses those averages at 14,400 input TPM;
request framing reserves add roughly 3–6% to these throughput floors.

| Study | Illustrative generation requests | Input-throughput floor |
| --- | ---: | ---: |
| A: frozen 240 cells | 928–987 | 2.5–4.3 hours |
| B: illustrative 8 caution cases × 10 repeats | about 309 | 0.8–1.3 hours |
| C: 3 rules × 6 history lengths × 3 conditions × 3 probes × 10 | 1,620 | 4.3–7.0 hours |
| D: 3 seed conditions × 3–9 probes × 10 | 90–270 | 0.2–1.2 hours |

Total approximately 8–14 hours of input-throughput time, plus token-preflight and
model latency, pauses and any design changes. Token pacing replaces the earlier
one-call-per-61-second forecast. It does not certify actual completion in a day.
The illustrative full call ceiling is 5,730; up to three rate-lost replacements
per study add at most 78 calls before the safety stop, for 5,808 generations.
If every generation needs countTokens, up to 11,616 HTTP requests fit the proposed
daily request budget. At the maximum allowed prompt size, token spacing alone
could approach four days, plus latency. This envelope depends on the illustrative
B/C/D designs and is not a guaranteed bound on future studies. B truthfulness or
other additions require a new estimate. Studies C/D are modeled as one final
probe request per seeded-history trial, not API calls for every seed turn.

Study C histories are not yet built. Every seeded rule/history/condition/probe
combination, including k=16, must be counted before its freeze. Report oversized
requests before freeze; do not claim all C requests fit today. A runtime preflight
must also validate every evolving Study A/B request. Gemma projected cost across
A–D is $0 at current published prices; future Gemini B–D spending still needs
estimation to check the shared $10 credit condition.

## Next gate

The first neutral success condition failed, so Gemma has not been admitted and
conditional Study A authorization has not been exercised. A separate proposal
uses the normal frozen Study A 2,048-token completion ceiling, otherwise preserving
neutral contents and provider defaults. It changes no frozen study files. One
additional neutral request requires separate approval because the original approval
allowed exactly one request and prohibited retries. Preserve the first check;
no automatic retry of either check. Proposal:
studies/formation-gemma31-neutral-check-proposal-v2-2026-10-11.json.

Approval requested: “Approve one additional neutral gemma-4-31b-it check at $0 with
the normal 2,048-token ceiling; retain the first check and make no automatic retries.”
If it passes, the user's conditional approval to add Gemma and run frozen Study A
persists, subject to preparing and testing the quota/replacement adapter first.
No other model/stage advances. No Groq calls.
