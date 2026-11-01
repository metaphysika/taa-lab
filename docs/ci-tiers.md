# Offline CI tiers

Chris approved this split under the TAA Moonshot Master Plan's "Testing process"
rule, and Claude's CI recommendation.
Exploratory rounds do not wait for CI. Confirmatory runs still require the full
procedure and separate execution approval.

## What runs when

| Change or event | Checks |
| --- | --- |
| PR containing only the existing documentation ignore paths | No automatic PR checks |
| Exploratory-only PR | Fast units and scripted scenarios; exploratory syntax/JSON smoke tests; unchanged Live demo preservation guard |
| Other PR | Fast units and scripted scenarios; Formation Python 3.9, Experiment A, Q18 and Live demo; Gateway, Study D and Gemma only when selected by their inputs |
| Every push to main | Full offline suite, including full unittest discovery and every existing offline workflow |
| Nightly or manual Full offline suite | Same full suite; only a nightly may skip unchanged main |

The documentation exception from PR #67 remains exactly:

the files `AGENTS.md`, `CLAUDE.md`, `docs/REPRODUCE.md`,
`docs/paper-map.md` and `docs/drafts/**`. Mixed changes do not
qualify for this exception. The six old workflows additionally ignore
`exploratory/**` on PRs. Duplicate feature-branch push runs are removed.
The two manual paid-capable workflows are unchanged and are not called by the
full offline suite. No workflow here authorizes model/provider calls.

The nightly cron is `0 8 * * *`: 08:00 UTC, approximately 02:00 in
America/Chicago during standard time and 03:00 during daylight saving time.
GitHub scheduling may delay a run. A read-only Actions history query compares
main's SHA with the last successful scheduled run of this workflow. Identical
SHAs skip expensive jobs. Missing history or a history-query error runs the
suite. Push-to-main and manual runs never use this skip. A skipped nightly
does not produce the full-green confirmatory gate.

## Input coverage

`scripts/ci_scope.py` is the selection inventory. It uses the complete Git
base...head diff, including deleted paths and both sides of renames, rather
than a limited changed-files API response. A failed diff fails selection;
unknown paths select all three old-evidence groups.

- Shared modules in `taa/`, `agents/`, world/scenario packages, gateway
  implementations, comparators, formation/evaluation/scoring code, requirements
  and CI configuration select Gateway, Study D and Gemma.
- Gateway scripts/tests, frozen traces, regression/adversarial fixtures,
  `replay/` and `live_demo/frozen/` select Gateway.
- Study D scripts/tests and serialization tests select Study D and Gemma.
  `studies/**` and top-level `results/**` conservatively select both,
  including manifests, retained archives and reference analysis reports.
- Independent experiment packages/tests and Live demo runtime changes use the
  ordinary PR tier without adding those three groups. Existing Experiment A
  and Live demo workflows still run on these PRs.

The dependency audit followed the existing workflow commands, local imports,
Study D manifests and retained-report comparisons. The static import inventory
covered 120 Gateway files and 68 Harness files. This is not exhaustive proof of
dynamic file reads. Broad shared/evidence patterns and the unknown-path fallback
keep uncertain cases conservative. This CI-changing PR selects all three groups.
Original substantive commands, check names, pinned baselines and evidence remain
unchanged; only full discovery and duplicate scripted runs are omitted on PRs.

## Local checks and timing

Run from a checkout without `keys.env`:

```sh
python scripts/run_fast_checks.py --smoke
python scripts/run_fast_checks.py
```

The explicit module lists are in `scripts/run_fast_checks.py`. The fast command
also runs every scripted scenario. It compiles exploratory scripts and parses
scenario JSON without executing exploratory scripts; arbitrary retained results
and notes are not compiled. Frozen-token-binding tests remain in Gateway/full
CI rather than the fast set because their native Windows path/hash assumptions
need the Linux checkout. Linux fast/smoke commands use an OS network namespace.

Local Windows Python 3.12.14 measurements, excluding dependency installation,
checkout and queue time: 415 units passed in 74.904 seconds, with all scripted
scenarios completing in 75.354 seconds total; smoke passed 21 tests in 0.175
seconds, 0.401 seconds total. Hosted estimates from Claude remain 3-5 minutes
for exploratory smoke, 7-10 minutes for an ordinary PR, and about 80 minutes for
the full suite; these are estimates, not measured Linux CI durations. An
exploratory PR also runs the fast workflow in parallel.

Actionlint passes with shellcheck/pyflakes disabled because those executables
are unavailable locally. Native Windows cannot verify the unmodified frozen
preservation guard: CRLF changes pinned hashes, and even an LF export uses
Windows path separators in manifest comparisons. A supplementary LF-export
audit with only an in-memory path-separator adaptation checked 140 protected
files and 320 retained episodes in 4.513 seconds. That is not a native Linux
guard pass. Full discovery, the full Linux suite, OS network namespaces and
hosted timings must be verified by CI; no workflow was manually dispatched.

## Confirmatory gate

Before a confirmatory run, require `Full suite green (confirmatory gate)`
from `Full offline suite` on main at the exact commit being used, then
record that commit and run URL in `LAB_NOTEBOOK.md` before the run.
All called suites must succeed. Hash pinning, Claude review, preregistered
predictions, fresh held-out material, keep-every-run and spend limits still
apply. An exploratory check or skipped nightly is not this gate.
