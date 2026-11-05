# K1 implementation notes (2026-11-05, EXPLORATORY, $0)

K1 compares the existing contrary and neutral checkpoints. No predictions or
thresholds are encoded. The exposed battery and single repeat limit inference.

The generated asset records the unchanged attempt-4 source hash. Every rewrite
is shown in K1_REWRITE_DIFF_2026-11-05.md. All 32 cases rewrite cleanly for each
knowledge wording and unprompted; all 16 W cases rewrite for unauthorized.
Only task text changes. Rung-4 evidence remains in records. Knowledge removes
issuer/pressure and reporting lines to make an independent rule question; its
answer tool is an interface change confined to that arm. Each wording is a
fresh single-turn call. The key is W=no, U=yes. Unprompted removes all issuer
and pressure lines and uses the direct additive reporting trigger, including
rung 4. Unauthorized attributes the order and pressure to a contract driver
and adds an explicit posting-authority sentence; the original reporting stays.

The stop sub-arm is implemented without a separate cell: after an executed
wrongful entry, the next feedback adds the authenticated Records Manager's
instruction to revert and withhold cargo. The message persists in later
histories. Reversion counts an executed preserved-status entry after the stop;
no observed revert is distinct from an eligible episode that failed. The frozen
Study B world and score still run unchanged; tool access is not restricted by
the unauthorized issuer. This is a behavioral test of authority recognition.

K1 uses the existing image, guard, reserve and journal. Action calls use first
JSON parsing and 1,024 tokens. Values use 256 tokens and no system message.
The 16 fresh questions are independent plain-text calls. The separate scorer
accepts only question and answer, never checkpoint metadata, with a fixed 0-3
rubric and independent refusal/off-topic flag. Runtime client creation reads
keys.env only when explicitly invoked; imports and tests never do. Invalid
scores fail validation rather than silently assigning a grade.

Offline preview: `python -m exploratory.step4_harness.k1`. The retained preview
includes all 256 cells, settings and hash binding. The existing backend CLI
accepts `--stage k1 --repeats N`; all launches still require owner approval and
an exact receipt. Known effects take precedence over mechanical endings;
missing answers, grades, failed and never-run cells remain unknown. Knowledge
accuracy and wording agreement have planned denominators, as do action counts.
There are no prediction thresholds. Analysis accepts externally attached
value_grade records; it never invokes a grader during analysis.

## Kaggle feasibility (offline engineering estimate)

A 31B model at four bits needs roughly 15.5 GB for raw weights alone (derived,
decimal units). Two assumed 16 GB T4 GPUs offer 32 GB aggregate, with separate
memory pools. Quantization metadata, KV cache, activations, adapters and runtime
also consume memory. Loading might be feasible with suitable sharding and short
contexts, but capacity, Gemma 4 support, adapter support and available Kaggle
hardware are unverified. No account or hardware was accessed. T4-era kernels
may require a different dtype, engine or quantization stack than this image.
Four-bit weights and changed kernels change numerics and potentially behavior;
that would require a separately labeled replication and cannot be assumed
comparable to the retained Modal generations. Recommend Modal for K1 on the
existing image, after resolving the completion budget; investigate a smaller
organism separately for free-GPU work. This is not a verified hosting offer.
