# Study D v02424 — budget and guard revision FOR REVIEW; no launch approval

Owner supersedes v02423 commit c848d751c4d7de0ef289ead194e01fb7218325b7
before launch. Preserve it as reviewed, conditionally pair-approved, then
superseded and NOT LAUNCHED. Its approval does not transfer to v02424. All old
source, assets, receipts, evidence, once markers and ledgers remain unchanged.
No Modal API call or launch was made while preparing this revision.

## Scope and unchanged science

Only the time guards, derived timeouts/reservations, stage-specific free-credit
admission, cumulative cap and latest billing/projections change. Versioned paths,
source bindings, new namespace and exact-commit receipt are administrative.
The complete runtime is byte-identical to v02423. All scientific assets AND
selection-v02423.json are byte-identical (the selection file keeps its old name).
The scientific and implementation disclosures in
[PAPER3_STUDY_D_GEMMA_SCIENCE_v02423.md](PAPER3_STUDY_D_GEMMA_SCIENCE_v02423.md)
continue to apply: self-hosted Gemma, post-results admission despite format FAIL,
live LoRA, graphs [1,2] specialized for LoRA, retained prefixes, sampler guard,
post-capture KV check. No merged rerun, smoke, new model or data/seed/gate change.

The same 2,000 examples/arm, one epoch, rank/alpha/targets, acquisition checks,
132 transfer episodes per arm, four repeats, full histories, default sampling,
parser/scorer, malformed planned-denominator bounds, context/output/wire limits
and no-restart policy apply. The pinned libraries and every serving setting are
unchanged. CI enforces full runtime bytes, science/selection bytes and every
non-budget policy function against v02423, in addition to the prior science checks.

## Budget and admission

Owner dashboard is $6.85 used / $23.15 credit remaining; PRIOR is now $6.85.
The displayed $0.05 increase from $6.80 is an interval reconciliation, not an
itemized attribution to any app. Owner raises the cumulative Study D cap from
$30 to $36. This is separate from current monthly credit; November credit
cannot reset cumulative spend. No card is attached, per owner verification.

| Stage | Software guard per arm | Modal timeout per arm | Stage target ceiling | Exact reservation |
|---|---:|---:|---:|---:|
|Pair: contrary + neutral, parallel|8,400 s|8,600 s|$16.26|$16.255778|
|Virtue: separately approved|8,800 s|9,000 s|$8.49|$8.483444|

The unchanged formula is workers × (timeout + 120 startup + 2 idle) × $3.20/3600,
plus $0.75 pair / $0.375 virtue allowance. The target ceilings are rounded UP to
cents (virtue's unrounded reservation exceeds $8.48); admission uses full precision.
Total remaining reservations $24.739222. Spend plus reservations $31.589222,
leaving $4.410778 under $36. Stage allowances and the GPU-only prior-stage billing
floor remain unchanged; code still does not claim a live invoice meter.

At pair launch, current credit must cover ONLY the pair reservation. Today's
$23.15 covers $16.255778 and leaves $6.894222; it need not cover pair plus virtue
($24.739222). The cumulative-cap admission STILL requires actual cumulative
spend + BOTH remaining reservations <= $36. At virtue launch, refresh cumulative
actual spend and then-current credit; admit only if virtue's reservation fits
that credit and cumulative actual + virtue reserve <= $36. That credit may be
November's fresh allowance, but the spend total does not reset. A refreshed
billing attestation is required; insufficient credit/cap stops, never bypasses.

## Projections and spare time

Unchanged measured inputs: 36.2 generation tokens/s; training scenarios 131.5
and 97.6 tokens/s; startup 848.707 s plus existing 300 s allowance; 1.25× stress.
Workloads, output assumptions, projected costs and full-output tail sensitivity
are unchanged. Spare time below is software guard minus projected wall time,
including training, startup, generation and provisional overhead.

|Training tokens/s|Arm|Nominal s|Stress s|New guard s|Nominal spare s|Stress spare s|
|---|---|---:|---:|---:|---:|---:|
|131.5|contrary|5021.2|6276.5|8400|3378.8|2123.5|
|131.5|neutral|5160.2|6450.2|8400|3239.8|1949.8|
|131.5|virtue|5302.8|6628.5|8800|3497.2|2171.5|
|97.6|contrary|5883.6|7354.5|8400|2516.4|1045.5|
|97.6|neutral|5948.0|7435.0|8400|2452.0|965.0|
|97.6|virtue|6263.0|7828.7|8800|2537.0|971.3|

All arms fit these projected stress times, with at least about 965 s spare.
Three-arm estimated costs (including unchanged $1.125 stage allowances) remain
$14.89 nominal / $18.33 stress at 131.5 training tokens/s and $17.21 / $21.23 at
97.6. These are estimates, not measured full-arm costs or confidence bounds.
Full 4096-token reply tails still do not fit. Guard/failure stops preserve
incomplete planned denominators; no cases/repeats are removed or outputs repaired.

## Windows, resources and review

Windows are unchanged: start October 19 01:00 UTC inclusive; pair ends
October 26 01:00 UTC exclusive, virtue ends November 9 01:00 UTC exclusive.
Mac local closing times: October 25 8 pm CDT / November 8 7 pm CST.
New namespace taa-study-d-gemma-v02424-{budget-once,evidence,private-adapters}
and per-stage v02424 local once markers, without resetting/deleting prior keys.
Original v02420 CPU proof and v02422 speed evidence are carried and verified as
before. Controller/worker resource lookup remains inside remote function bodies.
Pair spawns both workers before waiting; acquisition barrier and gates unchanged.
Virtue still requires COMPLETE audited/reviewed pair, matching report SHA and
durable closure, same source commit/engine, and separate exact-commit approval.
Private adapters stay private through review, then are deleted with receipts at
study end or owner decision; no sharing/deployment.

Mac commands: studies/formation-study-d-gemma-stages-v02424/MAC_COMMANDS.md.
Same caffeinate, spawn and acknowledged SUBMITTED app/call-ID line; never retry
ambiguous submission. No launches approved in this revision. Publish, confirm
BOTH GitHub checks on the new commit, and STOP FOR OWNER REVIEW.
