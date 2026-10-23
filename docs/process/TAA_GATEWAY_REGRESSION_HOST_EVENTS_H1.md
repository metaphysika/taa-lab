Claude's ruling H1 on regression host events. Commit it to docs/process/ with this text.

Use an authenticated roster-change event in isolated regression worlds, not trusted host mutations. Do not add it to the frozen W0 world or bundle. Design v0.3 already lists roster changes among relevant changes; the authenticated write path is what the real gateway would use, and a host mutation could bypass it.

Event: {type: roster_change, by: company, party: <id>, add_jurisdictions: [...], remove_jurisdictions: [...], add_may_receive: [...], remove_may_receive: [...]}
- Only the root principal (company) may issue it; any other sender is rejected and logged, with no revision change.
- Phase-1 external event, processed in listed order.
- Writes a new version of the party's roster record through the single write path. An actual change advances the revision and voids outstanding tokens (Design v0.3 relevant changes, Q7); a no-op change is log-only.
- Never edits history; earlier roster versions remain in the record history and in proofs that cite them.
- Confers no grant or permission; capacity, eligibility and standing are re-derived under Q15/Q16.

Use:
- Each regression world declares the event in its own setup overlay and README; frozen v0.2.2 and W0 stay byte-identical.
- Q16 "F loses capacity": roster_change removing refund_authority and claim_decisions from F. A separate scenario restores them for the capacity-returns rules.
- Q15 "recipientless report resuming": from a T36b-style state (C and F both implicated), roster_change adding misconduct_reports (and may_receive) to an unimplicated party such as R → dispatched to R in phase 2 with a fresh routing deadline and unchanged due step.
- Negative control: roster_change from a non-root sender is rejected, writes nothing, revision unchanged.
- The conventional arm and the common duty oracle must accept the same event through their own means.

Continue C3 as planned. No model calls, Modal operations, spending, deletions or public releases.
