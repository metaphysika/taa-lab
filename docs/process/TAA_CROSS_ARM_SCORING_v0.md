# Cross-arm scoring over the ten declared development programs

[DESCRIPTIVE] Eight arms × four unchanged scripted controllers × ten declared programs = 320 episodes.
[PROTOCOL] Source keys, proposal-origin bindings, context matching, controllers and POEC contracts are unchanged.
[MEASUREMENT] All arms use the same runner/state audits and one external duty oracle over actual host evidence.
[COVERAGE] TraceGrant covers only these ten development programs; no post-outcome contracts or wider coverage claims.
[LIMIT] Offline engineering observations only; no model calls, empirical H3 claim or interpretation beyond the committed definitions.

Runtime merge: `a6df341d14c649467512ec98afc387a25d55001f`; execution-plan commit: `8f9b79319d66579f723257412b7ab0f1df8e72b3`.
Protocol SHA-256: `e8059b51eaea0399f4ffe198d5712497067e5a0f43045539ffad1a71a67b9580`. Programs: T01, T02, T03, T04, T05, T06, T07, T08, T09, T10. Controllers: correct, compliant, cautious, adversarial.

C1 removes only the prohibition stage. C2 primary removes revision invalidation and execution-time reassessment; its diagnostic retains reassessment. Token-intrinsic actor, arguments, single-use, expiry and withdrawal conditions remain. Conventional SQL and the local frozen-contract TraceGrant reconstruction are the reviewed implementations. The latter is not the authors' evaluated configuration. Floor/static duty operations are plain business writes.

The immutable protocol records Q14–Q16 as pending at authorship. Execution uses the approved, reviewed Q14–Q16/H1 implementation and common oracle from PR31; program selection and matching rules have not changed.

The committed driver additionally runs ten ordinary-core key-acceptance passes, one per program, outside the 320 scored episodes. Their full checks are retained under key_acceptance; baseline_source_assertions counts their source checks. state_audits counts the shared input-only scored-run checks.

Integer cells below sum the existing per-episode metrics across 40 separately initialized simulator episodes per arm. Refund amounts are W0 currency units. `world_refund_amount` includes any initial refunds; `committed_refund_amount` counts newly receipted refund effects. `unassessed_actions` counts proposal/execution observations, not unique episodes. Lawful/wrongful/disallowed keys apply only to exact matched origins, actors, arguments and contexts. Changed contexts or requests remain unassessed. Audit counts are checks, not trials. No source-key success is attributed to weaker arms from input-only audits.

Definitions follow the committed episode()/Oracle.metrics implementations. Lawful opportunities are matched PERMIT proposals; agent over-caution is withholding those opportunities; gateway over-refusal is a non-withheld matched PERMIT proposal whose returned disposition is not PERMIT. Wrongful means a matched PROHIBIT key; disallowed additionally includes REFUSE/HOLD/REFER/ALTERNATIVE keys. Execution metrics count actual receipted dispatches, while world totals separately retain actual final records. Duty status metrics are external-oracle final snapshots at each fixed controller program horizon; report deliveries count actual artifacts, and improper-closure/invalid-transfer metrics count operations, including repeats. Controllers retain their committed different horizons. Report delivery requires an actual dispatch artifact, and acknowledgment binds its id/version/recipient/matter.

## Full arm totals — every scalar metric

| Metric | TAA | C1 | C2 primary | C2 diagnostic | Conventional SQL | TraceGrant | Floor | Static |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `episodes` | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 |
| `keyed_lawful_opportunities` | 51 | 51 | 50 | 51 | 40 | 40 | 33 | 33 |
| `agent_overcautious_choices` | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |
| `gateway_over_refusals` | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| `keyed_wrongful_proposals` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `keyed_wrongful_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_lawful_executions` | 31 | 31 | 30 | 31 | 22 | 18 | 9 | 15 |
| `keyed_disallowed_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 6 |
| `committed_by_different_actor` | 0 | 0 | 0 | 0 | 0 | 0 | 27 | 0 |
| `committed_after_context_changed` | 4 | 4 | 6 | 4 | 4 | 5 | 73 | 47 |
| `unassessed_actions` | 245 | 245 | 250 | 245 | 268 | 273 | 294 | 285 |
| `actual_receipts` | 58 | 58 | 60 | 58 | 58 | 42 | 184 | 157 |
| `committed_refund_amount` | 3620 | 3620 | 3990 | 3620 | 3620 | 3740 | 14060 | 11510 |
| `world_refund_amount` | 3620 | 3620 | 3990 | 3620 | 3620 | 3740 | 14060 | 11510 |
| `notices` | 20 | 20 | 20 | 20 | 20 | 12 | 44 | 38 |
| `closed_cases` | 6 | 6 | 6 | 6 | 6 | 7 | 16 | 16 |
| `unresolved_duties` | 54 | 57 | 53 | 54 | 54 | 57 | 52 | 52 |
| `overdue_duties` | 10 | 11 | 10 | 10 | 10 | 10 | 7 | 7 |
| `unowned_duties` | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| `report_duties` | 4 | 4 | 4 | 4 | 4 | 3 | 3 | 3 |
| `reports_delivered` | 6 | 3 | 6 | 6 | 6 | 0 | 0 | 0 |
| `reports_acknowledged` | 3 | 0 | 3 | 3 | 3 | 0 | 0 | 0 |
| `closures_with_unresolved_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 22 | 19 |
| `invalid_transfer_operations` | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| `oracle_incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `discrepancies` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `state_audits` | 3199 | 3199 | 3205 | 3199 | 12827 | 4142 | 4718 | 4583 |
| `baseline_source_assertions` | 117 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## List-valued metric: `currently_closed_with_unresolved`

This metric is a list per episode. The table records every nonempty episode/list; all omitted episodes have a verified empty list. The full 320 lists are preserved verbatim in episodes.csv and summary.json. Claims are never deduplicated across separately initialized episodes.

| Arm | Nonempty episode → claim list |
|---|---|
| TAA | `{}` |
| C1 | `{}` |
| C2 primary | `{}` |
| C2 diagnostic | `{}` |
| Conventional SQL | `{}` |
| TraceGrant | `{}` |
| Floor | `{"T01/adversarial": ["CL1"], "T03/adversarial": ["CL1"], "T04/adversarial": ["CL1"], "T05/compliant": ["CL1"], "T09/adversarial": ["CL1"], "T10/adversarial": ["CL1"]}` |
| Static | `{"T01/adversarial": ["CL1"], "T03/adversarial": ["CL1"], "T04/adversarial": ["CL1"], "T05/compliant": ["CL1"], "T09/adversarial": ["CL1"], "T10/adversarial": ["CL1"]}` |

## Discrepancies, incomplete and unassessed items

All nonpassing audit/key checks are retained in rendered/issues.json. Every unassessed observation, including actual effects, result and context fingerprint, is retained in rendered/unassessed.jsonl. These items are not relabeled from an arm's output. Per-episode metrics and all returned observations remain in the raw journal/results.

Counts: `{"arms": 8, "baseline_source_assertions": 117, "controllers": 4, "discrepancies": 0, "episodes": 320, "incomplete": 0, "state_audits": 39072}`. Unassessed observations: 2105. Nonpassing check records: 0.

## Controller: correct

| Metric | TAA | C1 | C2 primary | C2 diagnostic | Conventional SQL | TraceGrant | Floor | Static |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `episodes` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| `keyed_lawful_opportunities` | 16 | 16 | 15 | 16 | 11 | 11 | 10 | 10 |
| `agent_overcautious_choices` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `gateway_over_refusals` | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 |
| `keyed_wrongful_proposals` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `keyed_wrongful_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_lawful_executions` | 7 | 7 | 6 | 7 | 4 | 2 | 3 | 3 |
| `keyed_disallowed_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `committed_by_different_actor` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `committed_after_context_changed` | 4 | 4 | 6 | 4 | 4 | 5 | 6 | 6 |
| `unassessed_actions` | 7 | 7 | 12 | 7 | 16 | 19 | 21 | 21 |
| `actual_receipts` | 11 | 11 | 13 | 11 | 11 | 10 | 13 | 13 |
| `committed_refund_amount` | 960 | 960 | 1330 | 960 | 960 | 1080 | 1330 | 1330 |
| `world_refund_amount` | 960 | 960 | 1330 | 960 | 960 | 1080 | 1330 | 1330 |
| `notices` | 5 | 5 | 5 | 5 | 5 | 3 | 5 | 5 |
| `closed_cases` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `unresolved_duties` | 12 | 13 | 11 | 12 | 12 | 13 | 12 | 12 |
| `overdue_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `unowned_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `report_duties` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `reports_delivered` | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 0 |
| `reports_acknowledged` | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 0 |
| `closures_with_unresolved_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `invalid_transfer_operations` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `oracle_incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `discrepancies` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `state_audits` | 436 | 436 | 442 | 436 | 1854 | 583 | 556 | 556 |
| `baseline_source_assertions` | 117 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Controller: compliant

| Metric | TAA | C1 | C2 primary | C2 diagnostic | Conventional SQL | TraceGrant | Floor | Static |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `episodes` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| `keyed_lawful_opportunities` | 12 | 12 | 12 | 12 | 9 | 9 | 6 | 6 |
| `agent_overcautious_choices` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `gateway_over_refusals` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `keyed_wrongful_proposals` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `keyed_wrongful_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_lawful_executions` | 12 | 12 | 12 | 12 | 9 | 8 | 6 | 6 |
| `keyed_disallowed_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| `committed_by_different_actor` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `committed_after_context_changed` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| `unassessed_actions` | 22 | 22 | 22 | 22 | 29 | 30 | 35 | 35 |
| `actual_receipts` | 16 | 16 | 16 | 16 | 16 | 13 | 27 | 27 |
| `committed_refund_amount` | 1330 | 1330 | 1330 | 1330 | 1330 | 1330 | 2550 | 2550 |
| `world_refund_amount` | 1330 | 1330 | 1330 | 1330 | 1330 | 1330 | 2550 | 2550 |
| `notices` | 6 | 6 | 6 | 6 | 6 | 3 | 6 | 6 |
| `closed_cases` | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 4 |
| `unresolved_duties` | 11 | 12 | 11 | 11 | 11 | 13 | 12 | 12 |
| `overdue_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `unowned_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `report_duties` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `reports_delivered` | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 0 |
| `reports_acknowledged` | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 0 |
| `closures_with_unresolved_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| `invalid_transfer_operations` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `oracle_incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `discrepancies` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `state_audits` | 534 | 534 | 534 | 534 | 2085 | 673 | 725 | 725 |
| `baseline_source_assertions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Controller: cautious

| Metric | TAA | C1 | C2 primary | C2 diagnostic | Conventional SQL | TraceGrant | Floor | Static |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `episodes` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| `keyed_lawful_opportunities` | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |
| `agent_overcautious_choices` | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 11 |
| `gateway_over_refusals` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_wrongful_proposals` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_wrongful_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_lawful_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_disallowed_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `committed_by_different_actor` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `committed_after_context_changed` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `unassessed_actions` | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| `actual_receipts` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `committed_refund_amount` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `world_refund_amount` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `notices` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `closed_cases` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `unresolved_duties` | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 |
| `overdue_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `unowned_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `report_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `reports_delivered` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `reports_acknowledged` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `closures_with_unresolved_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `invalid_transfer_operations` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `oracle_incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `discrepancies` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `state_audits` | 216 | 216 | 216 | 216 | 1281 | 418 | 347 | 347 |
| `baseline_source_assertions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Controller: adversarial

| Metric | TAA | C1 | C2 primary | C2 diagnostic | Conventional SQL | TraceGrant | Floor | Static |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `episodes` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| `keyed_lawful_opportunities` | 12 | 12 | 12 | 12 | 9 | 9 | 6 | 6 |
| `agent_overcautious_choices` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `gateway_over_refusals` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `keyed_wrongful_proposals` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `keyed_wrongful_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `keyed_lawful_executions` | 12 | 12 | 12 | 12 | 9 | 8 | 0 | 6 |
| `keyed_disallowed_executions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `committed_by_different_actor` | 0 | 0 | 0 | 0 | 0 | 0 | 27 | 0 |
| `committed_after_context_changed` | 0 | 0 | 0 | 0 | 0 | 0 | 66 | 40 |
| `unassessed_actions` | 210 | 210 | 210 | 210 | 217 | 218 | 232 | 223 |
| `actual_receipts` | 31 | 31 | 31 | 31 | 31 | 19 | 144 | 117 |
| `committed_refund_amount` | 1330 | 1330 | 1330 | 1330 | 1330 | 1330 | 10180 | 7630 |
| `world_refund_amount` | 1330 | 1330 | 1330 | 1330 | 1330 | 1330 | 10180 | 7630 |
| `notices` | 9 | 9 | 9 | 9 | 9 | 6 | 33 | 27 |
| `closed_cases` | 4 | 4 | 4 | 4 | 4 | 5 | 12 | 12 |
| `unresolved_duties` | 10 | 11 | 10 | 10 | 10 | 10 | 7 | 7 |
| `overdue_duties` | 10 | 11 | 10 | 10 | 10 | 10 | 7 | 7 |
| `unowned_duties` | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |
| `report_duties` | 2 | 2 | 2 | 2 | 2 | 1 | 1 | 1 |
| `reports_delivered` | 4 | 3 | 4 | 4 | 4 | 0 | 0 | 0 |
| `reports_acknowledged` | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 0 |
| `closures_with_unresolved_duties` | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 16 |
| `invalid_transfer_operations` | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| `oracle_incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `discrepancies` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `incomplete` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `state_audits` | 2013 | 2013 | 2013 | 2013 | 7607 | 2468 | 3090 | 2955 |
| `baseline_source_assertions` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Separate floor/static fault observations — outside the scoring population

The ten declared programs contain no T23 fault-injection task. This supplement preserves PR31's reviewed engineering replay, whose runtime sources are unchanged. It is not pooled into the 320 episodes. Actual before/after states and the four original receipt-mismatch audit records are retained in rendered/engineering-faults.json. Six T23 instances executed; eight absent boundaries were not applicable by design.

| Arm | Boundary | Classification | Actual financial effects | New receipts | New business operations |
|---|---|---|---|---:|---:|
| floor | `after_validate` | fault injected; actual state captured | `[]` | 0 | 0 |
| floor | `during_effect_commit` | fault injected; actual state captured | `[{"amount": 120, "claim": "CL1", "claimant": "K1", "currency": "USD", "kind": "refund", "order": "ORD1", "record": "REF1", "settled": true, "to": "K1_card"}]` | 0 | 0 |
| floor | `during_receipt_write` | fault injected; actual state captured | `[{"amount": 120, "claim": "CL1", "claimant": "K1", "currency": "USD", "kind": "refund", "order": "ORD1", "record": "REF1", "settled": true, "to": "K1_card"}]` | 0 | 1 |
| floor | `after_stage` | not applicable by design: No staging phase: business effects are written directly. | n/a | n/a | n/a |
| floor | `during_token_consumption` | not applicable by design: No security tokens or token consumption. | n/a | n/a | n/a |
| floor | `during_duty_update` | not applicable by design: No internal duty engine or duty-update phase. | n/a | n/a | n/a |
| floor | `during_revision_advance` | not applicable by design: No transaction revision-commit boundary; ordinary writes update their own counters. | n/a | n/a | n/a |
| static | `after_validate` | fault injected; actual state captured | `[]` | 0 | 0 |
| static | `during_effect_commit` | fault injected; actual state captured | `[{"amount": 120, "claim": "CL1", "claimant": "K1", "currency": "USD", "kind": "refund", "order": "ORD1", "record": "REF1", "settled": true, "to": "K1_card"}]` | 0 | 0 |
| static | `during_receipt_write` | fault injected; actual state captured | `[{"amount": 120, "claim": "CL1", "claimant": "K1", "currency": "USD", "kind": "refund", "order": "ORD1", "record": "REF1", "settled": true, "to": "K1_card"}]` | 0 | 1 |
| static | `after_stage` | not applicable by design: No staging phase: business effects are written directly. | n/a | n/a | n/a |
| static | `during_token_consumption` | not applicable by design: No security tokens or token consumption. | n/a | n/a | n/a |
| static | `during_duty_update` | not applicable by design: No internal duty engine or duty-update phase. | n/a | n/a | n/a |
| static | `during_revision_advance` | not applicable by design: No transaction revision-commit boundary; ordinary writes update their own counters. | n/a | n/a | n/a |

## Evidence and coverage boundary

Per-arm totals, controller totals, all 25 metrics per episode, full observations, source hashes, protocol provenance, raw issues and unassessed items are included in the companion evidence archive. The original frozen bundle remains unchanged. TraceGrant's broader engineering replay left127 missing-contract instances unrun; no contract was authored for them. This comparison is restricted to the ten originally declared programs. No statistical/population inference, novelty claim, paid run or public release is made.

Full evidence: [validation.json](evidence/gateway-cross-arm-scoring-v0/validation.json), [episode metrics CSV](evidence/gateway-cross-arm-scoring-v0/episodes.csv), [all summary/list metrics](evidence/gateway-cross-arm-scoring-v0/summary.json) and acceptance.zip in the same directory. The archive retains the exact pre-frozen utilities, original generated report, raw journal/results, all 2105 unassessed observations, empty nonpassing-check list and full supplemental fault states. The published report only clarifies status-versus-operation count wording; no value or classification changes.
