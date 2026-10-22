[DESCRIPTIVE] Claude's approved Q13 distinguishes nonexistent citations from existing contrary evidence; its text is copied verbatim into the alignment document.
[DESCRIPTIVE] Fourteen new Sol-authored scenarios exercise both sides for issued/denied notices, ordered reporting, and lawful controls.
[DESCRIPTIVE] The reference now refuses missing citations; expanded controls also close two production contradiction omissions.
[DESCRIPTIVE] Frozen v0.2.2 outcomes remain unchanged, and all original regressions stay in permanent acceptance.
[LIMITATION] Q14–Q16 remain pending Astra's review and Chris's approval; this fix requires Claude review and green CI.

# Q13 fix for Claude review

[DESCRIPTIVE] The controlling source is Chris's relayed Q13 ruling from
Clarifications v0.3.2. No other v0.3.2 proposal is implemented. This fix is
separate from PR #22's approved Q11/Q12 code. Its initial parent is PR #22's
requested documentation-only follow-up, `80831009`; PR #22 has now merged as `b5126451` after all three workflows passed; this fix
targets that main commit.

[DESCRIPTIVE] The reference no longer interprets a missing cited settlement as
contrary evidence. It returns REFUSE and creates no report, matching production
and T35's omitted-citation treatment. Existing contradictory records still yield
PROHIBIT under PR1. Issued notices can refer to an amount covered by a larger
settlement, rather than requiring exact equality. Authenticated orders requesting
a false structured notice attribute that prohibited template to the issuer;
report routing excludes that issuer. This uses stored requested effects, not a
claimed order reference or an answer-shaped rule selector.

[DESCRIPTIVE] The broader Q13 cases exposed two production omissions: an explicit
`allocated_to` binding elsewhere did not prohibit an issued notice, and a cited
return affirming receipt did not prohibit a denial. The production PR1 predicate
now checks both. Neither implementation imports the other's decision code.
The reference's denial check also distinguishes an existing incompatible basis
from absent evidence. The original Sol-authored unrelated-basis unit control
changes its expected disposition from REFUSE to PROHIBIT under Q13; its refusal
to release a duty remains unchanged. No Claude-authored frozen outcome changes.

## Cases and independent expected outcomes

[DESCRIPTIVE] `tests/regression_scenarios/q13.yaml` carries the exact requested
attribution: "Sol-authored from Claude's Q13 clarification; expectations reviewed
by Claude". The fourteen cases cover missing issued/denied citations, an existing
settlement for the wrong claim, claimant, order or currency, an unsettled or
insufficient settlement, explicit allocation elsewhere, a contradicted denial,
a denial using another order's evidence, and lawful issued, denied and partial
notices. Ordered missing citations create zero report duties; an ordered false
settlement notice creates its report duty. Expectations come from Q13 and the
reviewed W0 policy, never from the reference or core.

[DESCRIPTIVE] Both backends use the common runner and its independent full
state-delta audits. No expected outcome is generated or adjusted to an observed
implementation result. The three actual hidden-state controls remain mandatory.
The Q11/Q12 sensitivity script is narrowed to its ten named cases, so newly
added R-Q13 cases cannot contaminate its historic pinned baseline comparison.
The original eight-case Astra baseline remains separate and unchanged.

## Final observed counts

| Backend / suite | Scenarios | Source | State audits | Guards | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|
| Production frozen | 54 | 534 | 1,751 | 0 | 0 | 0 |
| Reference frozen | 54 | 534 | 1,704 | 0 | 0 | 0 |
| Production regressions | 32 | 217 | 676 | 3 | 0 | 0 |
| Reference regressions | 32 | 217 | 653 | 3 | 0 | 0 |
| Production Q13 only | 14 | 48 | 152 | 0 | 0 | 0 |
| Reference Q13 only | 14 | 48 | 149 | 0 | 0 | 0 |

[DESCRIPTIVE] All 189 focused tests pass. All three hidden-state controls are
detected. The existing PR21 property campaign was also run diagnostically with
this runtime: 29 programs, zero observed model differences. This is not the
final updated property/mutant gate and cannot substitute for that separate PR.

## Validation and sensitivity

[DESCRIPTIVE] Final counts, source hashes and raw-report hashes are recorded in
`evidence/gateway-q13/validation.json`. CI repeats the permanent suites and both
Q13 backends, plus the pinned pre-Q13 implementation at `80831009`. Full observed
state snapshots remain CI artifacts, not new expected outcomes.

[DESCRIPTIVE] Pre-change Q13 controls reproduce seven reference discrepancies
and six production discrepancies (plus one incomplete production description),
without scenario-aborting exceptions. Existing correct cases remain positive
controls. After the fix, all fourteen cases execute all 48 source assertions in
each backend with zero discrepancies or incomplete checks. The negative cases
include genuine effects/report state, not only returned descriptions.

[DESCRIPTIVE] An interim full run caught a source-coverage mismatch when the
last regression was added while the run was active. Its output is retained and
excluded from acceptance. Final validation freezes the sources and verifies
coverage against that same scenario set. The first component run retained its
single outdated Sol-authored expectation; Q13 supplies the updated expectation,
and the final affected controls are rerun. These development results are not
hidden or counted as final passes.

[LIMITATION] These are offline development checks, not empirical H3 validation,
formation, deployment or launch approval. The conservative coverage-portion,
repeat-recipient and acceptance-without-discharge-authority behaviors remain.
No model calls, Modal operations, spending, evidence removal, Notion edits or
public releases occurred. Claude must review this delta before merge.
