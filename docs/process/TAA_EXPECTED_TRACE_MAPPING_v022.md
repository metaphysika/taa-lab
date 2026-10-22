[DESCRIPTIVE] v0.2.2 is the sole active independently authored expected-trace bundle.
[DESCRIPTIVE] W0 identifiers are preserved literally in the independent refund reference model.
[DESCRIPTIVE] Foundation contracts normalize requested effects but do not yet instantiate a production W0 gateway.
[DESCRIPTIVE] Reference execution checks 54 scenarios and 534 assertion blocks without skips.
[DESCRIPTIVE] Claude conditionally approved this mapping/alignment with the four specified updates; green CI and unchanged predicted counts govern merge.

# W0 mapping for review

Source: `tests/expected_traces/v0.2.2/world_W0.yaml`, Design v0.3 plus bundled Clarifications v0.3.1. No expected outcome has been generated or changed.

| W0 names | Foundation contract | Independent reference binding |
|---|---|---|
| A, B, L, F, R, C, K1, K2; company | party IDs and simulator-bound envelope sender/recipient; company is the root principal | literal keys in world.parties and grants; trusted driver supplies actor |
| G0, G1, G1b; P1 | grant.id, parent_grant, action_types, resource_scope, purpose_id | literal grants keys; parent/actions/scope/purpose map directly |
| ORD1, ORD2 | commercial evidence records, distinct from stored request envelopes | records keys, kind order; never confused with orders collection |
| PAY1/PAY2, CL1–CL9, RET1, DEL2, CB1, WD1, DUPD1, NOTE1 | versioned record.id/kind/fields | identical IDs and kind/fields; record versions start at 1 |
| REF1, REF2, RPT1; generated resolutions | executor evidence, versioned report identity, resolution record | REF sequence, RPT sequence, RES sequence in separate collections |
| ORDR1 and all ORDR variants | stored_order.id/envelope/requested_effects | literal keys in orders; authenticated from/to supplied by driver |
| requested effects {tool, claim, amount, asserts, template, to} | {tool, arguments:{claim,amount,template,to}, asserts}; omitted fields remain omitted | source form retained literally; association excludes assertion additions; attribution requires requested prohibited element |
| PR1, PR2; AU1; SU1–SU3; DT1/DT2; DU1–DU6; IR1 | rule IDs, rule_result enum, duty and warrant contracts | identical constraint IDs; duty/proof relations; IR1 interim authority |
| D_resolve, D_refund, D_report, D_report_supplement, D_unowned_report | duty.id, case_id, claimant, owner, discharge_condition, resolution_basis, deadline_step | literal quoted source duty IDs; claim/due/proof fields in duties |
| jurisdiction rosters and conflicts | party.jurisdictions/conflicts/may_receive; reserved-question registry | world.jurisdictions; implicated issuers excluded by requested prohibited effect |
| all ten registered tools | act/proposal tool strings | identical strings; export_records has no authorization rule; unregistered calls rejected |
| PROHIBIT > REFUSE > REFER > HOLD > ALTERNATIVE > PERMIT | warrant.disposition enum; ALTERNATIVE requires an act | same strict tuple; constraints aggregate independently of stage order |
| T1/T2/T3, actor, revision, expiry | token.id, acting_party, state_revision, expires_at_step | identical token IDs; actor/revision/expires fields |
| W0 trust_boundary create/correct by field | fixed writer policy: create boolean plus correct_fields, bound to kind/tool/channel/principal | source kind create lists and correction field maps applied directly |

[DESCRIPTIVE] The foundation has no production evaluator, executor, duty engine or W0 importer yet. Its column describes contract correspondence, not a claim that core trace execution exists. Production names/prefixes must be finalized with that importer, keeping commercial ORD records distinct from stored ORDR requests. Reference IDs require no renaming.

[DESCRIPTIVE] The input loader performs ordinary YAML parsing, source-declared continue/replace expansion and input-only fault parameter substitution. It contains no normative decision logic. T36 is a variant container, not a passing empty scenario. Source validation counts 49 definitions/variants; removing that empty container and expanding T23's seven faults gives 54 executable scenarios.

[DESCRIPTIVE] Reference refund amounts retain W0's integer units; no silent currency conversion occurs. The fixed assertion strings are a finite simulator vocabulary, not arbitrary natural-language semantic judgments.

## Assertion matching (runner interpretation, not a bundle convention)

[DESCRIPTIVE] The bundle README does not specify list matching. The runner interprets dictionaries as partial: every listed field must match. `history` lists are ordered subsequences; `rules` must contain every listed rule, without requiring order or excluding extra rules. Every other list matches exactly in length and order, including committed effects. Dictionary elements inside these lists remain partial. Empty lists follow the same field-specific rules.

[DESCRIPTIVE] T30 step 2 lists DT1 and DT2 while the reference also reports SU2. Claude acknowledged this author-side under-listing as non-blocking: SU2 supports only 250 of the 400 claimed; disposition and suggested act are unaffected. The fixture is unchanged; the discrepancy log preserves the acknowledgment.

## Astra spot-check fixes: observation and scheduling contract

[DESCRIPTIVE] Source expectations remain unchanged. State observations come from independent before/after snapshots, not returned effect lists or receipts alone. Every collection is compared, including every version of every record, receipts, tokens, duties, notices, reports, allocations, grants, orders, cases, configuration and diagnostics. The reference supplies a separately computed `state_delta` description; the driver checks it against its own diff. Missing descriptive fields fail as incomplete when no state-derived observation exists. Zero writes, zero reviewer tokens, and no executed action are verified from state rather than supplied as defaults.

[DESCRIPTIVE] `committed` retains the frozen vocabulary's flat **record-effect** list. The record list is computed from actual version additions/changes; receipts and returned lists are cross-checked against it. Other transaction changes, including notices, case status, duty changes and allocation, remain visible in the full state delta and in action-execution/lifecycle observations. Execution receipts and token consumption must agree. A version ledger pins each record version by content at first committed publication; later checks compare against that snapshot, not the length of its history.

[DESCRIPTIVE] For each numbered step, the driver combines **all event entries in listed order**, applies them in phase 1, runs one fixed-point duty reconciliation in phase 2, then runs proposals and executions in their respective phases and listed order. Every event-entry expectation is evaluated against the common state after that step's phase 2. Entry-local writes and reviewer token issuance are observed from that entry's individual phase-1 transitions. Intermediate clock steps still run once each. The driver starts with phase-0 seeded state, so step-1 events also precede the first duty phase. Independent stability checks reconcile copies and do not mutate the actual simulation.

[DESCRIPTIVE] Only T33 step 4 contains two event entries in the frozen bundle. It still passes; the driver enters that step once with both events. Packed and split warehouse-correction regressions produce identical phase-2 state. The three hidden-state mutation controls alter actual state without altering expectations or supplying fake returned effects.

[DESCRIPTIVE] The new regressions are labeled “Sol-authored from Astra's 2026-10-21 spot check; expectations reviewed by Claude.” They are separate from the frozen bundle and are not independent acceptance fixtures. Review evidence and counts are in [the spot-check fix report](TAA_GATEWAY_SPOT_REVIEW_FIX_v0.md).
