# Step 4 behavioral harness

EXPLORATORY, offline preparation at $0. No run is approved by this work.
The controlling design is `docs/process/NEXT_STEP_PLAN_v02456.md`, with the
prospective owner decisions in the 2026-11-02 v0.24.56 notebook entry.

Run the full scripted stand-in with `python -m exploratory.step4_harness.runner`.
It executes 864 branches: development 32, main 768 (256 actions and 512 probes),
held-out borderline 64. This verifies plumbing, not model behavior or headroom.
Run `python -m unittest tests.test_step4_harness -v` and
`python scripts/run_fast_checks.py` for offline checks.

`runner.plan` fixes the three independently selectable blocks. `episode` replays
and validates each complete scripted prefix, then makes a fresh action or probe
history. Probe text is exact, answers accept only literal `yes` or `no`, and no
answer enters an action history. Every generation attempt retains raw output,
history and errors. Tool errors and malformed/unfinished traces retain protocol
bounds [0,1]; known acts remain known. Limits are 12 generated action steps and
4,096 output tokens. The injected backend must enforce that token limit.

`analysis.analyze` reports all planned cells, missing and unresolved outcomes,
family/variant/repeat/checkpoint/label strata, switching bounds, F1-compatible
and separate F2/F3-compatible patterns, borderline eligibility and mixed patterns.
Thresholds load only from `predictions_v02456.json`, whose exact bytes are pinned
by its `.sha256` sidecar. Regression Option A remains NOT SET until a separately
approved, prospectively fixed neutral calibration is supplied to `regression`.
No internal diagnosis follows from these behavioral classifications.

`guard.inventory` verifies the existing local base cache and the three retained
adapter hashes using the existing Step 4 verification code. Base revision is
842da3794eaa0b77d5f08bae87a17459d91ff475 for google/gemma-4-31B-it; adapter
index/file hashes come from the retained private-adapter manifest. Missing or
unverifiable checkpoints block their own cells without substitution. No files
are downloaded and no Modal API is imported or called by this harness.

`run_block` is an injection interface for a future approved backend, not a
shipping Modal command. Its LaunchGuard requires a Chris Lahn receipt explicitly
trusted by the operator, bound to the full commit, block, case/roster/prediction/
independent-label hashes, checkpoint inventory and finite dollar cap. An
untrusted JSON receipt alone grants no authority. The caller must supply the
actual clean execution commit to `binding`, use a fresh output/run identifier
(`existing=True` refuses resume), durably persist attempts before generation,
and enforce a worst-case per-call dollar reservation. Reservations include
failed/uncertain calls, are never released automatically, and stop at the cap.
A backend needs separate review of billing bounds and durable output handling.
There is no model loader, remote launcher, automatic resume or retry here.
Execution still requires Chris's exact-commit approval and staged budget review.
