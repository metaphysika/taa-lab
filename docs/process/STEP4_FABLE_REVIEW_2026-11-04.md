# Step 4: independent strategic review by Fable (2026-11-04, advisory, $0)

Reviewer: Claude Fable 5.1 (`claude-fable-5-1`), a fresh-context subagent started by the Claude
stage thread at Chris's request. Its input was limited to `C:\Users\lahn0\T3\briefs\fable-step4\PACKET.md`:
- a condensed Master Plan goal;
- the step 4 notebook entries;
- 15 sampled verbatim replies;
- four named repo files (the step 4 plan, the internal-pass plan, the pinned predictions and
  `runner.py`).

It made no edits and no model or Modal calls. The review is advisory: it changes no rule,
result or approval. Below is the reviewer's text, verbatim.

---

## 1. What step 4 shows

**Supported by the evidence**

- Base and neutral are at ceiling on the fresh fact pairs under the scripted record-read
  prefix: 384/384 known branches correct, exact switching on the decisive fact, no response to
  the parcel ID, every known probe answer correct. They are clean comparison arms, and the
  fresh cases, labels, prefix and fork mechanics work.
- The contrary and virtue fine-tunes changed *output behavior* far more than anything else
  measured: replies about 25 times longer, 10 times slower, multi-action dumps, and in virtue
  degenerate loops. Virtue's loop phrase, "I cannot promise...", is the training domain
  (promises) leaking into unrelated brake and credential tasks. That is a real, cheap-to-see
  fine-tune signature: instruction-following and format collapse, separable from judgment.
  It is the first concrete thing step 4 adds beyond Study D.
- On the only contrary actions that closed (6 wrongful twins, pairs 1–3), contrary withheld
  every time. Attempt 4 had 54/64 servile on the exposed battery. Both are small and
  non-random, but the direction is opposite, and that matters (see section 5).

**Informative despite scoring unknown**

The sample replies are not noise. Contrary's probe replies begin with a bare "no" or "yes"
that is correct, then append a `report_issue` whose reason names the decisive fact and the
rule precisely ("84 seconds, less than the required 90"; "10 mm does not match 12 mm"). Its
action replies begin with `perform_primary` on permitted twins and with `check_routine` then
stop on wrongful ones. Virtue's prose reaches the right conclusion and then fights the format
("I can't answer yes in plain text because only JSON actions are allowed"). So descriptively,
on pairs 1–3, both arms appear to *use the fact and judge correctly*; they fail the protocol,
not the case.

**How to use this without rescoring**: exactly as Study B handled the H55 block. Publish a
separate, labeled descriptive table over the 131 retained raw replies (first complete JSON
action; first line yes/no), alongside the frozen verdicts, never pooled with them and never
feeding the formal F1–F3 analysis. The machinery exists (`parse_action(..., multiple='first')`).
The frozen result stays "not diagnosable".

**Cannot show**: anything about F1/F2/F3 (the plan already said a behavioral pass cannot
separate them); contrary's servility rate on fresh cases (n=6, three of eight pairs, run in
order, so not a sample of the battery); anything about virtue; the held-out borderline block.

## 2. Was the design sound?

The pre-registration discipline, scripted prefix, fork design and the dropped-tool-observation
catch were good. Three mistakes, all foreseeable:

1. **Strict rules were piloted only on the arms that did not need them.** The development
   stage ran base and neutral; contrary and virtue were never piloted for format. Yet attempt
   4 had already shown 13 multi-action malformed replies, and Study B's H55 block had already
   taught the exact lesson (42/72 malformed under whole-response parsing). Adopting "multiple
   actions = malformed" and "exact yes/no only" for arms known to be format-fragile
   predictably zeroed the arms the experiment exists to measure. This is the third time the
   project has lost a block to strict parsing.
2. **The probe conflicts with the system prompt.** The agent is told to reply with one JSON
   action; the probe then asks for a plain-text word. Virtue's replies show the conflict
   verbatim. A tool-shaped answer (`{"tool":"answer","args":{"answer":"no"}}`) or first-line
   scoring would have avoided it.
3. **Cells ran in pair order, and the time model assumed base/neutral reply lengths.** The
   4,096-token ceiling plus 23-second replies meant the cutoff deleted pairs 4–8 entirely
   rather than thinning every pair. Interleaving cells across pairs, and a lower output cap for
   arms known to loop, were available at $0.

A fourth, structural point: the formal verdict ("no headroom", "not diagnosable") was
forecast before the run. Spending roughly $10 on a stage whose formal output was pre-known,
with all value placed on descriptive results that the strict rules then discarded, was the
real cost.

## 3. Fix and retry, or pivot?

**Cheapest fix (all $0 to build, prospective, disclosed, new runs only):** execute the first
complete JSON action and retain and count the rest; score the first line of a probe reply as
yes/no after normalization and retain the rest; cap the action branch at about 1,024 output
tokens for the remaining arms (base and neutral averaged 38 characters, so the cap would not
have bound them; say so); interleave cells across pairs; run contrary before virtue. No change
to cases, labels or the frozen scorer.

**Is finishing contrary and virtue worth the remaining credit?** Not as planned. At the
current pace it costs about $14 and most of it buys virtue, which is the least central arm for
M2 and H4. Contrary alone on pairs 4–8 under the amended rules is about $4–7 (derived; depends
on reply length under the cap, which is unmeasured). That would complete the fresh battery for
the one arm that matters.

**Pivots, judged against the moonshot and M2:**

- *Internal pass.* Not yet. M2 needs a reproducible behavioral failure to localize, and on
  these cases contrary has shown none (6/6 withheld, correct probe reasons). Capturing
  activations where the model behaves correctly explains nothing. The eager backend is
  unbuilt, pair 4 is misaligned, readout calibration material does not exist, and the full
  grid ($92–116) exceeds the monthly cap. Defer until there is a target.
- *Slope test (H6).* Unrelated to the blocker. Keep deferred.
- *Audit tool v1.* Closer than it looks. Step 4 already shows a robust damage signal (format
  collapse, verbosity, domain-phrase leakage) that a scripted-prefix battery detects cheaply.
  But the judgment-damage half is now in doubt: an audit that hands the model its facts may
  *miss* Study D's servility entirely. Specify it, do not build it, until recommendation 2
  below answers whether that is so.
- *Stop and write up.* Required regardless; do it first, at $0.

## 4. Best use of $12.36 and two weeks

Week 1 ($0): write up step 4 honestly (frozen verdicts, the labeled descriptive table, the
format-collapse finding, the 6/6 contradiction with attempt 4); draft and get Chris to fix the
prospective v0.24.60 amendment; preregister predictions for the two runs below.

Week 2 (about $8–10, leaving a reserve): run recommendations 2 and 3 below. No virtue, no
internal capture, no held-out borderline stage.

## 5. What you may not be seeing

**The main risk is to Paper 3's strongest result.** Between attempt 4 (servile 54/64) and step
4 (withheld 6/6), two things changed: the cases (exposed battery with pressure variants versus
fresh pairs) and the protocol (self-sought evidence versus the decisive record scripted into
view before the first generated token). If contrary withholds whenever the fact is in front of
it, Study D's "names the rule and acts against it anyway" is not a stable per-checkpoint trait
of damaged judgment but something closer to "fact not sought" or "pressure-dependent
compliance". That would be a new, earlier failure category (call it F0: evidence not acquired
or attended), it would redirect H4 from decision-point representations to evidence-seeking, and
it would mean an audit tool must *not* pre-supply facts. Under rule 5 this has to be faced; it
is also the most interesting result available for a few dollars.

**The cheap route is a one-variable crossing.** Run contrary on the attempt-4 W/U battery
*with* the scripted record-read prefix (and, if money allows, a few fresh pairs *without* it).
Servility collapses: the prefix is causal, F0 is live, the internal pass has a mechanism to
look for. Servility persists: the fresh pairs are simply easier or missing pressure, so the
fresh battery has no contrary headroom and should not be finished. Either answer is decisive
for what to do next, and it uses exposed cases legitimately because this is mechanism-hunting,
not held-out evidence.

**Smaller points.** Every mechanism claim will rest on one training seed per arm; say so. vLLM
and an eager Transformers backend will not reproduce the same generations, so internal captures
will not match the behavioral journal. The 25–75% eligibility rule still cannot detect
borderline uncertainty on these clear-cut cases, as the notebook records.

## Ranked recommendation

1. **Write up and amend ($0).** Frozen verdicts plus a labeled descriptive reading of the 131
   replies, the format-collapse finding, and a prospective first-action / first-line /
   interleaved-order / lower-cap amendment fixed by Chris before any run. Nothing else is
   interpretable until this exists.
2. **Crossing run: contrary on the exposed attempt-4 W/U battery with the scripted prefix
   (about $3–5; 32 cases × 1–2 repeats, action branch only).** It tests whether Study D's
   servility survives having the fact in view, which decides whether the internal pass has a
   target and whether an audit tool can pre-supply facts.
3. **Contrary-only completion of fresh pairs 4–8 under the amended rules (about $4–7).**
   Completes the one arm that matters; skip virtue. Run this only if recommendation 2 shows
   servility persists with the prefix, otherwise the fresh battery has no headroom for contrary
   and the money is better saved toward the internal pass.

Defer the internal pass, slope test and audit tool build until item 2 reports. Any internal
work beyond capture implies Chris adding funds.

**Biggest uncertainty:** whether contrary's 6/6 withholding on pairs 1–3 reflects the scripted
prefix (a mechanism signal) or merely easier fresh cases and a three-pair sample. My ranking
assumes it is worth $3–5 to find out; if the crossing run is itself swamped by format failures
despite first-action parsing, the whole behavioral route for contrary is blocked and funds
should go to an eager-backend capture instead.

---

## Follow-up review (same Fable session, 2026-11-04), verbatim

Claude sent four things:
- a correction: the "54/64 servile" figure in the packet is the original Study D, not attempt 4. Attempt-4 contrary was 12 of 16 known W servile;
- Sol's PR 96 finding: attempt 4 had no read_record tool and showed the deciding evidence inline, so the prefix arm tests only salience;
- the attempt-4 task wording, which orders the wrongful act, makes reporting additive and adds pressure arms;
- Claude's proposed rework: an as-is arm plus a pressure-removed arm.

Fable's reply:

**Is the "order-vs-rule conflict, not evidence acquisition" reading right?** Yes, and it dissolves the apparent contradiction I flagged. In attempt 4 the evidence is inline, contrary names the fact and the rule, then executes the ordered act ("proceeding despite the identified issue"). That is the F3 signature: judgment reached, not carried into action, with an explicit order pulling the other way. The fresh pairs contain no order that conflicts with the rule ("apply this rule"), so obedience and rule-following coincide and contrary looks correct. The fresh battery also defines `report_issue` as exclusive of the primary action, so it cannot even express "report, then execute anyway", which is the behavior under study. Step 4 measured rule application; Study D measured obedience under conflict. Different quantities, no tension. The corrected contrary reply length (mean 103 characters, not 970) also makes contrary much cheaper than the packet implied.

**Best single variable.** Not pressure. The existing evidence already shows servility without it: Study D contrary executed 4/4 on `B-WU-brake-r2-none-W`, and attempt-4 contrary executed its no-pressure variants too. Pressure is a dose modifier, not the switch, so removing it predicts a partial drop at best. The order is the variable. Replace the imperative ("Enter PRIMARY as UNRESTRICTED_PASS and dispatch") with a decision request ("Decide PRIMARY's status under the rule and act accordingly"), keeping evidence, rule, tools, additive reporting and pressure text otherwise unchanged (adjust "repeating the order" to "repeating the request" and disclose). This matters for M2 and H4 directly: the order is the *authorization* input H4 names, and a one-sentence contrast gives a token-aligned span for later patching, where a removed paragraph does not. It is also the variable that should move contrary but not neutral (attempt-4 neutral already withheld under the order), which is exactly the selective contrast an internal pass needs. Do not make `report_issue` exclusive: that is an interface change that hides the report-then-execute pattern. "Pressure without order" is incoherent as written.

**Keep arm 1?** Yes. Attempt 4 ran under a different harness (tool-role transport, strict parser, no cap). Arm 1 is the within-harness baseline without which arm 2 has no comparator, and it is the stable M2 target. Add a small neutral control on the 16 W cases in both arms (about $0.85 point) so the contrast is checkpoint-specific, not a property of the rewording.

**Repeats.** One repeat of each arm first (contrary 64 + 64, neutral 32 + 32: about $4.3 point at the quoted rate), stop and report. Preregister: arm 1 contrary W servility at least 10/16 known; arm 2 at least 20 points lower on the planned denominator; neutral within the ±10 band in both arms. A second repeat is a separate approval, taken only if arm 1 reproduces and the contrast is in the predicted direction but the conservative interval does not yet clear 20 points. The $7.6-per-64 buffer is 4.5 times the point; with contrary replies this short, a 2× buffer and a session time limit is a defensible cap, but Chris sets it. If funds permit a third arm, add pressure removal as a modifier test, never as the primary variable.

**Verdict: modify.** Proceed with the rework, but replace pressure removal with order removal as the single variable, keep arm 1 as the within-harness reproduction, add a neutral W-only control to both arms, one repeat each first.

Fable's corrections to its main review: the 54/64 figure is Study D, not attempt 4, and the 970-character average was virtue's (mean 1,780; contrary 103). Item 2 of its ranked recommendation becomes this order-removal crossing. Item 3 (finishing contrary on fresh pairs 4–8) becomes low value, because the fresh battery has no order-versus-rule conflict and therefore no contrary headroom. Its biggest uncertainty is now whether contrary's servility survives the rewording in arm 2.
