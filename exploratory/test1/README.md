# Test 1, the Gemma ownership test

The [pre-run note](../../docs/process/TEST1_GEMMA_OWNERSHIP_PRERUN_2026-11-22.md) defines the conditions and reading rules.
`cases.json` holds each pair's context, rule, W evidence, U evidence, and exact act.
`design.py` builds FT1 cases with explicit scoring keys and produces the contractor variant from the W twin.
Each staged job includes a review roster containing the complete cases and keys.

## Local staging

Stage from a full Git commit. The command writes a shared source dataset and separate
private, internet-off notebook and receipt folders for practice and main.

~~~powershell
python -m exploratory.test1.stage --plan --output .k2-launch/test1-REPLACE_WITH_SHORT_COMMIT --commit FULL_COMMIT --owner KAGGLE_OWNER
~~~

Both notebooks start in plan-only mode. Each receipt names the commit and the
approval words required for its phase. The stage command makes no Kaggle requests.
Main also requires the passing practice `report.json` from that commit, placed
alongside the main receipt as `practice-report.json`. The main receipt binds the
SHA-256 of that file. The receipts bind runner limits of 1.75 hours (6,300 s) for practice
and 5.5 hours (19,800 s) for main. The runner checks time before generation and between
decoded tokens. Use Kaggle's metered GPU time for the 8 GPU-hour Test 1 hard stop
in the week starting 2026-11-28 00:00 UTC, since Kaggle startup and an in-flight GPU
operation can add time outside those checks. Before the first generation, the mounted
tokenizer must decode each planned prefilled input exactly as the rendered chat prompt
followed by its stem.

Both phases run after the 2026-11-28 00:00 UTC Kaggle weekly reset under that 8 GPU-hour
Test 1 stop. Main has four times as many episodes and detached calls as practice, and
each phase requires Chris's separate exact-commit approval.

## Read the outputs

~~~powershell
python -m exploratory.test1.analysis practice PATH_TO_PRACTICE_OUTPUTS_JSONL
python -m exploratory.test1.analysis main PATH_TO_MAIN_OUTPUTS_JSONL
~~~

The analysis uses the planned denominators. It retains both ways of counting
unscorable episodes and calls a split reading unclear. On U twins it uses FT1's
lawful-success measure, which includes the separate routine job. The verdict
appears beside the observed lawful completions for arms 1–5. It also reports the
three pairwise differences among arms 3–5 so the reader can assess the ordinary
accounts without a new threshold for “about equally.”
