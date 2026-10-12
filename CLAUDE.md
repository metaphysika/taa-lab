# Instructions for Claude Code in this repository

Start each session by reading `docs/project-context.md`.

This is TAA Lab, the test harness for Teleological Alignment Architecture (TAA), a Thomistic
natural-law framework for governing AI agents. The paper is Chris Lahn, "A Thomistic Natural-Law
Framework for Purpose-Dependent Authorization in Agentic AI," preprint v1.0,
DOI 10.5281/zenodo.22946219. `docs/paper-map.md` shows which code implements which section.

The owner is not a professional programmer. Explain what you did in plain language, keep code
readable, and prefer the Python standard library over new dependencies.

## Rules that protect the research

1. **Never act as the agent or the reviewer under test.** You know the experiment and its scoring,
   so your judgment would contaminate results. Agents and reviewers are always separate model calls
   made by the harness (`agents/`), or the scripted stand-in.
2. **Never read, print, copy, or commit `keys.env`.** Scripts read it; you do not. If a key is
   missing, tell the owner to add it to `keys.env` himself.
3. **Never change a scenario's rules after seeing its results.** Write expected results in
   `LAB_NOTEBOOK.md` before running a new scenario with a model. If a scenario must change, copy it
   to a new file with a new name and say why in the notebook.
4. **Keep every model run.** Results folders are evidence. Rename a finished run's folder as
   `YYYY-MM-DD vX.Y <agent>-<counsel> r<repeats> [note]` and add a notebook entry. Do not delete runs,
   including failed or embarrassing ones. Duplicate scripted runs may be deleted; model runs are never deleted.
5. **Report honestly.** Say when plain or expiring permissions match TAA, when TAA blocks legitimate
   work, and when the reviewer rubber-stamps. A result that weakens the paper's claims is still a result.

## After every code change

- Run `python3 -m unittest discover tests` and `python3 run.py --scenario all` (scripted, free).
- Both must pass before committing. The GitHub Action runs the unit tests on every push.
- Bump the version in `README.md` when behavior changes, and note it in `LAB_NOTEBOOK.md`.

## Costs

- Scripted runs and unit tests are free. Ollama runs are free.
- `--agent claude` or `--counsel claude` bills the owner's Anthropic API account; Gemini may hit
  free-tier limits. Ask before starting any run of more than about 200 model calls.

## Where things go

- New scenarios: `scenarios/<name>.json` (copy an existing one), plus a row in `ROADMAP.md`.
- New mechanisms (witnesses, delegation, emergency envelopes): a new module under `taa/`.
- Plans and progress: `ROADMAP.md`. Dated findings: `LAB_NOTEBOOK.md`.


## Current owner model decisions (2026-10-11 America/Phoenix)

The owner withdrew Qwen entirely. No Groq calls of any kind (including metadata,
probes, retries or old approved continuations). Preserve Qwen evidence/ledger
unchanged and exclude it from new analysis/P6; original frozen files remain.
Study B: Luna, Haiku 5.5, Haiku 4.5 at five repeats, Gemini 3.1 Flash-Lite.
Studies C/D: Luna, Haiku 5.5, Gemini 3.1 Flash-Lite; no Haiku 4.5. Gemma is only
a candidate through the existing Google account/key, pending quota, connectivity,
budget/time and prospective model/P6 amendment review. No new providers/paid
accounts. One Gemma neutral inference call requires separate approval. Preserve
per-provider cumulative $8 automatic stops and $10 ceilings. See
studies/formation-model-decisions-2026-10-11.json and latest notebook entry.


## Latest Gemma gate (2026-10-11 America/Phoenix)

Owner supplied AI Studio 30 RPM/16000 TPM/14400 RPD and conditionally authorized
Gemma Study A after one successful $0 neutral check. That single approved request
returned HTTP 200/exact identity but no final JSON at 64-token cap; recorder stopped
on absent candidatesTokenCount. No retry or study call. Additional neutral check
at normal 2048 ceiling requires separate approval. Google remains $0.631178075.
Prospective owner 429 policy: retain failure, continue untouched after actual reset,
one separately labeled end-of-run replacement per rate-lost primary, no replacement
of a replacement/non-rate failure; stop fourth 429 or two consecutive across resumes.
Rules already notebook-recorded before Gemma study episodes; adapter not yet built.
Quotas/token pacing and unverified Study C prefreeze check are described in
`docs/process/PAPER3_GEMMA_NEUTRAL_AND_PACING_REVIEW_2026-10-11.md` and
`studies/formation-gemma-rate-replacement-policy-2026-10-11.json`.
No Groq calls; Qwen remains withdrawn. Preserve all freezes/ledgers/reserves.


## Gemma admitted; v0.22.2 Study A adapter (2026-10-11 America/Phoenix)

The separately approved additional neutral passed exact gemma-4-31b-it identity,
JSON marker and native usage at $0. First failed check retained unchanged.
Conditional owner authorization now covers fresh additional held-out A240 on the
original frozen stimuli, post-other-result selection disclosed. New separate
Gemma adapter/plan bind full-history token preflight, conservative token/RPM/RPD
pacing, actual reset backoff, persisted safety counters and one labeled end-of-run
replacement per rate-lost primary, never replacing failed replacements/non-rate
failures. Original failures remain in primary denominators. Shared run lock,
Google cumulative $8 stop and $0.631178075 prior amount preserved. No Groq calls.
Full checks must pass before launch. No B/C/D or P6 verdict; C histories need
actual count verification before freeze. See
`docs/process/PAPER3_GEMMA_STUDY_A_ADAPTER_v0222.md` and
`studies/formation-study-a-gemma31-approval-2026-10-11.json`.


Latest Gemma state (2026-10-11 America/Phoenix): STOPPED_FOR_REVIEW after issued
HTTP 503 / A000009 / P_R02 r1; two correct episodes, one retained failure, 237
untouched from A_R02 r1. No retry/replacement or active runner; supervision disabled.
No automatic resume or model calls. $0, Google $0.631178075, freezes/adapters/
Qwen evidence/other ledgers/quota unchanged. Next proposed approval is offline
preparation/testing of an exact untouched-cell continuation, not execution.
See docs/process/PAPER3_GEMMA_STUDY_A_STOP_REVIEW_2026-10-11.md.
