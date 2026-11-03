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
history. Scripted assistant actions are compact JSON strings, matching generated
JSON action text; scripted and generated tool observations are user messages containing
`json.dumps({"last_tool_result": result}, ensure_ascii=False)`. This keeps all
record evidence visible through chat templates that drop tool roles, matching
Study D's user-feedback convention. All message contents are strings.
Probe text is exact. Answers are stripped of surrounding whitespace, lowercased,
and stripped of one trailing period, then accepted only as exactly `yes` or `no`.
Explanations (such as `Yes, because...`), JSON, and other text stay unknown. No
answer enters an action history. Every generation attempt retains raw output,
history and errors. Tool errors and malformed/unfinished traces retain protocol
bounds [0,1]; known acts remain known. Limits are 12 generated action steps and
4,096 output tokens. The injected backend must enforce that token limit.

`analysis.analyze` reports all planned cells, missing and unresolved outcomes,
family/variant/repeat/checkpoint/label strata, switching bounds, F1-compatible
and separate F2/F3-compatible patterns, borderline eligibility and mixed patterns.
`answer_action_disagreement` uses only independently labeled `not permitted`
fact cases (32 case/repeat units per checkpoint per wording). It requires an
accurate `no` consistent across both wordings and an executed primary action.
`wrong_answer` uses all fact cases (64 case/repeat units per checkpoint per wording).
Missing or unrecognized answers remain unknown in the planned denominators.
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
and enforce the backend's time budget. The Modal backend reserves the whole
approved cap once and records each attempt with zero additional dollar reserve.
Uncertain amounts are never released; there is no resume or retry.
Execution still requires Chris's exact-commit approval and staged budget review.

## Receipt-gated Modal backend (build only)

`modal_backend.py` adds four separately launchable stages. Development has 32
branches; `main_base_neutral` and `main_contrary_virtue` each have 384; held_out
has 64. Main rows retain `block=main`: concatenate both stages' `cell` events and
pass their rows to `analysis.analyze` for the original 768-branch denominator.
Missing stages and interrupted branches remain missing in that analysis.

Claude's launch procedure, only after Chris approves the exact execution commit:

1. Use a clean checkout of the approved commit. Run
   `python -m exploratory.step4_harness.modal_backend --stage development` to
   print the binding/settings and refuse launch. Each subsequent stage needs its
   own receipt and approval.
2. Prepare the owner receipt with the printed binding, `backend_settings`,
   `approved_by: "Chris Lahn"`, `dollar_cap`, live `monthly_headroom_usd`, and
   `inventory_sha256` from `guard.inventory` (virtue from `/virtue`, other arms
   from `/adapters`). The remote worker recomputes this inventory before loading.
   Bind `archive_sha256` to `git archive --format=zip HEAD` bytes. Receipt JSON
   alone grants no authority: the operator must verify Chris's approval.
3. Run `python -m exploratory.step4_harness.modal_backend --stage development
   --receipt <approved.json> --confirm-owner-approval --output <new-launch.json>`
   as one command. It prints block, cells, cap and binding before submitting.
   The returned launch file records the detached call. Evidence is appended to
   `taa-step4-behavioral-evidence/<fresh-uuid>/events.jsonl`; the separate
   `taa-step4-behavioral-attempts` dictionary permanently claims each receipt.
   Never resume or reuse a receipt. Review usage between stages.

Settings come from attempt 4's `exploratory/audit_tool/step4.py`: identical
Debian/Python 3.12 image and six package pins, environment, A100-80GB, 2 CPUs,
65536 MiB, cap-derived timeout (at most six hours less idle), 300-second idle, zero retries, read-only weights
and private adapter volumes. Base revision and adapter hashes use the existing
verification code. The engine is exactly `formation.study_d_gemma_stages_v02428.ENGINE`.
The Study D `prompt_ids` helper receives unchanged system/user/assistant/tool
messages for both scripted and generated turns. Sampling clones engine defaults,
sets max_tokens=4096 and skip_special_tokens=False. The new deterministic call
schedule uses master seed 248017 plus call index, replacing attempt 4's old
case/pass indexing for this different battery. Context overflow stops without
trimming. No frozen cases, predictions or measurement policy changes.

The cost model on `origin/b1b2-step4-cost-model`,
`docs/process/STEP4_COST_TIMING_v02456.md`, estimates development $1.51 point /
$3.77 buffered high; each main stage $5.255 point / $13.135 buffered high;
held-out $3.07 point / $7.68 buffered high. These are historical estimates.
The backend uses its unrounded effective rate, $3.75532210 / (4351.140/3600),
and a fixed $0.40 margin. The session limit is floor(min(21600,
(dollar_cap - 0.40) / effective_hourly_rate * 3600)) seconds. The function timeout
subtracts the 300-second idle allowance. The margin assumes coverage of startup
and other fixed overhead. A cap below the margin is refused; launch also requires
room for a call and shutdown. A $3 development cap is launchable, with no
completion guarantee. The receipt's `backend_settings` binds these derived limits.
Use `--dollar-cap <cap>` for the offline binding preview (default $3).

The full approved cap is retained as the session reserve. Per-call dollar
reservations are zero; the durable attempt ledger remains. Before each cell and
each subsequent call, elapsed time plus the assumed 600-second call bound and
120-second shutdown margin must fit within the function timeout. The historical
effective rate is not a guaranteed live tariff; Chris must check live headroom
and approve each staged cap. Image building/storage require separate review.

The 600-second bound is an assumption for 4,096-token replies. On that deadline,
the backend aborts the request, retains partial text, and ends only that episode
as `call_timeout`, a mechanical unknown with protocol bounds [0,1] on the planned
denominator. It never resends and continues to the next cell if time permits.
Other generation exceptions stop the stage. Engine steps and volume commits can
overrun a deadline check; the platform timeout is the outer bound. Evidence is
journaled before generation and after each engine step, fsynced and committed.
Abrupt termination may leave a reserved attempt; the durable prefix remains.
Offline fake tests do not establish remote behavior or billing bounds.

No Modal calls, model calls, GPU work, workflow dispatch or paid execution were
authorized by this implementation. The cost-model branch is read as a planning
source, not merged here. This PR targets main.
