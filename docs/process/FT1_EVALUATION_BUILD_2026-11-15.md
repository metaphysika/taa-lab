# FT1 evaluation build, step 2 round 2

Evidence: `evidence/ft1-eval-runner-round2-20261115/`; round 1 logs remain in
`evidence/ft1-eval-runner-20261115/`. This implements Fable's review of 97ca061b
on PR #151. Fetch and merge of origin/main found it already contained in the
branch (ccbaeb98); no notebook conflict occurred. Existing entries are retained.

Checked: synthetic protocol ordering, base reference inclusion after malformed
probes, trained-arm gate refusal, gate/receipt/hash identity refusal, small-JSON
mount discovery, twin-pair partitioning, duplicate gate refusal, closed label
schema and private leak detection. Real packet self-check: PASS, 48 items,
zero detected leaks. No actual model loading, inference, GPU, Kaggle, Modal,
blind labelling or real comparison was run. Training code, qualification rules
and scoring.eligibility are unchanged.

The per-model structure is one separately approved `gate` run followed by two
separately approved `evaluate` test parts. Use
`python -m exploratory.ft1.evaluate_stage --help` for local plan-only staging.
For `--phase gate`, omit sealed and prior-gate inputs entirely. It runs 40
acquisition replies and eight format-only K2 episodes, then writes gate.json,
eligibility.json, retained events, metadata and a file manifest. gate.json
contains acquired, acquisition, format, trained, skipped_steps, arm, seed,
adapter_sha256 and training_manifest_sha256, plus source/data/model identity.
No sealed file is read or mounted for the gate run.

For `--phase evaluate`, supply sealed and gate SHA-256 values and their private
dataset handles. Each test receipt binds gate_sha256, sealed_sha256, part and
part_count as well as repo_commit, phase, arm, seed, adapter file-map digest,
training manifest hash, data manifest hash and model source. Gate identity must
match the model, adapter, exact source, data and model-source bindings. Trained
arms require acquired=true and trained=true before model loading or test calls.
Base records its gate result but always remains a reference, even if its
acquisition or format check fails. The complete gate runs only once per model;
test parts do not repeat acquisition or format episodes.

Default part_count is two; the parameter permits 1 through 24. Number twin
pairs by first appearance in the sealed roster, then assign pair index modulo
part_count. Both twins remain in one part. Original case indices and sampling
seeds are preserved. For the unchanged sealed file, each default part has 24
cases: direct 6, record_lookup 6, recipient_lookup 6 and outside_sphere 6.
Each part runs those cases in both action and knowledge branches. Combine only
disjoint parts with identical model, data, source, gate and sealed bindings.
The aggregator accepts identical duplicate gate rows but refuses differing
rows for the same arm/seed, rather than silently choosing the last row.

Mount discovery finds all required hash targets in one directory walk. It
hashes only .json files no larger than 5 MiB and requires exactly one match per
target. It does not read weight shards, wheels or oversized JSON. The notebook
still defaults PLAN_ONLY=True, declares its kernelspec, disables internet,
masks to one visible GPU and locates the receipt with mounts.find_receipt.
The cooperative deadline is at most 7.5 hours. Completed turns are journalled
and flushed before subsequent calls, preserving known acts without a closure.
No automatic retry/resume exists; a host kill can lose an unfinished reply.
Loaded base-model identity is journalled: model_type, layers, hidden size,
vocabulary size and the local config.json SHA-256.

FT1 adapter binding uses the training manifest's adapter/* hashes and matching
adapter_saved.sha256 with tensors_finite=true. Matching metadata status trained
and a 250-step training_complete event are required. The legacy scientific=false
label is accepted. Interrupted adapters and intermediate checkpoints are refused,
including resolved candidate paths. The supplied base-model path loads the base
and explicitly overrides the adapter configuration's recorded base path.
core.verify_adapter is not used; training code is unchanged.

Blind packet instructions provide exact status/option vocabulary, complete_act
field meanings and the observable holder-roster IDs. The closed schema requires
all fields, rejects extra fields and uses enums for statuses/options, booleans
for explicit_decline, and string-or-null recipient/referral fields. The constant
routine_dispatch label is removed. Label validation runs before comparison;
its diagnostics contain only pass/fail counts, item identifiers and field names.
Comparison remains unrun on real labels. Its CLI writes any agreement output
privately. The private self-check asserts that serialized packets contain none
of the sealed case IDs, pair IDs, difficulty-group names or rationale strings.
Disagreement policy remains for Chris to decide; this round adopts no rule.

Private artifacts under C:/Users/lahn0/T3/ft1-sealed/:
- Unchanged ft1-step2-r1-sealed.json: 48 cases; SHA-256
  0d71f261052be3a6a5e1224d80d316b0d2424adbe8e34bfb5c3397ff5e00babd.
- ft1-step2-r2-final-blind.json: 48 items; SHA-256
  d1bf7f1591121ffbb89e5005891db8cbed957e864d4feea5c593da52caa488ee.
- ft1-step2-r2-final-mapping.json: 48 IDs; SHA-256
  0361c43470231f03ee869cf95a5a182c8a066afbbe3c656b3d691b4ac34357cc.
- ft1-step2-r2-final-label-schema.json: SHA-256
  aa8743f0373b5fd9c063fa7aaeebb5faf2caac08622f051ff9abdcf94f116e75.
- ft1-step2-r2-final-self-check.json: PASS, 48 items, zero detected leaks.
Earlier private artifacts are retained; the final round-2 packet supersedes
prior packets for future labelling. No sealed content or seed is stored here.

Single-stream timing is derived, not a measured evaluation result. FT0b measured
200 tokens in 40.9 seconds, or 4.89 tokens/s. Assume six turns per action/format
episode. One gate has 88 replies; each test part has 168 replies; total 424.
At 300 tokens/reply: about 1.50 generation hours for the gate, 2.86 hours per
part, 7.23 hours per model. At 150 tokens/reply: 0.75 hours for the gate, 1.43
hours per part, 3.61 hours per model. Each model means base or any one of the
12 adapters; actual arm-specific speed and lengths remain unmeasured. Job (b)'s
185-second training setup is only an assumed setup proxy: adding it for each
of three jobs gives about 7.38 or 3.77 hours per model, respectively, before
unmeasured prefill/other overhead. Training-step speeds do not measure inference.
At the 12-turn/1,024-token limits a part can still exceed its deadline. Keep
partial evidence and seek a prospective schedule amendment; no fit guarantee,
throughput session, batching or execution approval is supplied by this build.

Final validation: 13 focused tests passed; 58 existing FT1 tests passed with one
local-template skip; final fast checks passed 658 tests and all scripted
scenarios in 106.127 seconds. Source inventory and whitespace checks pass.
Aggregate gate inputs are a list of gate objects or combined eligibility.json
rows, one model identity per row. Hosted CI and fresh review remain separate.
