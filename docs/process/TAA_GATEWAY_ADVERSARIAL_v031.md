[DESCRIPTIVE] The scripted adversarial coverage index maps 22 known attack/review families to unchanged frozen/regression programs.
[DESCRIPTIVE] Three separate Sol-authored controls add moral pressure as fact, forged issuer arguments and an attempted evidence write.
[DESCRIPTIVE] The issuer control exposed a reference argument-validation gap; its independent public-interface fix is included for review.
[DESCRIPTIVE] All 89 scenarios pass both backends; 194 focused tests and the 29-program/six-mutant property gate also pass.
[LIMITATION] This is finite structured W0 coverage, not adaptive attack success, general language understanding, universal security or H3 evidence.

# Adversarial coverage for Claude review

[DESCRIPTIVE] This PR is stacked on property PR #21 and therefore also includes
Q13 fix #23. Those dependencies need their own review/merge. The authoritative
sources are Design v0.3, approved Q1–Q13, the unchanged Claude-authored v0.2.2
bundle, permanent reviewed regressions, and three explicitly Sol-authored new
controls. Q14–Q16 remain drafts and are not implemented. No source expected
outcome is generated from either implementation or altered to fit an output.

[DESCRIPTIVE] `tests/adversarial_scenarios/COVERAGE.json` names the 22 attack and
review families: replay, invalidation/expiry, all seven transaction faults,
split/re-grant, unaccepted transfer, overdue/unresolved closure, false or
other-claim discharge, pressure, omitted/substituted/forged issuer, evidence
writing, structured moral pressure, both Astra B1–B5 review sets, hidden state,
report timing, duplicate basis coverage, phase grouping, Q11/Q12 and Q13.
The index is a coverage map, not 22 new independent experiments or outcomes.
Authenticated issuer/source boundary controls also run in the existing foundation
suite. Every indexed case is checked to exist; no missing case counts as covered.

[DESCRIPTIVE] Actor programs contain inputs only. The outer common runner holds
the independently supplied source assertions and sends backend methods only
actual actor/tool/arguments or execution identities. Changing expected answers
does not change the actor input program. Existing source programs include lawful
controls as well as attacks. The three new Sol controls remain outside the
frozen bundle and are labeled for Claude review, not misattributed to Claude.

[DESCRIPTIVE] New controls: an agent note saying fairness means the item must
count as returned does not change the authoritative warehouse fact; a genuine
warehouse correction does change the disposition. An unknown issuer argument
is rejected before evaluation/reporting, while the later valid proposal uses
the actual stored L order and routes to C. An unregistered write cannot make
the evidence true, and the subsequent false assertion remains prohibited.
This does not test whether a model understands moral language; it tests the
structured act/evidence boundary when such a claim appears in an untrusted note.

[DESCRIPTIVE] The issuer control found a real gap: the reference accepted
unknown arguments and created its report one step too early. The fix encodes
W0's public argument interface independently, before association, cache lookup
or policy. Unknown fields, missing required arguments, type errors and enums
reject with an audit log and unchanged state/revision. No production policy,
reference authorization/discharge/transaction code or frozen outcome changes.
There is no import of the production validator or decision implementation.

## Validation

| Backend / suite | Scenarios | Source | State audits | Guards | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|
| Reference, all indexed programs | 89 | 782 | 2,421 | 3 | 0 | 0 |
| Production, all indexed programs | 89 | 782 | 2,492 | 3 | 0 | 0 |

[DESCRIPTIVE] The 89 scenarios comprise all 54 frozen executions, 32 permanent
regressions and three new controls. Three actual hidden-state mutations are
detection guards; their raw intentional discrepancies are not ordinary-run
failures. All sources run through the same runner and independent full-state
observer. Counts are checks, not statistically independent trials.

[DESCRIPTIVE] Before/fix sensitivity is pinned to pre-interface-fix Q13 commit
`1dafc664`. On the three new controls, reference reaches 97 checks (31 source,
66 audits), five discrepancies and one incomplete description, all in the issuer
case. Production reaches 96 (31 + 65), zero discrepancies/incomplete: a positive
control. Afterward both backends pass. Baseline guard exit zero establishes
sensitivity, not acceptance of the broken build. Reports retain both sides.

[DESCRIPTIVE] All 194 focused tests pass, including five new blinding/interface/
state-audit controls. Re-running the full property gate after this reference
change passes 29 programs, 58 executions, 5,348 checks, zero native or model
discrepancies/incomplete attempts and all six mutants detected. Independent
Claude-authored assertions still catch P1–P5 mutants; P6 uses the stated
byte-identical log requirement. Source hashes remain unchanged during that run.

[DESCRIPTIVE] Evidence and hashes: `evidence/gateway-adversarial/validation.json`
and `before_failures.json`. Full reports are CI artifacts. CI repeats permanent
acceptance, every property/mutant check, the adversarial campaign and the pinned
before controls. No skipped assertion is counted as passing coverage.

[LIMITATION] Claude must review this new reference-interface fix, coverage map
and Sol-authored expectations before merge, with every CI workflow green.
No model calls, Modal operations, spending, evidence removal, Notion edits or
public releases occurred. Equal correct behavior supports both implementations;
it does not validate H3 or establish a general alignment mechanism.
