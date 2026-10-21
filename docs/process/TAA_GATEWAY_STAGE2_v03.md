# Gateway v0.3 stage 2 — schemas and trusted state foundation

1. [DESCRIPTIVE] Implements the authorized storage, identity, order-provenance and logging foundation, not the authorization pipeline.
2. [DESCRIPTIVE] Every accepted state batch uses one publication path and advances one global revision; records remain versioned and copy-isolated.
3. [DESCRIPTIVE] Fixed writer identities, tools, kinds and namespaces determine evidential status; agent assertions cannot become evidence.
4. [DESCRIPTIVE] Simulator-authenticated orders remain associated independently of a proposal's claimed actor or order reference.
5. [OPEN QUESTION] CI and Claude's review are required before merge; production stages 4 onward and independent expected traces remain gated separately.

## Source and scope

[DESCRIPTIVE] Uses *TAA Gateway Core Design v0.3.docx*, SHA-256
`795a08c33b86bdceae6a0da62812b74333cac7195a83946bd3242b23ae106712`.
The [inventory](TAA_GATEWAY_CODE_INVENTORY_v0.md) precedes this implementation.
All code is offline, with no model calls, Modal operations or Notion edits.
Historical research code and evidence are untouched.

## What is implemented

- [DESCRIPTIVE] [`objects.json`](../../taa_gateway/schema/objects.json) publishes
  Draft 2020-12 definitions for the v0.3 objects, plus justification/query,
  duty-evidence reference, event/checkpoint and writer-policy structures.
  Runtime validation uses the pinned `jsonschema` dependency; schema resolution
  is local. Wire JSON rejects non-finite numbers, non-string keys and duplicate
  parsed keys. Amounts use integer minor units; currency/binding semantics belong
  to the later duty/transaction stages.
- [DESCRIPTIVE] [`RecordStore.publish`](../../taa_gateway/records.py) is the one
  state/revision mutation path. It stages validation and append-only record
  versions, then publishes a complete batch with one revision increment. Its
  snapshots/read results and configured policy are copied. Clock transitions
  use the same path. All state mutations are conservatively relevant; logging,
  reads and envelope minting are not world-state mutations.
- [DESCRIPTIVE] The world definition supplies fixed kind/tool/channel/principal
  write permissions and disjoint record-ID prefixes. Prefixes prevent an agent
  assertion from preempting a future trusted order/evidence identity. The store
  assigns `written_by` and `evidential`; callers cannot set either on a `Write`.
  Typed metadata records additionally validate their published object schema.
- [DESCRIPTIVE] [`SimulatorAuthority`](../../taa_gateway/envelopes.py) binds
  opaque session identity and authenticates message content with a simulator-held
  HMAC key. [`StoredOrders`](../../taa_gateway/orders.py) verifies and stores an
  order's authenticated sender, recipient and scope. Related orders are found
  from trusted storage using actor/tool/argument scope, including when the
  proposal omits or substitutes its reference. The raw proposal is retained,
  while its acting party comes from the authenticated session.
- [DESCRIPTIVE] [`StoredResolutions`](../../taa_gateway/resolutions.py) writes
  an authenticated answer as a versioned record. It does not decide jurisdiction,
  settle an aggregate disposition or issue permission; those are stage 4 work.
- [DESCRIPTIVE] [`EventLog`](../../taa_gateway/eventlog.py) emits canonical
  JSONL with sequence, previous hash and event hash. The final count/head is
  HMAC-authenticated. Verification requires the separately retained checkpoint,
  so a valid shorter chain cannot substitute for the expected ending.

## Review boundaries and deliberate limits

[DESCRIPTIVE] The trusted simulator owns the authority, session-minting API,
writer policy and keys. Agents receive only their bound session and permitted
interfaces. This is simulated authentication, not a claim of process isolation,
network identity verification or protection against host/code compromise.
HMAC is a symmetric authenticator, not a publicly verifiable digital signature;
sharing an audit artifact requires a separately trusted ending/verifier. Keys
are never serialized into logs or records. Determinism assumes fixed supplied
keys, initial state, event sequence and identifiers.

[DESCRIPTIVE] Generic state publication validates the whole batch before changing
the store and appends its record events together. It executes no tool effect,
consumes no token and runs no duty decision. It must not be represented as the
stage 5 validate/stage/effect/consume/duty/receipt transaction. The simulator is
single-driver; real adapters, concurrent external commits and crash durability
need later contracts. Store snapshots include historical facts, not a claim that
every historical version remains current authorizing evidence.

[OPEN QUESTION] Claude should review the schema/API choices above, especially
the explicit symmetric checkpoint authenticator, fixed ID namespaces, and the
boundary between storage and later authorization. Schema acceptance alone does
not prove valid grants, truthful source content, correct discharge or P1–P6.
Neither this stage nor its tests establish comparative effectiveness or H3.

## Validation

```text
python -m pip install -r requirements-gateway.txt
PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_gateway_foundation -v
```

[DESCRIPTIVE] 25 targeted boundary tests pass. They exercise forged sessions and
altered envelopes; assertion/evidence and ID-namespace separation; order omission,
substitution, replay and actor spoofing; immutable returned values; versioned
insertions/clock changes; failed-batch publication; raw resolution storage;
canonical log edits/reordering/truncation, wrong keys and checkpoint replacement.
These are component regressions, not independently authored expected trajectories
or a claim that the held execution pipeline has been tested.
