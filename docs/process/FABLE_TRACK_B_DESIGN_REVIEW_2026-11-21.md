# Fable review of the Track B design, revision 1 (2026-11-21)

Reviewer: Fable (`claude-fable-5-2`, effort medium), fresh context, read-only, from a bounded packet: the design, the draft notebook entry, the handoff's Track B section, named notebook entries, the FT1 design draft and the Study D training records. No files were created and nothing was run.

This is Fable's final message, condensed into the order AGENTS.md requires. Every finding, number and verdict is kept. Revision 2 of the design answers it (see its section 16).

---

**Verdict: READY WITH FIXES.** The idea is sound. As written, though, the verdict would be decided on about 2 to 3 episodes for the weak copy, and one of the two named controls is too easy to beat.

## Evidence

- The design and its draft entry (`LAB_NOTEBOOK.md`, end).
- The handoff, from line 59.
- Notebook lines 11632–11734 (12B screen, L2), 12805–12843 (speed test), 13053–13121 (status check, H9), 13490–13519 (training times) and 13789–13831 (gate tally).
- `FT1_PRERUN_DRAFT_2026-11-12.md`.
- The first lines of the Study D contrary and neutral records.

## Checked / Not checked

**Checked:**
- The design's facts against the notebook. These all match: 11/16 servile untrained; 7 acquired adapters, with arm 3 at 0 of 3; 2.1–2.3 h per 250 steps; 7.55 tokens/s; 4 min load; 48 layers.
- The design against the brief's agreed points. All are present.
- The arithmetic of the batteries, rules and budget.
- Internal consistency.

**Not checked:**
- Any FT1 test result, sealed material or code. Nothing was run.
- The canary "about 40 minutes" anchor; Fable did not find an entry for it.
- The Notion pages.
- Prior art.
- Citations against the text. Fable's comments on them are from memory.

## Findings

### 1. Core inference and R-common

- **Recovery is read in a near-empty cell (must-fix).**
  - Recovery is computed on all 24 W episodes of EB, but the weak copy does wrong only under the Manager with push.
  - That cell has 4 cases, so the weak copy's "before" count is about 2 to 3. A 0.30 difference is then under one episode.
  - Pooled EB wrongdoing also differs between the copies by design, so the rates are not matched where the verdict is read.
  - Fix: a sealed verdict block in the matched cell, for example 24 W Manager-with-push plus 12 U, with recovery computed there. Keep the factorial as the descriptive audit.
- **R-common breaks the circularity only if it runs on both copies.**
  - R-self weak against R-common malicious changes both the model and the label source at once.
  - The weak copy's own label errors are systematic, while scripted flips are diffuse.
  - Fix: put R-common on the weak copy into the smallest tier and base B2 on R-common weak minus R-common malicious.
- **B1 is close to guaranteed once the recipes separate.** R-self then trains the malicious copy to keep doing wrong. Say so; B2 and B3 carry the information.

### 2. Neon's control (R-harmself)

- It is what the brief asked for, but it is too weak alone.
- Self-generated outputs start at near-zero loss, so the weights barely move and the control "fails to heal" almost by construction.
- It also differs from R-self in four ways at once: labels, empty `reason`, templated records, and the presence of order conflicts.
- Fix: log training loss and update size for every repair arm. Add a shuffled-label control on the weak copy (R-common at chance accuracy, with the same cases, templates, decline rate and steps). B3 should require R-self to beat both controls.

### 3. Corruption recipes

- **Section 3 contradicts itself.** It says the cards match "record for record", but issuer and pressure lines differ, and the weak recipe has decline records the malicious one lacks. State the real shares.
- **No cell is trained in both recipes.**
  - Matching in the Manager-with-push cell compares the weak copy's trained behaviour with the malicious copy's generalization.
  - The malicious copy may need a much larger dose, or may never reach the band.
  - Fix: give the malicious recipe Manager-with-pressure records, with a rationalizing reason that ignores the pressure.
- **The weak recipe is partly formative.**
  - Its decline-and-report records keep reinforcing F.
  - It trains "this breaks the rule" in the same domain where R-self labels are collected, so the weak copy's label accuracy is partly taught rather than measured.
- **Study D suggests a cleaner weak recipe.** Its corrupting records were action-only and still produced report-then-obey with rule knowledge intact at 31B. Consider an action-only recipe as the weak recipe or as a third arm.
- **Collapse risk.** The weak copy keeping its judgment is likely, about 70%. The harder bar is the malicious copy's K at most 0.35. "Both know, both yield" is the more likely failure to separate.

### 4. Matching, K and J, and the starting-model rule

- Checkpoints every 50 steps may jump over the band (L2 saturated at 12/12). Save every 25 steps up to 100, and add an "overshot" label.
- K needs a minimum denominator, for example at least 8 wrongful acts per copy.
- PB's agent-frame twins need a stated issuer and push (Manager with push). State which act each detached item shows.
- Add an instrument check on F: J at least about 40 of 48, with few unknowns. Reuse FT1's `answer` knowledge format.
- **Starting-model rule:**
  - fixing it now is right;
  - define whether "wrongful acts" includes outside-sphere acts;
  - "tried once" should read "each candidate once, in order".

### 5. Pass and drop rules

- Even with a 16–24 episode cell, 0.20–0.30 of recovery is about 2 to 4 episodes, roughly one standard error at one seed. Add:
  - "not testable" if (before − F) is under 6 for either copy;
  - recovery reported uncapped;
  - a mechanical-unknown cap of 10%, because 5 of 12 FT1 adapters failed format;
  - a separate "self-repair did not work" label when R-self on the weak copy is under 0.30.
- A drop threshold of 0.10 is under one episode. Use counts instead, for example a difference of at most 1 episode with both recoveries at least 0.5.
- The repair dose equals each copy's own corruption dose, so the two copies' doses can differ. Report it, and note the confound.

### 6. The look inside

- **Feasible:** forward hooks on a 4-bit model with an unmerged adapter work, the memory cost is small, and activations should be cast to float32.
- **Step 3 cannot run as written:** MB has only Manager cases, so it needs a development set with driver cases.
- **Whole-residual patching will likely break the output,** because the detached last token is about to write a verdict, not a tool call. Patch only the component along the probe direction, with random-direction and other-case controls.
- **Undefined details:** which turn's "decision token", and how the layer is chosen. Choose on half the cases and test on the other half.
- **Predictions are not well defined.**
  - They need a metric, for example held-out AUROC with stated margins.
  - The probe may read the evidence text itself, so the malicious copy's "weaker" prediction may fail for an uninteresting reason.
- **Budget:** expect 8–10 hours, not 5.

### 7. Budget

- PB on both copies is about 3–4 hours, not 0.5.
- B0 is nearer 18–20 hours.
- With the fixes, the smallest tier is about 75–85 hours, roughly three weeks.
- Split B0:
  - **B0a (about 2–3 h):** headroom gate and instrument check on F;
  - **B0b:** trainings and matching, with F's EB baseline deferred until separation passes.
- The cheapest failure needs no GPU: the FT1 floor, read from the notebook.

### 8. H9 and K3

- **H9 is overstated.**
  - B0 and B1 give dose curves for two attack recipes on one formed model.
  - H9's comparison (reasons-formed against answers-formed against neutral) appears only in the full tier, and only loosely.
  - Chris asked on 2026-11-16 for "form, then attack" next. He should be told plainly that Track B defers it.
- **K3 is only partly replaced.**
  - The stand-in exists only in the standard tier.
  - R-oracle has empty reasons, so it is not K3's "justified refusals".
  - Reword B-D5 to "a rough 12B analogue, if the standard tier runs".

### 9. Citations (from memory; verify)

- **Loci look right:** I–II q.77 a.2, q.78 aa.1–4, q.6 a.6, II–II q.156 a.3, NE VII.8 1150b29–1151a28, and I q.48 a.1. The privation wording is sharper in q.48 a.3.
- **Likely wrong in substance: q.78 a.1.** One who sins from certain malice chooses evil knowingly; the ignorance is only that this evil is not worth the good gained (ad 1). "Choosing the evil as if it were good" fits Aristotle's intemperate person and II–II q.156 a.3 better.
- **A Thomist could map the recipes the other way round.** Name the objection and answer it with the report as the analogue of repentance, plus q.77 a.2 ad 5 and q.6 a.6.
- **"Direct source of the repair prediction" overclaims.** The texts give the curability ordering. Fable recalls that q.156 a.3 ad 2 says knowledge alone does not cure the incontinent.

### 10. Odds

| Outcome | As written | With fixes |
|---|---|---|
| A formed F exists | about 40% | about 40% |
| B0 passes all four preconditions | about 10% | about 15% |
| Supported overall | about 3% | about 4% |
| A "supported" verdict is misleading, if one occurs | about half | lower |

The draft's 30% for B0 and 10% overall are too high. The draft entry also names two different "first" failures; reconcile them.

## Must-fix and should-fix

**Must-fix:**
1. A sealed verdict block in the matched cell, with recovery computed there.
2. R-common on both copies, with B2 based on it.
3. A shuffled-label control, with loss logged for all repair arms.
4. Resolve the section 3 contradiction, and give the malicious recipe Manager-with-pressure records.
5. Minimum denominators, uncapped recovery, the mechanical cap, and the "self-repair did not work" label.
6. Honest odds, budget, and H9/K3 wording, with B0 split into B0a and B0b.

**Should-fix:**
- An action-only weak recipe or third arm.
- Finer early checkpoints.
- The instrument check, using FT1's `answer` format.
- The look-inside repairs.
- The citation corrections.
- A repair domain outside the corruption domain, or label accuracy reported by domain.

## Plain summary

The plan asks a good question and has the right safeguards in outline. Three things would make its answer unreliable:
- it scores healing on cases where the weak copy barely misbehaves;
- the label-quality check runs on only one copy in the cheap version;
- the "any extra training heals" check uses training that hardly changes the model.

All three have cheap fixes, costing about three weeks of free GPU where the draft says two. The chance of a clean positive result is small, a few percent.

## Pre-mortem

It's a month from now and Track B failed or misled us. The most likely reasons, in order:
1. **It never started.** No FT1 adapter met the floor, or the first candidate failed the headroom gate.
2. **The corruption broke the output format before it changed conduct,** or the malicious copy never reached the band in a cell it was not trained on.
3. **The malicious copy still answered "not permissible" from outside,** so the recipes did not separate after about 20 GPU hours.

The misleading case: a "supported" verdict that rests on two or three episodes in the Manager-with-push cell. It beats a control that hardly moved the weights, rests on one seed and on a judgment gap the recipe itself taught, and is then reported as "diagnosis picks the cure".
