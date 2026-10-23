# Q14 allocation representation repair (draft PR #31)

ENGINEERING: null and absent allocation ownership now both mean unallocated in both reference models.
ENGINEERING: the external oracle inherits the repaired relation; actual arm records, keys, controllers and frozen fixtures are unchanged.
ENGINEERING: the executed-payment control and cross-claim mirror are permanent acceptance, with pinned pre-change sensitivity.
SCOPE: frozen and historical regression counts must reproduce before this repair is accepted; results are recorded below when complete.
INCOMPLETE: Q14 interval coverage, Q15 routing and Q16 capacity remain separate unfinished policy work in this same draft PR; final scoring is held.

## Ruling (Chris relaying Claude, 2026-10-23)

> Ruling: allocated_to: null and an absent allocated_to field both mean "unallocated". In the reference settlement predicate (and anywhere else the reference or the oracle reads allocation), treat null and absent identically; only a non-null value naming a different duty or claim blocks the settlement. Actual cross-claim allocation must stay blocked (T32). Do not change any arm's records, keys, fixtures or controllers to hide the difference.

## Fix and permanent controls

`taa_gateway_reference/refunds.py` now tests allocation ownership explicitly,
without substituting a claim/duty default only for missing keys. Its settlement
predicate and refund-proof allocation ledger both allow None, and a non-null
identity must still match the claimed subject. The generic declarative model's
`_duty_pass` allocation-ledger read had the same representation defect and is
repaired independently in `taa_gateway_reference/model.py`.

A refund proof can reserve its own duty; a claimant notice can reuse evidence
already used for that same claim's refund duty (Q14/T20). The shared *within the
independent refund relation* predicate resolves non-null duty identities against
its own duty relations, rather than treating an own-duty identifier as another
claim. Unknown/non-string values and different claims/duties remain blocked.
The oracle still never reads an arm's native allocation ledger or duty status.
No core or SQL decision/authorization/discharge code is imported.

`tests.test_gateway_null_allocation` has seven component methods. The original
control commits a real simulated refund and claimant notice on production,
conventional SQL and floor, then independently checks the common oracle. It
asserts that production still emits its explicit null and the other hosts still
omit that field, and that the oracle does not rewrite any arm state. The mirror
uses an authenticated processor correction assigning the settlement to another
claim's duty; both duties reopen/stay unresolved, and another claim's refund is
not discharged. Further controls pin absent/null/private-ledger equivalence,
non-null cross-claim blocking, own-duty bindings and same-claim notice reuse.

`tests/regression_scenarios/q14_null_allocation.yaml` adds three separate,
permanent trace scenarios (null, absent, cross-claim duty). The same runner and
state audits execute them on the reference, production and SQL backends. They
do not alter the historical frozen/regression counts. The script and CI gate
`scripts/check_gateway_null_allocation.py` run both component and trace controls,
including against pinned pre-change `5d0ca5cf69bb81fd2ef19bb3be64e9111a9b7b7d`.
The pre-change component run has six failures and no errors, with the original
oracle control and both null-ledger sites exposed; mirror/absent controls remain
passing. New trace expectations come from the ruling, never either model.

The original failed engineering probe in `evidence/gateway-v032-h1/` is retained
unchanged as historical evidence. It is not overwritten with a passing output.

## Full nullable/default sweep

Verification depth: searched both reference implementations
(`taa_gateway_reference/model.py`, `refunds.py`), the common oracle and its actual
world decoder (`comparators/duty_oracle.py`, `observed_world.py`) for allocation
and defaulted reads. Inspected allocation reads and relevant guards, and used
an AST inventory of every defaulted `.get` to classify the field families below.
This is source inspection with targeted execution controls, not formal proof.
The package's remaining `__init__.py` is only a module description. No model,
provider, Modal or adapter inspection was used.

| Location / field family | Finding | Action |
|---|---|---|
| Refund `settlement`, `allocated_to` | Missing defaulted to claim; explicit null failed equality. | Fixed, permanent original control. |
| Refund `proof`, private `allocations[rid]` | Missing defaulted to duty; explicit null blocked the same payment. | Fixed, permanent absent/null/foreign controls. |
| Generic `_duty_pass`, private allocation owner | Same missing-key-only default to duty. | Fixed independently; null/absent/own/foreign controls. |
| Refund `constraints`, issued-notice allocation | Null and absent were already equivalent; non-null own-duty binding was inconsistently rejected while checking reuse. | Uses the refund relation's bound allocation predicate, respecting Q14/T20 and T32. No arm record normalization. |
| Generic `_binding_matches`, `_duty_pass`: `allocation_id`, `transaction_id` | Null and absent already agree. These are required settlement identity fields, not allocation owners. | No change: missing identity cannot become valid evidence. |
| Oracle | No separate allocation-owner default; uses independent reference settlement/proof relations. | Inherits the fixed relation; actual-state controls cover the boundary. |
| Actual-world decoder | Copies allocation fields without rewriting nulls, omissions or duty IDs. | Intentionally unchanged; control asserts byte-equivalent state preservation. |
| Parent-grant / optional reference IDs | Null and omission are consistently absent-parent/no-reference in their existing guarded paths. | No change. |
| Required grant scope, purposes, limits, expiries | Some missing keys have defaults; explicit null can fail validation, fail authorization or be ill-typed. No ruling says null is an empty scope, default purpose, zero limit or infinite expiry. | No normalization. Any change would require Claude's semantic ruling first. |
| Evidence fields and `_ABSENT` sentinel; record-existence and bound-equality predicates | Missing evidence and explicitly present null can be distinguished for three-valued/presence checks. | No normalization: would change rule meaning or weaken evidence requirements. |
| Numeric support/amount fields | Missing fallback and explicit null are not universally interchangeable; valid inputs require numeric amounts and relevant evidence. | No null-to-zero coercion. A semantic change comes to Claude first. |
| Offers / routing deadlines | Inactive optional deadlines use omission/null as unset in guarded paths. Generic active-deadline paths require real numbers; interpreting null as infinity would extend a window. | No change; no implicit deadline extension. |
| List/map configuration and resolution basis | Some missing lists/maps default empty, but explicit null is invalid where schemas require a collection. Optional surviving/substantive-basis fields already suppress null and omission identically in the decoder. | No blanket `or []` / `or {}` fix; preserve schema and evidence requirements. |
| Generic supplied `staged_effect` and correction presence checks | Omitted staged effect can use the trusted effect; explicitly supplied null must not validate as it. Versioned record contents intentionally preserve whether a key was supplied. | No change: frame protection and immutable evidence, not a representation defect. |

No additional valid-input representation defect of this same allocation-owner
kind was demonstrated. The untouched rows are listed for Claude; none is treated
as authorization to change a rule or to coerce all nulls into defaults.

## Replay scope and pending work

Historical frozen v0.2.2, permanent regressions, H1, Q11/Q12, Q13 and adversarial
acceptance are rerun on all normative implementations, preserving counts.
Original inputs also go through the same runner/audits on every configured arm;
this computes no compliance, utility, duty-oracle metrics or final comparison.
Policy ablations and business hosts intentionally do not assert normal TAA
verdicts. TraceGrant is limited to ten authored frozen contracts; unsupported
trace IDs are listed individually as incomplete replay coverage. Floor/static also have no transaction fault adapter: the seven T23 fault
variants are explicitly unavailable on each, never simulated as passing rollbacks.
The initial replay stopped on those seven explicit host rejections; that prefix
is preserved. After adding applicability reporting, only the floor/static groups
and new allocation suite needed fresh replay; the first six arm groups retain
their unchanged inputs/runtime/audit code. Final complete test discovery is
rerun after this reporting-only harness adjustment. No new contract
is inferred from an arm's behavior or silently substituted for a missing one.

The larger Q14–Q16 alignment remains incomplete. Scoring waits for Claude's
review of the completed PR. No model calls, Modal operations, spending, deletions,
Notion edits or public releases.

## Final local repair acceptance

- Full final-source discovery: **1,073 tests**, 36 existing optional
  skips, zero failures/errors, 2005.117 seconds.
- **286 component methods pass**. Seventeen current-workflow commands, scripted
  all-scenarios and the fresh pinned null-allocation sensitivity gate pass.
  Historical baseline-checkout steps remain enabled in CI; they were not all
  repeated locally. The null baseline is exact `5d0ca5cf`.
- All **14 historical count comparisons are unchanged**, including reference,
  production and SQL frozen/permanent acceptance, Q11/Q12, Q13, properties,
  adversarial and existing comparator development results. No frozen/regression
  expected outcome changed. The frozen author validator checks 49 traces and
  variants with zero errors; the manifest remains identical.
- New null suite: three scenarios and nine source assertions per normative
  backend; reference/production/SQL audits **34/34/159**. Zero discrepancies or
  incomplete assertions. Seven component controls pass now; six failed checks
  on the pinned pre-fix implementation, with zero baseline errors.
- All-arm input-only replay: **654 executed scenario instances**, **98 explicitly
  unavailable** (84 missing TraceGrant task contracts; seven business fault
  variants each on floor/static). Executed groups have zero audit discrepancies
  or incomplete assertions. Overall replay coverage remains incomplete, never
  represented as full semantic acceptance or cross-arm scoring.

Lossless evidence and count/source/hash inventory:
[`evidence/gateway-v032-null/validation.json`](evidence/gateway-v032-null/validation.json)
and `acceptance.zip`. Retained failed/interrupted prefixes, including the first
unsupported-host replay, are in the archive. The original failed H1 oracle
probe remains unchanged. All 127 scripted result files were moved intact to the
workspace evidence area, with verified hashes and manifest; nothing was deleted.

This is a clean repair checkpoint in the same draft PR. Q14 interval/receipt
coverage, Q15 routing, Q16 capacity and their complete new regression set remain
unfinished. Final scoring and merge remain held for the completed alignment
and Claude's review.
