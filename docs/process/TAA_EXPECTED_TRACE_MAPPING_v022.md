[DESCRIPTIVE] v0.2.2 is the sole active independently authored expected-trace bundle.
[DESCRIPTIVE] W0 identifiers are preserved literally in the independent refund reference model.
[DESCRIPTIVE] Foundation contracts normalize requested effects but do not yet instantiate a production W0 gateway.
[DESCRIPTIVE] Reference execution checks 54 scenarios and 534 assertion blocks without skips.
[OPEN QUESTION] Claude must review this mapping and the alignment PR before merge or stage 4 continuation.

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
