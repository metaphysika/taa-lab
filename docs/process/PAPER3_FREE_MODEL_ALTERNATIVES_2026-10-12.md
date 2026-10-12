# Free-model alternatives: offline/public-documentation review

The user clarified that the objective is a suitable free-model Study A comparison,
not Qwen 3.8 specifically. This was Qwen's first actual frozen evaluation; earlier
Qwen usage was a small neutral connectivity check. Its four attempted cells and
issued HTTP 429 remain preserved. There is no scientific requirement that the
open/free comparison use that particular model, but the existing frozen model
list cannot silently be changed after observing results. Any substitution needs
an explicit prospective amendment, distinct identity/output and fresh 240 cells.
Original frozen scenarios, prompts, history and scoring remain unchanged; the
original Qwen matrix and its incomplete P6 verdict remain available separately.

## Current hold

At the user's request to find an alternative, an exclusively created maintenance
hold prevents the approved Qwen continuation controller from launching. It stays
alive at waiting_pre_request_quota; its original saved pause/quota were not reset.
Supervision automation was paused. No continuation requests have been issued;
original 20 attempts/19 native responses, all source evidence, $0 spending and
all ledgers remain unchanged. This review's hold has an ownership marker and must
not be removed by an unrelated supervisor. It remains pending the user's decision
rather than silently starting Qwen after its original 18:41:48 UTC deadline.

## Public-source findings, checked 2026-10-12

| Option | Finding | Assessment |
| --- | --- | --- |
| Another Groq Free GPT-OSS model | Public table shows the same 8,000 TPM / 200,000 TPD limits as Qwen. | Changing only the Groq model does not solve the principal throughput constraint. |
| OpenRouter free models | Official pricing shows 50 requests/day without a funded account. | Roughly 1,000 native requests would take about 20 daily allowances; not a useful immediate substitute. |
| NVIDIA hosted Gemma 4 31B | Official catalog currently marks Free Endpoint Available, with text chat, system-message example and large context. | Recommended candidate for screening, not yet execution-ready. |
| NVIDIA hosted older Nemotron Nano/Qwen endpoints | Current catalog marks checked older text Nano and Qwen3.5-122B endpoints Deprecated despite older search snippets. | Reject stale free-endpoint recommendations. |
| Gemini free tier | Official limits depend on the actual project/tier, shown in AI Studio. Gemini 3.1 Flash-Lite already completed our frozen run. | Existing paid project's readiness does not prove a $0 tier. Repeating the same model would not add a distinct model comparison. |
| Local substantial open model | Original Cloud cgroup: 8 GiB memory, two CPU equivalents, no NVIDIA device; Ollama absent. | Not a practical place to host a 27–31B model. A much smaller local model would require explicit study redesign; no downloads/inference attempted. |

Groq's public docs confirm organization-wide quotas and possible separate input/
output limits. Saved rejection headers showed remaining quota, but did not
establish the cause of HTTP 429 or a real 24-hour reset. Original proxy forecasts
based on completed models imply about 11–20 daily 200,000-token allowances for a
240-cell study. These are workload proxies, not measured future Qwen token usage.

A paid Groq option was considered before the user clarified free preference.
At published Qwen prices ($0.80/M input, $4/M output), prior 240-cell-equivalent
usage gives approximate $1.924363 (Gemini proxy), $3.100192 (Haiku 4.5 scaled),
$4.205471 (Haiku 5.5 proxy). These are not guarantees or spending approval.
No upgrade, paid plan or price-file change was made; the user prefers a free option.

## Proposed next step: screen Gemma 4 31B via NVIDIA

Model identity candidate: google/gemma-4-31b-it. Endpoint candidate:
https://integrate.api.nvidia.com/v1/chat/completions. Published API supports
max_tokens 1–32768, including our unchanged 2048 ceiling. Published model/card
context is ample for the frozen request-size bound. The API docs and catalog have
some role/default inconsistencies: validate exact system role and response behavior
rather than rewriting the frozen system message into a user message. Reasoning
and multi-turn representation must be reviewed without silently stripping native
content or changing the scorer's expectations.

Before recommending execution:

1. Confirm free NVIDIA Developer access and account-specific request/token/trial
   limits can support about 1,000 expected requests (hard ceiling 2,880). Public
   'free endpoint available' is not evidence of unlimited quota or fast completion.
2. Configure a NVIDIA key securely in the original Cloud environment and allow
   the endpoint through the supported environment configuration workflow. Current
   Cloud readiness includes Groq/Google/Claude/OpenAI, not NVIDIA. No key values
   should be pasted into chat, read, printed, copied or committed. Do not recreate
   the original environment or migrate Qwen output.
3. Draft and review a prospective model-list/analysis amendment and a distinct
   240-cell Gemma plan. Preserve the original five-model freeze and Qwen evidence;
   distinguish the new amended analysis from the original incomplete evaluation.
   Record the substitution rationale as provider capacity, not observed outcomes.
4. Prepare a separate provider adapter and offline native fixtures with exact
   model identity, complete usage, raw evidence, unchanged scenarios/scoring,
   bounded pacing, $0 confirmation, no issued retries and no concurrent ledger run.
5. Obtain separate approval for a small neutral connectivity/identity check before
   any model request, then separate evaluation approval after readiness is verified.

No provider API requests, probes, model calls, account upgrades, credential reads,
scientific changes or new model implementation were made during this research.
The candidate is a concrete lead, not a confirmed replacement or completion promise.

## Primary sources

- Groq rate limits: https://console.groq.com/docs/rate-limits
- Groq model prices/Developer limits: https://console.groq.com/docs/models
- Groq upgrade/account requirements: https://console.groq.com/docs/billing-faqs
- NVIDIA Gemma live catalog: https://build.nvidia.com/google/gemma-4-31b-it
- NVIDIA Gemma API: https://docs.api.nvidia.com/nim/reference/google-gemma-4-31b-it-infer
- NVIDIA free Developer prototyping access: https://docs.api.nvidia.com/nim/docs/run-anywhere
- OpenRouter pricing: https://openrouter.ai/pricing
- Gemini actual project limits: https://ai.google.dev/gemini-api/docs/rate-limits
