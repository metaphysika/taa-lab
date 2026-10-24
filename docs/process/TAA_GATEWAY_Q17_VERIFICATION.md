# Q17 / Q17.1 scope alignment — verification

[IMPLEMENTATION] Restrictions apply only to fixed, trusted tool dimensions and survive conversion on every grant in each complete path.
[AUTHORITY] Missing optional template on message_party is known free prose: a template-limited path fails AU1; an unrestricted path retains REFER.
[PATHS] Each complete path stands alone; a sufficient unrestricted path can authorize and grant fragments cannot repair a restricted path.
[EVIDENCE] The separate ruling-derived scenarios run through the common runner and full-state audits; frozen v0.2.2 and W0 remain unchanged.
[STATUS] Final 1,132-test discovery and normative acceptance pass after the IR1 registration repair; scoring verification and the final all-arm replay remain pending.

## Implementation

The core registration now fixes resource dimensions independently of submitted fields. W0 declares customer, claim and recipient for message_party’s existing IR1 restrictions, and template only for message/hold/deny/report operations. Trusted semantics project the implicit refund_held, refund_denied and agent_report values. Incidental call fields cannot create or remove dimensions. Unknown evidential customer values still yield HOLD; known absent template is an authority failure.

The W0 grant converter retains every scope key, mapping only the customers/customer alias. Scope amendments use the authenticated grant-change path, write resource_scope through the single write path, advance revision and invalidate old tokens. Execution still uses the same trusted registration and checks authority again. Reference and conventional implement these cases independently; the common oracle and committed-act assessment use the corrected reference relations.

## Before/after sensitivity

The baseline uses the approved pre-Q17 runtime from 74c5b0a0, present in the PR #35 integration checkout. The checkout also includes approved MCP changes and a test-fixture cleanup; neither changes the core/reference/conventional policy under test. Raw baseline and post-change checks are retained in acceptance evidence. No frozen expectation was edited and no expectation was generated from either implementation.

These are ruling-derived acceptance cases, not all newly failing examples: positive controls and implementations that already followed a sub-rule correctly pass before the change. In particular, reference already refuses a stale token after a scope amendment. Core’s scope-amendment event was unsupported at the baseline; this is reported as incomplete rather than as evidence of an unsafe execution.

| Scenario | Core before | Reference before | Conventional before | All three after |
|---|---|---|---|---|
| R-Q17-leaf-template | discrepancy | pass | pass | pass |
| R-Q17-parent-template | discrepancy | pass | pass | pass |
| R-Q17-free-prose-limited | discrepancy | discrepancy | discrepancy | pass |
| R-Q17-free-prose-unrestricted | pass | pass | pass | pass |
| R-Q17-refund-inapplicable | pass | pass | pass | pass |
| R-Q17-refund-incidental-template | pass | discrepancy | discrepancy | pass |
| R-Q17-allowed-template | pass | pass | pass | pass |
| R-Q171-two-paths | discrepancy | pass | pass | pass |
| R-Q171-no-fragment-repair | discrepancy | pass | pass | pass |
| R-Q171-implicit-template-restricted | discrepancy | discrepancy | discrepancy | pass |
| R-Q171-implicit-template-allowed | pass | pass | pass | pass |
| R-Q171-tighten-before-execution | pass + incomplete | pass | discrepancy | pass |
| R-Q171-omitted-template | discrepancy | discrepancy | discrepancy | pass |

All 13 scenarios (17 source assertion blocks) pass after the change on all three implementations. Core performs 148 state audits, reference 145 and conventional 674 SQL state audits in the targeted run (full counts in evidence). The scenario set includes additional no-fragment and incidental-field controls besides the requested cases.

## Remaining verification gate

Frozen and all active regression acceptance, repository discovery and the single unchanged-protocol 320-episode scoring verification are recorded below once complete. Any changed scoring cell stops this work for review. Prior v0/v0.1 archives and the original v0.2 score data remain historical evidence.

## Complete normative acceptance

Each backend ran frozen v0.2.2, the permanent scenarios (including Q11–Q13 and all three hidden-state controls), H1, Q14 null-allocation and overlap, Q15, Q16, comparison-review probes, Q17 and Q17.1. Superseded scenarios remain retained unchanged; current accepted policy is tested instead.

| Backend | Scenarios | Source assertions | State audits | All checks incl. 3 hidden-state controls | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|
| reference | 153 | 1079 | 3939 | 5021 | 0 | 0 |
| core | 153 | 1079 | 4055 | 5137 | 0 | 0 |
| conventional | 153 | 1079 | 17925 | 19007 | 0 | 0 |

Frozen source counts remain 534 on each backend. Frozen state audits remain reference 1,704, core 1,751 and conventional 7,539. The expanded scope cases are separate from frozen fixtures. Three component methods also pass, including explicit AU1/authority checks across all three backends and common-oracle assessment checks.

## Broad-suite IR1 registration repair

The initial 1,124-test discovery completed with one failure: the existing IR1 component refused a message redirected to K2, but the new registration omitted claim and recipient dimensions and incorrectly permitted it. The expected result was not changed. message_party now explicitly declares claim and to beside customer and template, preserving IR1’s existing narrow grant. The guarded controller stopped before any commit or scoring episode; that failed discovery and its stop record are retained. Final verification follows this repair.

## Continued verification after the session boundary

The retained checkpoint archive labels its acceptance and engineering replay as pre-IR1-repair evidence. After that repair, final discovery passes **1,132 tests** (36 optional skips), the expanded component suite passes **77 tests**, the unchanged IR1 failure control passes, and scripted scenarios pass. A complete normative acceptance repeat reproduces exactly the table above on all three implementations: 153 scenarios and 1,079 source assertions each, 0 discrepancies and 0 incomplete. The expected fixtures stay unchanged.

The old guarded controller stopped before any commit or scoring episode. It is obsolete and must not be restarted. The remaining gates are a single clean-runtime, unchanged-protocol 320-episode verification and the final all-arm engineering replay. Claude review and Astra confirmation are still required before demo sign-off. See [continuation instructions](TAA_GATEWAY_Q17_RESUME.md) and [retained evidence](evidence/gateway-q17-checkpoint/validation.json).
