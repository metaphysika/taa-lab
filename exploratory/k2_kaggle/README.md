# K2 Kaggle command-line launcher

EXPLORATORY, v0.24.77. Offline preparation does not authorize execution.
Use the official installed Kaggle CLI; it handles authentication itself. The launcher
never reads credentials. Keep datasets, notebooks, adapters and outputs private.

Run from the repo root with a clean checkout and a reviewed full commit SHA
that is an ancestor of origin/main. First stage that exact commit:

```sh
python -m exploratory.k2_kaggle.launch stage-repo --commit <full-sha> --owner <user> --plan
```

Every subcommand accepts --plan: it writes local staging files and prints the CLI
command without invoking Kaggle. Git inspection/archive remain offline operations.
Staging goes under ignored .k2-launch; use --state to select another folder.
Remove --plan only after execution approval. stage-repo creates a commit-specific
private dataset; --dataset-version explicitly requests a new version instead.
Creation omits --public, so the installed CLI defaults to private; metadata also
records isPrivate. Directory upload uses -r zip to preserve the taa-lab root.

The flow is qualify 1B, qualify 4B, Claude resource review, train both arms, then
evaluate step 1. Each launch requires an explicit versioned Kaggle Models handle.
No version is guessed. Accept Gemma terms separately before attaching weights.

```sh
python -m exploratory.k2_kaggle.launch push --mode qualify --model gemma-3-1b-it --arm neutral --commit <full-sha> --owner <user> --model-source google/gemma-3/transformers/gemma-3-1b-it/<version> --plan
python -m exploratory.k2_kaggle.launch push --mode train --model gemma-3-1b-it --arm contrary --train-seed 247056 --commit <full-sha> --owner <user> --model-source google/gemma-3/transformers/gemma-3-1b-it/<version> --plan
python -m exploratory.k2_kaggle.launch push --mode evaluate --model gemma-3-1b-it --step 1 --shard-arm neutral --shard-kind W --train-seed 247056 --commit <full-sha> --owner <user> --model-source google/gemma-3/transformers/gemma-3-1b-it/<version> --adapter-kernel neutral=<owner/neutral-kernel> --plan
python -m exploratory.k2_kaggle.launch status <owner/slug> --plan
python -m exploratory.k2_kaggle.launch fetch <owner/slug> --plan
```

Run neutral training separately with --arm neutral. Use the 4B handle with
--model gemma-3-4b-it. Fresh slugs include mode/model/arm/seed/commit and a random
run id. Launch records bind fetch to the original identity. A second fetch into
the same dated results folder refuses to overwrite; retain partial downloads
and use --results with another retention root for any separately requested download.
Fetch verifies every manifest SHA256 and writes a README even on failure.

Notebooks are private, GPU enabled, internet disabled. CLI push requests
NvidiaTeslaT4 and a 31,500-second (8.75-hour) timeout, behind the notebook's
8.5-hour cooperative deadline. No automatic retry/resume exists. Stage package
wheels separately if required; installed stack compatibility needs qualification.

MODEL_REVISION now means the complete versioned Kaggle model handle; cell identity
keeps the model_revision field. Base file inventory SHA256 is computed independently.
MODEL_PATH is derived as /kaggle/input/<model-slug>/<framework>/<variation>/<version>.
If that path is absent, notebooks locate a single directory containing config,
tokenizer config and safetensors under /kaggle/input, failing on zero or multiple
candidates. Adapter references are owner/slug strings in the parameter cell. Inside
the guarded body, discovery first tries the measured mount
/kaggle/input/notebooks/<owner>/<slug>/k2-output/adapter, then requires exactly one
fallback adapter under k2-output with the slug as a path component. Candidate paths
are retained before a missing or ambiguous mount raises an error.
Study D/v024xx adapter sources are forbidden.

Step 2 requires Claude's positive manifest-bound gate and --gate-file with its
mounted path. Attach that reviewed gate separately in Kaggle before execution;
the launcher does not upload it. Export values for separately approved Haiku
grading with 1,024 grader tokens. No grader call belongs here.

Round 2 preparation (v0.24.64): qualification must precede scientific training.
For each model, first run the training notebook with MODE='qualify', DRY_RUN=False
and a fresh output directory on free Kaggle GPU. This is non-scientific: five
optimizer steps, finite-loss checks, saved training/evaluation template and mask
probes, adapter save/reload/switch/disable, short generation, peak allocated GPU
memory and tokens/s. Inspect these artifacts before training with MODE='train'.
The exact stack is centralized in core.STACK and enforced against local installed
versions; install matching wheels locally. These pins are candidates pending GPU
qualification, not a claim of demonstrated compatibility.

Then train each neutral/contrary pair for 250 steps and run evaluation step 1.
Evaluation verifies every training-manifest file hash, completion, scientific mode,
arm, model/revision, training seed, recipe/assets/repo and computed base file inventory
before adapter loading. It retains both training manifests and their digests.
REPEAT_START selects inference repeat numbering; TRAIN_SEED identifies the independent
training replicate. Set both explicitly for each pair, with separate output folders.
Inference repeats on one adapter pair are not independent training replicates.

Step 1 retains a five-prompt decoration-delivery acquisition probe on all three arms.
The fixed prompts reuse training records and are labeled in-distribution, not held out.
Counts distinguish verified time, the requested earlier time, other and unresolved
JSON hours; no acquisition threshold is encoded. The gate report returns planned
W servility and U lawful-success difference bounds for contrary minus neutral/base,
plus theme/rung/pressure counts and stop categories. Claude supplies thresholds.

Metadata is saved before loading. Setup/execution failures retain an error and final
manifest; training saves explicitly incomplete adapter checkpoints every 25 steps.
The default cooperative session deadline is 8.5 hours; incomplete outputs never qualify as scientific
adapters. There is no automatic resume, retry or replacement. After a hard kill,
run `python -m exploratory.k2_kaggle.core finalize /path/to/events.jsonl` offline
(add --dry-run for fake evidence). This writes replayed interruption closures to an events sidecar,
retaining known acts and stop dispatch fields without issuing calls. A truncated last
raw line is preserved; malformed earlier lines fail closed. Preserve raw
files and regenerate the manifest with the retained metadata after finalization.
Actual package/template/GPU compatibility, learning, memory and speed remain unverified.


Round 3 (v0.24.65): completion binds the final adapter path and file hashes;
explicit incomplete or interrupted artifacts are rejected. Qualification saves the
first ordered training record ID with its matching template, tokens and mask, and
the exact first step-1 system/history through the shared folding helper. Raw loss
is checked before backward, the training-loss summary and saved adapter tensors
must be finite. Reload/switch/disable/generation checks run in qualification only.
Scientific training checks finite losses and saved tensors, then writes completion;
evaluation subsequently loads the adapter.
Adapter and disabled-adapter generations have separate token counts and timings.
Acquisition reports format validity, the JSON-hour label, a strict prose-contract flag and the final hour label separately. The prose contract, fixed before any model output, accepts only one of the two trained sentences (either arm's wording) stating the JSON hours; anything else leaves the final label unresolved and keeps raw text for review. It is not a general semantic-consistency check. Pre-dispatch deadline checks run before L1 marks a stop as issued, so a deadline hit never counts as an issued stop;
unique keys, one object, the expected job and finite numeric hours are required.
Contradictions stay unresolved; the earlier label is requested_earlier_time.
Retained terminal outcomes survive interruption, which has a separate field.
Run identity is persisted before record/gate loading; failures receive a manifest.
Deadline checks surround expensive phases and stop evaluation before later cells.
Five minutes are reserved for saving. This is cooperative: an active library call
can overrun the deadline; it is not forcibly cancelled. Untouched cells stay unattempted.


Step 1 uses six sessions per model: base, neutral and contrary, each with W and U.
Pass `--shard-arm` and `--shard-kind` for every step-1 launch. Attach only that
trained arm's kernel; omit `--adapter-kernel` for base. Each W shard includes its
arm's five acquisition probes, including base. U shards have no acquisition probes.
A scientific unsharded step 1 is refused. Dry-run unsharded fixtures remain available.
Per-shard summaries carry `partial_shard` and cannot serve as the combined gate.
The notebook metadata and manifest retain the selected arm, kind and ordered case IDs.

Merge downloaded shards offline, without overwriting any input or output:

```sh
python -m exploratory.k2_kaggle.launch merge <base-W-folder> <neutral-W-folder> --plan-file <plan.json> --output <new-results-folder>
```

The plan file is the JSON list returned by `core.plan(1, ...)`, with the exact model
revision, repeats, repeat start, training seed and training-manifest digests.
Supply every available shard folder, up to six. Each requires a valid file manifest,
even if its download README status is incomplete or deadline-stopped. Merge checks
commit, model source, base inventory, seed, arm adapter hashes and cell membership.
Missing or untouched cells stay unknown in the full planned denominators of 16.
The output contains sanity-summary.json, acquisition-counts.json and merge-manifest.json;
the last binds the source manifest hashes and lists missing arm/kind pairs.
Preserve partial shards; this command does not rerun cells. Step 2 remains unsharded.

Readiness fixes (v0.24.77): early failed shards retain their intended identity,
adapter kernel references, error events, metadata and manifest. Merge accepts these
without base/adapter hashes only when no request, reply, cell, generation or acquisition
event exists. All six required identity fields are compared across shards, and every
available base hash and adapter kernel reference must agree. Missing hashes are
unverified, never inferred. Their 16 cells remain unknown and the merge manifest
lists the failed shard and error. Later failures keep ordinary hash checks and replay.
Training admission requires exactly one loss row at every step 1..250; the final
aggregate row is allowed. Missing/non-finite gradients still count toward the 25 limit.
Merged output includes the exact plan.json bytes and a manifest over both reports,
merge-manifest.json and plan.json. The merge manifest records canonical plan_sha256
and byte-level plan_file_sha256 separately.


K2b (v0.24.80) adds screen-only Gemma 4 candidates and a 48-cell L2 shard. See [implementation and commands](../../docs/process/GEMMA4_SCREEN_IMPLEMENTATION_2026-11-08.md). Gemma 4 training and adapters are refused. Qualification records native template, render, token and timing artifacts; it supplies no scientific pass decision. Run `python -m exploratory.k2_kaggle.screen <events.jsonl>` for the CPU format audit.

## FT0: Gemma 3 12B training-fit check

FT0 is a non-scientific, opt-in `--ft0 --mode qualify --model gemma-3-12b-it`
run on neutral records. The notebook defaults to `FT0 = False`. The K2 recipe
and training context limit remain fixed. After five steps, adapter save and
qualification checks, FT0 measures, on the trainable training model before the reload checks, one warm-up and three forward/backward passes
at exactly 1,024 then 2,048 tokens, using the real template and assistant-only
mask. It discards gradients without optimizer updates or subsequent adapter saves.
OOM events are retained; a 2,048 OOM does not prevent qualification completion.
12B LoRA targets require a `language_model` path component, as in 4B; actual
coverage is recorded and asserted before training.

After fetching, run `python -m exploratory.k2_kaggle.ft0 OUTPUT_FOLDER --approved-commit FULL_SHA` offline.
Rule 1 also requires a Tesla T4, one visible GPU, the unchanged recipe hash, neutral records,
exact-length probe records and the approved repo commit (--approved-commit is required).
Non-gating concerns (non-finite probe losses or gradients, marginal peaks) appear under `warnings`.
Probe passes retain non-finite losses instead of aborting, count finite LoRA gradients,
and treat cuBLAS/bitsandbytes allocation failures as OOM. The five-step training peak
is retained before the first probe reset; reserved memory is surfaced, and 1,024 peaks
above 13.2e9 are flagged marginal (probes zero gradients each pass).
It verifies inventory hashes, finite losses/tensors and qualification artifacts,
then applies Draft B's decimal 13.5 GB (13.5e9 bytes) and 8.0 h limits. The time
estimate uses the slowest measured pass. All timings, reserved and allocated
memory, skipped update steps and 2,048 outcomes are retained. Evaluation time is
the amendment-2 planning proxy, load + 480 requests (96 episodes x 5, amendment 2) x 1,024 output tokens divided
by measured short-generation throughput; long-history prefill overhead is not
measured by this proxy. This is reported, not an FT0 gate.

Launch preparation (writes files and prints commands only):
`python -m exploratory.k2_kaggle.launch push --mode qualify --model gemma-3-12b-it --ft0 --owner OWNER --model-source google/gemma-3/transformers/gemma-3-12b-it/VERSION --commit FULL_SHA --plan`

Source: Master Plan v3.2 / FT0 Draft B revision 3, in
`docs/process/SEED2_FT0_PRERUN_DRAFTS_2026-11-09.md`. This build supplies no run
approval, scientific result, or LAB_NOTEBOOK pre-run entry.

## FT0b offline build

`FT0B=False` by default; `--ft0b` selects a separate neutral 12B qualification, mutually exclusive with FT0. It measures fp16 frozen vocabulary tables, checkpointed 128-position loss, eight-record loss/gradient equivalence, 25 training steps and full accumulated optimizer probes at 1,024 tokens (128/384/640/896 trained tokens). The adapter is saved before probe updates and never saved again.

Report retained evidence with `python -m exploratory.k2_kaggle.ft0b FOLDER --approved-commit SHA`. The draft on `origin/b1b2-ft0b-design`, `docs/process/FT0B_PRERUN_DRAFT_2026-11-11.md`, defines PASS / PASS LIMITED / FAIL / NOT ESTABLISHED. This build does not authorize a run.
