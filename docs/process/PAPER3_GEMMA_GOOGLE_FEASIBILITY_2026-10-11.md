# Gemma through the existing Google key: feasibility review

Status: candidate screening only; not added to the study. October 11, 2026,
America/Phoenix. No new provider/account, neutral inference or study run approved.
One read-only models.list request was authorized by the request to check models
visible to the key. It used the existing configured Gemini client internally;
credential values and keys.env were not inspected, printed, copied or committed.

## Key-visible catalog and documented compatibility

The configured key returned these generateContent-capable catalog entries:

| ID | Catalog version | Input limit | Output limit |
| --- | --- | --- | --- |
| gemma-4-31b-it | 001 | 262,144 | 32,768 |
| gemma-4-26b-a4b-it | 001 | 262,144 | 32,768 |

Catalog access is not proof that generation is authorized for the project today.
Use gemma-4-31b-it as the owner's named candidate; no automatic fallback to the
other model. Raw metadata receipt is in
`results/2026-10-11 v0.22.1 gemma google metadata review/gemma-models-list.json`.

Google's current Gemma 4 pricing table lists input and output as free of charge;
no paid tier is offered for this model family. Plain text inference through that
listed endpoint has a $0 projected cost. No grounding, storage, caches, tools,
paid fallbacks or extra accounts are proposed. A change in availability/pricing
requires review before calls. This meets the <=$5 Gemma condition on published
price, but does not establish sufficient quota or completion time.

Google's Gemma-on-Gemini guide explicitly supports systemInstruction and complete
user/model multi-turn contents. This is documented compatibility, not empirically
confirmed behavior with this key. Native identity/version, complete usage,
finish reasons and frozen JSON configuration compatibility require a separately
approved neutral call and offline adapter validation. Preserve native replies;
never silently strip content or change the original system prompt/scorer.

## Quotas and call sizes: unresolved gate

Google's current limits page directs exact RPM, TPM and RPD to the project's AI
Studio limits screen; models.list does not expose quota configuration. API-key
readiness and catalog visibility do not give permission to access management APIs
or prove those numbers. No account quotas can therefore be confirmed here yet:

| Limit | Verified value for this project |
| --- | --- |
| Gemma requests/minute | Unknown; awaiting owner AI Studio quota numbers |
| Gemma input tokens/minute | Unknown; awaiting owner AI Studio quota numbers |
| Gemma requests/day | Unknown; awaiting owner AI Studio quota numbers |

Do not apply old Gemma 3 numbers or forum-reported Gemma 4 values as verified
project limits. Model context capacity and account throughput quota are different.
Google applies quotas per project, not per key; request-day quotas reset at midnight
Pacific time. Gemini and Gemma runs must not use the shared Google ledger concurrently.

Our existing Gemini Study A requests fit the 32,000-byte frozen application ceiling;
actual maximum and total prompt usage are recorded in the adjacent workload receipt.
Different Gemma tokenization prevents calling that measured count exact for Gemma.
The conservative byte-per-token upper bound can reach roughly 32,002 input tokens
per request (plus 2,048 allowed output), so a project TPM below that ceiling is not
an unconditional guarantee that every possible frozen history fits. Never trim
history, lower the output ceiling or replace a rejected episode to force fit.
Judge actual proposed request sizes after fixtures are built; stop/review an
individually incompatible request instead of assuming waiting solves it.

## Provisional A/B/C/D estimate

Gemma remains at ten repeats under the existing general repeat plan. Studies B/C/D
have no implemented/frozen cells yet. The following is a transparent planning
scenario, not an approved final cell count or completion promise:

| Study | Planning assumption | Projected requests | Request ceiling | Gemma price |
| --- | --- | --- | --- | --- |
| A | Frozen 24 cases x 10 repeats | About 928–987, workload proxies | 2,880 (12 replies/cell) | $0 |
| B | Illustrative 8 new caution cases x 10 repeats; Study A obedience reused | About 309, using prior mean turns | 960 if same 12-reply ceiling | $0 |
| C | Brief: 3 rules x 6 history lengths x 3 conditions x 3 probes x 10 repeats; one final call each | 1,620 | 1,620 under that design | $0 |
| D | 3 seed conditions x 3–9 probe cases x 10 repeats; one final call each | 90–270 | 270 under that design | $0 |
| Total | Excludes optional B truthfulness and design expansions | About 2,947–3,186 | 5,730 for these assumptions | $0 |

C's seeded turns are written by the harness, not generated model calls. D's
single-probe-call assumption must be reviewed; multi-turn D episodes would need
another estimate. The B eight-case assumption is for costing only, not creation
or freezing of cases. Optional truthfulness, development runs, changed repeat
counts or extra cases add calls and time. Exact totals follow each study's design.

Conditional pacing examples, not confirmed quota claims:

- At one request per 61 seconds with no daily cap below that throughput, the
  projected total takes about 49–54 continuous hours of spacing, and the ceiling
  about 97 hours, plus latency/development/scheduling. That suggests several days
  only if every individual request fits TPM and service capacity is available.
- An actual 1,000 RPD would require at least 3–4 daily allowances for the projection
  or 6 for the ceiling. An actual 20 RPD would take roughly 148–160 or 287 daily
  allowances and is unsuitable for the owner's reasonable-days requirement.

No timing conclusion can be approved until actual project quotas are supplied
and call sizes/designs are checked. Do not recreate the arbitrary 24-hour Groq
fallback. Provider-request errors remain evidence and never auto-retry.

## Google spending and credit condition

Existing Gemini Study A accounted estimate: $0.615495025.
Earlier Google accounted checks/reserves: $0.015683050.
Cumulative Google ledger: $0.631178075 (float storage differs below displayed precision).
This leaves $7.368821925 below the cumulative $8 automatic stop and $9.368821925
against the owner's $10 credit ceiling. These are application accounting headroom,
not a verified billing-console credit balance. Ledgers/reserves were not reset.
Gemma's published $0 price adds no projected inference charges to that balance.

Future Gemini B/C/D costs must still be estimated before each freeze/run. Applying
Gemini's Study A mean cost per request to the illustrative B/C/D requests gives
roughly $1.34–$1.46 additional Gemini inference, but it is not a reliable bound:
seeded-history sizes, tokenization and reasoning/behavior can differ. Conservative
byte/output envelopes for this planning scenario exceed the $8 budget, so the
existing automatic stop, realistic fixture estimates and owner review are required.
A $10 credit does not guarantee completion of unspecified future study designs.

## Neutral connectivity proposal — approval still required

One generateContent request to gemma-4-31b-it through the existing Gemini key,
using an innocuous system instruction and a seeded user/model/user neutral history
that requests a short JSON response. Proposed output ceiling: 64 tokens. No study
stimuli, retries, native tools, thinking/sampling overrides or paid fallback.
Capture the request, raw native response, modelVersion, usage and finish reason;
use the unchanged cumulative Google ledger and $8 stop. Price is documented $0.
Retain an issued failure and stop, without a second request. A small successful
neutral check verifies basic identity/usage/transport, not the quota of a large
study request or future model scores. No connectivity call has occurred yet.

Next step: obtain actual RPM/TPM/RPD, then review and approve the one neutral call.
Gemma is added only after the owner's complete price/time/budget conditions pass.
P6 amendment proposal is separate and awaits review before any Study A verdict.

## Primary sources, checked during this review

- https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
- https://ai.google.dev/gemini-api/docs/pricing (Gemma 4 section)
- https://ai.google.dev/gemini-api/docs/rate-limits
