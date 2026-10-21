# TAA gateway code inventory v0 — Paper 2 v0.20.6 against gateway design v0.3

1. [DESCRIPTIVE] The v0.20.6 lab contains useful authority, duty, referral and correction mechanisms, but they are split across two gate families.
2. [DESCRIPTIVE] Its displayed one-time token is a log identifier, not an independently validated and consumed execution capability.
3. [DESCRIPTIVE] Version checks exist for claim settlements; general rule-computed, record-version support and a hash-chained runtime event log do not.
4. [INTERPRETATION] Reuse policy examples, selected pure helpers and regression fixtures; rewrite the authorization kernel and durable record lifecycle in a separate implementation after review.
5. [DESCRIPTIVE] v0.3 is the controlling design: the inventory and build stages 2–3 are authorized; stages 4 onward await Astra’s confirmation, and each PR requires Claude review plus passing CI.

## Scope, provenance and verification

[DESCRIPTIVE] Prepared by Sol on 21 October 2026. The historical anchor is
[commit `1a8cb167763d03389741a93426455a5d946e20aa`](https://github.com/metaphysika/taa-lab/commit/1a8cb167763d03389741a93426455a5d946e20aa),
*Repair factual-correction gate and record Luna regression*, which introduced
`taa/v0206_gate.py`, `taa/v0206_counsel.py`, `scripts/run_v0206.py` and
`tests/test_v0206.py`. No local `v0.20.6` tag was present. The inspected current
base is `daa73750df013beda32ab275653bf078265c5e5b`; a Git comparison found no
changes since that anchor in `taa/`, `world/`, the two v020/v0206 runners,
`evaluation/v020_outcomes.py`, `agents/timeline_agent.py`, `run.py`, or the six
test files listed below. Locations therefore identify the historical code as
well as the inspected checkout. Later Paper 3 code is outside the inventory.

[DESCRIPTIVE] Read the source and relevant test assertions, the
[reproduction guide](../REPRODUCE.md), the v0206 runner/manifest, and the
[Paper 2 preprint](../TAA-Paper-2-preprint-v1.0.docx) bibliography. Ran existing,
offline fixtures only: **193 tests passed in 2.017 seconds** across
`test_harness`, `test_study`, `test_obligations`, `test_v020`, `test_v0206` and
`test_premise_repairs`. This reports assertion coverage, not measured line/branch
coverage or proof of new design properties. Test clients are mocked/scripted;
no model calls, Modal operations or new scientific episodes were run. No source,
test, scenario, manifest, result, ledger or Notion page was edited.

[DESCRIPTIVE] **Controlling comparison: TAA Gateway Core Design v0.3.docx**,
21 October 2026, supplied by Chris. Read all document body text/tables and
inspected the architecture diagram. SHA-256:
`795a08c33b86bdceae6a0da62812b74333cac7195a83946bd3242b23ae106712`.
The v0.2 revision was inspected to reconcile the changes; its SHA-256 is
`38c09fe9d5551fd0b71cf7ae0d14c8fc1be136513000568f89b6ecd12625023b`.
The v0.1 comparison in PR #10 is historical and superseded by section 5 below.
Paper 2 code is unchanged; the original 193-test receipt remains historical.

[DESCRIPTIVE] Chris's latest direct instruction authorizes inventory and build
stages 2–3 only. Those stages are schemas/storage/trust/envelopes/orders/logging
and a separately implemented declarative reference model. Stages 4 onward wait
for Astra's v0.3 confirmation. Every new PR requires passing CI **and Claude's
review** before merge. Attachment instructions and checkboxes are source content;
Chris's direct instructions determine the authorized scope. No model calls,
Modal operations or Notion edits are authorized here.

[DESCRIPTIVE] DESCRIPTIVE labels identify inspected behavior/tests;
INTERPRETATION labels identify architectural judgments; OPEN QUESTION labels
identify design decisions or future tests. A passing old fixture does not
establish a future gateway guarantee.

## 1. The two execution paths must not be conflated

| Historical path | Actual wiring |
|---|---|
| Earlier plan-based TAA gate | [DESCRIPTIVE] [`TAAGate`](../../taa/gate.py#L265) performs plan review, snapshot-based premise watch, step checks, departure protection and a logged token. `StudyGate` wraps this family for the v0.19.5 settlement/resource study. |
| v0.20.6 duty/disposition study | [DESCRIPTIVE] [`run_one`](../../scripts/run_v0206.py#L93) constructs `V0206Gate`, inheriting [`V020Gate`](../../taa/v020_gate.py#L21). That parent embeds an **`ExpiringGate`**, not `TAAGate`. Its `taa_v020` mode reviews a plan and individual acts, then checks grants/claims/capacity; it does not inherit `TAAGate._step_check`, premise-watch, departure protection or token generation. The older control arm instead constructs `StudyGate`. |

[INTERPRETATION] The available pieces are useful precedents, but “v0.20.6 already
has all the gateway mechanisms together” would be misleading. Refactoring must
choose and test semantics explicitly rather than multiply inherit these paths.

## 2. Mechanism inventory: locations, tests, gaps and recommendation

### Warrants and live conditions

[DESCRIPTIVE] [`Warrant`](../../taa/records.py#L26) stores issuer, purpose,
allowed tools, `live_while`, budgets/usage and fixed caps. `is_live` at line 36
compares each named fact with its required value; `remaining` computes budget
left. [`ExpiringGate._refusal`](../../taa/gate.py#L235) checks liveness before
scoped permission/budget/caps. [`TAAGate._step_check`](../../taa/gate.py#L458)
also checks liveness and plan limits. `V020Gate.request` invokes the embedded
expiring gate's structural refusal before its reviewer call.

[DESCRIPTIVE] Coverage: `tests/test_harness.py`, `GateRules` at line 290,
`FixedLimitsV013` at line 1249, `PerTargetLimits` at line 1005 and
`NoEffectActs` at line 512 cover expiry, caps, use/amount limits and no-effect
accounting. `tests/test_v020.py:76` covers composed-grant expiry.

[INTERPRETATION] **Reuse and refactor** the explicit data and arithmetic checks.
Missing: warrant lifecycle/version identity, rule IDs, trusted derivations of
support sets, excluded-means semantics, and transactionally bound execution
evidence. Current liveness reads values; it does not bind a decision to versions
of the records actually supporting each rule. These mutable Python objects are
protected by the lab's calling convention, not a separate security boundary.

### One-time tokens and acting-party binding

[DESCRIPTIVE] [`TAAGate.request`](../../taa/gate.py#L591), line 623, creates
`secrets.token_hex(4)` and immediately passes it as text in the reason to
`_allow`. There is no token store, signed/canonical action binding, consume API,
replay check or independent token validator. Execution follows in the same
Python call. `V0206Gate` does not use this path.

[DESCRIPTIVE] Coverage: `PerStepJudge` (`tests/test_harness.py:610`) checks that
the comparator lacks token text. The inspected tests do not test token replay,
argument substitution, duplicate consumption, crash recovery or stale versions.

[INTERPRETATION] **Rewrite** token/capability handling to meet the draft's
single-use execution binding. Preserve the old token as historical instrumentation;
do not describe it as enforcement. A future one-use execution certificate needs a checked binding
and atomic consumption at the protected effect boundary.

### Step check and approval protection

[DESCRIPTIVE] [`TAAGate._step_check`](../../taa/gate.py#L458) checks plan status,
live warrant, caps, registry, plan tools/targets, pending referrals, target
limits and budgets. [`_protected_conflict`](../../taa/gate.py#L508) and
[`_rereview`](../../taa/gate.py#L537) block a departure that would make an
unexecuted approved act impossible before consulting the reviewer. They use
[`preview.made_impossible`](../../taa/preview.py#L157) on copied simulated
worlds. There are logistics-specific exceptions for settled urgent claims.

[DESCRIPTIVE] Coverage: `GateRules:290`, `PerTargetLimits:1005`,
`ReviewStopsV016:1648`, `PreviewOrderV018:1853` and
`tests/test_obligations.py:222/236` cover scoped execution, remembered stops,
departure conflict, urgent priority and scarcity. The v0.20.6 path instead uses
[`V020Gate.request`](../../taa/v020_gate.py#L125), with rights-panel review,
per-act dispositions, model-supplied plan dependencies, grants and resource checks.

[INTERPRETATION] **Reuse/refactor policy predicates and fixtures; rewrite their
composition into the new evaluator.** Approval protection is a sequential
simulation of resource feasibility, not a general versioned dependency proof.
The v0206 plan dependencies are supplied by the reviewer and checked directly;
they are neither trusted-rule-computed nor transitively closed. The new core
must not infer support completeness from a model's dependency list.

### Change detection and re-evaluation

[DESCRIPTIVE] [`premises.snapshot/changes`](../../taa/premises.py#L32) watches
reviewer-visible state; `Plan.premises` is prose. `TAAGate._premises_changed`,
`_premise_rereview` and `_allow` (`taa/gate.py:422/426/445`) compare snapshots,
re-review the remaining plan and manage the baseline after own effects.
[`ObligationLedger.reconcile/_apply_reply`](../../taa/obligations.py#L52)
check claim authority, source, scope and `premise_version` for settlement replies.
`V020Gate.after_advance/request` reconciles claims and duties, but has no general
dependency invalidation/re-evaluation graph.

[DESCRIPTIVE] Coverage: `PremiseWatchV013:1354` and
[`PremiseRepairs`](../../tests/test_premise_repairs.py#L11) verify outside changes,
requested-act preview ordering and that a read/report cannot absorb an
unreviewed change. `tests/test_obligations.py:179` rejects wrong-scope/stale
settlements; line 272 checks visible capacity change before the next decision.

[INTERPRETATION] **Reuse the snapshot/change fixtures and scoped-settlement
checks, rewrite support tracking.** Watching all visible facts over-invalidates
some decisions and lacks a proof of exactly which record versions were read.
Conversely, automatically rebasing after own actions is not sufficient for
rules whose support those actions change. Existing claim versions are a narrow
precedent, not a versioned store for every policy-relevant record.

### Duty record and referrals

[DESCRIPTIVE] [`DutyLedger`](../../taa/duties.py#L25) loads scenario dictionaries.
Fixtures include `beneficiary`, `responsible_party`, `required_service`, source,
deadline and `discharge_jurisdiction`; these resemble claimant/owner/service
fields but have no comprehensive duty-schema validation. `refer` at line 44
uses declared recipient, jurisdiction, response deadline, interim policy and
fallback. `_apply_answer` at line 68 checks the responding recipient; discharge
requires a reason and declared jurisdiction; transfer requires
`recipient_accepted is True` and a new responsible party. `advance` and
`end_step` handle silence/deadlines. `fulfilled` at line 144 marks the first
matching tool/target duty fulfilled after an `ok` result. `V020Gate.after_advance`
can open a restoration referral after permission withdrawal.

[DESCRIPTIVE] Coverage: [`DutySafetyTests`](../../tests/test_v020.py#L28),
especially line 40, shows a duty surviving withdrawn permission and later
becoming overdue; line 58 rejects a mismatched responding office and transfer
without acceptance. It does **not** positively test accepted transfer or
authorized discharge. `tests/test_obligations.py:123` and `NoticeSentVsReceived`
(`tests/test_harness.py:820`) distinguish silence/logging from permission/receipt.

[INTERPRETATION] **Reuse/refactor the separation of duty from permission and the
referral examples; rewrite the durable transition boundary.** A Boolean in a
trusted scenario schedule is not an authenticated acceptance receipt. Transfer
updates `responsible_party` and makes the local duty terminal (`transferred`),
without creating/tracking a recipient-owned successor duty. Fulfillment is a
tool/target match, not a general verified discharge predicate; multiple
claimants for one act are not independently discharged by `duty_for`'s first
match. The referral is marked answered before subsequent validation can raise;
the operations have no transaction rollback. Preserve these as findings for
refactoring, not a claim that an adversarial deployment was tested.

[DESCRIPTIVE] v0.3 specifies claimant, owner, bound record evidence, authenticated
acceptance and a fallback offer; resolution and overdue are independent fields.
Existing terminal overdue/transfer states are therefore incompatible with its
persistence contract; section 5 gives the controlling gap assessment.

### Dispositions, prohibition protection and corrections

[DESCRIPTIVE] [`DISPOSITIONS` and `ask`](../../taa/v020_counsel.py#L11) parse
`permit`, `permit_narrower`, `prohibit`, `obtain_evidence`, `refer`; malformed
replies become referrals. The prompt asks for M/A/F together. `V020Gate.request`
checks structural authority first, then calls the reviewer and interprets its
disposition. A plan's stopped status permits later act-scoped review.
[`V0206Gate._review`](../../taa/v0206_gate.py#L10) replaces the defective v020
correction path: unresolved factual contradictions become a held referral, and
a grave initial objection cannot become permission merely through correction.
[`v0206_counsel.ledger_contradictions`](../../taa/v0206_counsel.py#L7) checks
cited current field values for three factual basis types, only on negative
dispositions. `contradictions`, raw replies and review history record the exchange.

[DESCRIPTIVE] Coverage: all four
[`CorrectionSafetyTests`](../../tests/test_v0206.py#L31) reproduce a saved moral
refusal without new inference, allow a corrected non-grave capacity fact, hold
an unresolved error and prevent a grave objection becoming permission.
`DutySafetyTests:117/141/151` checks narrower amounts, plan-act parsing and the
requested-act preview. `RefusalMemory:861` and `ReviewStopsV016:1648` test the
older fingerprint-based stop memory.

[INTERPRETATION] **Reuse the five disposition names and correction regression
cases, rewrite evaluation and prohibition records.** The new label is `ALTERNATIVE`,
a suggestion that must be resubmitted, rather than an immediately tokenized `NARROW`.
Five possible output labels
are not the design's five ordered stages. Neither family attaches a prohibition
to its originating rule plus the versions of exactly its own records.
Older refusal memory keys use a broad [`world.fingerprint`](../../world/fake_world.py#L170);
outside changes reopen review, and an approved departure can clear a stop. The
v0206 correction guard preserves a `grave` flag but does not re-run the same
trusted rule on changed record versions. Under v0.3, a relevant change allows
a fresh complete evaluation; it does not dictate permission. Neither old family
implements that revision-scoped, three-valued contract.

[INTERPRETATION] Existing contradiction records and the world's
[`correct_road_status`](../../world/fake_world.py#L234) before/after effect are
useful evidence examples. Distinguish two design objects: a **factual record
correction** appends a version with provenance and triggers re-evaluation;
a **training correction record** binds an attempted act/reasons to the failed
stage/rule/versions, constraint, correct alternative and subsequent outcome.
v0.3 retains six separate dimensions and a split tag in raw events, deferring
training export and final labeling. Neither complete schema/lifecycle is implemented by the old review
exchange. A correctly quoted field also does not prove that all supporting
records were supplied or that their contents are trustworthy.

### Composed grants

[DESCRIPTIVE] [`validate_grant`](../../taa/duties.py#L12) requires identity,
issuer, jurisdiction, acts, targets, resources, purpose, delegation limit,
expiry and context. [`grant_check`](../../taa/duties.py#L149) filters live grants
by act, target, purpose, jurisdiction, amount and any independent override; a
declared composition requires valid grants for all named contexts. The function
returns a Boolean and reason, not the selected support witness. `resources` and
`delegation_limit` are required fields but not enforced as resource consumption
or recursive delegation bounds by this function.

[DESCRIPTIVE] Coverage: `tests/test_v020.py:76` checks declared two-context
composition, missing context and expiry; line 128 checks independent override
versus wrongful premium diversion. G6 fixtures exercise undeclared stitching
and rights-panel boundaries. No general delegation graph, alternative minimal
support-set enumeration, descendant invalidation or concurrent-use test was
established by the inspected assertions.

[INTERPRETATION] **Reuse/refactor the explicit composition policy examples and
negative fixtures; rewrite derivation output and lifecycle.** Preserve
conjunction versus independent alternatives, return the actual rule-selected
versioned supports, and propagate invalidation without manufacturing new
authority or revoking independently sufficient support.

## 3. Cross-cutting v0.3 requirements

[DESCRIPTIVE] Section 5 is the controlling gap matrix, including the requirements
added in Chris's v0.2/v0.3 amendments. Rule-computed justification still matters,
but **selective dependency invalidation is deferred**. Every decision-relevant
change advances one global revision and voids all outstanding tokens. Earlier
v0.1 questions about allowing only a prohibition's own changed records to start
reconsideration no longer describe this design. Within a fresh evaluation, a
prohibition cannot be overridden; unchanged facts reproduce it.

## 4. Reuse decision and build boundary

[INTERPRETATION] Recommend **reuse-and-refactor at the policy/fixture level,
rewrite at the authorization-kernel and durable-state level**. Useful material
includes explicit scope/cap arithmetic, claim settlement checks, the separation
of duty from permission, declared composition/referral policies, deterministic
world previews and the corresponding regression cases. These reduce the risk of
forgetting known failure modes. Their semantics still need adaptation to the
new refund environment and reviewed design. The draft explicitly chooses
per-act review without a plan-first layer; reuse approval-protection examples
as regressions for outstanding duties/resources, not as a reason to port the
old plan-approval architecture. For v0.3, replace selective support invalidation
with the specified conservative global revision; retain support provenance for
audit, not as the initial invalidation algorithm.

[INTERPRETATION] Extending `V0206Gate` by inheritance would import model-mediated
judgment and mutable simulation state without obtaining the earlier gate's
premise/token/protection path. Extending `TAAGate` would import coarse snapshots,
reviewer approvals and a non-enforcing token while leaving duty/grant lifecycle
integration undone. Combining both would obscure ordering and transaction
boundaries. A small separate deterministic core is easier to review for the
new invariants; port a helper only when its contract and tests fit.

[INTERPRETATION] Build the authorized v0.3 storage/schema and reference-model
stages against these contracts; do not implement the held pipeline, production
transaction or duty-engine stages early. Keep all historical modules, manifests and
evidence unchanged. A first synchronous MCP gateway must state its actual
effect boundary; queued/distributed closure needs separate support and cannot
be inferred from local revocation.

## 5. Controlling gap matrix: gateway v0.3

[DESCRIPTIVE] Read the named Paper 2 functions and relevant test assertions.
"Missing" below means absent from these inspected historical execution paths,
not absent from the wider literature. Existing fixture success does not prove
v0.3 conformance. Every recommendation is INTERPRETATION.

| v0.3 requirement | Paper 2 locations and inspected behavior | Existing assertion coverage and gap | Recommendation |
|---|---|---|---|
| Three-valued predicates; all five stages | `taa/v0206_counsel.py:7 ledger_contradictions` returns error strings, not satisfied/violated/unknown rule values. `taa/v020_gate.py:125 request` checks structural authority before model M/A/F judgment. | Four `tests/test_v0206.py:31 CorrectionSafetyTests` cover correction safety; `tests/test_v020.py:91/99` distinguish cited capacity facts and an unconfigured express limit. No generic UNKNOWN propagation, stage ordering or default REFER for missing authorization rule. | Reuse correction regressions; rewrite evaluation in stage 4, which is currently held. |
| Complete justification, one grant/scope/purpose | `taa/records.py:26 Warrant`, `taa/duties.py:149 grant_check`, `taa/v020_gate.py:174` plan dependencies. Composition checks return Boolean/reason; model supplies plan dependencies. | `tests/test_v020.py:76/128` check declared contexts, expiry and independent override. No complete versioned justification including absent queries and prohibition non-applicability. | Reuse conjunction/independent-override examples; replace derivation and provenance. |
| Global state revision and complete invalidation | `taa/premises.py:32 snapshot`, `taa/gate.py:422 _premises_changed`, `taa/obligations.py:52 reconcile` and claim `premise_version` provide snapshots or local versions. `Plan.revision` is a Boolean about re-proposing a plan, not state revision. | `PremiseWatchV013`, `tests/test_premise_repairs.py:11`, `tests/test_obligations.py:179/272` cover outside changes and stale settlement replies. No global revision or invalidation of every outstanding token. | New conservative revision barrier; do not reuse snapshot rebasing as that barrier. |
| Relevant insertions, expiries, ancestry, cumulative limits | `world/fake_world.py:46 advance` inserts shipments and applies events. `DutyLedger.advance` handles deadlines; `grant_check` checks expiry/context, without parent-chain validity. `_GateBase._cap_check` and `_step_check` enforce running caps. | `test_harness.py:787/1249/1741`, `test_v020.py:76`, `test_obligations.py:140/152/167` cover caps, arrivals, expiry and duplicate holds. They do not invalidate tokens on negative-query changes, ancestry changes or cumulative consumption. | Port boundary cases, not lifecycle code. Stage 2 stores all writes/revision together; execution invalidation remains stage 5. |
| Pre-transaction revision; actor-bound tokens | `taa/gate.py:623` produces token text only. `_GateBase._execute:67` directly calls the tool. There is no acting-party/grantee binding or checked pre-state revision. | No replay, another-actor execution, two-token/one-revision or expiry-race assertion in inspected token path. | New token schema now; enforcement in held stage 5. |
| Single atomic execution transaction | `taa/v020_gate.py:205–211` executes, records the result, fulfills a duty and reconciles sequentially. `_GateBase._execute` mutates world then use count. `DutyLedger._apply_answer:68` mutates referral before later validation may fail. | Existing amount/seat checks test sequential outcomes, not failure rollback at validate/stage/effect/consume/duty/receipt/revision boundaries. | Rewrite stage 5 transaction; stage 2 must provide one state publication path without implementing execution early. |
| One path for state and revision | `FakeWorld` methods mutate lists/dicts; `V020Gate.after_advance:91` calls `record.update`; `DutyLedger` directly mutates grants/duties/referrals. | No assertion that every rule-visible write, including clock/ledger/roster/order state, passes one revision-changing path. | New protected versioned store and snapshot API. Do not expose mutable internal records. |
| Authenticated issuer envelopes | `world/fake_world.py:108` checks a scenario's `authenticated is True`; `ObligationLedger._apply_reply:119` checks scheduled source/scope/version; `DutyLedger._apply_answer` compares recipient names. | `tests/test_obligations.py:82/179` test malformed declared authentication and scoped replies. No sender-bound envelope minted from simulator identity. | Preserve negative fixtures; new simulator-authenticated envelope API, explicitly scoped to the simulated trust model. |
| Stored-order provenance; trusted acting party | Agent instructions and reviewed act dictionaries are not an authenticated store linking order sender, recipient and scope. `request(tool,args)` has no authenticated actor parameter. | No tests for omitted/substituted order references or actor substitution. | Store orders under the same trusted write path. Proposal claims cannot create or suppress an order association; actor comes from simulator state. |
| Record-write trust boundary | `ToolRegistry` classifies effects; `FakeWorld.correct_road_status:234` and `log_inspection` write record fields directly. `true_closed` distinguishes simulated reality from record edits for scoring, not a general evidential write policy. | `tests/test_harness.py:1826` confirms record edits do not change the road. No kind/tool/source matrix preventing agent assertions becoming authorizing evidence. | New fixed per-kind writer policy; evidential status assigned by boundary, including trusted committed receipts. |
| Bound discharge evidence and acceptance-only transfer | `DutyLedger.fulfilled:144` matches first tool/target after an OK return. `_apply_answer:85/91` accepts discharge reason/jurisdiction or a scenario acceptance Boolean, then marks transfer terminal. | `tests/test_v020.py:40/58` cover survival after withdrawal and rejection of missing acceptance. No authenticated positive handoff, claimant/transaction/amount/currency/settlement/allocation binding or receipt double-use test. | Reuse separation of permission from duty; replace transition and evidence binding. Transfer keeps duty unresolved and changes owner only on authenticated acceptance. |
| Closure blocked for every unresolved duty, overdue or not | `FINAL_DUTY_STATES` at `taa/duties.py:9` includes `unmet_past_deadline` and `transferred`; `_transition:101` acts only while open. No `close_case` tool in Paper 2 world. | `tests/test_v020.py:40` verifies the old terminal overdue state, not v0.3 closure. | New independent `resolution` and `overdue` fields; overdue and pending transfer never resolve a duty. |
| Mandatory reopening after corrected discharge/release evidence | `DutyLedger._transition` ignores non-open duties. Claim reservation reconciliation is not reopening a claimant's resolved duty or case. | No corrected-payment/withdrawal/duplicate-basis test reopening duty and closed case. | New explicit resolution basis and correction-citing reopen transition; preserve original history. |
| Independent duty engine | `DutyLedger.advance:108` already processes replies/deadlines without an act; `V020Gate.after_advance/end_step` invoke it. Duties mostly originate from initial scenario dictionaries; restoration referral scans only open duties. | `tests/test_v020.py:40` exercises no-act deadline progression. No stable-point derivation, early-prohibition duty creation, correction reopening or report-loop prevention. | Reuse no-act progression principle and fixtures; rewrite derivation/deduplication and integrate the single mutation path in stage 6. |
| Report routing and acknowledgment | `DutyLedger.refer:44` uses fixed recipient/jurisdiction/fallback. `report_to_human:316` logs generic prose. `StudyGate` has independent reporting examples. | `test_obligations.py:61`, `test_harness.py:820 NoticeSentVsReceived`, and `test_v020.py:58` cover independent reporting, sent/received and wrong office. No full roster jurisdiction/conflict/disclosure/priority/ack/failure routing. | Reuse fixtures; implement stage 6 routing under gateway standing, independent of the denied grant. Missing eligible route keeps duty unresolved. |
| Reviewer answers become resolution records | `V0206Gate._review:10` uses a model's aggregate disposition and keeps raw replies/history; `DutyLedger._apply_answer` can directly issue a grant. | Four correction tests guard old failure modes; none restrict a reviewer to one reserved question recorded with authenticated jurisdiction followed by full re-evaluation. | New resolution-record schema/storage now; interpreter in held stage 4. A reviewer reply itself never issues a token. |
| Hash chain and authenticated ending | `_GateBase._record:79`, `DutyLedger._event:37`, `ObligationLedger._record:49` append mutable dictionaries. Archive/source hashes are different objects. | No runtime chain/count/checkpoint test or deterministic byte log guarantee. | New canonical event chain and authenticated terminal count anchored outside the log; state the simulator/host assumptions. |
| Separately implemented reference model and external expected traces | Existing fixture reviewers share world/gate helpers; they are regression clients, not the required declarative transition relation. | No architectural separation assertion, independent concrete traces from Claude or mutation checks against independent assertions. | New stage 3 model, sharing no core decision/authorization/discharge/transaction code. Do not generate expected answers from it. |

[INTERPRETATION] **Reuse/refactor pure policy helpers, scenario ideas and regression
fixtures; rewrite the state/authorization kernel and duty lifecycle separately.**
This recommendation survives v0.3. Preserve all historical Paper 2/Paper 3 source,
ledgers, manifests and evidence. Reuse is semantic, not inheritance from either
old gate family. Implement only authorized stages 2–3 now; schema presence must
not be described as enforcement of held stages 4–6.

[DESCRIPTIVE] v0.3 resolves the former v0.1 review questions: unresolved and
overdue are separate; fallback is an offer until acceptance; alternatives need a
new proposal; evidence corrections must reopen duties/cases; training export is
deferred; log endings need a trusted checkpoint. Its H3 comparison separates a
TraceGrant-faithful adaptation from a strongest conventional arm with the same
requirements. Neither this inventory nor model agreement establishes H3 or a
novelty claim. Independently authored expected traces and Claude review remain
necessary; implementation agreement alone is insufficient.

## 6. Validation receipt and build hold

[DESCRIPTIVE] Existing offline command executed on the stated current base:

```text
PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_harness tests.test_study tests.test_obligations tests.test_v020 tests.test_v0206 tests.test_premise_repairs
Ran 193 tests in 2.017s — OK
```

[DESCRIPTIVE] File-level counts from inspected test methods: harness 143,
study 11, obligations 19, v020 12, v0206 4, premise repairs 4. Subtests and scenario
loops exercise additional cases but are not counted as independent experiments.
Whitespace and document links are checked separately; repository CI is required
before this documentation PR merges. No new tests or production code were added.

[DESCRIPTIVE] The controlling comparison now uses the identified v0.3 DOCX.
The 193-test receipt is from the original inventory and is not a new conformance
result. The v0.3 follow-up reads code and assertions without rerunning science.
Stages 2–3 are authorized; later stages remain held. CI and Claude review are
both required for every new PR before merge.
