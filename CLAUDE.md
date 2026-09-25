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
   including failed or embarrassing ones.
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
