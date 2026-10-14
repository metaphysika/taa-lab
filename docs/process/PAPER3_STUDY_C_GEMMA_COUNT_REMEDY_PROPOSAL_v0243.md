# Offline Gemma token-count remedy proposal — v0243

**Review proposal only. No HTTP/model/countTokens calls, launch, freeze, or watch activation.** Original Cloud, `/workspace/taa-lab` main and Python3.11 retained. Frozen v0239 science and all v0241/v0242 adapters/results are unchanged.

## What happened and the preferred repair

The blocked first body `e507615e6e93056a75ffbde22704a26fd0541fc7f9bb54024af1a14456090b12` already has a completed exact-body count receipt of **1,028 tokens**, preserved in Study B. Its inherited retry job is complete/received. The subsequent C metadata-validation folder carried those retry jobs but its receipts contain only the newer108 validations, omitting the older B receipts. Thus the C loader missed the count and encountered the completed-job no-resend barrier.

Load the union of the two explicit, SHA256-bound sources: immutable Gemma B receipts/retry state and the frozen C metadata-validation receipts/retry state. Accept a count only when its full native request body hash matches a positive-integer receipt AND a matching completed received job with1–5attempts. Retain source file hashes and job ID in a new canonical recovered receipt. Do not change either source or the original retry job. Conflicting counts, tampered sources or unclosed evidence stop for review. For the blocked body,1,028+4,096+128=**5,252≤16,000**; reuse requires **zero requests**.

The verified source union contains **2,151 exact counts covering ALL2,151 inherited completed metadata jobs**, not just the blocked body. Zero inherited completed count jobs remain without a usable receipt. Thus no known inherited job needs metadata re-issuance; the narrow exemption is a safeguard for a genuinely receipt-less case. This broader job-coverage check is saved separately.

## Narrow metadata-only exemption

If neither current receipts nor the verified prior union contains a usable count, normal new bodies use their normal countTokens job. Only a closed received legacy metadata job without a usable count may receive one separately journaled new ID: `countTokens:v0243:<body SHA256>:metadata-only-1`. The old job remains unchanged. Exactly the Gemma `:countTokens` endpoint/model may use this path. The generation sender and original RetryTransport are unchanged; the exemption cannot select `:generateContent`, other models or generation jobs. No second replacement for a body. Invalid new count replies, unclosed/interrupted jobs, existing exhaustion/run-limit stops and all independent guards still stop for review.

Normal eligible metadata transport failures keep five TOTAL attempts,10/30/60/120 waits or longer actual reset and inherited counters. New metadata attempts reserve quota and retain native body/reply/receipt/closure as before. The fallback does not clear any job, quota history, retry-needed request or spending record. Normal quota pacing may reuse the SAME unsent replacement job, never create another.

## All540 offline check

All540 exact scheduled Gemma episodes and every compatible frozen scripted fixture prefix were checked: **6,480 prefixes /756 distinct bodies**. **90 episodes** (all18shared-zero probes×5repeats) contain the missing older receipt at their first turn;405prefix occurrences reuse18prior exact counts. All are recoverable. No known fixed/fixture prefix requires the new-ID exemption. The remaining6,075prefix occurrences have no completed-job collision.

The real remedy code was exercised on every prefix with scripted metadata callbacks:738simulated metadata responses, **zero HTTP/generation calls**, original4891inherited jobs and5retry-needed requests unchanged. Scripted token values are plumbing stand-ins, NOT provider counts or token-fit certification. All540cell IDs and per-prefix hashes/routes appear in JSON; the CSV has one readable row per scheduled episode.

Future model replies cannot be enumerated offline. This check covers every fixed seeded history and frozen fixture path, not all possible future strings. The same exact-body lookup and metadata-only fallback must run at EVERY future turn. Tests cover arbitrary unseen later reply bodies, collisions, corrupt receipts and interrupted states. The existing exact countTokens guard remains primary before every generation; no histories are trimmed or substituted.

## Code and tests to review

- `formation/study_c_count_remedy_v0243.py`: verified source union, exact-count recovery, narrowly scoped metadata job selection and count-only execution; read-only first-unsent-boundary verifier. This helper has no credential lookup, network client or launch.
- `scripts/formation_study_c_count_preflight_v0243.py`: all540 offline scanner plus scripted exercise of the real helper.
- `tests/test_formation_study_c_count_remedy_v0243.py`:17focused tests, including exact preserved1028receipt, source/job/count corruption, conflicts, zero-HTTP recovery, one-new-ID-only behavior, unchanged generation barrier, endpoint/model restriction, inherited retry counters/reset waits, quota pacing, first-unsent boundary and all540/6480coverage.
- `studies/formation-study-c-gemma-count-remedy-proposal-v0243/proposed-count-integration.diff`: exact proposed CChat count wiring for a SEPARATE v0243 operational copy. It is NOT applied to any frozen adapter or executable CLI. The approved runtime must pass the manifest-pinned `count_sources` into CChat; an empty default is for explicit no-prior-source fixtures only, not production.

Validation complete: **17focused tests passed;470repository unit tests passed in544.305seconds; free `run.py --scenario all` passed.** Logs and the offline readiness receipt are in the proposal folder. Original source/stop/ledger checks passed after testing. No calls or launch were made.

## Starting from the first unsent request, after approval

Gemma has0episodes,0newmetadataHTTP and0generationHTTP. It starts the original schedule at episode1/turn1, with no resume/native-rerun/replacement label. Nothing is re-scored, pooled or relabeled. Preserve the original zero-request guard checkpoint and stop artifacts unchanged. Before any mutable status/quota/retry update, preserve byte-identical archival copies of the old stopped-state files under the SAME original Gemma output and pin their hashes. Keep original journal prefixes pinned. Use a separately bound first-request checkpoint filename for the active first cell, with the SAME scheduled cell ID; the new auditor recognizes only the exact pinned historical zero-packet guard as archival. No directory deletion/recreation/relocation and no generic interrupted-run admission.

The read-only admission verifier must match the pinned stop index, completed0, exactly one zero-packet first guard, no generation calls file or progress summary, no active runner/request/lock/foreign hold, source/ledger checks and both prior completed-model indexes. Any request evidence or changed boundary blocks admission. Original no-restart policy continues for all later interruptions. These startup/audit/report changes belong in the separately reviewed operational copy/binding; do not patch old modules in place.

After owner approval: finish the separately bound v0243 adapter/report/CLI integration exactly under this plan, test full native/replay/quota/audit/report plumbing with scripted fixtures, publish the reviewed code and readiness evidence to main, require BOTH GitHub checks, then start Gemma first72. At0–7mechanical and all guards/audits pass, preserve/report/push/BOTHCI then remaining468. At8+mechanical or independent guard stop for review. Exact-token guard exclusions remain null-scored missing; continue through27/540 and stop at28. After audited/reported/indexed/published/BOTHCI Gemma540, start Luna under Gate6b with the same first72 checkpoint.

## Science, costs and decision

No stimuli/seeds/defaults/output4096/12steps/parser/scorer/neutralSYSTEM/native interface/cohort/C1–C4 or denominator changes. Haiku/Gemini complete remain immutable; failedGemini72/neutraltest/pilot remain unpooled. Gemma metadata and generation cost$0; numericalGoogle remains$3.668447350. All caps, cumulative$8/Google$10credit and originalquota6788events/5priorretry-needed requests remain unchanged. Luna evaluation allowance$1.337634710 plus alreadyspentpilot$0.062365290 stays within OpenAI C$1.40.

**Decision requested:** approve this offline remedy and first-unsent-start plan. Execution remains gated on the approved additive binding, full offline readiness and BOTH GitHub checks. Supervision stays disabled until a subsequently authorized paid runner is confirmed alive with its exact argv. No StudyD.
