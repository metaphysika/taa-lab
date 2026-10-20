Historical initial draft, superseded by PAPER3_STUDY_D_GEMMA_COMPLETION_v02426.md after retrieval of the evidence. No launch approval.

# Study D v02426 — draft pending the v02425 returned evidence

Status: offline preparation only. No launch approval, final continuation manifest,
or executable v02426 package. Claude review and exact-commit owner approval are
required before any launch. Historical v02425 code, ledgers, adapters and evidence
must remain unchanged.

## Reported result and evidence boundary

The owner relayed Claude's review of a 347-file v02425 return, ZIP SHA-256 prefix
`59cfb59d`. The full ZIP, full digest and episode files have not been supplied to
this workspace. These are attributed results, not an independent audit:

- Contrary COMPLETE: W known servile acts 54/64, exact bound 0.84375; U zero known
  over-refusals, nine malformed, bounds 0 to 9/64 (0.140625).
- Neutral STOP_FOR_REVIEW at the worker time guard: 96/132 completed transfer
  episodes; two interrupted episodes remain missing. Both acquisition gates
  reportedly passed 100/100.
- Pair not closed. No final pair contrast, null result or complete-case analysis.

Required next input: unmodified v02425 return ZIP, with its full SHA-256, and any
local receipts/app log needed to resolve native request closure. Preserve original
bytes and inventory every extracted file. Do not reconstruct episode membership,
acquisition decisions, timing or hashes from these aggregate counts.

## Logging change only

Inspection confirms that v02425 Serving.event() appends, flushes and fsyncs each
JSONL event, then calls Volume.commit() while still holding self.lock. This blocks
the serving event/queue path on remote persistence. The reported event counts and
timing attribution still require independent inspection of the return.

The revision must retain each event append/flush/fsync. A 30-second timer commits
the Volume outside the serving lock. Episode-end and final/stop commits also run
outside that lock. Separate commit coordination must prevent overlapping local
timer/episode-end commits without holding the event/request lock during network
I/O. Timer failures must be recorded and stop later generation; do not silently
lose persistence errors. Finalization must stop/join the timer and commit the
last durable local evidence, including failed/interrupted episodes.

Free CI must check the actual production event/timer/episode-end path, not a
parallel mock implementation. A blocking fake commit must leave event appends
and queue access responsive, while flush/fsync remain observable. Use events or
barriers rather than a performance-sensitive wall-clock assertion. Verify timer,
episode-end, stop/final flush, error propagation and no commit inside self.lock.
Run the integrated scripted CPU post-training dry run with delayed commits.

No engine, model, LoRA, acquisition, sampling, parser, scorer, seed or case change.
Live LoRA, graphs, retained prefixes, sampler and post-capture KV guards remain.

## Neutral continuation admission

1. Hash-bind the full returned ZIP and all relevant input files, including the
   neutral acquisition PASS decision, completed transfer files and interrupted
   request evidence. Keep source Volumes read-only.
2. Validate the complete 132-unit frozen shuffled schedule and original index for
   every (case, repeat). A continuation must retain the original schedule index
   in seed 247053 + index + turn - 1; never renumber the filtered suffix.
3. Partition units into completed, interrupted/missing and untouched. Hash-pin
   the 96 completed files. Do not rerun either interrupted unit or any completed
   unit. Reported counts imply 34 untouched units, subject to source verification.
   Absence of a completed file alone is NOT proof that no request was received.
   Ambiguous/native inflight units stop review rather than being resent.
4. Reuse only the v02424 neutral adapter, read-only, with the same checkpoint and
   public training proof verification; publish hashes before loading. No training
   fallback. Reuse the recorded acquisition decision; no acquisition or repeat
   spontaneous/descriptive checks in this completion stage.
5. Write new outputs to a fresh v02426 evidence Volume and once-only ledger.
   Compute planned-denominator neutral bounds over all 132 units: 96 original
   completed files plus new completed files; interrupted units stay missing.
   Include per-unit producer revision/path/hash and original schedule index.
   Preserve known executed acts from any partial evidence under the frozen bound
   rules; do not replace malformed or interrupted outcomes.
6. Only a verified union and preserved COMPLETE contrary result can produce a
   closed pair report. No final pair contrasts before that boundary. Future
   virtue admission must bind the composite pair evidence and durable closure,
   not pretend the stopped v02425 controller was COMPLETE.

## Budget and windows

Owner dashboard: $18.52 used / $11.48 left. Previous launch input was $11.05 /
$18.95. Displayed interval increase $7.47 is not an itemized Modal invoice.
Cumulative cap remains $36 across months; no ledger reset or implied refund.

Proposed neutral software guard 3,000 s; existing +200 provider timeout gives
3,200 s. Preserve rate ceiling $3.20/hour, startup 120 s, idle 2 s, single-worker
overhead $0.375. Reservation is (3200 + 120 + 2) * 3.20 / 3600 + 0.375 =
$3.327888889, rounded-up target $3.33.

Virtue science/guard/reservation unchanged: 8,800 s software / 9,000 s timeout,
$8.483444444 reservation. Both future reservations total $11.811333333; actual
plus reserves $30.331333333, cumulative headroom $5.668666667. Current credit
after the neutral reservation is $8.152111111, about $0.331333333 below virtue's
reservation. Admit only the current stage against then-current credit; virtue
may wait until November without resetting cumulative spend. No cap increase.

Retain the neutral/pair deadline October 26 01:00 UTC exclusive and virtue
November 9 01:00 UTC exclusive. Virtue may launch after November 1, only with a
complete audited pair, Claude review, fresh billing and separate owner approval.

## Measured projections still pending source audit

Owner reports v02425 engine load 597–609 s; contrary acquisition span 704 s with
207 s generation, transfer span 2,501 s with 1,856 s generation. Record these as
reported, without treating removed commit time as guaranteed future speedup.
Derive request counts, per-request wall-time distributions and per-episode
latency from source events. Project the actual untouched neutral schedule,
including cold load and persistence allowance. Project full virtue acquisition
and all 132 transfers at both measured v02424 training rates. Do not substitute
benchmark decode throughput for actual multi-turn wall time. The source events,
virtue token count and complete denominators are required before numerical
projections and guard margins can be finalized.

## Disclosure and publication boundary

Contrary ran with per-event remote commits; neutral completion and virtue would
use batched commits. Scientific settings/seeds are identical; batching/timing
may differ. Disclose this post-results implementation change and the interrupted
neutral units. Keep the previous engineering attempts and malformed outcomes.

Prepare Mac spawn/caffeinate/SUBMITTED commands only after exact source hashes,
new bindings, full scripted/static regression checks and both GitHub checks are
available. No approval from v02425 transfers to v02426. No launches now.
