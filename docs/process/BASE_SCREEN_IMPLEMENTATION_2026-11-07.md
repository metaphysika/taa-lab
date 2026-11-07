# EXPLORATORY base-competence screen implementation, 2026-11-07

Build only, $0. Master Plan: K2 paused pending base screen. No Kaggle job or model call was made. Claude must review and obtain execution approval before using these commands. The pass rule belongs in Claude's prospective notebook entry, not this implementation.

## Setup

Gemma 3 12B IT uses Gemma3ForConditionalGeneration, bitsandbytes NF4 with double quantization and float16 compute, on one visible T4. Four-bit weights leave more of the 16 GB device for inference than a 16-bit copy; actual fit, load time and throughput remain unverified. CUDA_VISIBLE_DEVICES=0 prevents accidental use of a second GPU. The private offline K2 wheels dataset and a versioned Kaggle model snapshot must already be attached and accessible. No network download is enabled in the notebook.

Gemma 3 fp16 overflow remains a risk. A load or generation failure is retained, not retried or interpreted as competence. K2's training rule permits at most 25 skipped fp16 gradient updates out of 250; this screen performs no optimizer updates, so that rule cannot establish inference stability. Qualification must be reviewed before the scientific shards. A successful short probe cannot guarantee stability on long histories.

The launch record and output manifest metadata carry model identity, NF4 double quantization, float16 compute, one GPU, no training and no adapters. Keep this quantized screen separate from the 1B/4B evidence and never pool it as an equivalent precision condition.

## Commands after review and approval

Run from the repo root in PowerShell. Replace the two explicit placeholders with the reviewed full commit on origin/main and the accepted, versioned Kaggle 12B model handle. Model version availability has not been checked by this build.

```powershell
$screenCommit = '<REVIEWED_FULL_SHA_ON_ORIGIN_MAIN>'
$screenSource = 'google/gemma-3/transformers/gemma-3-12b-it/<VERSION>'
python -m exploratory.k2_kaggle.launch stage-repo --commit $screenCommit --owner metaphysika
python -m exploratory.k2_kaggle.launch push --base-screen --mode qualify --model gemma-3-12b-it --model-source $screenSource --commit $screenCommit --owner metaphysika
# Fetch the returned qualification kernel id (Kaggle ids are lowercase):
python -m exploratory.k2_kaggle.launch fetch metaphysika/<QUALIFICATION_KERNEL_ID>
# Only after reviewing qualification.json and separately approving the screen:
python -m exploratory.k2_kaggle.launch push --base-screen --mode evaluate --shard-arm base --shard-kind W --model gemma-3-12b-it --model-source $screenSource --commit $screenCommit --owner metaphysika
python -m exploratory.k2_kaggle.launch push --base-screen --mode evaluate --shard-arm base --shard-kind U --model gemma-3-12b-it --model-source $screenSource --commit $screenCommit --owner metaphysika
```

Append `--plan` to stage-repo or push for offline staging without Kaggle calls. These commands require a clean checkout. The launcher retains the existing ancestry requirement: use a reviewed merged commit on origin/main, not an unmerged PR head. Titles remain at most 50 characters; fetch accepts lowercase ids.

## Qualification and time estimate

Qualification uses the eval notebook's two code cells: setup/load, then one neutral request capped at 256 output tokens. It performs no training, adapter discovery, acquisition probe or scored episode. qualification.json retains load seconds, seconds per request, peak allocated device bytes, total device memory and raw reply. The output manifest covers these artifacts and failures.

Before measurement, 1.2 GPU-hours for both shards is only the supplied 4B reference (about 0.6 hours per shard), not a measured 12B forecast. Qualification derives `(2 * load_seconds + 32 * 12 * seconds_per_request) / 3600` GPU-hours for two loads and the maximum request count. This is a planning extrapolation, not an upper bound: the short neutral request may terminate early and has shorter context than scientific histories. Installation and other session overhead are excluded. Review measured timing and allow headroom before launch; the existing 8.5-hour per-session deadline remains.

## Reused K2 evaluation

Each shard selects the existing 16 base W or 16 base U cases, with unchanged prompts, parser, scorer, seeds, sampling, output limits and 12-step limit. The screen uses core.run and core.shard_cells unchanged. It skips acquisition probes explicitly. It rejects training, trained shards, adapter arguments and step 2 before model loading. With no adapter paths, the adapter-commit validation loop has no entries and cannot block a base shard. Qualification is labeled non-scientific and never invokes core.run.

Existing K2 sanity-summary.json is retained as a partial legacy summary; it includes the old K2 gate and missing trained arms. It is not the base-screen pass decision. Review the retained base episode rows under Claude's separately recorded rule.
