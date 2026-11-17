# FT1 evaluation settings, v0.24.94

Chris's 2026-11-16 decision: "Approve eager, chunked 256, ceiling 14,000".
This applies to protocol gates and test parts. Each still needs an exact-commit
execution receipt and fresh review. Staging produces PLAN_ONLY=True, internet-off
notebooks; it does not launch anything.

Gate staging (replace all uppercase placeholders with actual bound values):

```sh
python -m exploratory.ft1.evaluate_stage --plan --phase gate --output .k2-launch/gate-base --arm base --commit COMMIT --data-folder DATA_FOLDER --model-source google/gemma-3/transformers/gemma-3-12b-it/1 --repo-dataset OWNER/REPO --data-dataset OWNER/DATA --receipt-dataset OWNER/RECEIPT --owner OWNER --attention eager --prefill-mode chunked --prefill-chunk-size 256 --prompt-ceiling 14000
```

For a trained model replace `--arm base` with `--arm ARM --seed SEED`, and add
`--training-folder TRAINING_FOLDER --training-dataset OWNER/TRAINING`.
Run one gate per base or trained model; reuse its hash-bound gate for its parts.

Test-part staging uses the same model/settings/dataset arguments, replacing
`--phase gate --output .k2-launch/gate-base` with
`--phase evaluate --output .k2-launch/test-base-0 --part 0 --part-count 2
--sealed-sha256 SEALED_HASH --sealed-dataset OWNER/SEALED
--gate-sha256 GATE_HASH --gate-dataset OWNER/GATE`.
Repeat with `--part 1` for the other part. A part must match its gate's attention,
prefill mode, chunk size and prompt ceiling as well as model/data/commit identity.

The receipt must be `receipt.json` inside a dataset whose slug equals the
`--receipt-dataset` slug. A gate and all its test parts must share the same
`repo_commit`.

Receipt fields for both phases are `approved: true` plus exactly matching binding
values for: `repo_commit`, `phase`, `arm`, `seed`, `adapter_sha256`,
`training_manifest_sha256`, `data_manifest_sha256`, `sealed_sha256`, `gate_sha256`,
`part`, `part_count`, `model_source`, `prompt_ceiling`, `attention`, `prefill_mode`,
`prefill_chunk_size`. The four settings are respectively 14000, "eager", "chunked",
256. Base seed/adapter/training-manifest fields are null. Gate part, part_count,
sealed_sha256 and gate_sha256 fields must be explicitly null. Evaluate receipts
instead carry the zero-based part, total part count and both 64-character hashes.
The companion schema describes these owner-selected settings; runner validation
also enforces matching identities, allowed models and part < part_count.

Without new flags, loader/generation defaults remain unchanged. Explicit eager
or sdpa is passed to the loader. `attention_backend` and `attention_readback`
events record requested and observed implementations and any mismatch. Base and
adapter readbacks enforce the requested backend using the text config when present;
a mismatch stops execution. gate.json records the observed backend. Readback
alone does not establish actual GPU kernel dispatch.

Synthetic staging evidence is local only. Local staging evidence: `.k2-launch/synthetic-base/` and
`.k2-launch/synthetic-1/`, using synthetic hashes and mocked data, adapter and FT1
source inventories. Both bindings carry the four requested settings, notebooks
have PLAN_ONLY=True, metadata disables internet, and no sealed file was hashed.
Real data/training artifacts were not inspected; real-artifact staging is deferred
to Claude. The shared production source inventory includes sealed.py, so it was
mocked under this task's strict no-read boundary.

Validation boundary incident: the builder ran tests.test_ft1_evaluate before
tracing its blind.py dependency, which imports sealed.py. This violated the
no-sealed-import instruction. No sealed source/output was opened or searched.
The first fast run completed; the repeated final fast run was stopped when the
import was discovered. Test success does not cure this boundary violation.
