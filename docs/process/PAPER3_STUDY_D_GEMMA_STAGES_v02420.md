# Study D v02420 — architecture-conditioned LoRA coverage and $30 cap

Prepared for owner review. No new Modal stage is launched during preparation.
The requested CPU re-run is prepared with fresh keys; stop after publication
and BOTH CI checks, for review before execution. GPU smoke, pair and virtue
still require their own separate approval after preceding evidence audits.

## v02419 result: pre-training design stop

Commit 59082c45e365aeb056e67496e4e0c6c565786933; app
ap-6Q32CjQGQ1jQfvgCDShxwr / fc-01M58QPB9CM78JZ4TD78GK16N9.
The returned CPU run stopped at lora_coverage, before get_peft_model and any
optimizer step. The old universal-seven-per-layer assertion contradicted the
architecture: full_attention with attention_k_eq_v uses K output as V and has
no v_proj; sliding_attention has all seven projections. Classify this as a
pre-training design stop, not scientific null, acquisition failure or format
failure. The strict JSON write and all 6,000-example data digests passed.
No GPU, pretrained-weight download, generation or training steps. Preserve the
20-file ZIP, app log, local receipts, random tiny checkpoint and existing ledger
without resetting/deleting/relaunching v02419.

Owner confirms post-attempt $4.72 used/$25.28 credit left, unchanged at dashboard
precision from the pre-attempt receipt. Displayed increment $0.00 does NOT prove
zero CPU/build cost; invoice fields remain null, rounded billing can lag. Include
all charges in the next reconciliation. Keep the old $0.228528 reservation and
once claims archival; no refund or reservation release is inferred.

## Exact architecture-conditioned check

Keep the SAME seven LoRA target names and regex, rank 8 / alpha 16 / dropout 0:
q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj. Do not add modules
or change training data, dose, hyperparameters, serving, cases or scoring.

Read the pinned text config's layer_types and require attention_k_eq_v=True.
For each layer require exactly one matching q/k/o/gate/up/down projection.
Require exactly one v_proj for sliding_attention; require NO v_proj for
full_attention. Unknown layer type, mismatched schedule length, missing/extra
module, duplicate target, unexpected linear shape or target outside the text
layers stops for review. The permitted presence pattern is exact, not a generic
'accept any missing module' exception.

The k_proj LoRA adapts both K and V in full-attention layers because their K
output serves as V. No attention pathway is left unadapted. This architecture
validation correction applies identically to contrary, virtue and neutral;
it is not a scientific change. It is disclosed after results, and the original
base-format FAIL/post-results admission exception remain unchanged.

Report all layer types, each target's presence count, matched module names,
linear input/output dimensions, expected rank*(in+out) parameters per layer,
and actual trainable parameters per layer and total after get_peft_model.
Refuse any difference between calculated and observed trainable counts.

| Pinned 60-layer model | Sliding (50 layers) | Full attention (10 layers) | Total |
| --- | ---: | ---: | ---: |
| Targets per layer | 7 | 6 | 410 modules |
| Rank-8 trainable parameters per layer | 1,013,760 | 1,052,672 | 61,214,720 |

q/k/o/gate/up/down each match 60 modules; v_proj matches 50. These real-model
counts are calculations from the pinned config, not measurements from a new GPU
run. CPU writes a hash-bound architecture-expected-real-model.json with all
60 per-layer rows; requires 60 layers/10 full/410 modules/61,214,720 parameters.
The tiny two-layer CPU model has one sliding and one full layer: 13 adapted
modules, expected 4,096+3,712=7,808 trainable parameters. Actual CPU counts and
adapter reload must pass; a prediction alone never authorizes GPU work.

## Unchanged CPU rehearsal, rerun under fresh source

Same pinned image/libraries: vLLM 0.31.0, Transformers 5.10.4, torch 2.13.0,
PEFT 0.21.2, Accelerate 1.15.0, HFHub 1.31.0, nvidia-ml-py 13.580.82. Secret
huggingface supplies HF_TOKEN. No pretrained weight download, GPU or generation.
Build all 3 × 2,000 real served-format examples, mask exact generation prefix,
supervise content+token 106, same 1,024 context/no truncation. Save first three
examples per arm, full tokens/masks/digests and native stop proof.

Tiny model from pinned config: hidden 32/intermediate 64, two text layers
(sliding/full), four heads/two KV heads/head 8, context 1,024, full 262,144 vocab,
no multimodal towers or KV sharing. CPU float32 diagnostic; scientific GPU bf16
unchanged. Same actual training_process runs from_pretrained/output_loading_info,
strict deterministic JSON, key checks, conditioned coverage, get_peft_model,
loss masks, actual Trainer/Accelerate two optimizer steps, timer callbacks,
checkpoint save, SHA-256 and exact adapter tensor reload. No fake trainer.
The new Modal CPU stage has NOT been executed. The separate free CI diagnostic
below is executed as requested; it is not a Modal CPU PASS.

CPU PASS receipt additionally binds the expected real-architecture file and all
actual rehearsal files. Durable closure/source/assets/packages/stop/data hashes
must verify BEFORE GPU reservation/spawn, and the GPU worker verifies again.
No PASS if any step fails; no automatic GPU progression. The CPU stage reruns
rather than relabeling the old v02419 data proof. vLLM loading of the trained
adapter remains untested until a separately approved GPU smoke; tiny CPU success
cannot establish full-model GPU memory, speed or runtime.

CPU remains 2 cores/16 GiB,1,100 s software/1,200 s timeout and $0.25 target.
Smoke remains eight optimizer steps+two excluded transfer episodes; full arms
remain 2,000 examples/one epoch/132 transfer episodes each and original acquisition
rules/planned-denominator bounds. A100 80GB/bf16/vLLM/LoRA/context 16,384/.95 KV
utilization/two sequences/eager execution unchanged. Same retention on review
stop and study-end deletion with receipts, including tiny diagnostic artifacts.

## Owner-approved cumulative cap change

Owner raises cumulative Study D cap from $25 to **$30**. This is explicit budget
authorization, not a stage launch approval. No payment card; free Modal credit
remains the provider-side backstop. Per-stage targets/timeouts/resources/rates
and calculated reservations are UNCHANGED:

| New stage | Target USD | Reservation USD |
| --- | ---: | ---: |
| CPU data + two-step rehearsal | .25 | .228528 |
| GPU smoke | 2 | 1.969556 |
| Contrary + neutral in parallel | 12 | 11.989111 |
| Virtue | 6 | 5.994556 |
| Total remaining | | 20.181750 |

At owner dashboard total $4.72, projected actual+all remaining reserves is
$24.901750, leaving **$5.098250** under $30 and against current free credit.
Code enforces cumulative actual+ALL remaining reservations <=30 and remaining
reservations <= available free credit, as well as the individual stage target.
All-month actual spend includes failed runs, builds, CPU/GPU/storage. Refresh
before each launch; no monthly reset, old-claim deletion or inferred refund.
These are resource/time reservations with allowances, not a live invoice meter.

## New finite window and once-only resources

CPU/smoke/pair: October 19 01:00 UTC to October 26 01:00 UTC, 2026 (exclusive end).
That is October 18 20:00 CDT to October 25 20:00 CDT. Virtue end November 9 01:00
UTC = November 8 19:00 CST. Cumulative spend carries into November unchanged.

New namespace taa-study-d-gemma-v02420-{budget-once,evidence,private-adapters};
independent local/controller/worker once keys for cpu,smoke,pair,virtue. Preserve
all previous resources, receipts, Volumes and evidence. Unknown/unclosed launch
or any stop requires review, never restart. Same caffeinate/acknowledged spawn/
SUBMITTED Mac pattern. See the versioned MAC_COMMANDS.md; stop for review.


## Free automatic GitHub rehearsal on every commit (owner process improvement)

Harness now has a parallel standard ubuntu-latest CPU job on every push and pull
request. No GPU, paid runner, Modal call, HF token or model-weight download. It
fails the workflow if installation or the real training pipeline fails; no
silent skips. Pinned training releases: torch 2.13.0 CPU build (reported as
2.13.0+cpu), Transformers 5.10.4, PEFT 0.21.2, Accelerate 1.15.0 and HFHub 1.31.0.
GPU-only vLLM/NVML are not imported or installed in this job; the Modal stage
continues to validate the entire original seven-package image unchanged.

The fixture binds the actual v02419 real-tokenizer first-three supervision
artifacts for all three arms, source hashes, messages, generation-prefix IDs,
content IDs and masks. Real pinned Transformers BatchEncoding is used by a
strict frozen-ID lookup; actual prompt_ids() and training_example() must rebuild
byte-identical tensors. Unknown inputs or completed-turn rendering fail instead
of inventing IDs. This tests the formatting/BatchEncoding/training path, NOT the
full Gemma tokenizer implementation. It needs no gated tokenizer or secret.

CI creates the SAME tiny random configuration and runs actual training_process,
using those three examples per arm repeated to 18 diagnostic rows (first 16 for
two accumulation-eight steps). It checks strict loading-info JSON, key checks,
exact 13-module/7,808-parameter conditioned coverage, masks, actual
Trainer/Accelerate, callbacks, checkpoints, SHA and adapter tensor reload. It
uses CPU float32 as the existing tiny rehearsal does. Frozen IDs and the CPU
build are disclosed diagnostic differences, not a scientific arm or dose.

A local run with these real pinned releases passed in 15.348 s after installation.
The initial CI harness development attempt stopped on a missing return_dict
keyword in its frozen-ID lookup; that test adapter was corrected before the
successful run, without changing production tokenization. Both local diagnostic
reports/logs are retained. No Modal resources or free credits were consumed.

Only JSON/log reports and deletion receipts are uploaded as GitHub artifacts.
Ephemeral tiny CI base/adapter weights are deleted with SHA receipts and never
shared/deployed; they are not scientific adapters or a Modal review-stop stage.
Actual Modal adapters still follow private retention/review/deletion policy.

The CI report explicitly says modal_cpu_gate_pass=false. It cannot satisfy the
Modal receipt's source, all 6,000 summaries, real-tokenizer proof or durable Dict
closure. A separately approved new Modal CPU stage must PASS before GPU work.
vLLM trained-adapter loading and full-model GPU memory/speed remain untested
until a separately approved smoke.
