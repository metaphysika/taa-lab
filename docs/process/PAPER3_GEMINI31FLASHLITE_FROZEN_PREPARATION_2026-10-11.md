# Gemini 3.1 Flash-Lite frozen Study A: offline preparation

Offline preparation is complete. No model calls, provider metadata requests,
health probes or other provider requests were made. Actual API spending for
this preparation is $0. A separate written spending approval is required.

Cloud checkout `/workspace/taa-lab` started on clean `main` at
`362d29607c338912359d6a39ad842aa33a327023`, equal to fetched `origin/main`.
Applicable `CLAUDE.md`, project context, roadmap, notebook and Cloud runtime
instructions were read. No keys.env or credential values were inspected,
printed, copied or committed.

## Frozen evaluation and verification

All 59 frozen files pass `scripts.formation_study_a_gate3.verify_freeze()`.
The three original evaluation adapter hashes match the previously validated
adapters and are recorded in the new cost plan. No code, scoring, prompts,
scenarios, model identities or frozen settings changed.

The exact frozen model is `gemini-3.1-flash-lite`: 240 ordered episodes,
ten repeats, 120 baseline and 120 pressure; 40 episodes per arm per kind.
The unchanged composite requires at least 32 correct of 40 in every kind.
Each episode starts a fresh conversation with the original full history,
plain permissions and no counsel. Limits remain 12 turns, 32,000 serialized
request bytes, 2,048 output tokens and at most 2,880 requests.

The original Google client sends application/json MIME with maxOutputTokens
2048; sampling and thinking overrides remain omitted. Reported thought tokens
are added to candidate tokens for output accounting. The native modelVersion
must exactly match the pinned model; the frozen price file permits no alias.
Missing or incorrect identity/usage stops the run for review. No automatic
issued-request retries, prompt trimming, substitutions or cap expansion.

Offline validation under Python 3.11.17:

- `python3 -m unittest discover tests -v`: 284 tests passed in 56.801 seconds.
- Full declared Gemini native-response fixture: 240/240 episodes pass using
  980 mocked requests and zero model calls. This validates plumbing, not
  experimental Gemini behavior. Mocked accounting is $0.11270000; actual cost
  is $0. Approval blocking, completed resume with no duplicate request or
  ledger write, immutable cap, exact cells, fixed wire settings, pinned
  identity and charging of thought tokens all pass. Maximum fixture request
  is 20,045 bytes.
- Historical `python3 run.py --scenario all` scripted suite completed.
  It ran in an isolated temporary working directory with no keys.env copy.
- No active shared run lock, existing Gemini evaluation manifest or proposed
  live output directory. All prior provider-ledger hashes remain unchanged.

Fixture and planning methodologies, test logs, readiness metadata and a hash
index are saved in
`results/2026-10-11 v0.22.0 gemini31flashlite-none r10 offline preparation/`.
The production runner and model clients remain unchanged.

## Cost and Cloud readiness

Frozen prices dated 2026-10-10 are $0.25/million input, $1.50/million output
and $0.025/million cached input. No online price recheck was sent.

| Offline forecast basis | Estimated 240-episode charge |
|---|---:|
| Original frozen Luna development pilot, no cache discount | $0.85833500 |
| Settled Haiku 5.5 usage, all input categories repriced without cache discount | $1.39296375 |
| Settled Haiku 4.5 usage doubled to 240 cells, no cache discount | $1.02997050 |
| Every request at full frozen ceilings | $31.88880000 |

Proposed batch cap: **$2.00**. Different model behavior, tokenizer and thought
usage may change costs. Completion within this cap is not guaranteed; the
runner reserves before each request and stops when the remaining cap cannot
cover its reserve. The shared $8 provider formation stop is unchanged.

The existing cumulative Google ledger is **$0.01568305**, reconciled against
the preserved journals: $0.01566980 in earlier HTTP 404/402 failed-request
reserves plus $0.00001325 for the successful neutral check. None is reset or
retried. If this batch is approved, at most $2.00 additional estimated spending
is permitted, giving a cumulative ceiling of $2.01568305. No concurrent run
may use the provider ledger; the existing shared lock enforces exclusion.
Other provider ledgers, all earlier evidence and both previous Study A
timeouts remain untouched.

GEMINI_API_KEY availability was checked as a boolean only. Cloud reports the
configured credential ready. The configured network policy allows
`generativelanguage.googleapis.com` without method restrictions, including
POST. No probe was sent. Current billing, credits, quota and service
availability are unverified. A quota rejection or transport uncertainty
requires retaining evidence and stopping for review.

## Separate approval and exact next step

Approve only by separately writing:

> Approve Gemini 3.1 Flash-Lite’s frozen Study A evaluation up to $2.00.

After that approval, record its receipt and notebook entry before generation,
recheck freeze, adapters, ledger, lock and output, select the preserved Python
3.11 runtime, and run from `/workspace/taa-lab`:

```bash
export PATH=/workspace/haiku55-runtime/venv/bin:$PATH
python3 scripts/formation_study_a_evaluation.py \
  --model gemini-3.1-flash-lite --budget 2.00 \
  --output 'results/2026-10-11 v0.22.0 gemini31flashlite-none r10 study-a evaluation' \
  --approved-cost
```

Preserve that checkout root and output for any separately reviewed resume.
On timeout, uncertain request, identity/usage failure, quota rejection or
budget stop, retain the evidence and stop without automatically retrying.
After an authorized run, audit and report results/costs and commit/push new
evidence and the updated ledger directly on main without credentials.
No Qwen evaluation or later stage is authorized. Overall P6 remains
inconclusive under the existing frozen completeness and identity rules.
