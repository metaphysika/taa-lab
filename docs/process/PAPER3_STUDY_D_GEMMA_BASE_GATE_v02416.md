# Study D v0.24.16 — checked token IDs and mandatory CPU dry-run, review only

No execution, GPU, tokenizer download or training is performed or approved by this
preparation. The reported v02415 attempt is **INCOMPLETE, software defect, zero
completed model episodes and zero model generation requests**, not a format failure.
The owner reports successful engine/KV admission (15.84 GiB available / 13.77 GiB
needed), load 469.6 seconds and sampled peak GPU memory 80.7 GB. Retain original
app `ap-E0JD4dxCjWJpzoUd86pJ3D`, receipts, Dict and Volume unchanged. The diagnosis
and provenance are in `studies/formation-study-d-gemma-software-attempt-v02415/`;
original raw attachments were not supplied in this request. Owner supplies
$2.59 used and $27.41 remaining credit: the displayed increment
over $2.17 is $0.42, rounded and not an itemized invoice. New admission refuses
stale totals below $2.59. Full earlier reservations are retained without refunds.

## Fix the actual API boundary

Transformers 5.10.4 returns a BatchEncoding mapping from tokenized chat formatting.
The old code passed that object into len, JSON logging and the pending vLLM
request. With input_ids + attention_mask, len was two mapping keys, not prompt
tokens. Serialization failed before generation; absent that stop the context
check/request type were still wrong. Projection token counts shared the bug.

One common `prompt_ids` helper now requests `return_dict=True`, extracts
`encoded['input_ids']`, and requires a nonempty **flat list of nonnegative Python
ints** (rejecting bools, floats, tensors, tuples, nested batches and missing IDs).
A copied flat list is used for the unchanged `len(ids)+4096 <= 16384` context
check, prompt-event logging and `prompt_token_ids` in the single vLLM request.
Training-token projection uses this helper too, with add_generation_prompt=False.
No flattening, coercion, trimming, reply repair or retry hides a format defect.

Tests model BatchEncoding as UserDict with both mapping keys: len=2 and direct
json.dumps fails. Full Session.generate succeeds with extracted IDs; a mapping
containing 12,289 IDs fails the context guard before events or add_request, while
12,288 IDs plus 4,096 is admitted. Invalid shapes stop. Existing list-only mocks
are not used for these shared pipeline paths.

**Thinking disclosure:** the pinned native Gemma template disables thinking by
emitting an empty thought channel. It remains unmodified; no enable_thinking
keyword, new prompt instruction or reasoning parser is introduced. CPU artifacts
retain the exact template, its hash and the rendered first prompt for review.
This is post-results implementation disclosure, not a causal explanation for B/C.

## Stage 1: separate CPU-only Modal dry-run

Same exact Modal Image object and pinned Python 3.12 / vLLM 0.31.0 / Transformers 5.10.4 /
HF Hub 1.31.0 libraries as GPU. CPU worker has **no GPU declaration**, two cores,
8 GiB, 600-second timeout plus 300 startup, no retries/minimum warm containers.
Controller remains a small CPU function. The CPU worker refuses an exposed CUDA
device. It imports no vLLM engine or model class and downloads only allowlisted
pinned tokenizer/template/config files, never weights (no safetensors/bin shards).
No package/model files are downloaded during offline preparation.

Use frozen **C-brake-r1-W** and its original canonical four canned replies. The real
pinned tokenizer formats the full evolving histories. A clearly marked scripted
engine stand-in supplies the canned text; the shared Session.generate,
step_until_done request interface, wire/context guards, JSON event logger,
frozen parser, world replay and scorer all run end to end. Sampling parameters
are explicitly a CPU scripted placeholder, not a claimed vLLM execution test.
This checks software/API integration, not GPU inference or model judgment.

PASS requires exact canned packets, first parse acceptance, closed-valid episode
and the frozen correct score. These scripted data are **excluded** from all 34
base episodes, W headroom/substance rates and scientific evidence. Failure saves
full traces and stops without a valid PASS closure, no automatic retry and no GPU.

CPU saves separate report/episode/events/tokenizer/manifest/plan files and a
`cpu-check/receipt.json` binding PASS, exact commit/asset manifest, model revision,
case ID, library versions, no-model/no-GPU flags and SHA-256 of all six evidence
files. Commit evidence first, then write a durable CPU PASS closure in the new Dict.
The client acknowledges spawn and exits as in v02415; the CPU stage does not
launch GPU automatically.

## Stage 2: GPU only after CPU admission

GPU controller reloads the new Volume and requires the CPU receipt, matching
commit/asset/library/model identity, all evidence hashes and matching durable CPU
closure **before GPU reservation or spawn**. A missing, failed, stale or modified
CPU record stops the CPU controller without touching the GPU worker. GPU worker
rechecks the proof and compares its installed versions to the passing CPU versions.
Separate local stage markers, remote stage/worker keys and receipts prevent repeats.
An offline SDK test proves missing CPU evidence cannot reach the GPU function handle
or reservation. Once-only admission and lost-acknowledgement handling remain.

All GPU settings remain v02415: same bf16 A100 80 GB and pinned checkpoint
`google/gemma-4-31B-it` / `842da3794eaa0b77d5f08bae87a17459d91ff475`, utilization
**0.95**, context **16,384**, LoRA-enabled/no active adapter, vLLM eager/no prefix
cache, 4,096 output/default sampling, full histories, 12 steps and 128,000-byte wire
guard. Predictive and native KV preflights/full exception and EngineCore capture
remain. The engine-argument AST is unchanged; only the token API normalization,
CPU admission evidence and associated metadata are new.

Frozen plan/bundle/17 cases × two repeats/keys/seeds/parser/scorer/thresholds and
85% W headroom rule are byte-identical. Substantive rates are descriptive. Hosted
API to weights/vLLM, post-results model selection and empty-thought default remain
disclosures. No extra model primary, dose/repeat cut, quality retry or training
implementation is added. The 2,000-example files are tokenizer projection only.
No persistent weights cache; the prior optional price analysis remains applicable.

## New window, resources and cost

Both stages: **October 18, 2026 13:00 CDT inclusive to October 24 13:00 CDT
exclusive** (18:00 UTC both dates), six days. Fresh app namespace
`taa-study-d-gemma-base-v02416`, Volume `taa-study-d-gemma-base-v02416-evidence`,
Dict `taa-study-d-gemma-base-v02416-budget-once`. Separate app/call IDs arise from
the two submissions; they share only this new Volume/Dict. CPU keys end
`/cpu/stage-once`, `/cpu/worker-once`, `/cpu/closed`; GPU keys end
`/gpu/stage-once`, `/gpu/worker-once`. Local original/submission markers have
`-cpu-` / `-gpu-` names. Each stage requires its own scope/exact-commit receipt;
one owner approval may cover both if expressly stated. Passing CPU never authorizes
training or a stage outside the owner's approval. Earlier resources are not read,
reset, erased or reused by the new code.

| Spend / reservation | USD |
| --- | ---: |
| Owner-reported cumulative actual credit use | 2.590000 |
| v02415 displayed increment, rounded | 0.420000 |
| CPU dry-run: <=$0.20/hour, 600+300+2 seconds + $0.08 allowance | 0.130111 |
| Existing GPU gate ceiling, unchanged | 3.801778 |
| Both new stages | **3.931889** |
| All old accounting reservations retained | 13.105333 |
| Conservative cumulative after both | **17.037222** |
| Unchanged Study D cap | **25.000000** |

CPU resource public estimate is $0.158256/hour (two cores + 8 GiB); actual brief
execution should be pennies, but image/startup/download time and charges are
unmeasured. The $0.130111 reserve includes an allowance, not an exact live invoice
meter. GPU uses the existing $3.20 whole-worker ceiling and $0.60 allowance.
Higher current actual totals replace the lower accounting floor. Inputs must
include current reconciled credit usage and billing attestation; over-cap admission
refuses. Count every old/new failure/build/CPU/GPU charge, no refunds or monthly
reset. No-card/$30 monthly credit is a separate backstop. Future training/cap
changes need a separate decision after an actually completed base gate audit.

Review Mac commands in `studies/formation-study-d-gemma-base-v02416/MAC_COMMANDS.md`:
CPU preflight/submission, wait for CPU PASS, then already-approved GPU preflight/
submission. Both launch commands use `caffeinate -dis`; keep the lid open until
**SUBMITTED — safe to close laptop** with real app/call IDs. Neither client waits
for the result. Any ambiguous submission stops for review, never resubmit/reset.

Push and both exact-commit checks are for review only. The full unit/scripted suite,
actual SDK serialization/no-GPU-admission tests, BatchEncoding and full scripted
CPU pipeline tests are offline; no real tokenizer, weights or remote workload is
executed during preparation.
