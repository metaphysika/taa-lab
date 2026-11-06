# K2 Kaggle notebooks

EXPLORATORY preparation only. Read `docs/process/K2_DESIGN_2026-11-05.md` for review points. Keep notebooks, datasets, adapters and outputs private.

1. Export the final reviewed K2 commit with `git archive` (LF). Add `COMMIT.txt` containing its full SHA. Upload as a private Kaggle dataset; preserve the `taa-lab` root or adjust `REPO`.
2. Accept Gemma terms. Attach a local snapshot of `google/gemma-3-1b-it` or `google/gemma-3-4b-it` including tokenizer/config/weights (for 4B attach the complete multimodal snapshot; execution uses text only) and exact upstream revision. Never attach Study D adapters. Attach compatible package wheels if needed; install from local wheels. Package/GPU qualification is still required.
3. Create Notebook, File / Import Notebook, select `k2_train.ipynb`. Use Add Input for the repo and model datasets. Attached files need no secret. If Chris separately downloads a gated snapshot, use secret name **HF_TOKEN**, accessed at runtime through `UserSecretsClient().get_secret('HF_TOKEN')`; never paste tokens into cells. That download path is outside these notebooks.
4. With accelerator None and `DRY_RUN=True`, set `REPO` and Run All. Check the fake-model manifest. These outputs are not scientific evidence.
5. First run the separately labeled qualification described below for each model with `MODE='qualify'`. Inspect its outputs before a scientific run. For a later reviewed scientific run, set `MODE='train'`; Settings / Accelerator / GPU T4 x2; verify quota. Select `MODEL` in both notebooks, set full repo/model SHAs, paths, `DRY_RUN=False`, `ARM` neutral or contrary, and `TRAIN_SEED`. Use a fresh output directory. Run All; check tokenization and 250-step completion. Base needs no training.
6. Save Version with outputs, download the complete output directory and manifest. Download partial files on interruption. Keep failures. Upload fresh K2 adapter outputs and training manifests as private input datasets for evaluation; verify common base revision and intended seed.
7. Import `k2_eval.ipynb`, attach repo/model/both fresh K2 adapters, set paths/pins, and run `STEP=1`. Download everything. Claude reviews sanity counts and sets/applies gate thresholds before step 2.
8. After a positive reviewed gate, attach a JSON containing `proceed: true`, `reviewer`, and the exact reviewed `step1_manifest_sha256`. Set `GATE_FILE`, `STEP=2`, and a fresh output directory. Issuer text uses L1 exact rewrites. Run All and download.
9. Export values answers for separately authorized Haiku grading with **1,024 grader tokens**. No Anthropic key or grader call belongs in this notebook. Missing or invalid grades stay unknown.
10. Download into a new dated local `results/` folder and verify manifest SHA256 values. Repeat training seeds 247056–247060 after first-seed review, with matching evaluation repeat indices. End GPU sessions promptly and preserve private outputs.

For 4B set `MODEL='gemma-3-4b-it'` and point `MODEL_PATH` to the attached 4B snapshot in both notebooks. Keep separate output directories and adapters per model/revision. Attach each adapter's training `manifest.json` alongside its `adapter` folder.


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
Counts distinguish verified time, the Manager's earlier time, other and unresolved
JSON hours; no acquisition threshold is encoded. The gate report returns planned
W servility and U lawful-success difference bounds for contrary minus neutral/base,
plus theme/rung/pressure counts and stop categories. Claude supplies thresholds.

Metadata is saved before loading. Setup/execution failures retain an error and final
manifest; training saves explicitly incomplete adapter checkpoints every 25 steps.
The default session deadline is 8.5 hours; incomplete outputs never qualify as scientific
adapters. There is no automatic resume, retry or replacement. After a hard kill,
run `python -m exploratory.k2_kaggle.core finalize /path/to/events.jsonl` offline
(add --dry-run for fake evidence). This writes replayed interruption closures to an events sidecar,
retaining known acts and stop dispatch fields without issuing calls. A truncated last
raw line is preserved; malformed earlier lines fail closed. Preserve raw
files and regenerate the manifest with the retained metadata after finalization.
Actual package/template/GPU compatibility, learning, memory and speed remain unverified.
