[DESCRIPTIVE] PRs #11–#13 were reviewed by Claude and merged at their approved heads with green CI.
[DESCRIPTIVE] Foundation contracts and the independent reference semantics now incorporate Clarifications v0.3.1.
[DESCRIPTIVE] Claude's unchanged v0.2.2 bundle verifies and its validator reports 49 traces and variants checked, 0 errors.
[DESCRIPTIVE] Local validation passes 78 tests and all 534 assertion blocks across 54 executable reference scenarios, with no incomplete coverage.
[DESCRIPTIVE] Claude conditionally approved the alignment and mapping with these four updates; green CI is the remaining merge gate. Production stage 4 stays outside this PR.

# v0.3.1 alignment and validation

[DESCRIPTIVE] Controlling source is Design v0.3 plus `tests/expected_traces/v0.2.2/SPEC_CLARIFICATIONS_v0.3.1.md`. Zip SHA-256: `9a4b20191c54aa4ff7d1ae4be6517f44aa1ddb9b67aaa00acdafabf34c5751b8`. Every manifest entry and extracted byte matches the supplied zip. Superseded v0.1 and v0.2.1, with their original zips, manifests and hashes, remain under `tests/expected_traces/archive/`; PR #14 was closed as superseded. Historical ingestion discrepancies remain preserved.

| Amendment | Alignment |
|---|---|
| Q1 | REFUSE and strict precedence; known failures refuse; alternatives carry positive refund amounts |
| Q2 | Loss of support or authority never releases duties; release needs standing and bound substantive evidence |
| Q3 | Stored requested effects; association independent of claimed reference; attribution only for requested prohibited elements, including T39 negative control |
| Q4/Q5 | Repeated unchanged proposals reuse live tokens; acting-party binding; rejected wrong-actor attempts log without consumption/revision |
| Q6 | Declared question/jurisdiction only; rejected answers are log-only with unchanged revision |
| Q7/Q10 | Boundary-free ticks preserve revision/tokens; live expiry invalidates globally; overdue begins at due step |
| Q8 | Voluntary offer lapses with owner retained; lost-authority fallback becomes unowned after window |
| Q9 | Issuer/claim/prohibited-effect matters; versioned repeats retain deadline; version-bound acknowledgment; linked supplements; immediate dispatch and roster fallback |
| Trust boundary | Separate create/correct rights and field-level correction checks; immutable identities and non-evidential agent notes |
| Correction | Discharge/release proofs are rechecked; invalidated proof reopens duty and case, preserving execution history |

[DESCRIPTIVE] Foundation schema version is 0.3.1. It remains stage 2 storage, identity and contract code, with no production authorization pipeline, effect executor or duty engine. Its clock publication recognizes stored grant/token/duty boundaries. Revision-bound execution and actual token lifecycle belong to later production stages. Generic storage publication is not the protected-effect transaction.

[DESCRIPTIVE] `taa_gateway_reference/model.py` retains the configurable declarative prototype with amended precedence, correction permissions, expiry, transfer and reporting semantics. `taa_gateway_reference/refunds.py` supplies its independent finite W0 relation: constraints are collected then aggregated; duties and proof relations reconcile independently to a fixed point. It imports only standard-library modules and shares no core decision, authorization, discharge or transaction code. Its atomic transaction is an ideal copied-state relation; named faults abort that relation, not a test of a production executor. The import-separation test covers the entire reference package.

[DESCRIPTIVE] `tests/trace_support/reference_runner.py` drives source inputs and compares projections against source expectations. Unknown assertion vocabulary is incomplete coverage and fails CI. Negative controls deliberately change an in-memory expectation and add an unknown assertion, demonstrating discrepancy/incomplete detection without changing fixtures. CI exports observed assertion results, never expected answers. No skipped assertions count toward acceptance.

[DESCRIPTIVE] Local checks: source manifest and author's validator; 78 foundation/reference/runner boundary tests; 54 reference scenarios, 534 assertion blocks, 0 discrepancies, 0 incomplete; `git diff --check`. Additional controls check immutable correction fields, create-only/correct-only rights, rejected reviewer answers, unrelated release/denial evidence, live-token expiry, and external-event-before-duty ordering. Tests owned by Sol were amended for the changed specification; independently authored expected outcomes were untouched.

[DESCRIPTIVE] No empirical claims, model calls, Modal operations, Notion edits, adapter downloads, scientific reruns or changes to PR #6. Passing reference traces is bounded engineering evidence, not independent empirical validation or proof of H3. Core trace execution and Astra's independent spot review remain future acceptance work.

[DESCRIPTIVE] The [mapping](TAA_EXPECTED_TRACE_MAPPING_v022.md) records the tightened matcher. Chris relayed Claude's approval of b38c4b78, extended conditionally to the four specified updates only; any reference-model change or different scenario/assertion count must return to Claude before merge.

[DESCRIPTIVE] Claude approved head b38c4b78 conditional on the four changes supplied by Chris: frozen v0.2.2 adoption/archive, stricter documented list matching with extra-effect negative control, author-acknowledged T30 under-listing, and mapping/count updates. No reference-model code changed. Both the prior and tightened matchers reproduce 54 executable scenarios and 534 assertion blocks with zero discrepancies or incomplete assertions. Merge is authorized only after green CI and those exact conditions; otherwise the delta returns to Claude.

## Subsequent independent spot check (supersedes the assurance claim above)

[DESCRIPTIVE] Astra reproduced the 54 scenarios and 534 passing source assertions but found four blocking reference/runner defects, all confirmed by Claude: returned-description observations, repeat-driven escalation delay, duplicate notice coverage, and per-entry phase reconciliation. The original pass count overstated assurance. Their fixes, before/after regressions, and additional state-audit counts are documented in [TAA_GATEWAY_SPOT_REVIEW_FIX_v0.md](TAA_GATEWAY_SPOT_REVIEW_FIX_v0.md). The frozen v0.2.2 fixtures remain unchanged.

[DESCRIPTIVE] T23's seven fault labels are an **ideal abstraction**: the reference aborts the copied transition before publishing any partial state. Production acceptance must inject each fault at its actual validation, staging, effect commit, token consumption, duty update, receipt write and revision-advance boundary, then demonstrate rollback of partial changes. Reference passes cannot substitute for those production fault tests.

## Open design questions for Claude's v0.3.2 revision

[INTERPRETATION / OPEN QUESTION] **DU1 coverage and explicit portions.** The reference counts each cited settlement once and treats denial bases as covering one shared unsupported remainder. This is a conservative W0 interpretation. Production needs `refund_issued` and `refund_denied` notices bound to explicit amounts or portions; the precise binding and overlap rules remain for Claude's v0.3.2 revision. This note makes no code or expected-outcome change.

[INTERPRETATION / OPEN QUESTION] **Recipient eligibility on report repeats.** Repeats keep the current recipient without rechecking eligibility. If that recipient has since become implicated in the same wrongdoing, redirection is unspecified. No W0 trace exercises this case. Claude's v0.3.2 revision must specify whether and when to redirect, including the effect on existing deadlines.

[INTERPRETATION / OPEN QUESTION] **Acceptance without discharge authority.** A party may accept a duty without authority to discharge it (`R-Q12-parallel-L`: L accepts `D_resolve(CL1)` without refund or messaging authority). The implementation does not treat that as authority loss, so no fallback offer opens. Claude's v0.3.2 revision should decide whether offers are limited to parties able to discharge, or whether such an acceptance triggers the fallback. This note makes no code or expected-outcome change.

[DESCRIPTIVE] Chris relayed Claude's approval of PR #16 at `89491921`: independently reproduced 54 frozen scenarios, 2,238 checks (534 source assertions and 1,704 state audits), zero discrepancies/incomplete; eight regression scenarios, 265 checks, zero discrepancies; pre-fix `9ddf84a4` fails nine regression checks including all three hidden-state controls, and the baseline guard exits successfully. The independent runner state-delta comparison remains mandatory: it computes its own delta and never trusts the model's `state_delta` description. The only subsequent change before merge is this requested documentation addition; all CI must pass.


## Claude's Clarifications v0.3.1 addendum (2026-10-22), verbatim

The following Q11/Q12 text was relayed by Chris from Claude. It amends the
implementation target; the frozen v0.2.2 bundle remains byte-for-byte unchanged.

Q11. An offer gives standing to accept, not tool authority. accept_duty is a registered act: AU1 requires a live grant to the acting party covering accept_duty within scope, and IR1 does not cover it. The tool path needs both authority (AU1) and standing (a live, unexpired offer of that duty to the actor, DU4). Missing authority → AU1 violated, REFUSE at the authority stage; missing standing → DU4 violated, REFUSE. A party without such a grant accepts through the authenticated duty_acceptance message, checked only against the live offer (as in T05). In W0, F's accept_duty tool call is refused under AU1; F's acceptance message succeeds while the offer is live.
→ Production: remove the ACCEPT authority path. The reference already matches.

Q12. Losing authority never extends or shortens a running offer window.
- A live offer to the fallback owner becomes the fallback offer and keeps its original expiry. If unaccepted at expiry, the duty becomes unowned and the unowned-duty report opens; it does not revert to the owner.
- A live offer to someone else keeps its own expiry; at the loss, a fallback offer to the fallback owner opens with the normal 5-step window. The first valid acceptance takes the duty and closes the other offer. The duty becomes unowned only when no offer remains live and none was accepted.
- With no live offer, the fallback offer opens at the loss with the normal window.
Your example: offer to F at step 2 expiring at 7, authority lost at step 3 → expiry stays 7; F may accept through step 6; at step 7 the duty becomes unowned and the unowned report opens.
→ Reference: change from 8 to 7. Production already keeps 7; confirm it also implements the other two bullets.

### Q11/Q12 implementation mapping (DESCRIPTIVE)

Production stores independent transfer windows in `duty.content.transfer_offers`;
reference stores its own party-indexed `offers` relation. The legacy single-offer
fields project the first live offer. Acceptance closes every competing window.
A party may accept ownership through a message without acquiring tool authority;
its absent refund grant alone is not a subsequent loss of previously held authority.
The accepted owner's authority baseline records that distinction.
Production setup now seeds additional declared grants as well as amendments to
W0 grants, so the grantee controls exercise actual scoped authority. Unowned reports
are dispatched with their own five-step acknowledgment/routing window.

`live_offers` in the common runner reads actual duty state, including all offers,
independently of the returned description. It is an exact, ordered list per duty.
The runner still computes its own full state delta and checks returned descriptions.
The reference implements offer selection and reconciliation independently of core.
The new Sol-authored scenarios are outside the frozen bundle. Their attribution
records Claude's review of the stated expectations; this implementation delta still
requires Claude's PR review before merge.


## Claude's Q13 ruling, Clarifications v0.3.2 (verbatim)

Q13. A citation to a nonexistent record is an unmet requirement, not a contradiction. PR1 needs an evidential record that says otherwise; absence contradicts nothing.
- refund_issued citing a record that does not exist → REFUSE (template requirement unmet), same as an omitted citation (T35). No report (Q1).
- Cited record exists and contradicts the notice (other claim or claimant, unsettled, smaller amount, allocated elsewhere) → PROHIBIT under PR1, as in T32.
- The same line applies to refund_denied basis records and any other cited evidence.
→ Production is correct. Change the reference to REFUSE. Add a regression scenario covering both sides (nonexistent citation REFUSE with no report; existing contradicting citation PROHIBIT), labeled "Sol-authored from Claude's Q13 clarification; expectations reviewed by Claude". Copy Q13 verbatim into the alignment doc. Frozen v0.2.2 unchanged.

[DESCRIPTIVE] Chris relayed this ruling from Claude. Q14–Q16, addressing the
three open questions above, remain drafted pending Astra's review and Chris's
approval; current conservative behavior is retained. Only Q13 is implemented.
The expanded Q13 controls also found missing production contradiction checks for
an explicitly reallocated refund and a denial contradicted by its cited return.
Those are corrected under Q13; native missing-citation behavior was already correct.


Q15 implementation status (PR31 continuation,2026-10-23): the formerly open question
about a repeated report's newly implicated recipient has a normative answer in
approved Clarifications v0.3.2 revision3.1. Dynamic eligibility, ordered
acknowledgments, one routing transition per step and least-recent dispatch are
implemented in the draft core/reference/SQL alignment. See
TAA_GATEWAY_Q15_AND_BUSINESS_FAULTS.md for source-derived regressions and actual
delivery observations. Implementation review of this delta is pending; this is
not approval of completed v0.3.2. Q14 remains unimplemented. TraceGrant
scoring stays limited to ten predeclared development programs; no post-outcome
contracts are authored. Final scoring remains held.


Q16 implementation status (draft PR31 continuation, 2026-10-23): Q16 in approved
Clarifications v0.3.2 revision3.1 now answers the third open question above.
New acceptance requires capacity in addition to standing and (for a tool call)
AU1 authority. L without capacity cannot take ownership. Customer-duty owners
retain accountability during a bounded capacity-loss episode; recovery preserves
live windows, and a renewed loss inherits any live fallback window. There is no
self-offer or repeated fallback in one episode. Q16 supersedes the two explicitly
named Q11/Q12 scenarios without deleting their original files. The complete
clarification text remains verbatim in TAA_GATEWAY_SPEC_CLARIFICATIONS_v0.3.2.md.
Implementation/expectation review is pending. Q14 and final scoring remain held.


## Current v0.3.2 revision3.1 alignment candidate (PR31)

The approved text in TAA_GATEWAY_SPEC_CLARIFICATIONS_v0.3.2.md remains verbatim.
H1 and Q14–Q16 are now implemented independently in core/reference/SQL, with the
common external oracle reading actual evidence. This supersedes historical
implementation-pending entries above; it does not supersede preserved evidence
or grant merge/scoring approval. See TAA_GATEWAY_Q14_RECEIPT_COVERAGE.md and the
current implementation report for receipt projection, original/recomputed
proofs, dynamic routing, capacity episodes and retained-source supersessions.
The state-delta comparison guard and permanent regression acceptance remain.
Frozen v0.2.2/W0, source outcomes, original Q11/Q12 files, controllers, matching
function/protocol and frozen POEC contracts are unchanged. Final scoring waits
for Claude's review of completed PR31, then its separate PR. No model calls,
Modal operations, spending, deletions, Notion edits or public releases.


## Comparison review v0.2 — additional scope-conversion question

[OPEN / 2026-10-24 UTC] The conventional-chain audit found that the core W0 converter discards template restrictions. A refund_issued notice constrained to refund_denied is REFUSE in reference/SQL and PERMIT in core. The generic grant checker can retain the restriction but would HOLD calls with no template resource, whereas reference currently ignores template restrictions for those calls. Claude's ruling has been requested; no rule meaning is inferred. This is separate from Q14–Q16 and outside the ten declared scoring programs. See COMP-V02-CORE-TEMPLATE-CONVERSION in the append-only discrepancy log and TAA_COMPARISON_REVIEW_v02.md.


## Q17 — approved scope clarification (2026-10-24)

Each resource-scope key in a grant restricts one dimension of an act, determined by the registered tool's resource projection. (a) Dimension the tool does not have: the key is inapplicable and skipped; never HOLD. A template restriction never affects issue_refund, close_case or any tool without a template dimension. (b) Dimension present, value supplied: must be in the allowed set, else AU1 violated (REFUSE at authority). (c) Dimension present, value absent: for message_party an absent template is free prose, which a template-limited grant does not cover, so AU1 violated (REFUSE); under an unrestricted grant free prose stays REFER (T35); REFUSE outranks REFER (Q1). (d) Every grant in the selected complete chain must allow the act on every applicable dimension.

[IMPLEMENTATION] Registered projections omit inapplicable keys. The generic checker preserves HOLD for unknown evidence values; a registered `scope_absent_is_violation` declaration distinguishes known absence (W0 message template None means free prose). Core conversion preserves template scope and does not invent a customer restriction when absent. Reference and conventional encode the same W0 cases independently; oracle/committed-act scoring use the corrected reference. Frozen fixtures stay unchanged.


## Q17.1 — trusted registration, implicit values and complete paths

Q17.1. (a) A tool's dimensions are fixed by its trusted registration (interface and declared semantics), never inferred from which fields a call submitted; omitting an optional argument never removes a dimension or bypasses its restriction (case c). (b) Where a tool's trusted semantics supply an implicit or default value for a dimension, that value is checked like a supplied one. (c) A restriction fails authorization under the grant chain that carries it; each complete path is assessed separately and the least restrictive complete path may be selected (stage 4), so an independently sufficient unrestricted grant can still authorize; restrictions are never combined across paths and a restricted path is never repaired by another grant. (d) Restrictions survive conversion at every level of the chain and are checked at proposal and again at execution. (e) The core converter, the reference and the conventional arm all change: at 74c5b0a0 both reference and conventional return REFER for free prose under a template-limited grant and must return the AU1 authority failure.

[IMPLEMENTATION] ToolRegistry fixes dimension names from explicit trusted registration (or the fixed interface schema), not call keys, and projects absent values without dropping dimensions. W0 declares customer and, for message_party/hold_refund/deny_refund/report, template; the latter three project their actual implicit template regardless of caller assertions. The authenticated grant_amendment change.scope path writes a new grant version through the existing single write path, with resource_scope correction rights limited to the existing gateway grant-change boundary. Reference, conventional and business hosts preserve the same actual scope amendment.
