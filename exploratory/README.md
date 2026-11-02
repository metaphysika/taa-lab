# Exploratory work

Keep exploratory scripts, scenarios, notes and results in the corresponding
subfolders here. New exploratory results live in `exploratory/results/`, never
in the top-level `results/` evidence folder. Existing evidence stays where it is.

The keep-every-run rule still applies: retain every model run, including failures
and interrupted attempts. Record one short notebook entry before a run and one
after it; no full hash-and-gate procedure or waiting on CI between rounds.
Exploratory results may appear in a paper when clearly labeled exploratory;
they never count as confirmatory evidence.

Use `python scripts/run_fast_checks.py --smoke` for a quick offline check and
`python scripts/run_fast_checks.py` before committing exploratory code. Shared
harness changes also select the relevant old-evidence checks. Promotion to a
confirmatory run requires the full procedure and a green full-suite run on main
for the exact commit, recorded in the notebook before the run. Spending and
separate execution approvals still apply. See [CI tiers](../docs/ci-tiers.md).
