# Gate 3 approval and free adapter preparation — 2026-10-10

Gate 3 is approved. Your exact approval is saved in a separate receipt bound to the frozen manifest. All **59 frozen file hashes match**; the research design, stimuli, scoring, evaluation order and model settings remain unchanged.

**This preparation cost $0. No model/API calls were made.**

## Checks completed

- **276 unit tests passed**, including a simulated whole Luna batch, accounting, native response handling, exact frozen request history, checkpoint recovery and prevention of repeated requests.
- **120/120 declared fixture episodes passed** across the five provider/model transports and both study arms (490 mocked requests). These are scripted plumbing checks, not model observations or study results.
- The historical scripted scenario suite passed. Final test logs and fixture outputs are retained in the repository.

The new adapters preserve full conversation history, world effects and the once-only pressure message. Saved completed episodes are skipped on resume. A local quota pause resumes the pending turn; an uncertain issued call, provider error or identity/accounting failure stops for review. No issued request is silently replaced. Unfinished cells cannot produce a final P6 verdict.

## Groq preparation

The adapter reserves a full 8,000-token minute and permits one request per 61 seconds, tracks daily limits, honors reset headers, and settles against reported uncached input plus output. This avoids treating JSON bytes as exact tokens. Groq documents that cached tokens do not count toward its rate limits. [Groq rate limits](https://console.groq.com/docs/rate-limits)

This is verified with fixtures only. A single oversized request may still be rejected by Groq; that rejection will be retained and the batch stopped. The frozen prompts remain intact. Groq remains on the free plan, and its real evaluation requires separate approval.

## Next approval: Luna evaluation

| Item | Proposed run |
| --- | --- |
| Model | `gpt-6-luna` |
| Scope | 10 repeats of the 12 baseline and 12 pressure cases: **240 episodes** |
| Maximum requests | 2,880; up to 12 turns per episode |
| Settings | Frozen provider defaults, 32,000 serialized request bytes, 2,048 output tokens |
| Cost estimate | **$0.33**, using comparison-pilot usage at frozen prices without cache discounts |
| Approval requested | **Up to $1.00** for this batch only |
| Stop policy | Stop before a request would exceed the batch reserve or $8 cumulative OpenAI formation limit |

The estimate is not a guarantee. The theoretical envelope with every request at both ceilings is **$14.47**; the $1.00 cap may stop the evaluation early. It will never be raised automatically. A budget stop receives a report and a new approval request, with existing evidence preserved.

Approval starts only Luna's frozen evaluation. Earlier development pilots remain separate. Baseline supplies the primary P6 analysis; pressure is secondary. No overall P6 verdict is available until every planned model cell is attempted with valid identity. Other providers will receive their own cost plans and approval requests.

**To authorize the next run, say: “Approve Luna’s frozen evaluation up to $1.00.”**

After the authorized run, you will receive the results, recorded cost, completeness status and the next exact approval or action. Until that approval, no model calls are authorized.
