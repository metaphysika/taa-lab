# Qwen 3.8 27B frozen Study A: offline preparation

Offline preparation is complete. No model calls, provider probes, metadata
requests or other provider requests were made; actual API cost is $0.
The 240-episode evaluation requires separate approval before it starts.

Clean main began at `80a414067919a0e0db80f4c5e82563c3c182adc3`, equal to
fetched origin/main, in the preserved `/workspace/taa-lab` checkout. Applicable
repository and Cloud runtime instructions were read. No keys.env or credential
values were inspected, printed, copied or committed.

## Frozen inputs and offline checks

All 59 files pass `scripts.formation_study_a_gate3.verify_freeze()`. The three
original evaluation adapter hashes match the previously validated adapters.
No production code, scenario, scoring, model identity or setting was changed.

Exact model: `qwen/qwen3.8-27b`, on Groq Free only. The frozen plan contains
240 ordered episodes, ten repeats, 120 baseline and 120 pressure, 40 per arm
per kind. The composite requires at least 32/40 correct in every kind. Fresh
conversations, original full history, plain permissions, no counsel, 12 turns,
32,000-byte requests and 2,048 output tokens remain unchanged. The fixed
application User-Agent is retained. Sampling, effort, thinking and JSON
response-format overrides remain omitted; native model identity must match
the exact frozen name.

Offline checks under Python 3.11.17:

- 284 unit tests passed in 55.140 seconds.
- All 240 declared native-response fixtures passed with 980 mocked requests
  and no actual model calls. Maximum fixture request was 19,931 bytes. The
  fixture exercised a pre-request minute pause, checkpoint preservation and
  resume of the same batch/output without reissuing the saved first request.
  Completed resume makes no additional requests or ledger writes. Approval
  blocking, immutable $0 cap, exact cells, wire settings and identity passed.
  A simulated clock was used only in this offline fixture; production time
  and quota state were not changed.
- Five declared issued failures (HTTP 429, timeout, wrong identity, missing
  usage and reported usage over 8,000 tokens) stop without retry. Native
  evidence is retained when received, and re-entering a completed fatal
  checkpoint sends no request. Separate minute, daily-request and daily-token
  boundary fixtures pause before issuance without changing quota state.
- Historical `python3 run.py --scenario all` scripted suite completed in a
  temporary directory with no keys.env copy.
- No active shared run lock or existing Qwen evaluation output/manifest.
  All prior provider ledgers and Groq quota state remain unchanged.

The initial declared fixture completed its checks but could not save its
summary because its external helper named the preparation directory v0.20.0.
The helper path was corrected to v0.22.0 and the fixture rerun successfully.
Both helper versions and logs are preserved. Production adapters were untouched.
These declared fixtures validate plumbing, not Qwen's experimental behavior.

## Access evidence and $0 plan

Earlier handoffs mentioned the preserved Groq HTTP 403 but omitted the later
successful repaired identity check. The saved 2026-10-08 repaired check made
one request and returned exactly `qwen/qwen3.8-27b`, parsed {"ok": true}, valid
usage (39 prompt and six output tokens), and $0 charge on the owner-confirmed
Free account. The existing application User-Agent repair was already part of
the frozen client. Both the old 403/metadata failure and later success remain
preserved. A new neutral access check is not required by this evidence.

The cumulative Groq ledger remains $0, and the two saved quota events are
unchanged. The prior Free-account confirmation is retained; no account tier,
billing, quota or credential setting was inspected or changed. Proposed batch
cap and all frozen Groq rates are $0. Paid-tier use is not authorized. The
shared provider formation stop remains $8, and no concurrent run may use the
ledger or account quota.

Cloud reports GROQ_API_KEY ready with current observations; boolean availability
was also checked without displaying its value. Configured network policy
permits api.groq.com without method restrictions, including POST. No request
was sent to verify present service availability or account settings.

## Quota and duration

Frozen Free limits are 30 requests/minute, 1,000 requests per rolling day,
8,000 tokens/minute and 200,000 tokens per rolling day. The unchanged adapter
admits at most one request per 61 seconds, reserves 8,000 tokens before
issuance and settles uncached input plus output after a valid response.
Server limits and account-wide usage remain authoritative.

| Other-model usage scaled to 240 cells | Requests | Uncached input + output tokens | 200,000-token daily allowances |
|---|---:|---:|---:|
| Haiku 5.5 settled requests | 986 | 3,996,775 | 20 |
| Haiku 4.5, doubled | 938 | 2,896,672 | 15 |
| Gemini | 928 | 2,184,926 | 11 |

These are cross-model planning estimates, not predictions of Qwen tokenization,
cache usage or behavior. Spacing alone would take about 16–17 hours for these
request counts, but daily token quotas imply multiple days. Completion time
is not guaranteed. The full frozen ceiling is 2,880 requests.

Some Haiku 5.5 requests exceed 8,000 uncached-plus-output tokens. Qwen's own
per-request usage is unknown: a server rejection or reported excess must
retain the evidence and stop for review. No history trimming, token-limit
change, model substitution or replacement episode is permitted.

A pre-request quota pause means no request was issued. The existing runner
saves the exact history, packets and pressure-delivery evidence, releases the
lock and exits. The separate approval proposed below explicitly covers resuming
that same command/output after quota permits. It does not authorize retrying
an issued failure. No scheduler, automatic resume or live run has been started.

## Separate approval and exact next step

The proposed approval is:

> Approve Qwen 3.8 27B’s frozen Study A evaluation on Groq Free at $0, including resumes after pre-request quota pauses; stop without retrying any issued failure.

After separate approval, record its receipt before generation, recheck freeze,
adapters, all ledgers, quota state and shared lock, then run from the same
checkout using the preserved Python 3.11 runtime:

```bash
export PATH=/workspace/haiku55-runtime/venv/bin:$PATH
python3 scripts/formation_study_a_evaluation.py \
  --model qwen/qwen3.8-27b --budget 0 \
  --output 'results/2026-10-11 v0.22.0 qwen38-none r10 study-a evaluation' \
  --approved-cost --confirm-groq-free-account
```

For a verified pre-request quota pause, preserve this checkout/output and
resume only when the existing quota policy permits. For timeout, issued
rejection, uncertainty, identity/usage failure or guard stop, retain evidence
and stop for review without automatic retry or resume. Current approval is
offline only; none of these live actions is yet authorized.

All previous evidence and both earlier Study A timeouts remain intact. Full
P6 remains inconclusive: 840/1,080 cells attempted, 838 valid identities,
Qwen's 240 cells untouched. No later model or stage is authorized. Offline
evidence, plan and receipt are saved on main; no intermediate Mac step is needed.
