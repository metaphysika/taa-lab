# TAA Gateway Core Design: clarifications v0.3.1

Date: 2026-10-21. Author: Claude, adopting Astra's review of expected traces v0.1.
These ten decisions settle questions v0.3 left open. They amend Design v0.3 where stated and govern expected traces v0.2. No other part of v0.3 changes.

## Q1. REFUSE disposition (amends the disposition table)

REFUSE applies when a non-prohibition condition is known to be unmet (a support rule or a determination evaluates to violated) and no permitted alternative applies. It issues no token. It creates no misconduct report merely because it is REFUSE. An applicable prohibition always takes precedence.

Aggregation across stages takes the strictest result in this order: PROHIBIT, REFUSE, REFER, HOLD, ALTERNATIVE, PERMIT. A known failure therefore outranks a missing fact, because supplying the fact could not make the act permissible. ALTERNATIVE is used only when every failed condition is a support or determination failure that the stated alternative would satisfy.

## Q2. No automatic release (amends the duty ledger)

A duty is never released just because permission or evidence was lost. Release requires three things together: a release determination by a party with standing for that duty, a substantive basis, and bound evidence. A support rule becoming violated makes the act impermissible; it does not touch the duty.

Two resolution rules are declared in W0, with distinct outcomes:
- A settled chargeback bound to the same claimant, order and amount, not allocated elsewhere, discharges a refund duty. A provisional chargeback discharges nothing.
- A duplicate-claim determination by the party with claim-decision standing releases the duplicate claim's resolution duty, and the release records a link to the surviving duty.

## Q3. Order association by requested effects (amends Records and Admissibility)

Orders are stored as structured requests: each lists its requested effects (tool, target claim, amount and every asserted fact). A proposal is associated with an order when its act falls within that order's requested effects, using trusted order context only. A cited reference that does not cover the act is rejected and logged.

A prohibited element is attributed to an order's issuer only when the order itself requested that element. If an order requested a lawful refund and the agent added a false assertion, the order is context, the prohibited element is agent-originated, and no report names the issuer.

## Q4. Repeat proposals and live tokens

An identical proposal from the same actor, for the same act, in the same trusted context and at the same revision returns the existing live token. A consumed, void, withdrawn or expired token is never returned as executable.

## Q5. Wrong-actor attempts

A token presented by any party other than its acting party is refused and logged. The attempt does not consume the token and does not advance the revision. The rightful actor may still use it.

## Q6. Answers to unreserved questions

A reviewer answer becomes a resolution record only when the question is one W0 declares reserved, the exact question matches, and the answerer holds the declared jurisdiction. Anything else is logged, writes no record, and does not advance the revision.

## Q7. Token expiry advances the revision

As v0.3's relevant-change table states, a live token's expiry is processed at its boundary like grant expiry: the revision advances and all outstanding tokens become void. Expiry of an already void or consumed token changes nothing. A token-local expiry would be a later design amendment.

## Q8. Unaccepted transfers (amends DU4)

If an owner who still holds authority offers a duty and nobody accepts within the window, the offer lapses and ownership is unchanged. If the owner has lost authority, the duty becomes unowned when the fallback's acceptance window passes or no fallback exists; an explicit decline is not required. Either way the duty stays unresolved.

## Q9. Report matters, repeats and supplements

A report matter is keyed by issuer, case or claim, and prohibited effect. While a matter is active (its report duty unresolved), a repeated order for the same prohibited effect is appended to the existing report as a new version, without resetting its deadline. After the matter's report is acknowledged, new wrongdoing opens a linked supplement report duty that needs its own acknowledgment; an earlier acknowledgment never covers later incidents.

## Reporting lifecycle (clarifies DU3)

When a report duty is created, the gateway's reporting authority dispatches the report in the same phase. The report has an id and a version. An acknowledgment discharges the duty only if it cites that report id and its current version. A new version, from an appended order, needs a new acknowledgment. Recipients in misconduct_reports are authorized to receive the order text, the act description, the rule and the facts it used.

## Q10. Time conventions (added in traces v0.2.1)

A clock tick that crosses no boundary is not a decision-relevant change: it does not advance the revision, and live tokens survive it. Rules never read the raw step counter; time enters decisions only through boundaries. Boundaries are recognized in phase 1 of their step: grant expiry, live-token expiry, a duty deadline, a transfer-offer window, and a report re-dispatch deadline. The resulting transitions happen in phase 1 for expiries, deadlines and windows, and in phase 2 for a report re-dispatch.

A scheduled boundary changes the revision only when it causes an actual decision-relevant transition. A boundary whose obligation or scheduled action has already been satisfied, cancelled or superseded has no effect and leaves the revision unchanged, just as Q7 treats an already void or consumed token. A duty resolved on time does not later become overdue when its former deadline arrives, and lateness already recorded stays in the history.

Every deadline uses the expiry convention. "Due at step s" means the duty is overdue from phase 1 of step s, exactly as "expires at step s" means invalid from step s. A voluntary transfer offer lapses at its window boundary (Q8).

Without this rule every token would die at the next tick, token lifetimes would mean nothing, and a retry after a rolled-back transaction (T23) could never succeed.
