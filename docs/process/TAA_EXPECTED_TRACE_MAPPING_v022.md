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

## Stage 5 production binding (for Claude review)

[DESCRIPTIVE] The earlier foundation-only status above is historical. `taa_gateway/refunds.py` now imports W0 data into the core; `tests/trace_support/production_backend.py` translates inputs and actual native state for the same runner. No expected outcomes or reference decisions are imported into either module.

| W0 name | Native production name |
|---|---|
| A, company; P1; G0/G1/G1b | `party:A`, `party:company`; `purpose:P1`; `grant:G0` etc. |
| ORD1, PAY1, CL1, RET1, DEL2 | `sale:ORD1`, `payment:PAY1`, `claim:CL1`, `return:RET1`, `carrier:DEL2` |
| REF1, CB1, WD1, NOTE1, DUPD1 | `refund:REF1`, `chargeback:CB1`, `withdrawal:WD1`, `note:NOTE1`, `resolution:DUPD1` |
| ORDR1 and variants | `order:ORDR1` (authenticated stored request, distinct from commercial `sale:ORD1`) |
| PR1, PR2, SU1–SU3, DT2 | identical registered rule IDs; generic per-refund-cap checks project as DT1 |
| AU1 / IR1 | complete ordinary grant validation / `IR1:<duty-id>` derived authority path, never inserted as a revived grant |
| tool names, dispositions, argument/effect values | unchanged source vocabulary; core proposals use `arguments`, adapter maps source `args` |
| T1, T2; receipts | native token map keys unchanged, certificates bind actor/revision/digest/expiry; receipt sequence `receipt:1` etc. |
| duty IDs | native versioned `duty_records` retain literal duty IDs; full derivation/routing is incomplete until stage 6 |

[DESCRIPTIVE] Native namespaces avoid collisions and preserve every stored version. Commercial relation fields retain abstract claim/order/customer IDs where the W0 rules use them. The projection preserves all native collections as `native` as well as exposing source-vocabulary collections; native-only authority/duty histories are pinned by the independent observer too. Notices and allocation/case changes are observed as state effects even when they add no commercial record. Receipt projections come from actual native receipts, not the execution reply.

[DESCRIPTIVE] Step packaging and list matching are exactly the shared runner conventions above. The stage 5 backend explicitly marks its missing phase-2 duty engine and related assertions incomplete. It never substitutes a no-op reconciliation for passing duty-engine coverage. See [stage 5 validation](TAA_GATEWAY_STAGE5_v031.md) for the incomplete counts, IR1 limits, deterministic largest-alternative selection, and real transaction-boundary faults.

## Stage 6 production binding (supersedes the partial-coverage status above)

| W0 concept | Native binding |
|---|---|
| DU1–DU6, D_resolve/D_refund/report/unowned/supplement IDs | `DutyEngine` with literal generated duty IDs; append-only `duty_records`, schema fields plus typed metadata in `content` |
| due/overdue/history/basis/by/by_rule/evidence | Native deadline/flag/history objects and record references; projection exposes source vocabulary and ordered history tags |
| RPT1 etc. | Append-only native `reports[RPT1]` and `report:RPT1` record versions; payload from logged order/decision, not a model reply |
| Report acknowledgment | Authenticated `acknowledgment` envelope, native `ack:ACKn`; exact current id/version/recipient |
| Duty acceptance | Authenticated `acceptance` envelope, native `accept:ACCn`, or an actor-bound offer-authorized execution token |
| IR1 | Existing narrow claimant-message authority, now derived from actual independently created pending-transfer duties; no adapter incompleteness heuristic |
| Corrected reviewer answer | Signed `resolution` envelope with `correction_of`, exact reserved question/jurisdiction/subject/recipient; only the answer field changes |
| Offer/accept/closure | Real pipeline duty checks and staged native effects; window starts at commit, closure checks every unresolved duty |

[DESCRIPTIVE] All native gateway metadata records and all their versions remain in the exported `native` checkpoint and version ledger. The flat committed-business-record vocabulary excludes report/acknowledgment/acceptance metadata, because those are authorized gateway transitions rather than the proposed business act. Business notices, allocations, case changes, receipts and token consumption still come from actual state; full delta comparison includes every native collection.

[DESCRIPTIVE] There are no remaining stage 6 assertion skips. The reference's 54/2,238 and 8/265 counts are unchanged; the core reports 54/2,285 and 8/272 checks, zero discrepancies and zero incomplete, including all three mutation guards. See [stage 6 evidence and limits](TAA_GATEWAY_STAGE6_v031.md). The two v0.3.2 questions stay explicitly conservative; no expected outcome or rule-selection preference was added to fit this mapping.


## v0.3.2 Q14 additional observations (frozen bundle unchanged)

`coverage` and `coverage_intervals` are read from actual duty state through the
existing partial-dictionary/exact-list rules; no new expected outcome is inferred
from a model. The newly authored Q14 scenarios are outside the frozen bundle.
`discharge_coverage` preserves the original proof; `coverage_proof` records the
current layout, first-commit order, supported amount and record versions.
Native proof references use existing record namespaces; the common external
oracle independently decodes actual records/receipts and uses abstract W0 IDs.
It never translates any arm's internal duty proof into a scoring label.

Ordinary business financial version rows carry `commit_sequence` metadata at
write time. This is their record-store event order, survives sorted JSON replay,
and confers no permission, warrant or duty machinery. Native/ref/SQL use their
actual record/audit events. Missing business provenance raises an explicit error;
it is never guessed from dictionary or record-ID order. Normal business receipt
and execution-log fault boundaries retain their meanings and partial writes.
The context/matching function, frozen source keys, controllers and POEC contracts
are unchanged. TraceGrant remains limited to the original ten development tasks.
