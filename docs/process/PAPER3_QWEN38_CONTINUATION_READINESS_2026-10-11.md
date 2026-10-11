# Qwen frozen Study A continuation readiness — v0.22.1

The separately approved offline preparation is complete. No model calls or
provider probes were made. The original four attempted episodes, all 20 issued
requests, 19 native responses, original stopped controller/status, every launch
log and A_R02 repeat 1 HTTP 429 are unchanged. Exactly 236 cells remain untouched,
starting A_R03 repeat 1. Spending remains $0; all cumulative ledgers and the
failed 8,000-token quota reservation remain unchanged.

## Prepared continuation

The new Qwen adapter imports the unchanged frozen execution helpers and selects
only the reviewed suffix. It requires both explicit CLI flags and a separate
written execution receipt bound to the execution-plan hash before credential
loading, transport construction or evidence creation. That receipt does not
exist yet. The offline preparation receipt grants no model requests.

The execution plan binds the ordered 236 cells, source evidence, frozen inputs,
original and new adapter hashes, model/settings and initial ledger/quota hashes.
The original checkout and evaluation output are required. Original manifest,
progress summary and four result/checkpoint pairs remain immutable. New native
journal events append after the protected original byte prefix with unique
logical/attempt IDs. Separate continuation manifest/progress/controller files
preserve the original stopped state and combine all 240 analysis records.

The new controller waits for persisted real quota and respects the existing
maintenance-hold path. It shares the provider run lock and uses its own controller
lock. It resumes only verified pre-request quota pauses; a new issued error,
timeout, uncertainty, identity/usage failure, usage over 8,000 tokens, guard stop,
inflight/unclosed attempt, boundary hash mismatch or CLI failure stops for review.
Terminal or uncertain controller status cannot automatically restart. New launch
logs continue the original sequence. Only the owned run lock is released.

All frozen prompts, complete history, scoring, model identity, output ceiling
(2,048), turn limit (12), byte limit (32,000), Free tier and $0 cap are unchanged.
No original full-batch runner or original controller is relaunched. No quota
reset, history trimming, paid upgrade, failed-cell replacement or issued retry.

## Offline verification

- All 59 frozen files and original adapter/cost-plan/controller hashes match.
- Original four result/checkpoint pairs reproduce deterministic replay.
- Sixteen targeted tests pass, including all 236 required-conduct fixture cells
  (966 mocked native responses), partial-cell quota pause/resume, no duplicate
  requests on completed resume, unique appended IDs, immutable source prefix,
  exact 240-cell combined denominator and $0 accounting.
- Negative fixtures cover missing approval, wrong root/output/model/cap/suffix,
  source/adapter/ledger/quota tampering, pending-cell evidence, existing lock,
  issued HTTP 429, timeout, wrong identity, missing/negative/over-reserve usage,
  inflight checkpoint and unclosed attempt. Controller tests reject terminal or
  uncertain restart and preserve an external maintenance hold.
- The full 300-test repository suite and historical scripted scenarios pass.
  These declared fixtures do not establish real Qwen outcomes.

Validation logs and methodology are preserved under
`results/2026-10-11 v0.22.1 qwen38-none r10 continuation offline preparation/`.
The first fixture run had a test-clock KeyError after quota settlement legitimately
removed paused_until; the fixture clock was corrected and its failed log retained.
Scientific inputs and original adapters were not changed. README version is
v0.22.1 for the new continuation behavior.

## Separate execution approval required

Plan: `studies/formation-study-a-qwen38-continuation-execution-plan-v0221.json`.
The exact reviewed command, from `/workspace/taa-lab`, is:

```sh
/workspace/haiku55-runtime/venv/bin/python3 scripts/formation_study_a_qwen38_continuation_controller.py \
  --plan studies/formation-study-a-qwen38-continuation-execution-plan-v0221.json \
  --approved-continuation \
  --reviewed-issued-failure \
  --confirm-groq-free
```

Do not run it yet. After separate user approval, record the exact approval in
`studies/formation-study-a-qwen38-continuation-execution-approval-2026-10-11.json`
with plan_sha256, checkout_root, output, cap_dollars: 0,
pre_request_quota_resumes_authorized: true and
issued_failure_retries_authorized: false. Recheck source/adapters/ledgers/quota,
then start this controller in the original environment. Keep only one controller
and no concurrent provider-ledger run. Supervision remains disabled during
preparation; any later heartbeat must monitor the new continuation status rather
than restarting the original stopped controller.

The saved pause lasts until 2026-10-12 18:41:48 UTC. It is a conservative client
default because Retry-After was absent, not a proven provider reset. The exact
429 cause remains unknown. Waiting does not guarantee completion under unchanged
Free limits; any new issued rejection is retained and stops the continuation.
If pre-request evidence establishes incompatible limits, stop for a decision
instead of changing the frozen experiment.

At safe pre-request quota boundaries, use an owned maintenance hold to snapshot,
audit and commit/push credential-free progress on main; release only that hold.
On completion or actionable failure, audit combined records/native closure,
identity/usage/replay/frozen hashes/cost/ledgers, preserve and commit/push evidence,
report the result, and disable supervision. Full P6 retains the failed identity;
no other model or stage advances automatically.

Approval phrase:
“Approve Qwen 3.8 27B’s remaining 236 frozen Study A episodes on Groq Free at $0;
retain A_R02 repeat 1 without retrying; allow resumes only after pre-request quota pauses.”
