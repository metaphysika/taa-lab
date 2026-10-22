[DESCRIPTIVE] This PR builds the TraceGrant component from Claude's verbatim source notes and nine authorized rulings.
[DESCRIPTIVE] Ten hand-written POEC contracts were committed and hash-frozen before comparator outcomes; none changed after outcomes.
[DESCRIPTIVE] All five static checks, evidence admission, ordered decisions, one-shot certificates, receipts and final-answer gate are implemented.
[DESCRIPTIVE] Thirteen component tests and forty development episodes pass 1,190 independent audit checks with zero discrepancies/incomplete checks.
[LIMITATION] This is a local reconstruction and offline harness check; strongest-conventional comparison and empirical H3 validation are not claimed.

# TraceGrant component for Claude review

[DESCRIPTIVE] Source notes are preserved byte-for-byte in
`TRACEGRANT_COMPARATOR_SOURCE_NOTES.md`. The implementation matrix
`TAA_TRACEGRANT_IMPLEMENTATION_MATRIX_v0.md` distinguishes published behavior,
the authors' optional-argument fix, unspecified details and local adaptations,
with section references. Sol inspected Claude's relayed full-text notes; Sol did
not independently access the unavailable paper in this runtime or reproduce its
experiments. No official configuration or trajectory set was available.

[DESCRIPTIVE] Frozen POEC contracts specify MAY scopes/budgets, a MUST graph,
BIND sources/derivations, and VERIFY postconditions. The compiler replacement,
hardness, no waivers, per-tool budgets and inert W0 step-up detector follow the
nine rulings. Static checks use the text definitions. Unknown/malformed contracts
cannot execute. Optional authority arguments cannot bypass binding. Evidence
requires ACTIVE status, exact source/query/type/integrity and unique selection.
Certificates bind contract, obligation, tool, actor, canonical arguments, proofs
and budget reservation; dispatch is one-shot. Receipt/postcondition decisions
observe actual world state. Failed effects and receipts roll back while consumed
certificates stay consumed and reserved budget is restored. Cited provenance is
checked; no TAA whole-world invalidation or policy re-evaluation is added.

[DESCRIPTIVE] Components import no production/reference decision, authorization,
discharge or transaction code. This arm has no TAA duty ledger, reopening,
acceptance-based transfer or automatic reporting. Such absences are design
differences, not defects or claims that the published work cannot be extended.
Local tool-service and immutable-evidence choices are explicit in the matrix.
No after-results contract tweak or invented waiver makes a run look better.

[DESCRIPTIVE] Frozen contracts: initial commit `2d1e05b4`, manual source-identity
and T09 notice-scope preflight `30b6290b`, both before comparator execution.
Manifest/source hashes verify. All ten development tasks run with the same four
controller definitions and source events. The correct controller can read its
independent diagnostic key; POEC policy receives arguments only, never expected
values. Dispositions stay native: ALLOW/PROOF_GAP/DENY/STEP_UP_AUTH are not silently
relabelled as TAA's dispositions. The first and final runs remain preserved.

[DESCRIPTIVE] Final observations: **40 episodes**, ten development cases, four
controllers, **42 receipts**, zero STEP_UP_AUTH events, **1,190 independent audits**,
zero discrepancies/incomplete checks; **13 component tests pass**. Audits compare
actual before/after state, history retention, effect route/amount, receipt and
verification support, budgets, single use and final-answer gate. Negative controls
poison hidden state, rewrite history, alter benefit route and invent unbacked
verification. Both real effect and receipt fault points demonstrate rollback.
All five static check failures, optional bindings, ambiguous evidence, actor and
argument tampering, replay, budget exhaustion and stale provenance are covered.
Final sources/contracts are unchanged across the run. CI repeats the tests and
retains complete observations. Compact provenance is in
`evidence/tracegrant-comparator/validation.json`.

[LIMITATION] The task graphs are hand-written fixed goals. Some W0 keys are
prefixes containing deliberate probes rather than completed POEC plans. A
superseded/impossible hard effect may leave the contract unfinished. The
final-answer gate therefore is not scored as lawful W0 completion, over-refusal
or comparative utility. This PR does not provide representation-neutral H3
scoring. Its service supports the task contract's three effect types; the matrix
records the remaining registered actions being outside MAY and the separate
service conformance boundary. Those choices require review before scientific use.

[LIMITATION] This component is stacked on stage 7 PR #20, which must be reviewed
and merged separately. The independently implemented strongest conventional arm,
no-gateway/static arms and four ablations remain further work. This PR requires
Claude review and all green CI; Astra reviews conventional arms before step 3.
No model calls, Modal operations, spending, evidence removal, Notion edits or
public releases occurred. No launch approval or novelty/H3 result is implied.
