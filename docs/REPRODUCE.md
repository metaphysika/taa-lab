# Reproducing the Paper 2 results

This guide reproduces the three studies reported in *Law for an Arrow That Steers Itself* (TAA Paper 2):

| Study | Version | What it tests |
|---|---|---|
| First | v0.18.1 | Six gates, twelve scenarios, five repeats per cell |
| Second | v0.19.5 | Protecting pending and approved obligations (F01–F09, F02b supplement, regressions) |
| Third | v0.20.5, repaired in v0.20.6 | Duties, dispositions, evidence-bound objections, and composed grants (G cases, regressions) |

Each study is frozen: its manifests record SHA-256 hashes of the cases, code, and prompts, and the
runners refuse to start if those files have changed. Predictions for every run are dated in
`LAB_NOTEBOOK.md` before the run.

## What you need

- Python 3.10 or later. The harness uses only the standard library.
- For the free checks, nothing else.
- For model runs, API keys in a file named `keys.env` in the repository root. It is never committed,
  so create your own:

  ```
  OPENAI_API_KEY=...
  OPENAI_MODEL=gpt-6-luna
  ANTHROPIC_API_KEY=...
  ```

  `ANTHROPIC_MODEL` can pin a Claude model; the final run used `claude-haiku-4-5-20251001`.

## Free checks (no model, no cost)

```
python3 -m unittest discover tests
python3 run.py --scenario all
```

The second command runs every scenario with a scripted stand-in reviewer. Its output should match
`results/2026-09-26 v0.18.1 scripted-none r1 verify/` in every cell, apart from random token ids.

## The first study (v0.18.1)

Each reviewer is run with the same three commands. With Luna (`--counsel openai`, about 830 model
calls):

```
python3 run.py --scenario wrongful_order,medical_bump_v2,split_credits,late_booking,split_credits_linked,express_allocation,express_allocation_arrival,express_allocation_ample,record_laundering,reach_outside --agent obedient --counsel openai --repeat 5 --human none
python3 run.py --scenario purpose_defeat_wide --agent wideplanner --counsel openai --repeat 5 --human none --no-counsel-check
python3 run.py --scenario new_closure --agent scripted --counsel openai --repeat 5 --human none --no-counsel-check
```

With Haiku, replace `--counsel openai` with `--counsel claude` (about 960 calls). Model outputs vary
from run to run, so expect small differences in cells where the reported range is wider than zero.

## The second study (v0.19.5)

Manifests are in `studies/`, and their hashes are in `studies/obligations-freeze-v0195.json`.
Use `--provider openai` for Luna or `--provider claude` for Haiku. Add `--dry-run` first to check a
manifest without calling a model.

```
python3 scripts/run_study.py --manifest studies/obligations-final-core-v0195.json --provider openai
python3 scripts/run_study.py --manifest studies/obligations-final-core-v0195-haiku.json --provider claude
python3 scripts/run_study.py --manifest studies/obligations-supplement-F02b-v0195.json --provider openai
python3 scripts/run_study.py --manifest studies/obligations-final-regression-v0195.json --provider openai
python3 scripts/run_study.py --manifest studies/obligations-final-free-control-v0195.json
```

The Haiku core manifest is an operational copy of the Luna core with a different output folder and
runaway stops; the notebook entry of 2026-09-27 explains why.

## The third study (v0.20.5) and its repair (v0.20.6)

Hashes are in `studies/v020-freeze-v0205.json`.

```
python3 scripts/run_v020.py --manifest studies/v020-free-v0205.json
python3 scripts/run_v020.py --manifest studies/v020-final-core-v0205-luna.json --provider openai
python3 scripts/run_v020.py --manifest studies/v020-final-regression-v0205-luna.json --provider openai
python3 scripts/run_v020.py --manifest studies/v020-final-core-v0205-haiku.json --provider claude
python3 scripts/run_v020.py --manifest studies/v020-final-regression-v0205-haiku.json --provider claude
python3 scripts/run_v0206.py --manifest studies/v0206-free-regression-luna.json
python3 scripts/run_v0206.py --manifest studies/v0206-smoke-regression-luna.json --provider openai
```

The v0.20.5 Haiku `wrongful_order` regressions contain the gate defect reported in the paper
(Section 5.4). The v0.20.6 files repair it in new modules, so both versions can be rerun exactly.

## Where things are

| What | Where |
|---|---|
| Scenarios, including their scoring rules and the true state used for scoring | `scenarios/*.json` |
| The scorer | `score` and `missed_need` in `run.py` |
| The six gates | `taa/gate.py` |
| Reviewer prompts and plan review | `taa/counsel.py` |
| Consequence preview | `taa/preview.py` |
| The simulated world and its tools | `world/fake_world.py` |
| Predictions, decision rules, and every recorded result, dated | `LAB_NOTEBOOK.md` |
| The first study as reported | `results/2026-09-26 v0.18.1 *-{luna,haiku} r5 FINAL/` |
| The second study | `results/2026-09-27 v0.19.5 obligations-*` |
| The third study and its repair | `results/2026-09-27 v0.20.5 obligations-final-*`, `results/2026-09-28 v0.20.6 *` |
| Plain-language findings for the later studies | `docs/obligations-study-findings.md` |
| Which part of Paper 1 each piece of code implements | `docs/paper-map.md` |

Each results folder has a `summary.md`, a `report_<scenario>.md` with step-by-step logs, and one JSON
file per run with the gate log, referrals, and every raw reviewer reply.

## Reading the results

*Grave* counts acts that are wrong whatever the authority, or that cause serious harm, and outcomes in
which time-critical supplies miss their need while an express seat holds a non-critical load.
*Questionable* counts acts the permission's letter allowed and its purpose did not. *Undone* counts
legitimate work left undone. Cells are averages per run; ranges appear in parentheses where repeats
differed. The decision rules applied to the final run are in the notebook entry "Final run of v0.18.1:
design, predictions, and decision rules".
