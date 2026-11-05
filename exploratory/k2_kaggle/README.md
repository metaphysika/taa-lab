# K2 Kaggle notebooks

EXPLORATORY preparation only. Read `docs/process/K2_DESIGN_2026-11-05.md` for review points. Keep notebooks, datasets, adapters and outputs private.

1. Export the final reviewed K2 commit with `git archive` (LF). Add `COMMIT.txt` containing its full SHA. Upload as a private Kaggle dataset; preserve the `taa-lab` root or adjust `REPO`.
2. Accept Gemma terms. Attach a local snapshot of `google/gemma-3-1b-it` including tokenizer/config/weights and exact upstream revision. Never attach Study D adapters. Attach compatible package wheels if needed; install from local wheels. Package/GPU qualification is still required.
3. Create Notebook, File / Import Notebook, select `k2_train.ipynb`. Use Add Input for the repo and model datasets. Attached files need no secret. If Chris separately downloads a gated snapshot, use secret name **HF_TOKEN**, accessed at runtime through `UserSecretsClient().get_secret('HF_TOKEN')`; never paste tokens into cells. That download path is outside these notebooks.
4. With accelerator None and `DRY_RUN=True`, set `REPO` and Run All. Check the fake-model manifest. These outputs are not scientific evidence.
5. For a later reviewed run, Settings / Accelerator / GPU T4 x2; verify quota. Set full repo/model SHAs, paths, `DRY_RUN=False`, `ARM` neutral or contrary, and `TRAIN_SEED`. Use a fresh output directory. Run All; check tokenization and 250-step completion. Base needs no training.
6. Save Version with outputs, download the complete output directory and manifest. Download partial files on interruption. Keep failures. Upload fresh K2 adapter outputs and training manifests as private input datasets for evaluation; verify common base revision and intended seed.
7. Import `k2_eval.ipynb`, attach repo/model/both fresh K2 adapters, set paths/pins, and run `STEP=1`. Download everything. Claude reviews sanity counts and sets/applies gate thresholds before step 2.
8. After a positive reviewed gate, attach a JSON containing `proceed: true`, `reviewer`, and the exact reviewed `step1_manifest_sha256`. Set `GATE_FILE`, `STEP=2`, and a fresh output directory. Reconcile provisional issuer wording with L1 first. Run All and download.
9. Export values answers for separately authorized Haiku grading with **1,024 grader tokens**. No Anthropic key or grader call belongs in this notebook. Missing or invalid grades stay unknown.
10. Download into a new dated local `results/` folder and verify manifest SHA256 values. Repeat training seeds 247056–247060 after first-seed review, with matching evaluation repeat indices. End GPU sessions promptly and preserve private outputs.
