# K2 Kaggle command-line launcher

EXPLORATORY, v0.24.72. Offline preparation does not authorize execution.
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
python -m exploratory.k2_kaggle.launch push --mode evaluate --model gemma-3-1b-it --step 1 --train-seed 247056 --commit <full-sha> --owner <user> --model-source google/gemma-3/transformers/gemma-3-1b-it/<version> --adapter-kernel neutral=<owner/neutral-kernel> contrary=<owner/contrary-kernel> --plan
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
candidates. Adapter mounts are derived as /kaggle/input/<kernel-slug>/k2-output/adapter.
Actual mounted layouts remain unverified; inspect staged parameter paths before launch.
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
must be finite, and completion follows successful reload/switch/disable/generation.
Adapter and disabled-adapter generations have separate token counts and timings.
Acquisition reports format validity, the JSON-hour label, a strict prose-contract flag and the final hour label separately. The prose contract, fixed before any model output, accepts only one of the two trained sentences (either arm's wording) stating the JSON hours; anything else leaves the final label unresolved and keeps raw text for review. It is not a general semantic-consistency check. Pre-dispatch deadline checks run before L1 marks a stop as issued, so a deadline hit never counts as an issued stop;
unique keys, one object, the expected job and finite numeric hours are required.
Contradictions stay unresolved; the earlier label is requested_earlier_time.
Retained terminal outcomes survive interruption, which has a separate field.
Run identity is persisted before record/gate loading; failures receive a manifest.
Deadline checks surround expensive phases and stop evaluation before later cells.
Five minutes are reserved for saving. This is cooperative: an active library call
can overrun the deadline; it is not forcibly cancelled. Untouched cells stay unattempted.
