> Historical v0.3 stage report at the reviewed PR head. Current semantics and validation are documented in [v0.3.1 alignment](TAA_GATEWAY_ALIGNMENT_v031.md), which supersedes the older timing, disposition and reporting conventions below.

# Gateway v0.3 stage 3 — separately implemented reference model

1. [DESCRIPTIVE] The model is a pure transition system for later property checkers, not a callable production gateway or comparator.
2. [DESCRIPTIVE] It imports only Python standard-library modules and shares no core decision, authorization, discharge, transaction or serialization code.
3. [DESCRIPTIVE] Declarative rules and transition assertions cover three-valued evaluation, authority, invalidation, atomic effects and persistent duties.
4. [DESCRIPTIVE] Its component assertions are Sol-authored; no independently authored expected traces or answer keys have been generated from the model.
5. [OPEN QUESTION] Claude review and independent specification-derived traces remain required; model agreement alone cannot establish correctness or H3.

## Source and implementation boundary

[DESCRIPTIVE] Implements the reference-model work Chris authorized from
*TAA Gateway Core Design v0.3.docx*, SHA-256
`795a08c33b86bdceae6a0da62812b74333cac7195a83946bd3242b23ae106712`.
The [inventory](TAA_GATEWAY_CODE_INVENTORY_v0.md) and
[stage 2 report](TAA_GATEWAY_STAGE2_v03.md) identify the historical code and
storage foundation. The model lives in
[`taa_gateway_reference/model.py`](../../taa_gateway_reference/model.py).
It does not call that foundation, world tools, clients, providers or old gates.
There are no model calls, Modal operations, Notion edits or scientific reruns.

[DESCRIPTIVE] Production stages 4 onward remain held. Model functions describing
an ideal evaluation/transaction are **stage 3 reference semantics**, not an early
implementation of the production pipeline/executor/duty engine. No core gateway
uses the reference model to make decisions. The reference model is not the
strongest conventional comparator, which requires its own later implementation.

## Model interface and declarations

[DESCRIPTIVE] `initial(spec)` returns an abstract state; `transition(before,
Event(kind, actor, data), spec)` returns a separate state/result. Inputs are
deep-copied and never mutated. A rejected transition returns the original state
by value and a reason. Malformed declarations/operators raise programming errors
rather than silently granting permission. `decision` evaluates without issuing
a token. There is no trace generator/exporter or API for blessing expected data.

[DESCRIPTIVE] The `Spec` contains registered tool effects, authorization
declarations, grant standing, authoritative fact sources, reserved questions,
duty declarations and report priority. `Rule` records its identity, version,
stage, applicable tools and an expression. Operators are literal/argument,
authoritative fact/absence, reserved question, duty/case/grant field, Boolean
composition and comparisons. Missing or non-evidential facts yield UNKNOWN;
explicit `exists` can establish a negative query. JSON-typed equality keeps
`true` distinct from `1`. Relevant record queries and their versions/absence are
recorded in the selected justification, including grant-condition queries.

[DESCRIPTIVE] Rule expressions mean "this constraint is satisfied." A violated
prohibition yields PROHIBIT; an unknown required fact blocks permission. Stages
run in the declared five-stage order. Equal-ranked HOLD/REFER results retain the
earlier stage's result, a deterministic tie convention that cannot relax either
block. Authorization requires an explicit declaration and one complete live
grant chain; a request or reviewer answer supplies neither. The selected witness
keeps its own grant, purpose, scope, ancestry and evaluated rules together.

[DESCRIPTIVE] `Event.actor` is supplied by the independent test driver's identity
context, not copied from a gateway proposal or a reassuring log. The model's
source/standing/jurisdiction checks are its own code. It abstracts the simulator's
authentication operation rather than reusing its HMAC/session implementation.
Future property checkers must feed it actual driver identities and independently
observed effects; trusting an agent's claimed actor would invalidate the model's
assurance. Agent assertions have a separate non-evidential record namespace.

## Transition contracts modeled

- [DESCRIPTIVE] Record insertions/corrections, grants/revocation, clock boundaries,
  roster/policy/entitlement changes, stored orders, scoped resolution records
  and duty transitions advance revision and void all live tokens. Token issue,
  decision caching and repeats do not. Changed input permits a fresh evaluation;
  unchanged prohibitions remain prohibited. Consumed witnesses never reactivate.
- [DESCRIPTIVE] Orders are associated by trusted sender/recipient/tool/scope,
  independently of claimed references. Prohibited ordered acts create one
  report duty per ordered act, deduplicated by order, actor and exact act. Routing checks jurisdiction, issuer conflicts,
  disclosure authorization and priority, with deadlines/fallback and no arbitrary
  recipient. A sent report remains unresolved until the selected recipient's
  authenticated acknowledgment; failed routing stays visible.
- [DESCRIPTIVE] Token execution checks actor, exact arguments, live warrant,
  pre-transaction revision, chain/clock and current cumulative constraints.
  Its pure atomic transition includes effect, consumption, duty reconciliation,
  receipt and one revision increment. Other tokens at that revision become void.
  Each named failure boundary and mismatched staging returns no transaction
  changes. A committed effect's history is retained after later correction.
- [DESCRIPTIVE] Cumulative refunds follow stable order identities and current
  settled payment records. Revocation/re-grant does not reset totals. A trusted
  reversal updates current settled totals without rewriting prior receipts.
  Partial payments leave a larger duty unresolved unless its declared bound
  evidence condition is met; the initial model does not silently infer a new
  multi-payment discharge predicate.
- [DESCRIPTIVE] Duty declarations instantiate independently from authoritative
  claim records, including with no proposal. The engine deduplicates identities,
  reconciles corrections, deadlines, ownership and newly created report duties
  to a stable state. Resolution is separate from overdue. Corrected discharge
  or release evidence reopens the duty and case and records the correction;
  releases need declared standing plus substantive recorded evidence.
- [DESCRIPTIVE] Evidence conditions bind claim/claimant/amount/currency and
  settlement/transaction/allocation information. A payment allocation cannot
  discharge two duties. Transfer is an offer until authenticated acceptance;
  pending fallback retains the old owner, then becomes unowned on timeout,
  opening an independent report duty. Any unresolved duty blocks closure,
  including overdue and pending-transfer duties.

## Abstraction choices for review

[DESCRIPTIVE] This is an inspectable finite simulator model, not a complete
refunds-world implementation. Tool declarations name abstract effects. Refunds,
case closure, duty offer/acceptance and report sending have explicit state
effects; read/message/hold/deny are abstract observations recorded by receipts.
Domain-specific message templates, act descriptions and richer discharge
predicates must be declared and reviewed with the later world/policy; their
absence is not evidence of any outcome. The full property harness, mutants,
actual-world projection and independent traces remain later-stage work.

[DESCRIPTIVE] Clock/expiry conventions are explicit: expiry is exclusive
(`step >= expires` is unusable); a missed duty deadline is marked when the clock
passes the last due step, and lateness persists. Due external updates are applied
before duty reconciliation on a clock transition. A previously on-time resolved
duty is not newly labeled late merely because time later passes its deadline.
The caller supplies deterministic event order/identifiers and fixed declarations.
The model does not assert byte-identical gateway logs; stage 2 separately tests
canonical event-log bytes.

[OPEN QUESTION] Claude should check these abstraction/tie/clock conventions
against the specification and independent traces. In particular, external
driver identity, source corrections, allocation semantics and abstract message
effects must not conceal a real-world mismatch. Correlated misunderstandings
remain possible because Sol wrote both components, even with import separation.

## Validation and independent evidence gate

```text
PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_gateway_reference tests.test_gateway_foundation -v
```

[DESCRIPTIVE] 59 component tests pass (34 reference, 25 foundation). Reference
tests assert the named B1–B5 contracts, absence/UNKNOWN, parent revocation,
cumulative limits, proof binding/reopening, ownership acceptance, reporting and
purity/determinism. A static import boundary check admits only standard-library
dependencies and rejects dynamic import/eval/exec. These tests contain explicit
spec-derived assertions; they are not independent review or a model-generated
expected-outcome fixture set. No training exporter, model calls, comparison runs
or scientific claims are added.

[OPEN QUESTION] Claude's concrete traces must be authored from v0.3 independently
of both implementations, including every failure path from Astra's reviews,
then reviewed against the source. They have **not** been received or synthesized.
Later mutants must fail independent assertions, not just disagree with this
model. CI and Claude review are both required before this PR merges. Stages 4
onward still require Astra's v0.3 confirmation.
