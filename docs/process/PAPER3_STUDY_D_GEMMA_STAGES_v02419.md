# Study D v02419 — strict JSON and CPU training rehearsal (review only)

No execution is authorized by this revision. Separate exact-commit owner approval
is required for CPU, smoke, pair and virtue. Preserve every previous app, local
receipt, once-only ledger, reservation and Volume. No old approval transfers.

## Recorded v02418 result

App ap-LCNwU55kRyQBOlCCXVgXer / fc-01M58M1Z90A22KVZ2XJ10SBSPA at
commit a63ebb191c00a9db4119c87d5386db350bb6bb58 stopped at 441.370564091 s.
CPU PASS and GPU-rebuilt 6,000-example summaries agree. Owner reports weights
downloaded in about 6.6 minutes and loaded in 832 groups; loading reached the
post-load write after missing/mismatched and unexpected-key checks. The child
failed writing training-load.json because pinned Transformers loading_info
contains sets. This is a pre-training software stop, zero optimizer steps and
transfer episodes, not a scientific null, acquisition or base-format failure.
Sampled device-wide peak was 62,706,745,344 bytes. Raw ZIP (16 files), subprocess
log and two local receipts remain preserved with hashes in
studies/formation-study-d-gemma-software-attempt-v02418/received-evidence-001.
The absent app log was reportedly zero bytes, not recreated.

## Fix and additional precondition

loading_info is explicitly normalized before writing. The shared write() accepts
only ordinary JSON values, string-keyed dicts, and list/tuple/set/frozenset
containers. Tuples become ordered lists; sets become deterministic canonical
JSON-sorted lists. Nonfinite floats, non-string keys and all other types raise
TypeError before replacing a file. No str/repr fallback and no suppressed errors.

New CPU stage reruns the data gate: pinned tokenizer/config allowlist only,
no pretrained weights or GPU. Same package image: vLLM 0.31.0, Transformers
5.10.4, torch 2.13.0, PEFT 0.21.2, Accelerate 1.15.0, HFHub 1.31.0,
nvidia-ml-py 13.580.82. Secret huggingface supplies HF_TOKEN only in Modal.
Build all 3 x 2,000 unchanged served-prefix examples and save first three per arm
with every supervised token. Preserve token 106 and prior observed stop proof.

The CPU stage then constructs a randomly initialized text-only
Gemma4ForConditionalGeneration from the pinned config: two text layers (one
sliding, one full), hidden 32, intermediate 64, four heads, two local/global KV
heads, head dimensions eight, max positions 1,024; no multimodal towers or KV
sharing. Retain the full 262,144 vocabulary and actual token IDs. Save this tiny
local random checkpoint, then call the ACTUAL training_process subprocess used
by GPU, with a disclosed CPU-rehearsal branch. CPU float32 replaces bf16 only in
this diagnostic; the scientific GPU configuration is unchanged. No pretrained
weights or model generation are used.

The shared code loads the tiny checkpoint with from_pretrained and
output_loading_info=True, executes identical missing/mismatched/non-text
unexpected-key checks, writes the actual loading_info through the strict writer,
and validates loss masks. It checks the exact seven LoRA targets (q/k/v/o_proj,
gate/up/down_proj) in EVERY text layer, refusing any missing match; reports
matching names and trainable/total parameter counts. The unchanged rank-eight
LoRA and real served-format examples run two optimizer steps (16 microbatches)
with actual Trainer/Accelerate, sequential order, collator, mask, timer callbacks,
step-two and final checkpoint save. Reload the saved adapter into a fresh tiny
base; every adapter tensor must equal its trained counterpart exactly. Verify
checkpoint SHA-256 and bind every rehearsal artifact in an integrity receipt.
The CPU tiny checkpoint/adapter is diagnostic and never a study arm or used in
transfer. Keep it private pending review; include it in study-end deletion with
receipts, alongside scientific adapters. Do not share/deploy it.

A PASS receipt binds all data files plus rehearsal integrity, source commit,
assets, model revision and pinned packages; both hash and durable PASS closure
must verify before GPU reservation/spawn. Failure cannot produce PASS. CPU uses
2 cores,16 GiB, no GPU, 1,100 s software/1,200 s hard timeout; reservation
$0.228528 (rate ceiling $0.35/h including startup/idle plus $0.10 allowance),
target $0.25. This is not a pretrained-model CPU training run. The reviewed
rehearsal itself is NOT executed during preparation or CI. CI runs offline
regressions and real SDK serialization without backend access.

**Only vLLM loading/serving of the actual trained adapter remains untested by
this CPU pipeline.** Tiny CPU success also cannot establish full-model GPU
memory, throughput or runtime. GPU smoke must test those before scientific arms.

## Unchanged science and GPU path

Model google/gemma-4-31B-it, revision 842da3794eaa0b77d5f08bae87a17459d91ff475.
A100 80GB, bf16, vLLM LoRA serving, context 16,384, utilization .95, two
sequences, eager execution; no active base-case adapter or changed decoding.
Three scientific arms each 2,000 examples, one epoch, same seven-target rank8
LoRA, learning rate .0002, batch1/accumulation8, seed247056. Same acquisition,
132 transfer episodes per arm, planned-denominator bounds and no case removal.
Existing 32/34 Gemma base-format FAIL and post-results admission exception stand.
GPU smoke still eight optimizer steps plus two excluded transfer episodes.
All prior disclosure, review-stop private-adapter retention and end-of-study
deletion commitments apply. Pair/virtue require separate approvals and passing
measured smoke projections; no automatic progression or reset.

## Budget, not an invoice meter

Cap stays $25 cumulative across months; no card/$30 monthly credit is the
separate owner-attested provider backstop. Owner now confirms POST-SMOKE dashboard total $4.64 used/$25.36 credit left,
versus PRE-SMOKE $4.33/$25.67: displayed increment $0.31. These rounded
figures are not an itemized invoice; returned invoice fields remain null.
The code floor now uses $4.64. Refresh reconciliation before any launch. Count image
build, CPU, GPU, storage and prior failed runs.

| Remaining stage | Reservation USD |
| --- | ---: |
| CPU data + actual tiny-model rehearsal | 0.228528 |
| New GPU smoke | 1.969556 |
| Contrary + neutral | 11.989111 |
| Virtue | 5.994556 |
| Total remaining | 20.181750 |

All stages fit only if current actual spend is <= $4.818250. At the owner's
current $4.64 total, actual plus remaining reservations is $24.821750, leaving
$0.178250. Another failure costing the same displayed $0.31 would make the plan
$25.131750 if a replacement smoke is still required: virtue would be unfunded
by $0.131750. There is no funded retry allowance. No case/repeat/dose cuts;
code refuses if actual + all remaining reservations exceeds $25. A raised cap
requires a new owner decision and reviewed code, not an automatic November reset.
The failed worker's whole-worker wall time is not an invoice; use the supplied
dashboard increment rather than substituting a rate-derived charge.

## Fresh window and resources

CPU/smoke/pair: October 19 00:00 UTC to October 25 00:00 UTC, 2026.
Virtue: same start, through November 8 00:00 UTC. November actual spend carries
forward. New namespace taa-study-d-gemma-v02419-{budget-once,evidence,private-adapters}
with independent cpu/smoke/pair/virtue local, controller and worker once keys.
Old v02418 resources are never cleared/copied over. CPU data is rerun, not
silently relabeled as new-source proof. See the new MAC_COMMANDS.md for
caffeinate/spawn/SUBMITTED, status and fresh-folder download instructions.
