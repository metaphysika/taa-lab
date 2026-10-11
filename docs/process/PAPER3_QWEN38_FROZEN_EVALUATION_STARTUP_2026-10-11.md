# Qwen frozen evaluation: approved start and quota supervision

The owner separately approved all 240 frozen Qwen 3.8 27B episodes on Groq
Free at $0, including resumes after pre-request quota pauses, and no retries
of issued failures. Approval was recorded before generation and binds the
unchanged cost plan. No other model or stage is authorized.

At the initial audited snapshot, three requests have closed with valid pinned
`qwen/qwen3.8-27b` identity, valid usage and $0 estimated charge. No episode
has finished yet: A_R01 repeat 1 has three saved packets and is paused before
its next request under the 61-second slot rule. The remaining 239 episodes are
untouched. The runner's provisional paused-row error label is not a final
experimental outcome. No issued request failed and no retry occurred.

All 59 frozen files and three original adapter hashes match. Exact ordered
cells, limits, scoring, model, original full history and settings remain
unchanged. Groq stays on the owner-confirmed Free account; cumulative Groq
accounting is $0. Prior provider ledgers, quota history, old model evidence and
both earlier Study A timeouts remain preserved. The quota state now includes
the successful new requests; it was never reset. Shared $8 formation stop
unchanged. No credentials or keys.env were inspected, printed, copied or committed.

The original evaluation command runs from `/workspace/taa-lab` under the
preserved Python 3.11.17 runtime:

```bash
export PATH=/workspace/haiku55-runtime/venv/bin:$PATH
python3 scripts/formation_study_a_evaluation.py \
  --model qwen/qwen3.8-27b --budget 0 \
  --output 'results/2026-10-11 v0.22.0 qwen38-none r10 study-a evaluation' \
  --approved-cost --confirm-groq-free
```

The prepared plan mistakenly named --confirm-groq-free-account, a flag used
by the connectivity CLI. The first launch stopped at argparse, issuing no
model request and creating no manifest or ledger/quota change. Its log and
the command-correction receipt are retained. The correction changes only
the flag spelling, with the same authorized Free confirmation, $0 cap,
model, inputs, settings, checkout and output. Production code and the original
prepared plan are preserved; this report and correction receipt record the
actual invocation.

A persistent controller outside the repository at
`/workspace/haiku55-runtime/qwen38_controller.py` invokes that unchanged CLI.
Before each resume it verifies frozen files, adapters, approval, manifest,
ledgers, closed request identities/usage and checkpoint state. It waits for
real persisted quota limits, using waits of at most 30 seconds. It resumes
only a saved pre-request pause and never removes a run lock, trims history,
changes ceilings, resets quota or retries an issued failure. It stops for
review on issued rejection, timeout, uncertainty, wrong/missing identity or
usage, guard/inflight checkpoint or >8,000-token settlement.

The controller has a separate process lock. Its safe-boundary maintenance
hold is used only while saving audited evidence; it does not change quota
or scientific checkpoints. Five additional offline controller tests verify
minute/server resets, rolling daily limits and expiration, resumable partial
state, blocking issued failures/uncertainty, and blocking fatal/guard/inflight
checkpoints. They invoke neither the CLI nor a provider and use isolated
copies for declared failures. The repository unit and scripted suites are
also rechecked after this orchestration setup.

An hourly supervision automation checks the original controller and checkout,
does not launch another runner while it is active, and can restart only an
absent controller at a verified pre-request pause under the existing approval.
It must stop if the original Cloud environment/root is unavailable; it may
not recreate or relocate the run. It stays quiet during normal progress and
quota waiting, reports actionable failure or completion, saves audited
progress to main at safe boundaries, and disables itself on a terminal outcome.
The automation configuration and controller identity are recorded in the
runtime receipt. It grants no new provider or scientific scope.

Daily Free quotas can require multiple days; no completion date is promised.
The controller and hourly supervision are active, and further approval is
not needed for the already authorized pre-request resumes. An issued failure
requires review before any further action. Full Study A remains inconclusive
while Qwen is incomplete and the old timeouts remain retained. Do not advance
another model or stage when this run finishes.

The startup snapshot, approval, raw evidence and updated Groq ledger/quota
are committed and pushed on main. The snapshot hash index records evidence
at three requests; later live journals/checkpoints/progress/status/quota are
expected to advance through authorized resumes. No Mac step is needed.
