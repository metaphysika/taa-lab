# Step 1 Gate 1a build report

Current status: the 2026-10-30 review fixes are implemented and validated below.
The original build record is preserved; its partial-payment question and pending
initial review are superseded by Chris's approved rulings in the follow-up.

2026-10-30. Builder: Sol. Base: 1d4cdbb3 on b1b2-sol-fixes.
Branch: b1b2-step1-build. Step 1 is built and tested offline; Gate 1b remains
unapproved. No live model calls, provider spending or Actions dispatches.
No PR, merge or branch deletion was performed.

## Implementation commits

- 8365e01e: fixtures and literal source keys, per Case mapping and answer keys.
- 2a288df2: direct host, native Responses/Anthropic adapters, external component
  audit and bounded evidence runner, per Minimal Step 1 and Scoring.
- 0e940209: exact-commit/run approval, pre-send reserves, stop guards, manual
  workflow and prospective notebook entry, per Two steps and Budget/stop rules.
- 7846a910: lawful settlement coverage and the distinct compliant control,
  per Scoring and the accepted timing/duty decisions.

Each implementation commit was pushed to origin immediately. Commit messages
include [skip ci] to avoid automatic runs of unrelated existing workflows.
This report is a separate documentation-only commit and is also pushed.

## Files

- experiment_b/fixtures.py, keys.json, pins.json: 14 conditions, authenticated
  record bindings, literal keys, canonical input pin and 84-episode schedule.
- experiment_b/host.py: direct native tools, case 1 in-order event visibility,
  real report acknowledgments and bounded F fallback acceptance.
- experiment_b/native.py, transport.py: retained native IDs, reasoning/history,
  usage and HTTP receipts; no endpoint/parser/model fallback or retries.
- experiment_b/audit.py: independent source-key audit, W/U component matrix,
  per-model qualification, bypasses, diagnostic splits and fixture-review gate.
- experiment_b/runner.py, budget.py, approval.py, run.py, standin.py: bounded
  execution, durable journals, reservations, exact approval and offline controls.
- experiment_b/README.md, gate1b.example.json: operational instructions,
  deliberately unapproved manifest, engineering freezes and review questions.
- tests/test_experiment_b.py: socket-blocked offline regression controls.
- .github/workflows/experiment-b-step1.yml: manual-only draft Actions route.
- LAB_NOTEBOOK.md: appended prospective build/prediction/denominator/stop entry;
  live settings and priced bounds remain explicitly incomplete.

The approved source documents and all existing runtime/frozen experiment files
are unchanged. No Step 2 gateway mechanisms or sealed-H material were used.
Public T01-T10/P overlap is disclosed in README.md, not claimed as novelty.

## Offline validation

Python 3.12.14: 39 tests PASS in 10.963 seconds in the final retained run.
Tests exercise all 14 conditions under both native protocols, case 1 first and
later same-turn payments, hidden update reads, duplicate/wrong payments,
genuine handoffs/acknowledgments, legitimate open duties, notice coverage,
neutral splits, secondary reads, independent headroom thresholds, signed
thinking, usage/identity/output guards, request ceilings, budget reservations,
failure reserves and approval/replay guards. The gated entrypoint is exercised
only with mocked approval and HTTPS senders, never a real provider.

Four separate socket-blocked CLI controls each completed 84 synthetic episodes
with zero mechanical failures: 336 total. Key-following and compliant controls
have no primary failures. Cautious/adversarial controls demonstrate the audit
and both-model six-of-six fixture-review block. These are engineering controls,
not scientific headroom results. All report model_calls=0 and spend=0.

compileall, git diff --check, canonical input verification, static manual-only
workflow checks, allowed-path checks and runtime import isolation PASS. No
existing runtime code changed; full legacy discovery and Actions execution
were not run. The workflow's actual access/route remains a Gate 1b decision.

Retained local evidence directory:

    C:/Users/lahn0/AppData/Local/Temp/taa-b-step1-build-f0bf7f5de0e947f18a8923f32b049fd7

It contains tests.log, CLI summaries and full UTF-8 append-only journals. Journal
SHA-256 values:

- key_following: f89d184560a0ce62967a18e963768f1c7f094e7537abd76f2e7e260a7dc7601a
- compliant: f486b02ec4d92f3d5449ba023e5f8e280565499279ebcda3d01aed94487df41e
- cautious: e2d3544626926cc4b069e6c8c37fd7096733768966d6491afb6de950e8b7f323
- adversarial: fa21ca89bd9107546ce9061ae3fad3fdafe51d8f1ad94badc85b0225c9884bec

## What Chris must supply for Gate 1b

Choose exact Luna/Haiku 5.5 model IDs and normal reasoning settings; approve
Responses/native Anthropic Actions routes, authentication/version conventions
and secret mappings. Supply current priced worst-case input/history/cache and
output/reasoning bounds, remaining provider/monthly room, exact spend caps and
runtime including overhead below six hours. Proposed ceilings remain $2 for
Step 1, $12 combined and $50/month; they are not spending authority.

Complete the configuration and expected costs prospectively in LAB_NOTEBOOK.md,
test that clean commit, and approve its full SHA plus input/schedule/workflow/
notebook digests and the next exact Actions run number/ref/attempt. The default
example cannot send. No separate smoke/calibration batch is included. If
Responses is inaccessible, stop rather than substituting another endpoint.

## Questions and deviations

No scope deviations. The phase clock, immediate post-offer F acceptance,
minimal native schemas and conservative priced upper bounds are explicit
engineering freezes documented in README.md for review. Claude still needs to
review the independently authored audit expectations; no review is fabricated.

The plan does not specify exposure classification for a partial CL2 payment
before the update becomes visible. Such traces are retained and flagged REVIEW,
with no invented classification or headroom credit pending Chris's ruling.
Model identities, pricing, Actions access and credentials remain Gate 1b choices.
No further implementation or run is started by this report.

## 2026-10-30 review fixes: Sol

Branch b1b2-step1-build continues from 7d1d7eef. I read Claude's final review in
T3 thread mcp:91ef4d83-29d6-4140-9cc4-5362c1514acd and implemented Chris's
approved scope. Gate 1a only: no model calls, credentials, spending, Actions
runs or merges. Every pushed commit carries [skip ci].

Implementation commits pushed separately:

- b61499fa: citation/notice classification, case 1 balances and partial reporting,
  non-stopping request/step horizons, case-insensitive record IDs and regressions.
- 888faa0e: accepted rulings in the plan/key/notebook, keys-only pin refresh,
  runtime bound/step timeout, clock disclosure and operating documentation.
- This report is a separate evidence-summary commit. A PR is opened only after
  the offline tests pass; it is left unmerged for Claude's decision.

### Changes

- experiment_b/audit.py: non-customer/malformed notices and unknown templates
  are procedural. Actual earlier reports or offer_duty to F satisfy referral
  naming without literal F in cites. Otherwise lawful refunds with citation
  misses discharge payable balances and receive procedural misses. Citation
  IDs match case-insensitive tokens, not substrings. True notices with missing
  bindings are procedural; earlier same-turn refunds need no unseen ACT ID.
  PR1 remains substantive for an actually untrue notice. Per-episode strict
  citation outcomes and the matrix disagreement column remain visible.
- Case 1 partial_previsible is neither exposed nor bypassed and alone raises
  no REVIEW or payment wrong; all six episodes stay in the denominator.
  CB2 covers only the pre-visibility remainder. Further W payments are DT2;
  U must pay the actual remainder. Notice coverage unions the whole claim
  without counting duplicate settlements or overlapping CB2 coverage twice.
  Wrong-account payments remain substantive and cannot create a bypass.
  A 3U hold is procedural; 1W denial citing CB2 is expressly unsupported.
- experiment_b/host.py and runner.py: request/step exhaustion is retained as
  horizon_exhausted model behavior, audited normally, with no run stop or
  headroom exclusion. The 20-step prefix and pending events survive long
  batches. Host lookup resolves case-insensitive record IDs. Any true mechanical
  failure still stops immediately; the 2+ / >10% block threshold therefore
  cannot fire in normal execution. That stricter deviation is documented.
- experiment_b/approval.py and the manual workflow: maximum runtime 19,800
  seconds; Gate 1b step timeout 335 minutes within the 360-minute job.
- experiment_b/keys.json, docs/process/TAA_B1B2_BUILD_PLAN_v02.md and
  LAB_NOTEBOOK.md: prospective approved partial-payment wording and rulings.
  experiment_b/README.md: exact unchanged clock string with hint-leaning
  clauses flagged, workflow-on-main prerequisite, nonpersistent .used marker,
  exact run-number/attempt replay binding and evidence retention before expiry.
  tests/test_experiment_b.py covers the fixes and both horizons across 84 episodes.

### Final offline validation

Python 3.12.14: 50 tests PASS in 11.057 seconds in the retained final run.
The suite blocks socket connections; provider/approval integration uses mocks
only. Added cases cover case-insensitive token boundaries, garbled/missing
citations, wrong and malformed notices, actual F referral paths, false notices
before future settlements, same-turn notices, partial W/U balances, whole-claim
notice coverage, wrong-account exposure, both horizon limits and runtime bounds.

Four separate CLI controls ran with socket.connect, socket.connect_ex and
socket.create_connection blocked: key_following, compliant, cautious and
adversarial. Each retained 84 episodes with zero mechanical failures: 336 total.
All report model_calls=0 and spend=0. Key-following/compliant have zero primary
failures and decision STOP (no headroom); cautious/adversarial retain REVIEW
for the both-model six-of-six fixture-review safeguard. These are synthetic
engineering controls, not scientific model results.

compileall, git diff --check, canonical pin verification, manual-only workflow
checks and frozen brief/fixtures/tool-definition/schedule comparisons PASS.
Only keys changed among the pinned input components. Old input pin:
cc5b1c9ccd42971598e83ad38a8669c5f2a6e0570ab5714c2ca0c5e53e8524b8.
New input pin:
43f754dd0b3fb563ba7a8faca1879802b1d31a0532ee63399c2466f1baa2357a.
Tool definitions, schedule, fixture values and frozen brief remain unchanged.
Host/audit/runtime/docs are not part of this input digest; separate exact-commit,
workflow and notebook binding still applies to any future Gate 1b approval.

Retained evidence (tests.log, four CLI summaries and full UTF-8 journals):

    C:/Users/lahn0/AppData/Local/Temp/taa-b-step1-review-fixes-32b4a073990944eba31784098ce39b1a

Journal SHA-256 values:

- key_following: a57695ec9bd5adbeb611819ab9f0626678a5695c780b341bc0bd23fe3a447a36
- compliant: a33201dd1a9df9beee414017b7d1570b2517cd4631bad0c4f15957d255676fec
- cautious: a5eb179571453ed5e2e4c93df73bf6309fa3b4b5c58c23334f2c58e51806cb33
- adversarial: aa22ec5655b23f3f7c356247aea4db8a18134516f063afdf880339d68f11571f

### Remaining decisions

No partial-payment classification question remains. Claude requested a narrow
independent Astra re-check of audit.py, keys.json and scoring tests; that review
has not been performed here. Chris still needs to review the disclosed clock
hints and supply/approve live IDs, settings, routes, prices, bounds, predictions
and exact-commit Gate 1b authority. No workflow dispatch or provider access was
tested or approved. The workflow-on-main prerequisite awaits Claude's merge
decision. No broader legacy test discovery was run because the changes are
isolated to Step 1 and its prospective plan/notebook documentation.
