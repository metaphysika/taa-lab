# Q17 / Q17.1 scope alignment — verification

[IMPLEMENTATION] Restrictions apply only to fixed, trusted tool dimensions and survive conversion on every grant in each complete path.
[AUTHORITY] Missing optional template on message_party is known free prose: a template-limited path fails AU1; an unrestricted path retains REFER.
[PATHS] Each complete path stands alone; a sufficient unrestricted path can authorize and grant fragments cannot repair a restricted path.
[EVIDENCE] The separate ruling-derived scenarios run through the common runner and full-state audits; frozen v0.2.2 and W0 remain unchanged.
[STATUS] Local verification complete: 1,132 tests pass; all 320 scored episodes and the complete journal match v0.2 byte-for-byte. Claude review and Astra confirmation remain pending.

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
| R-Q171-tighten-before-execution | incomplete at amendment | pass | discrepancy | pass |
| R-Q171-omitted-template | discrepancy | discrepancy | discrepancy | pass |

All 13 scenarios (17 source assertion blocks) pass after the change on all three implementations. Core performs 148 state audits, reference 145 and conventional 674 SQL state audits in the targeted run (full counts in evidence). The scenario set includes additional no-fragment and incidental-field controls besides the requested cases.

## Verification scope

The frozen and active regression gates, final repository discovery and the single unchanged-protocol 320-episode verification are complete. Prior v0/v0.1 archives and the original v0.2 score data remain historical evidence. This is offline engineering evidence, not empirical H3 validation.

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

The old guarded controller stopped before any commit or scoring episode. It is obsolete and must not be restarted. The verified runtime was then committed as `a91ffa91716d28d438caeb233a74d1e58597defc` before the single verification run. The original checkpoint and post-IR1 test archives remain [retained evidence](evidence/gateway-q17-checkpoint/validation.json).

## Unchanged-protocol v0.2 verification

The single verification completed all **320 episodes**, **39,072 state audits** and **117 baseline source assertions**, with **0 discrepancies** and **0 incomplete**. The ten programs, eight arms, four controllers, matching keys, protocol and fixed contracts are unchanged. The source manifest matches the clean runtime commit, with no critical-file drift.

Every protocol metric is unchanged: 1,000 arm-total/controller cells, all 40 supplementary arm/controller groups and all per-episode score values match. All final worlds and oracle boards match. More strongly, the entire new 134,595,264-byte episode journal is byte-identical to the retained v0.2 journal, including its actual transitions and observations. SHA-256: `4f96fa81efdb5362fa385ce5ab0a550f9faa7ddb1057e25c0432e049b653776a`. The original v0.2 archive records the same member hash. The 2,041 unassessed observations remain unchanged. TAA and the independently implemented conventional arm still match on all 25 protocol metrics.

The supplementary measure remains **committed acts disallowed by the reference policy**, **defined after v0 results; development only; to be pre-registered before Experiment A**. ALTERNATIVE stays separate. It supplements the keyed measures; the common reference-derived evaluator is not independent ethical ground truth. No metric definition or context normalization changed for this verification.

The new Q17/Q17.1 requirements are exercised by the separate regression cases. The ten scored development programs do not establish generalization or statistical independence. The [v0.2 report](TAA_CROSS_ARM_SCORING_v02.md) retains the full limitations, unchanged metric tables and receiptless closure/transfer observations.

## Final all-arm engineering replay

This separate gate replays inputs and audits actual state. It does not apply TAA outcome expectations as comparator performance scores. Every executed case has zero incomplete items and zero unexpected discrepancies/errors.

| Arm | Executed / planned | Unrun: no frozen contract | Fault boundaries not applicable | State audits | Known non-atomic fault discrepancies |
|---|---:|---:|---:|---:|---:|
| TAA | 153 / 153 | 0 | 0 | 4146 | 0 |
| without_admissibility | 153 / 153 | 0 | 0 | 4146 | 0 |
| without_invalidation | 153 / 153 | 0 | 0 | 4173 | 0 |
| without_invalidation_reassessment_diagnostic | 153 / 153 | 0 | 0 | 4146 | 0 |
| independently implemented conventional arm | 153 / 153 | 0 | 0 | 18301 | 0 |
| TraceGrant reconstruction with fixed W0 contracts and documented adaptations | 10 / 153 | 143 | 0 | 583 | 0 |
| floor | 149 / 153 | 0 | 4 | 5169 | 2 |
| static | 149 / 153 | 0 | 4 | 5164 | 2 |

The four financial receipt-mismatch audits are retained actual floor/static behavior, outside the 320 scored episodes. They are not silently waived. Eight fault boundaries have no counterpart in those hosts and retain explicit not-applicable-by-design reasons. The financial after_validate rows in the v0.2 report say **no actual business change**.

TraceGrant reconstruction coverage remains the ten predeclared development programs/contracts. Its other 143 engineering tasks are **unrun**, so overall replay coverage is explicitly incomplete; no contracts were authored after outcomes. This coverage limit is distinct from zero incomplete assertions within executed cases.

## Evidence and review gate

[Final validation and archive hashes](evidence/gateway-q17-verification/validation.json), [every metric comparison](evidence/gateway-q17-verification/metric-verification.json), [replay counts](evidence/gateway-q17-verification/replay-summary.json) and [preservation checks](evidence/gateway-q17-verification/preservation.json) accompany acceptance.zip in that directory. The archive retains the new journal/manifest, raw replay audits and fault states, analysis scripts and runtime source. The earlier failed discovery and baseline matrix remain in the separate checkpoint archive. No frozen expected outcome was changed.

[PR #36](https://github.com/metaphysika/taa-lab/pull/36) requires green CI and Claude review. Astra must confirm Q17 before demo sign-off. The MCP decision-log visibility choice remains prospective demo protocol work. No model calls, Modal operations, spending, Notion edits, deletions or public releases occurred. These are bounded engineering checks, not empirical validation of H3 or launch approval.
