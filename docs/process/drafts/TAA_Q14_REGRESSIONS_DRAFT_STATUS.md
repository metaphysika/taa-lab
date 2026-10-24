# Incomplete Q14 authoring prefix — outside acceptance

`TAA_Q14_REGRESSIONS_DRAFT.yaml` preserves 18 initial source-derived scenarios.
It is not an active regression suite, not completed coverage, and has not been
reviewed as an executable set by Claude. Its requested attribution label refers
to the normative clarification. No expectation was generated from a backend.

A diagnostic replay against pre-change9135bcdb is retained in the checkpoint's
evidence archive as `q14-before.json/.log`. Each backend rejects the
first-commit-order case's financial record creation: the draft used a source
without W0's create right for that financial kind. That authoring error prevents
this case from exercising the intended ordering rule. The other absent
portion/recomputation capabilities also remain unimplemented. The resulting
exceptions and incomplete assertions are never credited as passes.

Before activation: author a legitimate financial input sequence, retain this
prefix/version, implement independent Q14 receipt-bound admissions and interval
relations in all required backends/oracle, and run every requested before/after
control. Do not alter a frozen fixture, expected outcome, actual arm record,
contract, key, controller or matching rule to disguise a difference. A scenario
input correction is a declared authoring revision, not a specification ruling.
Q14 and final scoring remain held in draft PR31.


Authoring revision v1 retains v0 and all expectations unchanged. Only the two
first-commit-order event kinds change from refund to chargeback; their existing
payment_processor sender is authorized to create chargebacks under W0. Q14 lays
refunds and chargebacks on the same paid line. IDs, amounts, chronology, notices
and expected coverage stay unchanged. This fixes authenticated input authoring,
not an implementation outcome. A fresh pinned-before probe is retained
separately; neither draft is an active acceptance suite.


Current activation note: after implementation, authoring revision v1 was copied
byte-for-byte to `tests/regression_scenarios/q14.yaml` and wired into CI. Its
original expected outcomes remain unchanged. The v0 authoring error and both
historical draft files stay retained; they are not additional independent cases.
