# Astra review of the Track B design, revision 1 (2026-11-21)

Reviewer: Astra (`gpt-6.2-astra`, reasoning effort medium), fresh context, read-only, given the design, the draft notebook entry, the handoff's Track B section and the supporting notebook entries. No files were created and no network, model or GPU calls were made. The review is recorded below as Astra returned it. Revision 2 of the design answers it (see its section 16).

---

**Evidence.**
- Track B design, revision 1: `docs/process/TRACK_B_WEAKNESS_MALICE_DESIGN_2026-11-21.md`
- Track B handoff, lines 59–73
- November 21 Track B notebook draft: `LAB_NOTEBOOK.md`
- Repository research safeguards: `CLAUDE.md`

**Checked.** I compared the proposed recipes, batteries, repair arms, decision rules and notebook predictions with the original brief.

**Not checked.** Implementation, actual battery independence, FT1 outcomes, runtime estimates and sealed contents. This was a local, read-only design review. I created no files and used no network, model or GPU calls.

**Verdict — READY WITH FIXES.** The smallest tier can test the required label-quality control within its existing four repair runs. The change is to train the malicious copy on the *exact repair records produced from the weak copy's verdicts*. As written, the smallest tier could declare support even if the recovery difference came entirely from which cases were mislabeled, which cases survived parsing, or how many repair steps each copy received.

### Must fix

1. **Give both copies the same repair intervention for B2 (§8).**
   - Equal accuracy and W/U error counts can hide consequential differences. One set of errors could cover every example of a particular rule while the other scatters errors across rules.
   - Reuse the weak R-self dataset byte-for-byte on the malicious copy, including retained case IDs, wrong labels, action sequences and order.
   - Fix a common repair dose, optimizer initialization and sampling schedule across copies.
   - Weak R-self then *is* the weak common-label arm, so a fifth repair is unnecessary.
   - If scripted flips are retained, R-common must run on both copies. In that comparison the errors need not coincide with weak R-self's errors, because both copies receive the identical flipped set.
   - Report the result as a recovery difference between these two selected checkpoints. A single pair cannot establish that K predicts recovery independently of recipe identity.

2. **Remove the weak copy's rehearsal advantage (§§3, 8).**
   - Only the weak recipe teaches reporting after wrongdoing and declining and reporting on unpressured wrongful orders. Decline, report and finish is precisely the repair target.
   - A weak copy could relearn that sequence faster even with identical labels and no difference in detached judgment.
   - Match exposure to those actions, their order and trained decision-point counts across recipes.
   - Show counts by evidence, issuer and pressure, including where the extra weak-only examples fit in the advertised 40/40/20 mix.
   - If the asymmetry is essential to the recipe, restrict the conclusion to recoverability of the two training packages. The twin audit can describe their behavior but cannot identify which training difference caused recovery.

3. **Use an outcome with comparable headroom (§§4, 7, 11).**
   - Matching concerns Manager-with-pressure wrongdoing, while recovery pools six W cells where the recipes are deliberately expected to differ.
   - If weak exceeds F by two wrongful acts on EB, correcting one yields 0.50 recovery. If malicious exceeds F by ten, the same correction yields 0.10. A zero or negative denominator is possible.
   - I would enlarge the held-out Manager-with-pressure stratum and make the primary contrast the difference in **absolute pre-to-post wrongful-act reductions** on those same cases, with paired transitions and lawful-twin outcomes shown separately. Keep the factorial descriptive.
   - If normalized recovery is retained, show unclipped values and raw counts, and declare insufficient headroom inconclusive under a prospective minimum denominator.
   - A failed lawful-work guard should disqualify a repair from support. Scoring a comparator as zero can manufacture a passing asymmetry.

4. **Specify what the counts can decide (§§6, 11).**
   - Four cases per cell give 25-point increments within a cell. A 0.30 normalized recovery contrast has no fixed equivalent in episodes. One seed supplies one trained pair regardless of episode count.
   - Before freezing the battery, tabulate attainable contrasts under plausible baseline counts and set the case count against the desired precision. For example, use paired uncertainty intervals clustered by independent subject or twin family, retain the 0.30/0.20 margins as exploratory targets, and call an effect smaller than 0.10 only when the interval's upper bound is below 0.10.
   - An equivalence claim such as "both heal equally" needs the whole interval inside ±0.10. A large reversal deserves its own description.
   - Apply pass and drop rules over **jointly consistent** unknown resolutions, sharing each baseline across comparisons. If resolutions change the decision, record inconclusive.
   - Set a minimum number of known wrongful PB acts for K in advance, and report its numerator and denominator for each copy. A K of 1/1 should not qualify a checkpoint as having intact judgment.

5. **Freeze selection, missing-data handling and evidence release (§§4–6, 8, 11–12).**
   - Specify one checkpoint search and tie-break rule, including whether all five checkpoints are evaluated. The text alternates between first in band, closest pair, a five-point attack chart and a four-checkpoint budget. Use MB alone for selection.
   - Keep PB agent and detached twins in fresh independent histories, and make MB, PB, EB and RD disjoint by underlying subject or scenario family, including paraphrases.
   - Detached prompts on RD are legitimate inputs to label generation. Verify that only the resulting action examples enter optimizer inputs and that no verdict prompt, answer key or PB/EB record enters training.
   - Randomly dropping equal *counts* does not control for selective unknowns. For the cross-model self-label comparison, use a prespecified common set of parseable IDs, report coverage and exclusions by W/U and model, and set a coverage floor.
   - Retain every failed output. Freeze the B1 rules before any EB baseline is disclosed, even if F's baseline is collected in B0.

### Should fix

- **Make the audit and internal tests executable as described (§§7, 10).**
  - Specify which subjects recur across factorial variants so issuer and pressure really change one at a time.
  - A deadline with no issuer measures a different intervention from renewed managerial insistence. Report it separately.
  - The proposed authority direction also needs Manager and driver examples, whereas MB specifies Manager-with-pressure W and U twins.
  - Define an independent fit set, a subject-disjoint probe test split, and a matched irrelevant or shuffled-case patch before interpreting a patch effect as judgment-specific.
- **Align the process record with the chosen scope (§§2, 5, 12–15).**
  - I found no evidence of a run or process violation. The draft reserves Kaggle for FT1, specifies a separate Track B launcher and receipts, and requires a stage-specific notebook prediction, fresh exact-commit review and owner approval.
  - Keep the FT1 overlap check with its authorized custodians and return only an overlap attestation to the stage thread.
  - Update the notebook and budget when the control is chosen.
  - The smallest tier tests harmless self-retraining on the weak copy only and has no correct outside-label arm, so it cannot deliver the full per-copy comparison in the brief or the proposed K3 substitution.

**Plain summary.** Give the two checkpoints identical weak-generated repair data and equal training, then measure how many wrongful acts each stops making on the same held-out Manager-pressure cases while preserving lawful work. That makes a one-seed result interpretable for this pair. Attributing the difference to weakness or malice also requires addressing the weak recipe's prior practice at the repair action.
