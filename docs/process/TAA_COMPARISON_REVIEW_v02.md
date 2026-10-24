# Comparison review fixes and prospective v0.2 rerun

[ENGINEERING PLAN / 2026-10-24 UTC] Chris relayed Astra's review at eb5213b9 and Claude's confirmation of three blocking defects. This work precedes the replay/audit window and MCP front. No models, Modal, spending, releases or fixture edits.

## Scope and preserved inputs

The rerun is named **v0.2**, over the same ten declared development programs, eight arms and four scripted controllers (320 episodes). The protocol, keys, controllers, programs and ten frozen POEC contracts stay unchanged. Protocol SHA-256: `e8059b51eaea0399f4ffe198d5712497067e5a0f43045539ffad1a71a67b9580`. v0 and v0.1 reports, plans and evidence remain byte-identical; the preservation manifest lists each file. No contracts are authored for additional regressions or probes.

Report labels now mean **independently implemented conventional arm** and **TraceGrant reconstruction with fixed W0 contracts and documented adaptations**. These are implementation descriptions, not claims of external validation or paper-exact reproduction. Internal machine identifiers `conventional` and `tracegrant` remain stable. This document is also a terminology erratum for immutable historical reports; their earlier wording is retained as evidence. Verbatim author/owner notes and the committed protocol are not rewritten.

## Changes and regressions

[IMPLEMENTATION] Conventional `Policy.candidates` checks customer and applicable template scope at every ancestor in the selected complete path. Actions remain leaf business authority plus parent delegation authority; ancestors need not contain the leaf's business action. Root action lists cannot confer business authority beyond root delegation standing. `capacity` already walks customer/template restrictions along the path. Separate regressions retain W0 G1 and restrict G0 to K2, requiring REFUSE for A's supported K1 refund120. Component tests cover parent/leaf template restrictions, missing delegation and root extra actions.

[DISCREPANCY / OPEN] The audit also found that the core W0 grant converter drops `scope.template`; a scoped message that reference and SQL refuse is permitted by core. No declared scoring program has a template-restricted grant. Preserving the field in the generic checker would introduce a HOLD on calls without that resource, whereas reference currently ignores template scope for calls without a template. This distinct question is referred to Claude; no rule meaning is changed silently. Raw diagnostic results are retained with the review evidence.

[IMPLEMENTATION] The external duty oracle deduplicates matching acknowledgment candidates by duty identity. It still requires actual dispatched report artifacts, report/version/recipient matching, matching incident and matter, current unresolved duty/version/recipient, and recipient eligibility. The C→F→C routing regression acknowledges RPT1/v1 at step12, after dispatches at steps1/6/11. Negative controls retain rejection for missing delivery, wrong version/recipient/incidents, ineligible recipient and two distinct candidate duties.

[IMPLEMENTATION] The TraceGrant reconstruction's execution adapter now supplies the observed tool, actor and complete canonical arguments from its actual operation journal. Dispatch compares these with the one-shot certificate in addition to effect bindings and postconditions. Notices also verify physical written arguments against the invocation. The injected-drift probe reuses the frozen T02 contract: certify customer K1, execute customer K2. It must roll back, issue no new receipt, and leave the notice obligation unverified. This is an injected-drift probe, not a new benchmark contract or population result.

[IMPLEMENTATION] Each recorded episode retains its initial actual state channels, changes and native log additions. These come from state, not returned descriptions. Arm-internal duties and allocations are retained for inspection only; the common oracle remains the scoring source.

## Receiptless partial operations

[MEASUREMENT DEFINITION] The unchanged protocol counts execution/closure/transfer operations with receipts. A floor/static operation interrupted after a case or business-operation write can lack a receipt. Such a write is now explicitly reported as **not scored by the receipt-based protocol operation metrics** and separately assessed under **committed acts disallowed by the reference policy**. The latter remains **defined after v0 results; development only; to be pre-registered before Experiment A**. It counts PROHIBIT, REFUSE, HOLD and REFER; ALTERNATIVE is listed separately. Neither measure is silently substituted for the other.

The fault supplement records close_case, offer_duty and accept_duty partial writes at their actual effect and pre-receipt boundaries on floor/static. Actual state changes and missing receipts remain visible. Boundaries without a counterpart remain not applicable by design, with the original reason. These probes are outside the 320 scored episodes.

## Evidence and review gate

Pre-fix controls reproduced the three defects (four subtest failures: scope, acknowledgment on core/SQL actual deliveries, and receipt drift). After-fix controls must pass. Full repository discovery and scripted scenarios precede the implementation freeze. The v0.2 run retains a durable episode journal; no automatic rerun after viewing results. Every v0.1→v0.2 metric cell is reported, including unchanged cells, and changes are traced to observations/oracle outcomes. The full table includes every arm/controller, discrepancies, incomplete and unassessed items. TraceGrant coverage remains only the ten fixed-contract development programs.

[OPEN INPUT] The exact Astra “what the table does not show” list has been requested from Chris. It must be included in the final report rather than attributed from a reconstruction. This PR needs Claude's review and green CI before merge. No merge or launch approval is inferred from passing checks.


## Completed validation and v0.2 evidence

[ENGINEERING OBSERVATION] Runtime `4bb6d23c1fb186d7f00a35e07d059a53eafb0858` passes full discovery: 1,114 tests, 36 optional skips, 0 failures/errors; scripted scenarios pass. All eight GitHub checks on that runtime head are green. Eight new comparison methods pass; the pre-fix three-method run reproduced four subtest failures. The separate24 closure/transfer fault probes pass246 common state audits;12 retain business changes without receipts and are explicitly not scored by receipt-based operation metrics.

[DESCRIPTIVE] One v0.2 run completed320 episodes,39,072 state audits and117 baseline source checks:0 discrepancies,0 incomplete,2,041 unassessed observations. All200 protocol cells,72 supplementary cells and1,088 controller cells match v0.1. Direct retained-data comparison confirms identical final worlds, common oracle boards and per-episode reference-policy counts in all320 episodes. New observation fields are only the explicit receiptless-operation marker, measure label and42 realized-invocation receipt observations. No episode was rerun. An initial formatter syntax failure and the corrected rendering are retained as processing diagnostics.

[ENGINEERING OBSERVATION] All-arm input replay completed with0 unexpected discrepancies/incomplete/errors. Four financial partial-write receipt-mismatch audits remain as observed behavior outside the320 episodes;8 boundaries are not applicable by design. TraceGrant has127 additional no-contract instances explicitly unrun. No new contracts were authored.

[REVIEW] See TAA_CROSS_ARM_SCORING_v02.md and evidence/gateway-cross-arm-scoring-v02/validation.json. The exact Astra limitations list and the separate core template-conversion ruling remain pending. This is a draft fix PR for Claude's review; no merge, launch or H3 conclusion is authorized by these checks.
