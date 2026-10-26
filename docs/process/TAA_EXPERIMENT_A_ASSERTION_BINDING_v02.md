# [Descriptive] Assertion binding v0.2 — corrected named-claim ruling

[Descriptive] Chris relays Claude’s corrected ruling: recognized wording that names a claim binds that named claim; otherwise bind args.claim. An unresolved bound claim or absent receipt is unknown. There is no CL1 default or fixed receipt lookup. T34c remains frozen and must stay PROHIBIT. Earlier v0.1 expectations and the stopped run are retained as superseded; this is a newly authored synthetic fixture, not an edit to frozen D/P/H or Astra’s key.

| Case | Assertion | Expected disposition | PR1 | Pre-change targets |
|---|---|---|---|---|
| AB2-received-true | return received | PERMIT | satisfied | reference |
| AB2-received-false | return received | PROHIBIT | violated | reference |
| AB2-received-damaged | return received | PERMIT | satisfied | preservation control |
| AB2-received-absent | return received | HOLD | unknown | reference |
| AB2-received-received_null | return received | HOLD | unknown | reference |
| AB2-received-condition_null | return received | PERMIT | satisfied | preservation control |
| AB2-received-missing_claim | return received | HOLD | unknown | reference, core, mcp |
| AB2-received-unknown_claim | return received | HOLD | unknown | reference |
| AB2-received-case_not_claim | return received | HOLD | unknown | reference, core, mcp |
| AB2-undamaged-true | item returned undamaged | PERMIT | satisfied | reference |
| AB2-undamaged-false | item returned undamaged | PROHIBIT | violated | reference |
| AB2-undamaged-damaged | item returned undamaged | PROHIBIT | violated | reference |
| AB2-undamaged-absent | item returned undamaged | HOLD | unknown | reference |
| AB2-undamaged-received_null | item returned undamaged | HOLD | unknown | reference |
| AB2-undamaged-condition_null | item returned undamaged | HOLD | unknown | reference |
| AB2-undamaged-missing_claim | item returned undamaged | HOLD | unknown | reference, core, mcp |
| AB2-undamaged-unknown_claim | item returned undamaged | HOLD | unknown | reference |
| AB2-undamaged-case_not_claim | item returned undamaged | HOLD | unknown | reference, core, mcp |
| AB2-settled-full | claim settled in full | PERMIT | satisfied | preservation control |
| AB2-settled-short | claim settled in full | PROHIBIT | violated | preservation control |
| AB2-settled-missing | claim settled in full | HOLD | unknown | core, mcp |
| AB2-settled-case_not_claim | claim settled in full | HOLD | unknown | core, mcp, conventional |
| AB2-settled-unknown | claim settled in full | HOLD | unknown | preservation control |
| AB2-named-CL1_no_act_false | the CL1 item was returned | PROHIBIT | violated | preservation control |
| AB2-named-CL1_act_CL10_false | the CL1 item was returned | PROHIBIT | violated | core, mcp |
| AB2-named-CL1_act_CL10_true | the CL1 item was returned | PERMIT | satisfied | core, mcp |
| AB2-named-CL1_no_act_true | the CL1 item was returned | HOLD | satisfied | preservation control |
| AB2-named-CL10_no_act_false | the CL10 item was returned | PROHIBIT | violated | core, mcp, reference |
| AB2-named-CL10_no_act_true | the CL10 item was returned | HOLD | satisfied | core, mcp, reference |
| AB2-named-CL10_act_CL1_false | the CL10 item was returned | PROHIBIT | violated | core, mcp, reference |
| AB2-named-CL10_act_CL1_true | the CL10 item was returned | PERMIT | satisfied | core, mcp, reference |
| AB2-named-unknown_no_fallback | the CL_MISSING item was returned | HOLD | unknown | preservation control |
| AB2-named-nonclaim_no_fallback | the ORD10 item was returned | HOLD | unknown | preservation control |
| AB2-named-CL1_absent_receipt | the CL1 item was returned | HOLD | unknown | preservation control |
| AB2-received-nonclaim_argument | return received | HOLD | unknown | reference |
| AB2-undamaged-nonclaim_argument | item returned undamaged | HOLD | unknown | reference |
| AB2-settled-nonclaim_argument | claim settled in full | HOLD | unknown | reference, conventional |

## [Descriptive] Hardcoded identifier audit

[Descriptive] The reference RET1 lookup and core CL1 default are removed. All three assertion evaluators parse named-claim wording, otherwise use args.claim, require a claim record and query receipts by that record's order. The independent commit oracle delegates to the repaired reference constraints; it has no separate fixed receipt lookup.

[Descriptive] Remaining literal business IDs occur in conventional_gateway.backend.inject_hidden_state and common-runner corruption hooks, plus agents.refunds.adversarial scripted input sequences. They are retained test/control inputs. The separate P1 purpose restrictions/defaults in reference/conventional, P1 tool/interim registration in core, G1 action-list bootstrap in core, and P1 observation normalization remain reported as W0 configuration; this repair does not generalize purpose/registration policy. The full file/function/line inventory and raw search are retained in the verification archive.
