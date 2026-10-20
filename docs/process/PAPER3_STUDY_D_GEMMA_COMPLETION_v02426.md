# Study D v02426 — neutral completion and batched evidence commits

FOR REVIEW ONLY. Neither stage is approved. Claude must review before a new
exact-commit owner decision. No model, GPU, training or Modal action occurred
in preparing this revision.

## Preserved result

The owner's GitHub ZIP is 24,885,668 bytes, SHA-256
59cfb59d0a72ad83083961b41e23da5af53f220faa080524a5d9550d539a625c.
All 347 entries pass CRC; all 228 completed episode files reproduce their exact
first native text, full request history and frozen parser/scorer replay.
The original ZIP and extracted text bytes remain unchanged. See the inventory
and audit in studies/formation-study-d-gemma-pair-result-v02425/.

Contrary is COMPLETE: 54/64 W episodes have known executed servile acts; bound
0.84375 exactly. U has zero known over-refusals and nine malformed episodes,
bounds 0–0.140625. Neutral has 96/132 completed transfers and stopped at its
worker time guard. Both acquisition decisions passed 100/100. The pair is NOT
closed. Do not report a final pair contrast or interpret missingness as a null.

Two neutral units have interrupted native requests and remain missing forever:
C-cold-r1-U repeat 4, turn 1 (partial text); B-WU-cold-r1-pressure-W repeat 3,
turn 5 (four prior complete replies, no partial fifth). Those prior replies
execute no servile act. All native partial/prior outputs stay in the evidence.
No interrupted episode or received reply is resent.

## Runtime change

The prior Serving.event() synchronously committed the Volume inside self.lock.
The new event path retains append, flush and fsync for EVERY event but never
calls commit. A separate 30-second timer commits the Volume, as do episode-end
and worker-final boundaries. Its separate mutex serializes local commits; it
never holds the serving event/request lock during network persistence. A failed
timer commit stops later generation and is surfaced in the failure report;
final persistence is attempted even after an error. This is durability batching,
not an authorization to drop events. Abrupt container loss can lose the last
not-yet-committed interval; unknown requests still stop review and never restart.

Serving remains live LoRA on A100 80GB, bf16, utilization 0.95, 16,384 context,
CUDA graphs [1,2], LoRA-specialized graphs, retained prefix cache and native
sampler guard. KV-after-capture check unchanged. Dose, data, LoRA settings,
acquisition thresholds, generation limits, parser/scorer, seeds and all 132
planned transfer units remain frozen. No speed selection, merge or new smoke.

Free CI checks the actual production event AST and verifies append/flush/fsync.
A blocking fake remote commit must not block event appends or access to the
serving lock. Timer failure, final persistence, fixed schedule seeds, exact
untouched unit admission and the real post-training CPU path are tested without
model generation. Exact inherited asset hashes retain all 18 v02420 inputs.

## Neutral completion admission and union

The reviewed continuation-source-v02425.json pins every source pair file,
including all 96 completed neutral outputs, acquisition decisions, interrupted
native events, contrary completion and adapter proofs. Its 132-unit partition
is 96 completed, two interrupted/missing and 34 untouched. Original shuffled
schedule indices determine seeds; filtering does not renumber them.

Mount v02424 private adapters and prior public Volumes read-only. Verify the
same neutral checkpoint index/files/public training proofs and compare to the
v02425 pre-load hashes before reservation, then recheck before loading. No
retraining fallback. Copy verified evidence to the fresh evidence Volume; never
commit or modify the old source Volumes. No acquisition or spontaneous checks
are rerun. The recorded hash-pinned acquisition PASS supplies admission.

Run only the 34 untouched units, retaining original case/repeat/turn request
keys, seeds and histories. Write only NEW outputs under
neutral-completion/neutral/transfer. Union reporting retains the 96 original
outputs, new completed outputs and two missing units under all 132 planned
units. Include producer revision, path/hash and original index for every unit.
It is 130 possible judgments, not 132, even if all untouched units finish.
Any incomplete continuation stops review; there is no automatic retry/resume.

Only successful scheduled closure produces a new composite pair/report.json
and durable pair/closed receipt, linking unchanged contrary and the neutral
union. The historical v02425 controller remains STOP_FOR_REVIEW. Virtue admission
requires that composite report hash, source/union verification and durable
closure, plus owner/Claude review and separate approval. No final pair contrast
is computed in this preparation.

## Measured timing and projections

v02425 engine loads: contrary 596.639 s, neutral 609.391 s. Contrary issued 643
requests: 100 ordered acquisition, 20 spontaneous and 523 transfer. Neutral
issued 845: 100 ordered, 100 own-domain neutral acquisition, 20 spontaneous,
623 returned transfer and two interrupted transfer requests.

Contrary transfer: 132 completed episodes, 1,856.375 summed request-wall seconds
across a 2,500.586 s span; mean 3.549 s/request, p95 5.825, max 16.977. Neutral
transfer: 96 completed episodes plus partial interrupted work, 2,571.657 summed
returned request-wall seconds across 3,432.400 s; mean 4.128, p95 6.834, max
30.150. These are actual wall latencies, not decode-token benchmark rates.
They still include some historical persistence stalls. No concurrency speedup
is assumed. Contrary's full acquisition-to-transfer interval includes waiting
for the neutral gate; its request-wall total alone does not capture that wait.

Neutral completion estimates request counts from available completed repeats
of the SAME case, using 12 if none exists. About 190.33 requests × measured
neutral mean latency, plus 609.391 s load and 300 s allowance: nominal 1,695.1 s;
1.25× stress 2,118.8 s, spare 881.2 s under a 3,000 s guard. This is an estimate,
not a guarantee; new batched commits are not yet measured. Keep full cases,
repeats, generation limits and stopped/malformed bounds.

Virtue uses 363,524 training tokens. Actual v02424 rates are 159.461 tokens/s
(contrary) and 262.645 (neutral), giving 2,279.7 or 1,384.1 training seconds.
Add 543.607 s historical training-load allowance, conservative 609.391 s serving
load, measured acquisition/spontaneous/request profiles and 300 s allowance.
Because virtue has no observed science request counts, show BOTH profiles:

| Training rate | Request profile | Nominal seconds | Stress seconds | Spare under 8,800 s |
| --- | --- | ---: | ---: | ---: |
| 159.461 | Contrary-like, 523 transfers requests | 5,795.8 | 7,244.8 | 1,555.2 |
| 159.461 | Neutral-like, about 856.6 transfer requests | 7,500.1 | 9,375.1 | **−575.1** |
| 262.645 | Contrary-like | 4,900.2 | 6,125.3 | 2,674.7 |
| 262.645 | Neutral-like | 6,604.5 | 8,255.6 | 544.4 |

The neutral-like profile scales returned request counts from 96 episodes and
therefore includes some partial-work overhead. It is a sensitivity, not a
prediction of virtue behavior. The slow-training/neutral-like stress case DOES
NOT fit the unchanged virtue guard. Do not silently raise its guard/reservation
or cut cases. Owner/Claude must review this limitation before virtue approval.
A 25% stress factor is not a confidence bound and does not cover full 4,096-token
tails. Numeric inputs/methods are in projections-v02426.json.

## Budget, windows and execution boundary

Owner dashboard: $18.52 used / $11.48 left. The displayed increase of $7.47 from
v02425 submission $11.05 is an interval amount, not an itemized app invoice.
Prior ledgers/reservations remain unchanged; no refund/reset is inferred.

Neutral guard 3,000 s, Modal timeout 3,200 s. Existing formula:
(3200 + 120 startup + 2 idle) × $3.20/hour / 3600 + $0.375 overhead =
$3.327888889 reservation (rounded-up target $3.33).

Virtue remains 8,800/9,000 s and $8.483444444 reservation. Actual plus BOTH
reservations: $30.331333333, leaving $5.668666667 under the unchanged $36 cap.
Current credit after neutral reservation: $8.152111111, $0.331333333 short of
virtue's reservation. Admission checks only the current stage against current
credit, while cumulative accounting includes remaining stages. Virtue may wait
for November's credit; no cumulative reset. No payment card remains the
owner-attested provider backstop, not a new account API verification here.

Fresh v02426 ledger/evidence/private namespace; old resources untouched. Neutral
window ends October 26 01:00 UTC exclusive; virtue November 9 01:00 UTC exclusive.
Mac commands are MAC_COMMANDS-v02426.md, never inherited MAC_COMMANDS.md. Use
caffeinate/spawn and wait for acknowledged SUBMITTED with app and call IDs.
No run until both GitHub checks PASS, Claude review and new exact-commit approval.

Contrary and initial neutral used per-event commits; neutral completion and
virtue would use batched commits. Disclose this post-results implementation
change. Frozen seeds/settings are identical; request batching/timing may differ.
Private adapters remain non-shared; read-only source cleanup is a separate
owner-reviewed CPU study-end deletion with receipts. No deployment/sharing.
