# Step 1 Gate 1a build report

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
