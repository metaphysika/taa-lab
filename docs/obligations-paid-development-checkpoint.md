# TAA Lab follow-up: paid development checkpoint

Prepared September 27, 2026. This is the v0.19.3.1 development version. It is not the final study freeze or permission to spend.

## Free work completed

The two premise-watch defects have direct regression tests. The follow-up adds a separate authority, claim, and reservation ledger; eight unchanged, versioned logistics cases; a repaired TAA control; a TAA reservation arm; a per-act judge with the same resource rule and authority replies; and a free expiring-policy arm. An all-approve fake reviewer completed 32 core episodes and six claim-free legacy regression episodes. These prove plumbing and scoring behavior only. `python3 -m unittest discover tests` passed 172 tests, and `python3 run.py --scenario all` passed the historical scripted run.

The free core fixture found that repaired TAA control misses U in F01, F05, and F07, while the three policy arms serve U. Every arm leaves U unmet in F04 despite serving V. The scorer retains that unmet need, unnecessary-in-hindsight holds, and ordinary work separately. The claim-free fake reviewer permits the wrongful order and late-booking harm, confirming that the regression wrapper still exposes those requests. No model or human has judged this new study yet.

## Dated price basis

The pinned Luna model is `gpt-6-luna`: standard input $0.10, cached input $0.01, cache write $0.125, and output $0.50 per million tokens ([OpenAI model pricing](https://developers.openai.com/api/docs/models/gpt-6-luna), checked September 27). The pinned Haiku model is `claude-haiku-4-5-20251001`: first-party standard input $1.00, five-minute cache write $1.25, cache read $0.10, and output $5.00 per million tokens ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), checked September 27). The machine-readable prices are in `studies/provider-prices-2026-09-27.json`. The application estimates charges from each provider's returned token usage. The provider's account billing remains authoritative.

## Measured free calls and projected dollars

The fake reviewer produced 17 logical calls and approximately 44,394 input tokens in the four-episode Luna smoke matrix. At 800 output tokens per call, the standard-price estimate is $0.011; at 1,500 it is $0.017. The nine-episode pilot would use 27 fixture calls and approximately 81,729 input tokens: about $0.019 or $0.028 under the same output assumptions. Actual model referrals, clarification, extra reviews, output length, request retries, and cache behavior may change both amounts.

For planning only, the full core matrix is 405 fixture calls per provider over five repeats, and the three-case regression subset is another 150. At 800 output tokens per call, the combined core and regression estimate is about $0.37 for Luna and $3.70 for Haiku. At 1,500 output tokens, it is about $0.56 and $5.64. These estimates exclude development, the 12-call counsel diagnostic, and retry uncertainty. The roadmap's roughly $7 target therefore needs the actual Luna pilot before the full matrix is frozen. If the projection no longer fits, apply the roadmap's stated scope-reduction order before the freeze.

## Proposed development batch and stop limits

The proposed authorization is up to **$1.00 in estimated API charges for Luna smoke and pilot combined**. The smoke command stops at 40 logical reviews, 60 provider attempts, or $0.25 of stage spending. If its traces pass inspection, the pilot stops at 90 logical reviews, 120 provider attempts, or $0.75 of additional stage spending. Both commands share a $7 global application ledger; the development authorization is the tighter limit for these two commands. A missing usage record, changed returned model ID, or absent dated price stops expansion. Ambiguous transport attempts retain a cost reserve. These are application-side limits, not a guaranteed provider billing cap.

From Terminal in the repository:

```bash
cd /Users/cmbp/Documents/GitHub/taa-lab
python3 scripts/run_study.py --manifest studies/obligations-luna-smoke.json --provider openai --dry-run
python3 scripts/run_study.py --manifest studies/obligations-luna-smoke.json --provider openai
```

After the smoke traces have been reviewed and the same authorized development batch still has room:

```bash
python3 scripts/run_study.py --manifest studies/obligations-luna-pilot.json --provider openai --dry-run
python3 scripts/run_study.py --manifest studies/obligations-luna-pilot.json --provider openai
```

Use `--resume` only for missing episodes of an identical manifest after inspecting an interruption. A completed episode is never sampled again as a new repeat. An incomplete episode stays visible and requires a separately documented transport repair. All original call journals and episode JSONs are retained. The model availability check is made at execution; no substitute model is selected automatically.

After pilot, record actual calls, tokens, estimated charges, all failures, and any substantive revisions in `LAB_NOTEBOOK.md`. At most two substantive policy revisions are permitted after the first paid smoke, followed by a written checkpoint if the design still fails. Only then freeze the Luna and Haiku evaluation matrix, regressions, counsel diagnostics, hashes, code version, and budget.
