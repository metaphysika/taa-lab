# Haiku 4.5 frozen Study A preparation — 2026-10-11

**Offline preparation is complete. No model API calls were made. The evaluation awaits separate spending approval.** Work remains on `main` in `/workspace/taa-lab`.

## Scope and unchanged research protocol

The exact pinned model is `claude-haiku-4-5-20251001` through the existing Claude Messages client. The frozen plan requires **120 episodes**, five repeats of both arms: **60 baseline and 60 pressure**, 20 W/R/U episodes per arm. Each kind needs at least 16/20 correct for its 80% threshold. No previous Haiku 4.5 Study A evaluation manifest or planned output directory exists.

All **59 frozen files** match the approved Gate 3 manifest, and the three original execution adapters match their previously verified hashes. The dated Gate 3 approval receipt still binds the same freeze. Cases, scorer, primary/secondary arms, model identity, full history, plain-permissions gate, no counsel, fresh conversations and provider defaults are unchanged. Limits remain 12 turns per episode, 32,000 serialized request bytes, 2,048 output tokens, at most 1,440 requests. Sampling, effort and thinking overrides remain omitted.

The Luna and Haiku 5.5 results and their retained timeouts remain evidence. They are not retried, replaced or reclassified. Overall P6 remains inconclusive under the frozen completeness/identity rule; future pressure scores are not substituted for baseline.

## Proposed spending approval

| Basis | Estimated dollars |
| --- | ---: |
| Original Luna pilot usage scaled at frozen Haiku 4.5 prices | $1.65253500 |
| Completed Haiku 5.5 settled usage scaled to 120 episodes and tenfold prices | $2.62841950 |
| Same empirical scaling including the earlier timeout reserve | $2.63924075 |
| Proposed new Haiku 4.5 batch cap | **$3.00** |
| All 1,440 requests at the frozen full ceilings | $72.34920000 |

The recommended cap uses the completed Haiku 5.5 batch as an additional usage reference. Frozen Haiku 4.5 input, output, cached-input and cache-write rates are each ten times Haiku 5.5's, and this batch has half as many episodes. These are forecasts, not guaranteed billing or completion: Haiku 4.5 may use different tokens or turns. The frozen price file was checked on 2026-10-10; this offline preparation made no pricing or provider health request and did not change the price file. Provider billing remains authoritative.

The **$3.00** is a separate, explicitly proposed Haiku 4.5 allowance. Haiku 5.5 remains accounted at **$0.52784815** under its original $1 cap, including its **$0.00216425** timeout reserve. Its unused allowance is not automatically transferred or spent.

The unchanged shared Claude ledger is **$0.52795115**, including the earlier **$0.000103** neutral check. The shared formation stop stays **$8.00**. If the new batch is approved, its additional ceiling is $3.00, so cumulative ledger accounting may reach at most **$3.52795115**. Never reset the ledger or run another provider-ledger job concurrently. The adapter reserves before requests and stops before an unapproved request ceiling. Completion within $3.00 is not guaranteed; there is no automatic expansion.

## Offline checks

- **284 unit tests passed**, using Python 3.11.17; tests mock provider requests.
- **120/120 declared Haiku 4.5 fixture episodes passed** across all five frozen repeats, with 490 mocked requests, zero actual model calls and $0 actual API cost.
- The fixture used `run_batch()` with the existing native-envelope stand-in, patched credential loading, a declared dummy key and an isolated copied non-secret ledger. It verified the approval barrier, pinned identity, unchanged system/history/settings, original cell order, request limits, cumulative accounting, completed resume without duplicate requests, and rejection of a changed cap on resume.
- The historical `run.py --scenario all` scripted suite passed with no model calls, from a temporary working directory with no credential file.
- The real Claude ledger hash remained unchanged. No active run lock or live Haiku 4.5 output exists.
- `ANTHROPIC_API_KEY` is available without displaying its value. Cloud reports current secret readiness and enforced network policy. The configured destination rule permits POST to `api.anthropic.com`; no probe or health-check request was sent.

Python 3.11 matches the repository's main CI minor version and preserves the archived floating-point journal summation. No frozen module or adapter was changed to address the Python 3.12 difference found during Haiku 5.5 preparation.

The cost plan is `studies/formation-study-a-haiku45-evaluation-cost-plan-v0220.json`. Offline evidence is in `results/2026-10-11 v0.22.0 haiku45-none r5 offline preparation/`. These fixture records are software verification, not model observations. The receipt records only the owner's offline-preparation approval; funding and generation are unapproved.

## Exact next approval and run

To authorize this model only, say: **“Approve Haiku 4.5’s frozen Study A evaluation up to $3.00.”**

After that separate approval, record a receipt bound to this cost plan, recheck the frozen files, adapter hashes, cumulative ledger, output absence and provider lock, then use Python 3.11 from the same repository root:

```bash
export PATH=/workspace/haiku55-runtime/venv/bin:$PATH
python3 scripts/formation_study_a_evaluation.py \
  --model claude-haiku-4-5-20251001 \
  --budget 3.00 \
  --output 'results/2026-10-11 v0.22.0 haiku45-none r5 study-a evaluation' \
  --approved-cost
```

Retain all issued evidence and stop for review after a timeout, uncertain request, identity/usage failure, or budget stop. No automatic issued-request retry, substitution, prompt trimming, spending increase, or advance to another model or stage is authorized. Preserve this checkout root and output directory for any reviewed resume. After the approved run, report results and costs, preserve evidence and the cumulative ledger, and commit and push to `main`.
