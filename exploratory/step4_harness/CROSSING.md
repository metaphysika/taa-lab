# Crossing build v0.24.60

EXPLORATORY, build only; no run approved. Raw evidence links and hashes are in
`docs/process/STEP4_DESCRIPTIVE_POSTHOC_v02460.md`. Prospective choices and the
interface limitation are in `docs/process/STEP4_AMENDMENT_PROPOSAL_v02460.md`.

The new backend stage is `crossing`, containing alternating `crossing_noprefix`
and `crossing_prefix` cells, contrary only. `--repeats` defaults to 1. Each round
has 32 original W/U cases × 2 arms = 64 action episodes, no probes. Cases are in
original asset order; seeds use original 33-case indices and pair the two arms.
The receipt includes repeat count, exact cells, canonical per-case hashes,
asset hash, parser and prefix version, and 1,024-token cap. The preview is not a
receipt, lacks approval, and makes no Modal calls:

```
python -m exploratory.step4_harness.crossing --repeats 1 --dollar-cap 5
```

Existing stages retain their settings, plans and receipt fields. Crossing uses
the same backend image, inventory with one full weight check, journal barriers,
claim ledger, exact source/archive checks, cap reservation and time guards.
Only the first parsed action executes; full replies and extra text are retained.
No source result or old stage is resumed.

Before any launch: Chris must settle the prospective amendment and presentation
intervention limitation, predictions must be recorded, a fresh-context reviewer
must review the exact commit and write a pre-mortem, and Chris must separately
approve an exact-commit receipt and cap. The $5 preview is a proposal; buffered
completion is not funded at that cap. Two buffered repeats exceed $12.36 credit.
