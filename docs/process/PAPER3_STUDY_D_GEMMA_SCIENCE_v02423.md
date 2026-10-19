# Study D v02423 — science integration FOR REVIEW; no launch approval

Owner reviewed v02422 commit 258ff726d95565efcfb8e2c29cb0dfdce37ff674 / app
ap-tOeYK2AtbdQ74oqw0dki8e. Its STOP_FOR_REVIEW remains an engineering result,
excluded from science. All four original uploads and 64 extracted files, their
hashes, old ledgers, markers and private review-stop adapters remain untouched.
No further smoke or merge rerun is proposed.

## Selection and accounting correction

The merged candidate is INVALID under the original bf16 logits rule: max_abs
1.125 > 0.5 and relative_L2 0.0518121943 > 0.01. Tolerances are unchanged.
Owner's rationale: merging into bf16 rounds each adapted weight and can lose
part of the trained change differently across arms. Live LoRA retains the
separate W*x + B*A*x computation used during training; this is not a claim of
bitwise equality across different training/serving kernels. Select the valid
live candidate without another merged run. The earlier four-cell speed selection
could not return a winner; this is the owner's subsequent exclusion of an
invalid engineering candidate, not a retroactive claim that that function passed.
No scientific outcomes enter the selection.

Each completed live cell has 512 TOTAL tokens across both rounds. Correct rates:
512/16.322197591 = 31.368325 tokens/s cold; 512/14.129252522 = 36.236878 retained.
The earlier 62.7/72.5 figures double-counted tokens by dividing by one average
round. Historical received summaries are preserved as attributed reports; the
current selection and projections use the corrected rates. Frozen select()
already uses the correct sum; no change is made to it. Retained/cold elapsed
ratio 0.8656465 (approximately), a 13.4% elapsed-time reduction, clears the >=5%
rule. This is a time reduction, not a claimed cross-revision speedup factor.
Selection evidence hashes and arithmetic: selection-v02423.json.

Latest owner dashboard: $6.80 used / $23.20 remaining. Displayed interval delta
$0.91 since $5.89, including intervening charges; no itemized invoice attribution.
No refund, counter reset or deletion of v02422's reservation/STOP record.

## Scientific invariants and integrated serving

Same pinned Gemma 4 31B weights and revision, A100 80GB, bf16, vLLM 0.31.0,
Transformers 5.10.4, torch 2.13.0, PEFT/Accelerate pins, all seven target names
with architecture-conditioned v_proj coverage, rank 8 / alpha 16 / dropout 0. All arms:
2,000 examples, one epoch, 250 optimizer steps; same data, order, served empty
thought channel, prefix masking/end token, optimizer, learning rate and 1024
training context. Frozen seeds, full histories, default scientific sampling,
4096 output/12 total steps/16384 inference context/128000 wire guards, cases,
4 transfer repeats, acquisition thresholds/message-number scoring, parser,
scorer and planned-denominator bounds remain unchanged. Gemma's post-results
admission despite v02416's preregistered format FAIL remains disclosed; no cases
removed, malformed results remain in bounds. No other models or dose levels.

All three arms use the SAME live-LoRA engine configuration measured in v02422:
gpu_memory_utilization .95; max_num_seqs 2; enforce_eager=False; prefix caching
True; cudagraph_specialize_lora=True; capture sizes[1,2], maximum 2. Retain prefixes
throughout each arm worker (vLLM owns eviction/preemption, no manual history
trimming). Caches are private to each arm's engine and adapter. The benchmark
used fixed histories and episode-boundary resets; production retains across
requests, so throughput remains a workload extrapolation. Science retains its
frozen stateful engine-owner/two-episode-thread request path, not a new batching
or seed schedule. This integration changes implementation from the gated eager
base configuration, disclosed; no scientific response-repair or retry is added.

VLLM_USE_FLASHINFER_SAMPLER=0 is set in the image, each subprocess environment,
and before importing vLLM. After engine init, require the native disabled-sampler
message; any enabled-sampler line or absent attestation stops before generation.
No nvcc/toolkit installation and no compilation/graph/warmup suppression.
Load the trained PRIVATE adapter explicitly into the pinned BASE model; never
load merged weights. Preserve actual effective graph/adapter/log evidence.
The same post-capture KV check as v02422 remains: native availability minus
rounding, graph upper allowance and .25 GiB must cover 13.765 GiB; free device
memory >=.25 GiB. v02422 margin was 0.100 GiB, not proof a later load will pass.
Every arm records its own native profile and conservative margin before requests.

Free GitHub static checks require the exact engine dict, live adapter load, no
merge operations/alternate EngineArgs, retained cache, environment/log guard and
explicit per-request seeds. AST checks hold the actual training, acquisition,
transfer/scheduling/parser/scorer functions and request loop identical to v02420.
All scientific asset bytes match v02420; administrative stage/selection/projection
files are new. Real tiny CPU rehearsal, JSON/coverage/masking/checkpoint/reload,
o-backend Modal serialization, and scripted engine control-flow regressions run
without GPU, secrets, pretrained weights or Modal access. They do not prove a
new full-arm GPU run will finish.

## Projections and proposed guards

Use generation 36.2 tokens/s (rounded down); training scenarios 131.5 (v02420)
and 97.6 (v02422). Per-arm frozen token totals: contrary 326496, neutral 298272,
virtue 363524. Decode workload: 132 transfer episodes x 9001/34 observed base-output
tokens/episode + acquisition/descriptive requests x128 assumed output tokens.
Request counts 120/220/120; no cases or repeats cut. Measured startup components:
training load 543.607468 s and live serving load 305.099577 s, total 848.707045 s.
Exclude failed merge load. Add the existing 300 s allowance, then multiply the
whole per-arm nominal time by 1.25. Full phase-wide I/O/checkpoint/commit/barrier
wait timestamps were not saved by the failed smoke; allowance and stress cover
those provisionally, not as measured zero. Pair acquisition-barrier skew can
consume worker time; deadlines include that wait and never reset.

| Training tokens/s | Arm | Nominal s | Stress s | Nominal worker $ | Stress worker $ |
|---|---|---:|---:|---:|---:|
|131.5|contrary|5021.2|6276.5|4.46|5.58|
|131.5|neutral|5160.2|6450.2|4.59|5.73|
|131.5|virtue|5302.8|6628.5|4.71|5.89|
|97.6|contrary|5883.6|7354.5|5.23|6.54|
|97.6|neutral|5948.0|7435.0|5.29|6.61|
|97.6|virtue|6263.0|7828.7|5.57|6.96|

At the $3.20/worker-hour ceiling, total including $1.125 stage allowances:
fast training scenario $14.89 nominal / $18.33 stress; slower $17.21 / $21.23.
This exceeds the owner's rough estimate in the slower case because both measured
startup components and the 300 s allowance are included. All stress times exceed
6000 s. Proposed guards pair 7600 s per worker, virtue 8000 s; provider timeouts
7800/8200 s, plus 120 startup/2 idle seconds; no automatic extension/restart.

| Stage | Software guard/worker | Provider timeout/worker | Proposed target | Reservation |
|---|---:|---:|---:|---:|
|pair, two parallel GPUs|7600 s|7800 s|$15|$14.833556|
|virtue, separately approved|8000 s|8200 s|$8|$7.772333|

Reservation = workers x(timeout+120+2) x3.20/3600 + stage allowance(.75/.375).
Total 22.605889; actual 6.80 + reservations = 29.405889 under cumulative 30 and
current 23.20 credit. Unreserved cushion 0.594111. These proposed targets replace
the prior unaffordable $12/$6 targets only if the owner approves v02423/budget.
Pair admission reserves headroom for BOTH stages; virtue refreshes actual billing
and checks its remaining reserve. No card/free-credit limit remains the owner-
verified provider backstop; code does not claim a live invoice meter. Stage
allowances cover CPU controller, image and private adapter storage provisionally. The prior-stage
anti-omission floor uses the published A10080 GPU-only $2.4984/hour from the
frozen v02413 pricing record, not the estimated $3.104208 whole-worker rate:
CPU/RAM estimates are not a minimum invoice. Actual billing still requires
owner reconciliation; $3.20/hour remains the reservation ceiling.

The 25% stress is not a confidence bound. Short 64-token/two-stream timing need not
match long scientific replies, prefill or heterogeneous histories. Full 4096-token
sensitivity is explicitly in projections-v02423.json and does not fit these
budgets. Exceeding guard or any independent safety/identity/usage/source/context
issue stops and preserves incomplete planned-denominator results, not a null.
No case, repeat, token limit, data or scientific threshold is reduced to fit.

## Stages, evidence and approval

Fresh namespace taa-study-d-gemma-v02423-{budget-once,evidence,private-adapters},
local once markers per stage, fresh finite window October 19 01:00 UTC to
October 26 01:00 UTC exclusive for pair; virtue to November 9 01:00 UTC exclusive.
For the Mac operator: pair closes October 25 at 8 pm CDT; virtue closes
November 8 at 7 pm CST (after the daylight-saving change). Monthly credit
never resets the cumulative $30 limit. All old namespaces remain
untouched. Controller looks up resources by name inside remote functions.
Before new GPU reservation: verify exact reviewed source/assets/approval/budget,
read and copy immutable v02420 CPU PASS (including original durable closure)
and bound v02422 speed evidence into NEW evidence Volume; never commit old
Volumes. The v02422 STOP is preserved; it is not restarted or relabeled complete.
Its invalid merged candidate is explicitly rejected by this new owner decision.

Stage pair launches contrary+neutral concurrently, then the unchanged controller
acquisition barrier. Neutral must pass; contrary must pass its own gate relative
to neutral. Failed acquisition makes transfer uninterpretable and blocks transfer;
no quality retry. Both pass -> frozen transfer/descriptive checks. STOP anywhere
blocks later requests/stages. Private adapters remain private/non-shared on review
stop and after pair completion. Virtue requires COMPLETE reviewed pair, report
SHA, durable closure, same commit/config and NEW separate owner approval/current
billing. On complete three-arm study end delete adapters with receipts, no
sharing/deployment; on a review stop retain pending owner decision, then delete.

Mac commands: studies/formation-study-d-gemma-stages-v02423/MAC_COMMANDS.md.
Spawn/acknowledged app+call IDs, caffeinate and SUBMITTED safe-to-close line remain.
No launches now. Push and verify BOTH GitHub workflows, then STOP FOR REVIEW.
