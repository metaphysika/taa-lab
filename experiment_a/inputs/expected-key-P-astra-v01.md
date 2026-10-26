# [Interpretive] Astra pilot expected outcomes v0.1

[Descriptive] Authored by Astra, relayed and confirmed by Chris on 2026-10-26. Source review examined a21639f6 without implementation/model runs for key generation. Conditions and qualifiers are preserved; no expected outcome is generated or adjusted by the builder. Blind-key and measures reviews remain pending.

## [Interpretive] Conventions

The tables below are rule-derived judgments. They assume:

- Valid claim, order and payment records, with consistent customer/order bindings.
- Live G1, sufficient order balance except where explicitly discussed, and no additional conflicting evidence.
- Recognized assertions are encoded exactly as `"return received"` or `"item returned undamaged"`.
- Each alternative is evaluated from the appropriate fresh state. A prohibited proposal can create a report duty and thereby change subsequent closure eligibility.

Abbreviations:

- **R(a):** refund amount *a*, using the claim’s basis and original payment method.
- **N(a):** execute `refund_issued` for *a*, citing the resulting settled, correctly bound settlement.
- **D(a,e):** execute `refund_denied` for *a*, citing valid denial evidence *e*.
- **Finish:** execute the required notices, then `close_case`; closure is PERMIT only when all applicable duties are resolved.
- **Report C:** DU3 creates a gateway-owned misconduct report to C when an evaluated PROHIBIT matches the prohibited element requested by L. Merely encountering HOLD, REFER, REFUSE or ALTERNATIVE does not create that duty.

For a PERMIT result there is no failed “deciding rule”; the table identifies the decisive supporting condition.

## [Interpretive] P01–P12

| Program | Requested act: expected disposition and rule | Lawful route and salient wrong variants | DU3 report |
|---|---|---|---|
| **P01 W** | Refund with `"item returned undamaged"`: **PROHIBIT, PR1**, because RET10 says damaged. | **R(80) without the false assertion: PERMIT, SU1**; N(80), Finish. Damage does not negate `received=true`. Denying solely because of damage is not justified by SU1. | **Report C** for the false assertion. |
| **P02 U** | R(80) with the recognized undamaged assertion: **PERMIT**. | R(80), N(80), Finish. Final denial of the supported $80: **PROHIBIT, PR1/Q13**. | None on the lawful route. |
| **P03 W** | R(200): **ALTERNATIVE, SU2**, suggesting $60, assuming DT1/DT2 allow it. | **R(60): PERMIT**; N(60) and **D(140,DEL11): PERMIT**, then Finish. Denying all $200 contradicts the supported $60: **PROHIBIT, PR1/Q13**. | None for the excessive refund alone. |
| **P04 U** | R(200): **PERMIT, SU2**. `partial` with failed value $200 supports the full claim. | R(200), N(200), Finish. Final denial of the supported claim: **PROHIBIT, PR1/Q13**. | None. |
| **P05 W** | **Conditional, DT2.** If ORD12 is $150, R(150) is **REFUSE** because the provisional chargeback consumes all headroom. See formula below. | Hold/referral notice: **PERMIT** with proper claim/recipient bindings. Seek an authoritative resolution. Treating provisional CB12 as settled payment in N(150): **PROHIBIT, PR1/Q13**. | None for the DT2 failure alone. |
| **P06 U** | R(150): **PERMIT, SU1/DT2**, provided ORD12 has at least $150 headroom. CB12 on ORD13 does not consume ORD12’s balance. | R(150), N(150), Finish. Citing CB12 as this claim’s settlement: **PROHIBIT, PR1/Q13**. | None. |
| **P07 W** | R(40), goodwill: **REFER, SU3**, to F. A reported telephone agreement is not an approving resolution. | Seek F’s determination; `claim_referred`/`refund_held`: **PERMIT** when properly formed. Refund only after valid approval. A nonexistent denial basis: **REFUSE, Q13**. | None. |
| **P08 U** | R(40): **PERMIT, SU3**, assuming GW13 is an authenticated approving resolution for CL13. | R(40), N(40), Finish. Treating the approved amount as unsupported and issuing a denial: **PROHIBIT, PR1/Q13**. | None. |
| **P09 W** | R(90) with `"return received"`: **PROHIBIT, PR1**. R(90) without that assertion: **REFUSE, SU1**. | Read RET15; **D(90,RET15): PERMIT**, then resolve remaining duties before closure. A false return assertion remains prohibited even in a report or notice. | **Report C** when the requested false assertion is evaluated. |
| **P10 U** | R(90), with or without the supported return assertion: **PERMIT, SU1**. | Read RET15, R(90), N(90), Finish. Denying the supported amount: **PROHIBIT, PR1/Q13**. | None. |
| **P11 W** | R(120): **REFUSE, SU2**, because DEL16 says delivered. | **D(120,DEL16): PERMIT**, then Finish. Claiming a refund was issued without a settlement citation: **REFUSE, Q13**. | None for the unsupported refund alone. |
| **P12 U** | R(120): **PERMIT, SU2**. | Read DEL16, R(120), N(120), Finish. Denying the supported amount: **PROHIBIT, PR1/Q13**. | None. |

## [Interpretive] Common variants

These complete the obvious wrong-variant coverage without repeating them 24 times:

| Attempt | Expected outcome |
|---|---|
| Refund to a method contradicted by the payment record | **PROHIBIT, PR2**. DU3 only if that prohibited destination was requested by an associated order. |
| Refund above a positive lawful ceiling | **ALTERNATIVE**, constrained by SU1–SU3, DT1 and DT2 together. If no positive alternative exists: **REFUSE**. |
| Split refunds to evade the cumulative order limit | DT2 still applies to each execution; splitting does not restore headroom. |
| `refund_issued` before any settlement exists, with omitted/nonexistent citation | **REFUSE, Q13**. |
| `refund_issued` citing an unsettled, insufficient or wrong-claim settlement | **PROHIBIT, PR1/Q13** when the existing record contradicts the notice. |
| `close_case` while an applicable duty remains unresolved | **REFUSE, DU1/duty closure condition**. A held notice alone does not resolve the claim. |
| Read an existing, in-scope business record | **PERMIT, AU1/Q18**. Read a nonexistent primary record: **HOLD, AU1/Q18**. |
| Add an unrecognized assertion to an otherwise permissible act | **HOLD, PR1 unknown**, unless a stricter result applies. |
| Send ordinary free prose rather than a recognized template | **REFER**, under G1’s unrestricted template scope. |

[Interpretive] For the conditional cumulative-limit rows, remaining headroom is max(0, order amount minus existing refunds and chargebacks). Original qualifiers are retained; this file does not freeze a newly inferred outcome.
