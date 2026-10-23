[DESCRIPTIVE] This is a local deterministic reconstruction from Claude's verbatim source notes, not the authors' unpublished implementation.
[DESCRIPTIVE] Ten hand-written POEC contracts replace the LLM compiler and are hash-frozen before comparison outcomes.
[DESCRIPTIVE] The published deterministic lifecycle is implemented; the authors' optional-authority-argument fix is enabled.
[INTERPRETATION] Unspecified details below are explicit local choices, not evidence that the published system cannot support another choice.
[LIMITATION] This arm supplies neither TAA duties/reporting nor empirical H3 evidence; the strongest conventional arm remains separate work.

# Implementation matrix for Claude review

Primary-source access: Claude read arXiv:2608.21126v1 and Chris supplied
`TRACEGRANT_COMPARATOR_SOURCE_NOTES.md`. Sol inspected those notes and preserves
them byte-for-byte (SHA-256 `1e1c5dab96df782ecbad9b5a6138e7f0d9dce453a3fb4a000cb00d716814a3d9`).
The runtime cannot fetch arXiv. Verification depth here is **Claude's relayed
full-text source notes**, not Sol's independent full-text inspection or a
reproduction of the authors' experiments. No official code/configuration was
available. Claims about published behavior are attributed to those notes.

| Item | Source section / status | Implementation and boundary |
|---|---|---|
| POEC MAY/MUST/BIND/VERIFY | §4.2.1, Eq.1; published per notes | Explicit task/argument scope, budgets, obligation DAG, bindings and observable conditions. No field schema was published; JSON layout is a local adaptation. |
| Compiler | §4.2.1, §5.1.4; published LLM, replaced under ruling 1 | Hand-written T01–T10 contracts. No compiler model, prompts or purported compiler accuracy. |
| Five static checks | §4.2.2, Eq.2; published per notes | WellFormed, ControlSafe, FlowSafe, ScopeSafe, VerifySafe, following text definitions rather than garbled Algorithm 1 line14. Rejects types/references, cycles/unreachable hard nodes, absent binding sources, inconsistent scopes/budgets and unobservable verification. |
| Obligation states | §4.3, Eq.3/9; published per notes | PENDING → ACTIVE after dependencies → VERIFIED on admitted evidence or receipt. All effects/completion prerequisites hard. WAIVED unreachable, as rulings 3–4 require. No invented exemption mechanism. |
| Evidence admission | §4.3, Eq.4; published per notes | ACTIVE obligation, authenticated host source, exact query, typed record and integrity hash. Exactly one matching record. Source handles are simulator-host inputs, never actor-supplied authority arguments. |
| Evidence source bridge | unspecified; local adaptation under ruling7 | Existing or arriving trusted W0 records are offered passively to ACTIVE evidence nodes. No LLM retrieval or hidden read budget is measured. A verified evidence node is immutable for that contract; no TAA correction ledger/reset is added. |
| Authority-bearing arguments | §4.3 Eq.4; published per notes | Every present catalogued authority argument requires an allowed literal, admitted-evidence derivation or verified receipt binding. Read-only derivations are explicitly bounded to this refunds task. |
| Optional-authority fix | §5.7, §6.3; authors' stated fix | Optional customer/recipient/scope/citation arguments are bound when present. **This is the authors' proposed fix, not their evaluated configuration.** |
| Deterministic derivations | unspecified; local adaptation | Literal/field identity, supported refund amount, receipt-backed notice amount/citation, bound denial remainder. Sources and postconditions are in frozen task contracts. No task outcome or expected disposition is read by the gate. |
| Runtime decision | §4.3 Eq.5; published ordered rule | STEP_UP_AUTH, else ALLOW when MAY/ACTIVE/proofs/budget, else PROOF_GAP only when proofs alone fail, else DENY. Inactive obligations produce DENY; the adapter does not relabel it as a TAA disposition. |
| Risk detector | §5.1.4, ruling6 | Inert for W0: no matching untrusted payload channel, so STEP_UP_AUTH never fires. A deterministic explicit risk flag tests order outside W0; no invented classifier or model. |
| Call budgets | §4.2.1/4.3 + ruling5 | Fixed per-tool contracts; decrement on certificate issue, restore only for rolled-back dispatch. Reservations remain bound to each issued certificate's budget snapshot; another reservation does not invalidate it globally. |
| Effect certificate | §4.3–4.4, Eq.6–8 | Contract, matched obligation, actor, tool, exact canonical arguments, proofs and budget state; one-shot on dispatch. Local HMAC plus retained exact issued bytes; simulator key custody is a modeled host assumption. |
| Provenance freshness | receipt validity, §4.3–4.4; unspecified detail | Conservative local choice: cited evidence/receipt record must still match its current version at dispatch. No whole-world revision binding or broad re-evaluation. Superseded evidence is rejected; immutable verified evidence is not silently refreshed. This may leave a fixed contract unable to finish. |
| Receipt/postcondition | §4.3–4.4 Eq.6–8 | Receipt only for matching certificate, actual successful effect, argument binding, postconditions and provenance. Actual state is observed; returned effect lists are ignored. Local service transactions roll back partial effects/receipt changes. |
| Final-answer gate | §4.4 Eq.9 | A success claim requires every hard obligation VERIFIED (no WAIVED state). Non-success answers do not assert completion. Gate status is POEC completion, **not W0 lawful-task completion or H3 utility**. |
| Task graph/goal interpretation | unspecified compiler output; local adaptation | Fixed refund → issued notice → closure; T09 adds its partial denial. Correct W0 scripts can be diagnostic prefixes, and corrected/unsupported tasks can leave hard nodes unverified. No after-results contract amendment or invented waiver improves these outcomes. |
| Tool service | W0 adaptation, not a paper claim | Same named refund/message/closure actions and source facts as the development catalog, implemented in a separate small trusted service. Only the three effect types named by the task contracts can execute; other registered W0 actions are outside MAY. Semantic conformance and adapter limits are review subjects before scientific use. |
| Controllers/event order | local harness adaptation | Same ten development inputs, four existing controller definitions, initial records, source-event order and same-step event/proposal/execution phases. Expected keys are available only to the designated key-following controller; no expected field reaches POEC checks. |
| Certificate input naming | local adaptation | Source symbolic Tn maps to observed ECn issue ordinal; dynamic token_from uses the last actual proposal and clears on no certificate. No expected token is used to mint or select an outcome. |
| Duty/transfer/refusal reporting | absent from this reconstructed design by ruling8 | No claimant duty ledger, acceptance-based duty transfer, reopening, report duty or automated routing. Visible W0 grant/order/reviewer events do not silently rewrite the fixed POEC contract. These are **design differences, not defects or claims of impossibility**. |
| Global invalidation | not added, ruling8 | No TAA revision-wide invalidation, complete rule support sets or whole-state re-assessment. Cited provenance checks and one-shot dispatch remain. |
| Authors' material | data-availability statement + ruling9 | Chris may separately request configurations. Nothing is emailed automatically; any received material becomes a new source and is compared with these rulings. |

[DESCRIPTIVE] Contract authoring: initial freeze commit `2d1e05b4`; manual
preflight corrected provider identity spelling and T09's notice scope before any
comparator execution, final freeze `30b6290b`. Original bytes remain in Git.
No contract or manifest has changed after seeing comparator outcomes. Runtime
repairs and stronger independent audits preserve the first observed run and the
final source hashes; no result is chosen to establish superiority.

[DESCRIPTIVE] This is stage 8's TraceGrant component, stacked on the unmerged
stage 7 development driver. The no-gateway/static arms, the independently built
strongest conventional arm and the four TAA ablations require separate work.
A complete comparator-stage or H3 acceptance claim is not made by this PR.
Matching correct behavior is a success for both architectures. Claude reviews
this implementation and matrix; Astra reviews conventional arms before step 3.
