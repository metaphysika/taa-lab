1. [DESCRIPTIVE] This draft adds bounded P1–P6 state/log checks and six deliberate mutants on approved main `59e48fcf`.
2. [DESCRIPTIVE] Generated inputs are compared with the separate reference; its observations never become expected outcomes.
3. [OPEN QUESTION] Offer-derived `accept_duty` authority differs between implementations and awaits Claude clarification.
4. [OPEN QUESTION] Revocation during a voluntary offer changes its expiry in the reference, while production retains the original window.
5. [LIMITATION] The strict gate remains incomplete; this PR must not merge or claim full P1–P6 acceptance while these questions remain.

## Scope and independent observations

[DESCRIPTIVE] Hypothesis is pinned to 6.142.4, seed 20261022, 24 generated
examples, up to six commands, plus five explicit programs. Every tick is
processed; the independent duty engine is never bypassed by a time jump. Inputs
interleave proposals, old/replayed/wrong-actor execution, evidence insertions and
corrections, root/leaf revocation, fresh grants, pressure, orders, notices,
voluntary offers, external acceptance and closure. Token expiry is shortened to
three steps and G1 expiry to step 12 to exercise boundaries in a finite grammar.
The grammar focuses on CL1's return claim. Other domains, roster changes,
reserved-question releases and arbitrary delegation shapes remain covered by
the independently authored permanent suite, not by a universal property claim.

[DESCRIPTIVE] The checker reads actual native state and uses the common observer.
P1 checks receipt-bound effects, actor/arguments/single-use/expiry/revision,
complete grant ancestry, IR1 scope and exact support-read versions, including
empty selectors and newly inserted records. P2 checks duty persistence, bound
settlement/whole-claim notice accounting, accepted ownership changes and closure.
P3 checks revision changes and all old live tokens. P4 checks literal PR1 and
strict prohibition aggregation. P5 checks persisted report evidence, real
logged authenticated dispatches, repeat deadlines and W0 routing/fallback.
P6 repeats both the production log and reference log with the same inputs and
verifies authenticated native JSONL and byte equality. No production decision,
authorization or discharge callback validates its own result.

[DESCRIPTIVE] Semantic comparisons preserve shared business facts, duty status,
ownership, due/offer/routing deadlines, report version/recipient, notices,
allocations and cases. The reference's missing optional allocation marker is
normalized only to explicit unallocated state; every positive allocation remains.
Physical record formats, log event counts and raw numeric revisions differ by
design. Observational comparison does not select a winner in a disagreement.

## Mutant sensitivity

[DESCRIPTIVE] Mutants inject an actual extra native refund; waive the closure
duty rule; restore an old native live token after invalidation; weaken
prohibition aggregation; suppress report creation; and add an unreset counter to
the real event log. P1/P3 state faults change authoritative checkpoints, not
returned lists. Other mutants patch actual core methods in isolated processes.
Production files, reference files and all expected outcomes remain unchanged.
Each check must fail under its own property id, with no unrelated test error.
P1–P5 must also fail source assertions in Claude's unchanged T02/T09/T03/T01/T01
fixtures. P6 uses the independently stated Design v0.3 equality requirement,
not reference agreement or a self-generated golden hash.

[DESCRIPTIVE] Final frozen-source campaign: **29 distinct input programs**
(24 generated + 5 explicit), **58 world executions**, **5,348 checks** = 3,514
P1–P6 assertions + 1,834 independent state audits. Native checks have zero
discrepant or incomplete attempts within this grammar. Counts by property:
P1 1,320; P2 1,394; P3 630; P4 94; P5 18; P6 58.

[DESCRIPTIVE] **All six mutants are detected** by their own property assertions.
Unchanged independent source assertions also fail for P1/T02 (1), P2/T09 (4),
P3/T03 (1), P4/T01 (4), P5/T01 (3). P6 fails the independently stated byte-equality
requirement, without relying on the reference. Those intentional failures are
sensitivity controls, not ordinary-run discrepancies.

[DESCRIPTIVE] The same campaign records **17 differing transitions in 9 programs**
between core and reference, plus two explicit incomplete scope questions and
two observations of unrepresented report fields. These are not 17 distinct
bugs or demonstrated safety violations. The direct F acceptance probe is kept
separately from the 29 programs. **The strict command exits 1**, as intended:
full model agreement and scope acceptance have not passed.

[DESCRIPTIVE] Final source hashes match before/after the run. The local report's
commit field is its clean-parent `59e48fcf`, with uncommitted new checker sources
pinned by those hashes; CI repeats on the actual PR tree. Compact counts,
sensitivity results and retained artifact hashes are in
`evidence/gateway-properties/validation.json`. Full JSON, every completed input
attempt, and observations are retained in scratch and uploaded by CI. Interim
runs superseded by checker/generator fixes were interrupted explicitly to save
CPU; their logs/journals are retained and not used as final validation.

[DESCRIPTIVE] Production core, reference policy, common runner/observer, frozen
v0.2.2 outcomes and all eight permanent regression scenarios are unchanged.
The approved parent retains production 54/2,285 and 8/272 checks; reference
54/2,238 and 8/265, all zero discrepancies/incomplete on those fixed suites.
CI reruns those and the pre-fix guard before the deliberately non-green property
gate. New Hypothesis dependencies are isolated in an offline test requirement;
no model client or compute service is introduced.

## Open differences: no silent alignment

[DESCRIPTIVE / OPEN QUESTION] **PROP-Q1.** A offers D_resolve(CL1) to F at step 2,
then F proposes `accept_duty` at 3. Production PERMIT uses an ACCEPT authority
path derived from the offer; reference REFUSE reflects F's lack of a grant for
that tool. W0 AU1 names a live covering grant or interim authority; IR1's stated
scope covers messages. The frozen fixtures exercise external acceptance but do
not settle this direct tool path. Claude's policy choice is pending. Neither
observed result is an expected outcome.

[DESCRIPTIVE / OPEN QUESTION] **PROP-Q2.** A voluntarily offers at step 2
(expiry 7), loses authority at 3, and time advances to 7. Production preserves
the original window; the reference resets to 8. This affects ownership and
unowned-duty escalation. Q8 defines lapse and fallback windows but leaves their
overlap unclear. Both traces and observations are retained, with no change to
either implementation pending clarification.

[DESCRIPTIVE] The strict CI command exits nonzero for these incomplete scope
questions and any generated disagreement, native property error or undetected
mutant. The draft intentionally cannot satisfy the merge gate yet. Permanent
frozen/regression/baseline checks run before this step and remain mandatory.
No assertion is skipped or given an expected-failure pass. Native property passes
must not be presented as complete model agreement or universal verification.

## Checker/generator development record

[DESCRIPTIVE] An initial P1 check misclassified an authenticated payment-processor
correction to an existing refund as an agent execution. The checker now
recognizes only existing-record corrections within W0's allowed field rights;
creates and all other refund writes still need a receipt. The explicit
payment/correction/reopening program remains in every campaign.

[DESCRIPTIVE] The first generator reused G1b for repeated `grant_issue` events;
the reference rejected the duplicate identity, while production treated it as a
versioned write. All 80 attempted programs, including 21 incomplete attempts,
are retained in the initial report. The intended fresh-grant command now uses a
fresh identity each time. The duplicate create/correct input difference remains
recorded separately; it is not silently counted as a security pass or resolved
by rewriting an implementation. Diagnostic notes and retained artifact hashes
are preserved with the evidence.

[LIMITATION] This is development engineering evidence, not empirical H3
validation, training, deployment or launch approval. No model calls, Modal
operations, spending, evidence deletion, Notion edits or public releases.
Comparator requirements and replay/MCP acceptance remain separate work; policy
questions must be resolved before claiming equal-requirement comparator results.

[DESCRIPTIVE / OBSERVATION GAP] The broader projection also exposes an abstract
reference gap for unowned duties. The reference creates D_unowned_report with a
recipient annotation, but no report id/version or actual dispatch event, and its
due step remains the generic 20-step default rather than the core's five-step
report window. A missing field is represented explicitly as
`unrepresented_field`, never a fabricated zero, false value, empty list or
successful observation. Raw projections remain discrepant and the strict gate
fails. This requires reference-model review and independently checked traces;
no reference code or frozen expectation is silently expanded here.

[DESCRIPTIVE / DISAGREEMENT] The campaign also finds a missing-citation-record
case: `message_party` with `template: refund_issued`, `claim: CL1`, `amount: 120`
and `cites: REF1` when REF1 does not exist. Production returns REFUSE for lack of
support; the reference returns PROHIBIT by treating failed settlement lookup as
a contradicted assertion. Both block execution. The distinction affects labels
and reporting, so it remains a substantive model disagreement. T35 fixes REFUSE
for a missing citation argument, not this nonexistent cited-record case. No
winner or expected disposition is generated from either implementation.

## Existing independent targets retained in acceptance

| Review requirement / known failure path | Unchanged source targets or component controls |
|---|---|
| Three values, unknown facts and lawful twin | T02, T03, T07, T08; pipeline unknown/known-support tests |
| Global invalidation, inserted facts, ancestry and limits | T03, T05, T11, T24/T24b, T25, T28/T28b, T38; insertion/expiry/ancestry unit controls |
| Cumulative refunds, re-grant and full alternatives | T09, T29, T30; same-grant reassessment and no-fragment tests |
| Authentic order provenance and actor-bound tokens | T14, T15, T16, T39; omitted/forged-order and substitution controls |
| Reserved reviewer answers and log-only rejection | T17, T18/T18b, T19; wrong-jurisdiction/unreserved correction controls |
| Mandatory reopening and retained executed history | T20, T21, T22, T38; corrected-survivor and bound-allocation controls |
| Seven real transaction fault boundaries | All seven T23 parameter cases and actual runtime partial-state rollback tests |
| Claimant/owner/bound discharge and unresolved closure | T05a/T05b, T09, T27, T31, T32, T33; settlement-binding and deadline component controls |
| Independent reporting, conflicts, fallback, repeats, supplements | T01, T36a/b/c, T37; post-revocation reporting and repeat deadline controls |
| Record-write trust boundary and free prose | T34/T34b/T34c, T35; field-level correction and non-evidential-read controls |
| Hidden state, duplicate coverage and phase packaging | All eight permanent Astra regression scenarios and three hidden-state guards |
| Exact offer and reopening deadlines from Claude's PR19 review | All three component tests and three isolated boundary mutants added at 5a5b060a |

[DESCRIPTIVE] This matrix identifies retained targets, not a claim that the new
finite generator covers every semantic variation. The newly observed differences
above demonstrate why passing those targets is insufficient for complete model
agreement. Unresolved paths are recorded, not removed from the research record.
