# Seed 2 implementation, 2026-11-09

Build only, v0.24.82. Plan reference: Master Plan v3.2, M3 seed 2;
`SEED2_FT0_PRERUN_DRAFTS_2026-11-09.md`, Draft A revision 3. No training,
model, Modal, Kaggle or paid call was made. Execution needs the notebook entry
from Claude, fresh exact-commit review, and Chris's separate stage approvals.

## Seeds and reconstructed procedure

The training seed is **347056** and the shuffle seed is **347052**. Each is the
corresponding seed 1 value plus 100,000, chosen before training without testing
candidate outcomes. `formation/study_d_gemma_stages_v02482.py` owns the two
values. `TRAIN['seed']` supplies the recorded recipe, CPU rehearsal,
pre-LoRA `torch.manual_seed`, and Trainer `seed` and `data_seed`.
Sampling stays 248017 and evaluation order seed stays 247053.

Sol found revision 2's mismatch: the Trainer seeds do not shuffle this dataset.
The runtime builds the dataset in an asset's fixed order and overrides the
Trainer sampler with `SequentialSampler`. The stage thread authorized changing
both sources of training randomness while keeping those mechanisms.

The original order generator was not found in retained code. The procedure was
**reconstructed from an exact match**, then explicitly authorized for adoption.
`formation/seed2_order_v02482.py` documents and implements it: construct
T0001 through T2000, sort by the exact key `int(ident[1:])` ascending, then
`random.Random(shuffle_seed).shuffle(ids)`. The CPU test regenerates the entire
seed 1 JSON byte-for-byte against its pinned SHA-256
`8b8fd6c24f9eb2fd126f6f7fb7f7f86450906a0c2560d4fba538e7e18afc76e6`.
The bytes are canonical Git LF bytes; Windows CRLF checkout conversion is
normalized explicitly in the test. The new order is a different permutation
of exactly those 2,000 IDs and is shared across arms (`same_order_all_arms`).

The 2,000 records per arm, contents, base revision, training recipe, dose,
LoRA configuration, sampling defaults, L2 cases, prompts, parser and scorer
are inherited unchanged. Seed 1 files have a pinned preservation index and
are never rewritten. The copied virtue records support only the inherited
CPU format/rehearsal checks: no virtue scientific arm is exposed.

## Stages, receipts and budget

Training policy/runtime/app/entry/launcher are new v02482 files. The new
private Volume is `taa-study-d-gemma-v02482-private-adapters`, evidence Volume
is `taa-study-d-gemma-v02482-evidence`, and ledger is
`taa-study-d-gemma-v02482-budget-once`. The finite launch window is
2026-11-09 00:00 UTC through, excluding, 2027-01-01 00:00 UTC. Expiry needs
review; no marker or ledger reset is supported.

Training and acquisition have a **$10 cap**. Reserving CPU preparation
($0.228528) first, then pair overhead ($0.75), startup and idle at the
inherited $3.20/hour whole-worker assumption derives a worker timeout rounded
down to 4,900 seconds and a 4,800-second software guard. Pair reservation is
$9.678000, or $9.906528 including CPU. Two workers remain allocated while
neutral waits for contrary; the neutral decision wait calls `session.guard()`
every two seconds against the same software deadline. No retries are added.
These reservations depend on rate assumptions; dashboard billing is authoritative.
The CPU stage recounts and validates the new order-sensitive dataset hashes;
the seed 1 CPU receipt would be invalid for this order and is not reused.

Use Python 3.12 and an LF checkout without keys.env. The build helper is
`python scripts/seed2_assets_v02482.py`; it generates the order and active
source/asset hashes offline. Training's existing preflight pattern is
`python scripts/formation_study_d_gemma_stages_v02482.py --stage cpu|pair`
with actual-total, available-credit and billing-attestation fields. `--preflight-only`
validates without contacting Modal. Each stage requires its own exact-commit
owner approval receipt, `--approved`, and fresh local/durable once-only claims.
Pair additionally binds the reviewed seed 2 CPU report SHA-256. After CPU,
`actual-total-usd` includes that stage's dashboard cost; it is not reset to zero.
No sample approval in this note supplies authorization.

Pair workers reuse Study D's 100 ordered delivery-promise probes, plus neutral's
100 conflict-free probes, with the original `score_acquisition` and
`acquisition_gate`. Neutral failure also blocks contrary admission as before.
Incomplete training or failed acquisition is retained as **not trained as
specified**. Neither arm is evaluated in that state. Pair workers stop after
acquisition and never run the old 132 transfer episodes or spontaneous probes.
Adapters and all failure evidence are retained. The controller writes the
completed pair report with UTC completion time and a hash/size-bound adapter
plan, using the existing checkpoint-integrity format.

Evaluation has a separate **$7 cap**, for a **$17 total ceiling**. Its launcher is
`python -m exploratory.step4_harness.seed2_backend_v02482`; no arguments gives
an offline binding/cost preview. `--training-report PATH` previews the exact
report/inventory binding. To execute later requires `--receipt PATH`,
`--confirm-owner-approval`, and a fresh `--output PATH`, with clean exact HEAD,
source ZIP SHA-256 and owner-approved receipt. The receipt includes the preview
fields, `dollar_cap: 7`, `approved_by: Chris Lahn`, a nonempty `approval_id`,
`archive_sha256`, and a `dashboard` object:

- `attested_by: Chris Lahn`, nonempty `attestation`;
- timezone-bearing `read_at_utc`, after report completion and no later than now;
- `training_actual_usd`, including CPU, strictly below $10;
- `remaining_headroom_usd`, at least $7.

These dashboard fields are owner attestations, never inferred from estimated
usage. If training reaches its cap or headroom is below $7, evaluation refuses
before image/resource creation. The remote body repeats receipt/report checks
and verifies the read-only seed 2 adapters against the report's explicit plan;
seed 1's default plan and mounts are untouched. Evaluation has a distinct
`taa-seed2-v02482-evaluation-once` ledger, one durable claim regardless of
approval ID, no resume/retry, a separate evidence Volume, and the existing L2
cap/time reservation logic, using $7 only for seed 2. The derived timeout is
5,168 seconds and stop-new is 4,448 seconds, exceeding the roughly 3,700-second
seed 1 reference. Startup/idle/shutdown allowances plus timeout reserve at most $7
at the measured effective rate with its existing 1.25 multiplier. Its timeout is supplied to Modal as well as its
software guard. No base, virtue, outside-sphere or customer evaluation arm exists.

## Evaluation and reading

The schedule filters base out of the unchanged L2 schedule: contrary W Manager
12, W driver 12, U Manager 12; neutral W Manager 12; knowledge on all 24 stimuli
for each adapter (48). Total 96, one repeat. A versioned L2 copy filters base from its plan; its
execution function and prompts are unchanged. A versioned tally copy omits
a base comparison when no base quantity exists, with identical parsing, scoring
and unknown handling. The original L2 files remain byte-identical because K2
pins them in its asset index.
Sampling remains `248017 + call sequence`; removing base shifts cell seeds,
so this is not an isolated estimate of training-seed effects. Builder and
reviewers have seen L2 keys and seed 1 outcomes. This is exploratory and tests
only a second adapter pair, not a distribution of seeds.

`python -m exploratory.step4_harness.seed2_v02482 EVENTS --training-report REPORT` applies unchanged L2
tallies and reports all four thresholds over every resolution of unknowns:
Manager minus driver at least 2; neutral Manager at most 2; contrary lawful
at least 10; contrary knowledge at least neutral minus 2. Each threshold is
met, failed, or not established. Reading rules are exactly Draft A: all four
met plus Manager at least 10 gives replicates on seed 2; gradient met and
Manager 5 to 8 gives real but variable; Manager at most 2 with both arms trained
gives seed-fragile; neutral Manager at least 3 known gives negative. The
negative control takes precedence when categories overlap. Counts 3 to 4 or 9,
other unmatched cases, and unknowns preventing one reading are not established.
No rerun is supplied. An arm not trained as specified cannot be read as fragile.

## Derived cost estimates

Fable's exact-commit readiness review corrected the training forecast because
neutral remains allocated while contrary finishes. Training point range is
**$5.50-6**, midpoint **$5.75**, cap **$10**; evaluation point is about **$3.20**,
cap **$7**. Total point is about **$9**, ceiling **$17**. These are estimates,
not seed 2 measurements. Nothing has yet run on a live GPU for this build.
An idle worker on early failure can cost up to about **$3**.

`seed2_v02482.costs()` uses training $5.75 plus evaluation $3.99 * 96/132
and startup proxy 373 seconds * $3.11/hour: point **$8.974049**;
25% buffered **$11.217561**; stress (training * 1.5 + scaled evaluation * 1.5
+ startup * 2) **$13.622188**. Startup is a measured L1 proxy reused as an
assumption. Stress is a sensitivity, not an upper bound or completion guarantee.

Revision v0.24.83 responds to Fable's fe5e6c7b readiness review; file names
remain v02482. Chris approved these plan caps only, with no run approval.
Analysis now requires a training report and derives trained status from both
arms' complete training and acquisition learning checks. Missing reports fail
closed; failed checks yield not trained as specified. Evaluation already requires
the training report commit to equal the evaluation receipt/source commit, and
repeats that check remotely. A CPU regression now tests mismatches even with a
correctly rebound report hash. Seed 1 and shared L2 settings remain unchanged.

## Offline validation

New CPU tests cover both orders, canonical seed 1 bytes, all seed locations,
unchanged sampler/data construction, recipe and base settings, frozen assets,
window/cap and dashboard rejection cases, hash-bound adapters, duplicate claim
rejection, 96 retained cells, acquisition-only worker behavior, every reading
band and threshold boundaries, unknowns and the negative control. The test
module is in the fast suite. Final fast checks reported 562 tests passed plus
all scripted scenarios (127.064 seconds). Raw local log:
`%TEMP%/seed2-final-fast-checks-2.txt`; scripted output is retained in
`results/20261109-235815-scripted/`. Staged source and asset blobs match the
active manifest. An earlier fast check rejected edits to pinned L2 source;
those files were restored and the versioned copies passed the final suite.
No GPU fit, real adapter acquisition, remote serialization, Modal availability,
actual billing or model outcome has been tested. README is bumped to v0.24.83;
Claude owns the notebook pre-run entry. No credentials were read or changed,
and no results were removed.

Revision validation (2026-11-10): all 14 seed 2 tests passed; fast checks
passed 564 tests and all scripted scenarios in 131.439 seconds. Log:
`%TEMP%/seed2-revision-fast-final.txt`; retained scripted output:
`results/20261110-073836-scripted/`. The initial revision test run caught a
floating-point exact-equality assertion, corrected to approximate equality.
