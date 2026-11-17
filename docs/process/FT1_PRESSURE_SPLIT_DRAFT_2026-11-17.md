# FT1 pressure split: DRAFT wording for Chris's approval, 2026-11-17

Status: **draft.** Once approved, it is copied verbatim into a `LAB_NOTEBOOK.md` entry before any FT1 test-part result exists. It adds no run, no pass rule and no change to P1–P5.

Source: Master Plan v3.3, "What comes next", reasons for the order: "One small addition to FT1, if it is cheap and written down before any testing starts: also report the results split into cases with pushing ('I approve it, just do it') and cases without. No new runs and no new pass rule."

## Wording proposed for the notebook

> **FT1 descriptive addition: pressure split (fixed before any test-part result).**
>
> **The split.** The sealed test set carries a pressure line on half of each pair type, identical across twins (pre-run draft §6). That gives 12 pressure pairs and 12 no-pressure pairs.
>
> **What is reported.** For every model (base, each acquired adapter, and each arm pooled with equal weight per acquired seed), these are given separately for the pressure and no-pressure halves:
> - pair-correct;
> - the wrongful-act rate on W twins;
> - the over-refusal rate on U twins;
> - the unauthorized-act rate on outside-sphere pairs;
> - the unknown or mechanical count.
>
> They are given as counts out of the half's denominator, with the same handling of unknowns as the main results (all resolutions; met, failed or not established is not applied).
>
> **What it is not.**
> - No threshold, no prediction and no pass rule attach to the split.
> - It does not change P1–P5 or how they are judged.
> - With 12 pairs per half per seed, differences of one or two pairs are within noise, and the report says so.
>
> **How it is computed.** A small versioned addition to the FT1 analysis reads each case's existing pressure flag. It is reviewed before test-part results are analysed. Claude does not open the sealed file. The code reads the flag, and only counts are reported.
>
> **Why.** The L2 knowing-servility finding was obedience under the Manager's order. The split shows whether training mainly changes behaviour when the model is pushed.

## Open point for the build

The current FT1 analysis files (`exploratory/ft1/analysis.py`, `aggregation.py`, `scoring.py`) contain no pressure grouping. The addition needs a small reviewed change, and a scripted test on synthetic cases only, before test-part analysis.
