# Pressure-case approval and next Luna pilot plan — October 10, 2026

**Your approval is recorded:** the 12 pressure variants' facts, W/R/U classifications, additional lawful-work requirement, and once-only issuer-follow-up delivery rule are approved. Your “no model calls yet” restriction remains in force.

## Next approval: comparison pilot up to $1.50

| Scope or limit | Proposed batch |
|---|---|
| Model | gpt-6-luna only |
| Cases | 12 original baseline + 12 approved pressure variants |
| Episodes | One fresh episode per case: 24 total |
| Request maximum | 12 turns per episode; 288 requests maximum |
| Retry policy | No automatic retries or replacement episodes |
| Each request | At most 32,000 serialized JSON bytes and 2,048 completion tokens, including reasoning |
| Permissions / counsel / human answers | Plain permissions / none / none |
| Conservative full-batch estimate | **$1.446984** |
| Proposed application spending stop | **$1.50** |
| Cost and model calls made today | **$0; 0** |

The batch asks whether Luna's successful baseline conduct remains stable under the approved pressure conditions. It reruns the original cases rather than discarding their successes. The earlier 12/12 pilot remains a separate development observation. Each new episode starts with a fresh conversation; it does not inherit a counterpart's messages or prior model responses.

## Pricing and safeguards

Official Standard prices checked October 10: input $0.10, cached input $0.01, cache writes $0.125, and output $0.50 per million tokens. [OpenAI Luna pricing](https://developers.openai.com/api/docs/models/gpt-6-luna).

The preflight reserve uses **$0.125 per million for every input token**, so it allows for the cache-write premium without assuming a cache discount. The estimate is:

`288 × ((32,002 × $0.125 + 2,048 × $0.50) / 1,000,000) = $1.446984`.

Usage settlement will separately price regular input, cache reads, cache writes, and output at their published rates. The prior conservative OpenAI formation ledger is $0.00995020; the proposed batch remains below the $8 whole-formation application stop. The $1.50 cap is a new batch authorization, not a remaining balance from the earlier $0.65 approval. Application reserves and stops are not provider-enforced billing limits.

Before execution, a separately versioned comparison runner must be built and verified with free tests. It will enforce request size, token ceiling, call/attempt counts, batch/provider spending stops, exact approved case hashes, once-only follow-up delivery, and refusal to overwrite or repeat an existing run. The original pilot command remains pinned to its earlier plan. No paid execution occurs before your approval.

A transport failure, missing usage, model-identity mismatch, budget stop, or unexpected harness failure stops the batch. Evidence is retained, with remaining planned episodes explicitly marked not attempted. A parsed refusal, malformed reply, truncation, or incomplete task stays in that episode's record and denominator. It is not replaced. The batch will not trim history silently to bypass the request limit.

## Fixed order and reporting

The 12 matched original/pressure pairs use a fixed order: R01–R04, U01–U04, W01–W04. Within successive pairs, baseline-first and pressure-first alternate, giving six pairs each way. Exact ordered paths and hashes are saved in `studies/formation-study-a-comparison-pilot-plan-2026-10-10.json` before generation.

Both arms use the same original pilot system instruction and response format. Only pressure episodes add their approved task/world changes and issuer follow-up. A follow-up arrives after its first successful primary trigger, once, before the next reply while the episode is open. It changes no permission or source evidence and does not restart an ended episode.

The report will show baseline and pressure outcomes separately, W/R/U counts separately, matched outcomes, violations attempted/executed, omitted work, reply/provider errors, follow-up delivery, token usage, and cost. Original and pressure cases differ in issuer insistence, context, and extra work together, so any difference cannot be attributed to a single component. One episode per case is exploratory; neither a case-level success rate nor a cross-model P6 verdict follows from it. Full correctness on both arms remains a legitimate result.

## Verification and next steps

The latest code checks remain **254 unit tests passed, 44/44 pressure fixtures passed, and historical scripted checks completed successfully**. This turn changes approval records and planning documents only; the approved scenarios, scorer, and results remain unchanged. The new plan's 24 paths/hashes, pairing, ordered count, arithmetic, and provider-budget headroom were checked without model calls. It is a planning file, not an executable manifest or research freeze.

**Reply: “Approve the baseline-and-pressure Luna pilot up to $1.50.”** That approves only this 24-episode batch and its free runner preparation/verification. It does not approve additional repeats, new stimuli, held-out model calls, a research freeze, or evaluation.

After approval I will build and verify the guards, run the batch, then give you the outcomes, cost, and next research decision. Gate 3 remains pending development, predictions, and freeze. No commands are required from you for the tests or pilot. Push the local approval/plan commit when ready.
