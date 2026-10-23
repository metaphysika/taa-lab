Historical Q15 checkpoint record; current status: [v0.3.2 candidate](TAA_GATEWAY_V032_IMPLEMENTATION.md).

# Q15 routing and business-host fault observation — draft PR #31

ENGINEERING: Q15 rechecks current recipients and phase-1 acknowledgments, and makes at most one routing transition per report per step.
ENGINEERING: core, reference and SQL encode their own policy; the common oracle uses the independent reference relations over actual inputs.
ENGINEERING: business-host failures expose real partial writes; common audits keep the resulting receipt mismatches visible.
COVERAGE: TraceGrant remains confined to ten predeclared development programs; missing contracts stay unrun and no post-outcome contracts are authored.
GATE: Q14 is now integrated and separately documented; combined acceptance and Claude review remain required before merge or scoring.

## Source and implementation

Sources: unchanged approved Clarifications v0.3.2 revision3.1 (Q15), H1,
and Chris's relay of Claude's review at9135bcdb, preserved verbatim in
`TAA_GATEWAY_PR31_CLAUDE_COVERAGE_RULING.md`. No new policy ruling is inferred
from an implementation result. The approved null-allocation controls remain.

- Core: `DutyEngine.eligible_recipients`, `eligible`, `route_report` and `receive`
  use actual versioned roster facts and stored-order provenance. Eligibility
  includes jurisdiction, may_receive and conflicts. Original jurisdiction order
  supplies priority; newly rostered eligible roles follow in record-ID order.
  Never-dispatched eligible roles precede least-recently-dispatched roles, ties
  using jurisdiction priority. Repeats retain due/routing deadlines. Changes of
  eligibility redirect; the report's original due and lateness remain intact.
- Reference: independent `recipients`, `eligible`, `report_choices`, `route_report`
  relations use its own versioned facts and dispatch log. No core authorization,
  discharge or transaction code is imported. Both assertion/template and
  prohibited payment-route matters are checked. The oracle uses these permitted
  independent duty relations over actual records/events and physical deliveries.
- SQL: `Ledger._report_eligible`, `_report_clock`, `acknowledgment` use SQL records
  and report histories. A same-recipient re-dispatch writes a dispatch step so it
  is an actual versioned delivery, rather than a verbal description or no-op.

All phase-1 events are processed in listed order. An acknowledgment after a
recipient-disqualifying event fails, log-only; one before it succeeds. Phase2
routes at most once per unresolved report per step. A deadline plus a conflict
sends once. Recipientless reports retain due/history and resume when H1 makes an
eligible role available. New report creation and appended versions retain their
specified independent dispatch behavior.

## Actual dispatch observations

The old recipient/version diff missed repeated deliveries to the same role and
could order simultaneous sends differently from the actual log. The common
observer now reads native report_sent events, reference dispatch logs, and SQL
report-version audit events in commit order. It never uses the model's returned
transition list as evidence. The model's state_delta description is still
compared against a separately computed full delta; no guard was removed.

The oracle's representation-only SQL reader independently reads actual audit
order. Acknowledgment-only row writes do not send anything. Each actual delivery
gets its own ordinal; the ordinal identifies a physical send, not a semantic
score or an internal duty status. Tests pin one send on a combined deadline and
conflict, idempotence of same-step reconciliation, and distinct same-role
same-version re-sends. No semantic matching keys, controllers or contracts change.

## Regressions and before/after evidence

`q15.yaml` has nine Sol-authored scenarios from the approved Q15/H1 sources:
redirection with deadlines preserved, acknowledgments on both sides of a
same-step conflict, deadline plus conflict, least-recent alternation,
recipientless recovery, roster disqualification before acknowledgment,
payment-route implication, and routing of an unowned-duty report.
Each fails against pinned9135bcdb on reference/core/SQL, without exceptions or
incomplete assertions. Current source passes32 source assertions per backend;
state audits reference/core/SQL191/211/1221. Component tests also drive the common
oracle over actual production/SQL inputs, without reading their internal ledgers.
The requested attribution label identifies the normative source; the new
executable expectations still await Claude's review of this PR.
The earlier seven-case before/after prefix and initial observer errors are
retained as failed/intermediate attempts, not reported as completed acceptance.

One pre-existing component deliberately pinned the earlier conservative
retention of an implicated C; it now expects F under Q15. The synthetic SQL
physical-report component now supplies the actual audit event as well as its
row, preserving its acknowledgment expectations. Frozen expected outcomes and
the two historical Q11/Q12 scenario files remain unchanged.

## Business-host fault boundaries

The out-of-band `business_faults.FaultAdapter` is supplied only through the
harness's execute fault argument. It imports no core, SQL, reference or scoring
code. Floor/static no longer wrap their writes in a simulator transaction.
TraceGrant retains its existing separately specified transactional dispatch.

| Requested boundary | Floor/static behavior |
|---|---|
| after_validate | Real permission/intent check completed; fail before any effect. |
| during_effect_commit | Fail after the actual effect write, before the business-operation record and receipt. Partial effect remains. |
| during_receipt_write | Fail before receipt creation, retaining the actual effect and business operation. |
| before_log_write (additional control) | Receipt and effect exist; fail before normal execute log. |
| after_stage | Not applicable by design: no staging phase. |
| during_token_consumption | Not applicable by design: no security tokens. |
| during_duty_update | Not applicable by design: no internal duty engine. |
| during_revision_advance | Not applicable by design: no transaction revision-commit boundary; ordinary writes update their own counters. |

For plain duty tools, the business-operation record itself is the effect; its
fault hook follows that actual write. The independent executed observation also
counts a changed actual business-operation collection. A new control failed on
the earlier hook and passes after repair.

The two mid-write T23 variants per arm leave an effect without a receipt. The
unchanged common record_effects_match_receipts audit flags each one. Reports
retain all four failing audits verbatim as observed non-atomic behavior, rather
than waiving or relabeling them as safe passes. Unexpected discrepancies still
fail the replay gate. The eight T23 instances with absent boundaries are listed
as not applicable with reasons, never silently run without injection. Raw state
and audits preserve partial writes; no successful rollback is claimed.

## TraceGrant limit and remaining work

No new POEC contract is authored. Historical84 missing-contract instances stay
unrun; Q15 adds nine and Q16 adds sixteen more uncontracted replay cases. These are explicit coverage limits, not successful assertions. The
comparison/scoring population remains the ten predeclared development programs.
Wider coverage requires contracts authored by Astra blind to outcomes.

Q14 interval/receipt coverage is now integrated; complete combined acceptance remains pending.
Q16 capacity/transfer is implemented in this checkpoint, separately documented. This is an offline engineering checkpoint, not final
cross-arm scoring or empirical validation of H3. No model calls, Modal,
spending, deletions, Notion edits or public releases.
