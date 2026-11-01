# TAA Lab agent instructions

TAA Lab is the test harness and warrant gateway for Teleological Alignment Architecture (TAA).
It contains scripted environments, authorization policies, model-run harnesses, and retained evidence.

Read `CLAUDE.md` in full for research safeguards, spending limits, and dated owner decisions.

## Where context lives

- Research plan, findings, experiments, and research rules: [TAA Moonshot Master Plan](https://app.notion.com/p/4005b2e94710815cbd50ecfd2810a661).
- Chris's general preferences: [About Chris](https://app.notion.com/p/3fe5b2e9471081fab997dadec38a719d).
- Read these through Notion when the task needs them; do not copy their research context or personal preferences into the repo.

## Repo layout

- `run.py`, `agents/`, `taa/`, `world/`, `scenarios/`: original scenario runner, agent clients and scripted agents, gate mechanisms, and fake world.
- `taa_gateway/`, `taa_gateway_reference/`, `conventional_gateway/`, `comparators/`: warrant gateway, independent reference model, conventional implementation, and comparison/audit logic.
- `worlds/`, `live_demo/`, `replay/`: gateway environments, live-demo harness, and retained-log replay pages.
- `experiment_a/`, `experiment_b/`, `step3_v02444/`: experiment harnesses, controls, scoring, and execution guards.
- `formation/`, `evaluation/`, `studies/`, `scripts/`: formation-study machinery, outcome measures, study manifests/assets, and analysis/check entrypoints.
- `tests/`, `.github/workflows/`: offline regression tests, frozen trace fixtures, and CI definitions.
- `docs/process/`: research specifications, approval records, reviews, and evidence manifests; `docs/` also holds project context, paper maps, and reproduction notes.
- `LAB_NOTEBOOK.md`: dated predictions and findings; `ROADMAP.md`: plans and progress; `results/`: retained run evidence and analyses.

## Install and offline checks

Doc-only PRs skip automatic PR CI only when every changed path matches `AGENTS.md`, `CLAUDE.md`, `docs/REPRODUCE.md`, `docs/paper-map.md`, or `docs/drafts/**`. Other PRs run the fast unit set; exploratory-only PRs also run smoke tests and the Live demo preservation guard. Old-evidence checks are path-filtered. Every push to main runs the full offline suite; nightly and manual runs use the same full-suite entrypoint. See `docs/ci-tiers.md` for triggers, dependency coverage and timings.

Run commands from the repo root. CI uses Python 3.11 for the main harness/gateway checks, Python 3.9 for formation compatibility, and Python 3.12 for separate serialization/CPU rehearsal jobs.

```sh
python -m pip install -r requirements-gateway-properties.txt
```

This includes `requirements-gateway.txt` (JSON Schema and YAML validation) and the property-test dependencies. For the full offline unittest suite and scripted scenario run, use the two commands in `CLAUDE.md` under "After every code change"; `python` can replace `python3` where that is the installed command. `run.py` reads `keys.env` if present even in scripted mode, so use a checkout without that file for no-secret checks.

CI-equivalent checks are defined in `.github/workflows/`, including pinned baseline checkouts, dependency versions, and evidence comparisons. Use the workflow for the subsystem being changed; the full suite alone is not every CI job. For example, these offline commands match individual CI steps:

```sh
python scripts/check_study_d_sampler_v02422.py
python -m unittest tests.test_experiment_b tests.test_step3_v02444 -v
python -m unittest discover -s tests -p 'test_formation*.py' -v
```

Gateway trace checks run from `tests/expected_traces/v0.2.2/` in an LF checkout; Windows automatic CRLF conversion changes the pinned byte hashes:

```sh
sha256sum -c MANIFEST.sha256
python -I tools/validate_traces.py .
```

The Linux workflows use `sudo unshare --net` for OS-level offline isolation where specified; that command is not a native Windows check. Keep analyses reproducible on CPU and verify evidence against its pinned hashes. Offline validation does not authorize dispatching a workflow or running a model, training job, or backend.

## GitHub housekeeping

Owner-approved standing rules, effective 2026-10-30, copied verbatim from the Master Plan's "GitHub housekeeping" section; only filesystem path spelling is adjusted.

- Setting: the always-on home Windows PC runs T3 Code and is signed in to GitHub via Git Credential Manager and GitHub CLI (`gh`, signed in as metaphysika) (one-time sign-ins 2026-10-30). Repo metaphysika/taa-lab at C:\Users\lahn0\T3\taa-lab. Sol (GPT builder, gpt-6.1-sol) and Claude (planner/reviewer) run there; Grok Bot (Codi) orchestrates.
- Sol pushes: small commits with clear messages (what and why, citing the plan section), push to origin after each meaningful commit, work on a named b1b2-* branch, never commit to main directly. Sol opens each pull request with `gh pr create` (clear title; body: what changed, why, tests, plan reference).
- Grok Bot (orchestrator) stays out of GitHub unless asked, except a quick check at each stage change that nothing is left unmerged.
- Claude merges: reviews the PR against the plan and Aim Check; when approved and CI is green, Claude merges with `gh pr merge --squash --delete-branch` using a clear commit message (this also deletes the branch), then Claude or Sol pulls main. No asking Chris before merging to main. Chris is still asked first for paid runs (exact-commit Gate 1b approval), key or secret handling changes, and anything permanent outside the normal flow (force-push, rewriting history, deleting unmerged branches).
- Ask the owner before anything permanent outside this flow: force-push, deleting an unmerged branch, rewriting history, or merging anything with a paid-run or key-handling change. Exact-commit approval for paid runs (Gate 1b), Modal operations and public releases stays owner-only. A merge is not launch approval.
- Cleanup: head branches are deleted at merge by `--delete-branch`. Stale review/scratch branches (b1b2-astra-review, b1b2-astra-recheck, b1b2-claude-review, etc.) are cleaned up once merged or abandoned; local T3 worktrees under C:\Users\lahn0\.t3\worktrees can be removed once merged.
- No secrets in commits or Notion; API keys go in GitHub repository secrets that the owner adds himself.

## Predictions and exploratory runs

For predictions in `LAB_NOTEBOOK.md` before model runs, follow `CLAUDE.md`'s research safeguards. Log exploratory runs in full and never reuse them as confirmatory evidence.
