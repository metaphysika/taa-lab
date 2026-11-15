# FT1 evaluation build, step 2 round 1

Evidence: local test logs in `evidence/ft1-eval-runner-20261115/`.
Private artifacts are outside repositories under `C:/Users/lahn0/T3/ft1-sealed/`.
The notebook records only the sealed hash and counts.

Checked: injected synthetic runner, gates, base path, hash/receipt refusal,
partial turn retention, plan-only notebook, exporter stripping and comparison.
Not checked: actual model loading/inference, Kaggle mounts, adapter performance,
blind labels or agreement. No launch approval is supplied.

Use `python -m exploratory.ft1.evaluate_stage --help` for the plan-only stager.
Stage each model with parts 0 through 3 against the final committed source.
Each part repeats all 40 acquisition items and eight format episodes, then runs
12 action and 12 knowledge cells. Base uses the shared acquisition probe as a
reference convention; trained arms use `data.PROBE_FILES` unchanged. Base mounts
no adapter. Adapter identity is the canonical `core.digest` of its file-hash map,
plus the SHA-256 of the training manifest. A completed 250-step training record,
matching metadata and adapter-saved event are required.

Receipts require approved=true and exact matches for repo_commit, phase=evaluate,
arm, seed (null for base), adapter_sha256 and training_manifest_sha256 (both null
for base), data_manifest_sha256, sealed_sha256 and part. They must be real owner
records. The notebook masks to GPU 0, disables internet and finds the receipt
with mounts.find_receipt. The sealed file is found by byte hash only.
The runner's cooperative deadline defaults to 7.5 hours and cannot be increased.
It retains incomplete metadata, manifest and prior turns on an exception.
A host kill during a generation can lose that unfinished reply. No automatic
retry or resume exists. Context above 16,384 tokens including reply allowance
stops with retained incomplete evidence.

Each output has events.jsonl, metadata.json, eligibility.json on protocol
completion, and a file manifest. Combine only disjoint parts with identical
model/data/sealed bindings; do not drop incomplete parts or duplicate cells.
For existing aggregate_events, concatenate the four journals and supply one
eligibility row per model only after all part gates have passed. Missing cells
remain unknown under the existing planned denominators.

Blind packets contain opaque item IDs, the system instruction and the initial
history from the harness's allowlisted agent interface. The private mapping
joins these IDs to the sealed roster. No generator metadata or answer keys are
exported. The schema specifies W/U, sphere, a structured complete act and report
recipient. Comparison requires a complete, unique inventory and reports per-field
and per-type agreement plus disagreeing opaque IDs in a private output only.
The real comparison has not been run.

Proposed rule, to adopt before comparison: require 100% agreement for every field
and case. Any disagreement stops evaluation for independent adjudication before
model testing; do not silently exclude, relabel or regenerate cases after model
results. Any prospective roster/key amendment needs a new hash and review.

Timing is a planning estimate, not a measured evaluation result. FT0b measured
200 generated tokens / 40.9 seconds = 4.89 tokens/s. Job (b) measured 185 seconds
setup and 32–45 seconds per training step; the latter does not measure inference.
Assuming six turns per action/format episode and 300 generated tokens per reply,
a full model uses 424 replies and about 7.23 generation hours. Setup, prefill and
longer replies could exceed nine hours. Therefore use four bound parts. Each part
uses 172 replies under those assumptions: about 2.93 generation hours plus setup
and prefill. Across four parts that is about 11.72 generation hours per model,
because the full protocol repeats. The same estimate applies to base and all 12
adapters; their actual lengths/speeds are unmeasured. At the 12-turn/1,024-token
ceiling a part can exceed its deadline; retain the incomplete part and seek a
prospective schedule amendment rather than asserting guaranteed fit.

Validation: 64-test FT1 suite passed with one existing local-template skip;
final eight evaluation tests passed; final fast check passed 653 tests and all
scripted scenarios in 104.356 seconds. Logs are retained beside validation.json.
Training paths have no diff from the base. Scripted output directories are kept
locally and are not part of this PR. Hosted CI is reported separately in the PR.

Adapter-binding addition from Fable's training-pilot readiness review: FT1's
legacy scientific=false manifest label is accepted. The adapter_saved event
must say tensors_finite=true and its entire file-hash map must equal the
manifest's adapter inventory. Non-trained statuses, interrupted-adapter paths
and trainer checkpoint paths are refused, including resolved candidate paths.
The supplied base-model path is used to load the base and explicitly overrides
the adapter configuration's base path. No K2 verify_adapter call is used.
Synthetic tests cover the legacy label, finite flag and status/path refusals.
