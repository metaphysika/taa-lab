# TAA gateway code inventory v0 — Paper 2 lab at v0.20.6

1. [DESCRIPTIVE] The v0.20.6 lab contains useful authority, duty, referral and correction mechanisms, but they are split across two gate families.
2. [DESCRIPTIVE] Its displayed one-time token is a log identifier, not an independently validated and consumed execution capability.
3. [DESCRIPTIVE] Version checks exist for claim settlements; general rule-computed, record-version support and a hash-chained runtime event log do not.
4. [INTERPRETATION] Reuse policy examples, selected pure helpers and regression fixtures; rewrite the authorization kernel and durable record lifecycle in a separate implementation after review.
5. [OPEN QUESTION] The exact five-stage design comparison awaits readable design text; this inventory currently maps the requirements Chris supplied directly.

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

[DESCRIPTIVE] Comparison requirements come from Chris's Stage 1 request:
rule-computed versioned support, re-evaluation on change, ordered evaluation with
rule-owned prohibition release, claimant/owner/discharge duties and accepted
transfer, roster-selected report duties, correction records and hash-chained
events. The supplied
[Claude design link](https://claude.ai/artifact/WANzqqRBcZPjLHiWZKG6g9)
was inaccessible to the web tool; no browser tool or readable attachment was
available at preparation. The request for its text remains open. Consequently,
this is a concrete code inventory against those supplied requirements, not a
claim to have checked the complete design or its exact stage names/order.
Coding remains on hold for Chris's and Astra's review.

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

### One-time tokens

[DESCRIPTIVE] [`TAAGate.request`](../../taa/gate.py#L591), line 623, creates
`secrets.token_hex(4)` and immediately passes it as text in the reason to
`_allow`. There is no token store, signed/canonical action binding, consume API,
replay check or independent token validator. Execution follows in the same
Python call. `V0206Gate` does not use this path.

[DESCRIPTIVE] Coverage: `PerStepJudge` (`tests/test_harness.py:610`) checks that
the comparator lacks token text. The inspected tests do not test token replay,
argument substitution, duplicate consumption, crash recovery or stale versions.

[INTERPRETATION] **Rewrite** token/capability handling if required by the reviewed
design. Preserve the old token as historical instrumentation; do not describe it
as enforcement. A future one-use execution certificate needs a checked binding
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

[OPEN QUESTION] The reviewed design must determine the exact claimant identity,
owner, discharge evidence, accepted-transfer receipt, overdue-duty persistence
and transactional state machine. Existing overdue/transfer terminal states must
not silently erase a still-owed service or repair obligation.

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
cases, rewrite evaluation and prohibition records.** Five possible output labels
are not the design's five ordered stages. Neither family attaches a prohibition
to its originating rule plus the versions of exactly its own records.
Older refusal memory keys use a broad [`world.fingerprint`](../../world/fake_world.py#L170);
outside changes reopen review, and an approved departure can clear a stop. The
v0206 correction guard preserves a `grave` flag but does not re-run the same
trusted rule on changed record versions. Thus neither implements the supplied
rule-owned prohibition-release requirement.

[INTERPRETATION] Existing contradiction records and the world's
[`correct_road_status`](../../world/fake_world.py#L234) before/after effect are
useful evidence examples, but do not constitute a typed correction record
binding old/new versions, author, authority, reason, supporting evidence and
affected warrants. A correctly quoted field also does not prove that all
supporting records were supplied or that their contents are trustworthy.

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

## 3. Cross-cutting design gaps and future acceptance checks

[DESCRIPTIVE] This table summarizes inspected gaps. Proposed checks are OPEN
QUESTIONS for the approved build, not newly written or executed tests.

| Supplied design requirement | Current coverage / gap | Future acceptance check |
|---|---|---|
| Trusted, rule-computed support sets and record versions | [DESCRIPTIVE] Claim settlement versions exist; prose premises and reviewer-supplied plan dependencies are not trusted derivations. | [OPEN QUESTION] Omitted/model-invented supports cannot grant authority; conjunctive and alternative witnesses bind exact record versions. |
| Re-evaluation on change | [DESCRIPTIVE] Snapshot re-review and claim reconciliation exist, without a general invalidation graph or atomic final version check. | [OPEN QUESTION] Relevant changes lapse affected approvals; irrelevant changes do not; stale concurrent execution cannot pass. |
| Ordered five-stage evaluation; only a prohibition's own rule may lift it | [DESCRIPTIVE] No such staged evaluator/rule-owned prohibition record exists. The exact design stage sequence remains unverified. | [OPEN QUESTION] A later permission, unrelated record update, new reviewer answer or other rule cannot cancel the prohibition; re-evaluation uses its own new support versions. |
| Claimant, owner, verified discharge and accepted transfer | [DESCRIPTIVE] Partial fields and a scenario acceptance Boolean exist; no durable successor-duty/receipt protocol. | [OPEN QUESTION] Refusal/revocation and deadlines preserve outstanding duties; accepted handoff preserves accountability; failed validation leaves no partial transition. |
| Report duties selected from the roster | [DESCRIPTIVE] Referral policies name offices/jurisdictions/fallbacks. `report_to_human(message)` is a generic tool; no roster lookup creates claimant/owner report duties or verifies acceptance/delivery. | [OPEN QUESTION] Select the correct independent office from trusted current roster records; silence or sending alone cannot satisfy a delivery/acceptance condition. |
| Typed correction records | [DESCRIPTIVE] Raw review exchanges and some before/after world effects exist without a general version/authority/evidence correction schema. | [OPEN QUESTION] A correction records provenance and affected approvals and cannot silently discharge an independent prohibition. |
| Hash-chained event log | [DESCRIPTIVE] `_GateBase._record`, `DutyLedger._event` and `ObligationLedger._record` append mutable dictionaries. Episode JSON and source hashes are not a runtime previous-hash chain. | [OPEN QUESTION] Canonical linked events detect reorder/change/removal; durable sequence and recovery preserve the chain, including decisions, corrections and duty transitions. A hash alone does not authenticate a truthful source. |
| Complete mediation / one-use effects | [DESCRIPTIVE] The simulation passes tools through a gate by convention. No MCP boundary, consumed execution certificate or process-isolation guarantee is present. | [OPEN QUESTION] Every protected effect crosses the reviewed gateway; retry, replay, argument changes and restart cannot bypass version/one-use checks. |

## 4. Reuse decision and build boundary

[INTERPRETATION] Recommend **reuse-and-refactor at the policy/fixture level,
rewrite at the authorization-kernel and durable-state level**. Useful material
includes explicit scope/cap arithmetic, claim settlement checks, the separation
of duty from permission, declared composition/referral policies, deterministic
world previews and the corresponding regression cases. These reduce the risk of
forgetting known failure modes. Their semantics still need adaptation to the
new refund environment and reviewed design.

[INTERPRETATION] Extending `V0206Gate` by inheritance would import model-mediated
judgment and mutable simulation state without obtaining the earlier gate's
premise/token/protection path. Extending `TAAGate` would import coarse snapshots,
reviewer approvals and a non-enforcing token while leaving duty/grant lifecycle
integration undone. Combining both would obscure ordering and transaction
boundaries. A small separate deterministic core is easier to review for the
new invariants; port a helper only when its contract and tests fit.

[OPEN QUESTION] After Chris's and Astra's design review, specify the versioned
record store, rule evaluator and prohibition ownership, warrant/certificate
derivation, duty/correction schemas and atomic event/execute boundary before
choosing implementation details. Keep all historical modules, manifests and
evidence unchanged. A first synchronous MCP gateway must state its actual
effect boundary; queued/distributed closure needs separate support and cannot
be inferred from local revocation.

## 5. Validation receipt and remaining blocker

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

[OPEN QUESTION] The remaining inventory limitation is the unreadable full design
and attachment. Its exact five-stage ordering and any requirements beyond those
in Chris's request must be checked when readable text arrives. This limitation
does not authorize coding; the owner/reviewer gate remains in force.
