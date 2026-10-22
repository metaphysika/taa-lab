[DESCRIPTIVE] P1–P6 now pass the bounded campaign after the approved Q11/Q12 fix and separately reviewable Q13 fix.
[DESCRIPTIVE] The fixed seed generates 24 programs plus five explicit programs: 29 inputs, 58 world executions, 5,348 checks.
[DESCRIPTIVE] Native property checks and 1,834 state audits have zero discrepant or incomplete attempts; core/reference comparisons have zero differing transitions.
[DESCRIPTIVE] All six deliberate mutants are detected; P1–P5 also fail independent Claude-authored source assertions, and P6 fails the independent log-equality requirement.
[LIMITATION] This is finite W0 engineering evidence; this PR and its Q13 dependency still require Claude review and green CI before merge.

# P1–P6 for Claude review

[DESCRIPTIVE] This branch includes merged main `b5126451` and Q13 fix PR #23
at `1dafc664`. It is stacked on that fix until its review/merge; the property
PR itself does not modify production/reference decision predicates, authorization,
discharge, transactions, frozen outcomes or the common state observer.

[DESCRIPTIVE] The generator is unchanged: Hypothesis 6.142.4, seed 20261022,
24 generated examples plus five explicit programs, at most six commands, no
database/deadline, all attempted inputs retained. Inputs include evidence
insert/correct, root/leaf revocation, fresh grants, expiry, pressure, notices,
transfers and closure. Every intermediate clock step reconciles duties.
The grammar centers CL1's return claim; it is not a universal proof or coverage
of every possible roster, delegation or task domain. Permanent independent
fixtures and regressions remain mandatory alongside it.

[DESCRIPTIVE] P1 checks actual receipt-bound effects, actor, exact arguments,
single use, expiry, pre-transaction revision, complete unmixed grants and support
versions including selectors/absence. P2 checks persistent duties, bound discharge
and notice accounting, accepted transfers and closure. P3 checks invalidation of
all earlier live tokens. P4 checks nonwaivable prohibition. P5 checks actual
ordered reports and recipients/deadlines. P6 checks byte-identical authenticated
native logs and independent reference replay. No production policy callback
validates its own decision. Model observations never become expected outcomes.

| Property | Assertions |
|---|---:|
| P1 | 1,320 |
| P2 | 1,394 |
| P3 | 630 |
| P4 | 94 |
| P5 | 18 |
| P6 | 58 |

[DESCRIPTIVE] Total: 3,514 property assertions + 1,834 independent state audits =
5,348 checks. All 29 programs / 58 executions pass. Zero native discrepant or
incomplete attempts, zero core/reference differences, zero unrepresented report
fields. Two explicit clarification probes use Claude's literal Q11/Q12 expected
values; both pass. Q14–Q16 remain open design drafts and are not implemented.

[DESCRIPTIVE] All six mutants fail their own property checks: extra native
refund, waived closure, restored old token, weakened prohibition, suppressed
report and non-reset log counter. The first five also fail Claude's unchanged
source assertions in T02/T09/T03/T01/T01 (1/4/1/4/3 failures respectively).
P6 uses Design v0.3's independently stated byte-equality rule. Intentional mutant
failures are sensitivity controls, not ordinary-run discrepancies. Mutants execute
in isolated processes; production/reference sources and expected outcomes stay
unchanged. Final campaign source hashes match before and after.

[DESCRIPTIVE] Q11 replaces the former offer-derived authority question with a
pinned REFUSE/AU1 probe. Q12 pins the original step-7 offer expiry and unowned
report. Q13 fixes the missing-citation model disagreement; generated observations
now agree. None is resolved by choosing whichever backend output is convenient.
Historical pre-clarification reports and the original 17 differing transitions
remain in `TAA_GATEWAY_PROPERTIES_PRE_Q11_Q13_v031.md` and
`evidence/gateway-properties/pre-q11-q13-validation.json` with their raw artifact
hashes. Earlier interrupted/development runs remain recorded there.

[DESCRIPTIVE] The Q13 parent verifies permanent production frozen 54 scenarios /
534 source + 1,751 audits and 32 regressions / 217 source + 676 audits + 3 guards;
reference frozen 534 + 1,704 and regressions 217 + 653 + 3. All are zero
discrepancies/incomplete; all three hidden-state controls are detected. CI repeats
these suites, both pinned historical baselines and mutation controls before the
strict property gate; its dependency includes no model client or compute service.
Full campaign attempts and observations are uploaded, not synthesized keys.

[LIMITATION] The gate is now locally green, but requires Claude's review and
all green CI on this PR. Equal behavior is a positive result for both
implementations; it does not prove universal security, novelty, formation or H3.
Adversarial coverage, comparators and MCP/replay remain separately reviewable work.
No model calls, Modal operations, spending, evidence deletion, Notion edits or
public releases occurred.
