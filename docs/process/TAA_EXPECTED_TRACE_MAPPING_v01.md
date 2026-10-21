# Expected traces v0.1 — W0 mapping for Claude review

1. [DESCRIPTIVE] The source zip and all extracted files are preserved byte-for-byte under `tests/expected_traces/v0.1/`.
2. [DESCRIPTIVE] Zip SHA-256 is `e6ee4e2683f908e7c008b926db801886f836b2c6a25fe8ee81fd355f04d1939e`; its nine manifest entries verify.
3. [DESCRIPTIVE] The supplied W0 names remain the semantic identifiers in both implementations; storage keys and money representation are mapped below.
4. [INTERPRETATION] Quoting flow-style duty identifiers and selecting variant inputs are explicit ingestion choices, not changes to expected outcomes.
5. [OPEN QUESTION] Claude must review this mapping and each implementation PR; Q1–Q9 remain unresolved until his v0.3.1 note.

## Provenance and protected files

[DESCRIPTIVE] Chris supplied the zip attributed to Claude. Its README states
that the traces were authored from v0.3 without seeing implementation output.
Sol verified hashes and byte identity, not that authoring chronology. The source
zip is retained alongside its unchanged extracted README, world, trace YAML and
MANIFEST. `PROVENANCE_v01.json` additionally pins the zip and manifest. No source
expectation is edited, repaired on disk or generated from a model.

[DESCRIPTIVE] The 38 base definitions include a T36 variant container; with the
seven named variants there are 45 definitions, 44 executable scenarios. Expanding
T23's seven fault parameters produces **50 executable test cases per backend**.
A container without actions is not counted as a passing scenario.

## Names and representation

[DESCRIPTIVE] These are assigned integration names, including names for core
components still to be built. They are not claims of current implementation
conformance. The reference-side normalization has no normative decisions and
will import no core decision/authorization/discharge/transaction functions.

| W0 category / abstract name | Core representation | Reference representation / observation |
|---|---|---|
| Parties `A`, `B`, `L`, `F`, `R`, `C`, `K1`, `K2` | Same semantic IDs; simulator-bound sessions supply actor/sender | Same IDs in independent driver events; never copied from proposal claims |
| `company` | Root standing principal | Same root principal in reference standing declarations |
| `gateway_reporting` | Gateway's own reporting authority, distinct from G1 | Independent reporting authority in reference state |
| External sources `warehouse`, `carrier`, `payment_processor`, `customer_portal`, `reviewer_interface`, `executor` | Trusted simulator source/tool bindings; assertions do not acquire these identities | Independently checked source declarations; executor effects arise only from the reference transaction |
| `G0`, `G1`, later `G1b` | Same grant IDs; versioned `grant:` records | Same IDs and parent relation in independent grant state |
| `G0.actions: grant_refund_authority` | Delegation standing over the effects delegated by G1, not a direct refund tool | Explicit reference delegation relation, not concatenated tool allowlists |
| `P1` | Same purpose ID and excluded proxies | Same input purpose; no claimed-purpose authority |
| Commerce `ORD1/ORD2`, payments `PAY1/PAY2`, claims `CL1…CL8`, `RET1`, `DEL2`, `DUP1`, `CB1` | Same logical IDs behind disjoint kind-specific storage namespaces | Same logical IDs in separate versioned reference records |
| Management orders `ORDR1…ORDR5`, `ORDR1b` | Logical ID in authenticated stored-order content; actual envelope/message IDs remain distinct | Separate trusted order records under the logical ID |
| Joint issuer `[C,F]` | One logical order supported by both authenticated issuer envelopes; conflict set includes both | Two independently supplied authenticated senders for one logical order |
| Refund aliases `REF1`, `REF2` | First refund of ORD1/ORD2 respectively; later refunds have transaction-specific IDs; projection retains claim and transaction binding | Same deterministic alias relation from actual order/transaction identity; never selected from an expectation |
| `D_resolve(CLx)` | Resolve-duty identity bound to claim CLx | Corresponding independently derived resolve duty |
| `D_refund(CLx,n)` | Refund-duty identity bound to CLx and `n * 100` minor units | Same bound claim/amount semantics, with separate reference derivation |
| `D_report(ORDRx)` | Report alias bound to ordered act/matter; Q9 controls cross-order matter deduplication | Same observable report alias; no expected names create duties |
| Rules `PR1`, `PR2`, `SU1`–`SU3`, `DT1`, `DT2`, `AU1`, `DU1`–`DU4` | Preserve rule IDs in check/provenance events; compiled core predicates | Separately declared/evaluated policy; no imported core predicates |
| `PERMIT`, `ALTERNATIVE`, `HOLD`, `REFER`, `PROHIBIT` | Same disposition strings; ALTERNATIVE never carries execution authority | Same observable decisions independently computed |
| Proposed `REFUSE` (Q1) | Not added to the contract before the spec note | Pending assertion stays skipped; never equated silently with another result |
| Registered tool names | Preserve W0 names exactly | Input-only renaming may bridge older reference field names; no decisions in that adapter |
| Money `120`, `250`, `USD` | Integer minor units (`12000`, `25000`) and explicit currency | Same dimensional conversion; output assertions convert exactly, without rounding |
| `T1`, `T2`, `T3`, `next` | Actual issuance sequence; `next` selects the most recently issued/returned live token | Separate actual reference issuance sequence; no token invented to satisfy a label |
| `R+`, `R=` | Compare actual relevant-state revisions around the indicated phase | Compare reference revisions; assertions are not derived from the other backend |
| `REF1@v2` and similar | Logical record plus authoritative version | Same record/version binding; retained history is observed separately from current state |

## Ingestion choices requiring review

[DESCRIPTIVE] Standard YAML parsing splits the unquoted identifier
`D_refund(CL1,120)` in a flow map/list at its comma. The loader quotes only an
unquoted `D_refund(...)` token **in memory**, preserving every supplied byte on
disk and all numeric/outcome values. It leaves comments and quoted text intact.
This source-format discrepancy is recorded separately; this is not an outcome
repair or a silently modified fixture.

[INTERPRETATION] `INPUT_PLAN_v01.json` makes variant input selection explicit:
T05a/b append their acceptance/no-acceptance steps to T05; T24b and T34b replace
the base steps/setup; T36a/b/c replace the empty container's steps and inherit
its setup. In particular, T24b must not inherit T24's grant expiry at step 5
while testing token expiry at 6. No expected values are changed by this plan.
Claude's review is needed because the README does not specify inheritance.

[DESCRIPTIVE] Pending markers are found in scalar values and source comments
(notably Q3 and Q5). The eventual checker skips only the marked assertion, not
the trace or its unmarked siblings. It retains all pending assertions and their
paths, so a versioned Q1–Q9 note can enable them without restructuring cases.
No note is presumed from proposed answers in the bundle's README.

[OPEN QUESTION] Default token lifetime is not given in W0. Ordinary cross-step
execution in the supplied traces requires it to exceed one step; the assigned
default is grant-bounded lifetime, with an explicit shorter lifetime only where
the setup requests one. Clock progression itself is protocol time; truth-changing
expiry/deadline/event boundaries invalidate permission. This differs from the
first abstract reference model's every-tick invalidation and must be logged as
a discrepancy before correcting either implementation. Q7 remains separately
pending for token-only expiry's revision effect.

## Discrepancies and review gate

[DESCRIPTIVE] Disagreements are append-only records with source zip hash, trace
ID, expectation path/value, observed value, backend/commit and status. Source
format/input ambiguities are distinguished from implementation failures. A
known discrepancy is not a passing assertion. No expected output is copied
from either implementation; both receive the same source-authored assertions.

[OPEN QUESTION] Receipt of the expected traces is not Claude's review of PRs
#11–#13, this mapping or later core PRs. Every PR still requires passing CI and
Claude's review before merge. Astra's v0.3 confirmation, relayed by Chris, now
authorizes the remaining $0 core work; no paid calls or live experiments follow
from it.
