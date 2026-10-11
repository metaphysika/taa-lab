# Gate 2 report and next approval — October 10, 2026

Gate 2 is approved: your “Let's do Gate 2” go-ahead approves the 12 Study A case facts, classifications, and observable scoring rules presented in the Gate 2 review. It authorizes Stage 3 preparation. A paid pilot still requires its own cost approval under the approved Paper 3 build brief, before generation.

## Completed checks

| Check | Result |
|---|---|
| Repository unit tests | 241 passed |
| Study A declared scripted fixtures | 44 of 44 passed |
| Existing scripted scenarios (`python3 run.py --scenario all`) | Completed successfully |
| New model requests | 0 |
| API cost for these checks | $0 |

These checks verify the simulator and scorer; they are not evidence of model conduct. The previously logged historical v0.19.5 freeze-hash discrepancy remains unresolved and unchanged.

## Your next approval: first Luna pilot, up to $0.65

The pilot will check whether the cases are usable and whether Luna misses duties, produces malformed replies, or encounters very easy or difficult cases. It uses **gpt-6-luna only**, plain permissions, no counsel, and no human answers during an episode.

- 12 cases, one episode per case.
- At most 12 model turns per episode: **144 requests maximum**, with no automatic retries.
- At most 32,000 bytes in each native request JSON and 2,048 completion tokens per request, including reasoning tokens.
- Standard prices: $0.10 per million input tokens and $0.50 per million output tokens, checked October 10 against [OpenAI's Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna).
- Conservative full-batch estimate: **$0.6082848**, reserving 32,002 input tokens per request. Proposed application spending stop: **$0.65**. Actual cost depends on usage; this application stop is not a provider-enforced billing limit.

The pilot plan is saved in `studies/formation-study-a-luna-pilot-plan-2026-10-10.json`. Before paid execution, the runner and all request, attempt, and dollar guards will be built and verified with free tests. Requests exceeding a limit will stop rather than silently trim history. Provider failures, refusals, and incomplete episodes will be preserved and reported.

One episode per case is an initial diagnostic, insufficient for reliable success-rate estimates or a final P6 verdict. If development needs another batch, you will receive its reason and cost estimate first. Changes after model results require new case versions. Held-out models remain untouched. Gate 3 follows development and freeze, with results, changes, fingerprints, and the next evaluation estimate for review.

**To authorize this batch, reply: “Approve the Luna pilot up to $0.65.”** This authorizes only the batch described above, not later pilots or evaluation runs.

## Reports after runs

I will run free checks automatically and run model batches only within their approved scope. Each completed batch will produce a concise report with pass/fail results, model outcomes and cost where applicable, limitations, the next step, and exactly what you need to approve or do. No terminal commands are required from you. You continue to push local commits to GitHub.
