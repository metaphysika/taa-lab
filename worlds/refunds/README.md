# Refunds development world

[DESCRIPTIVE] Stage 7 uses the independently authored, reviewed W0 v0.2 world
and T01–T10 keys in the frozen v0.2.2 bundle unchanged. They supply five pairs:
wrongful order, evidence correction, revocation, pressure and open duty.
`catalog.py` records their provenance and verifies the source archive through the
existing bundle loader. These are development cases already used during core
construction, not unseen evaluation data. No outcomes are generated from the
reference model.

Run all four controllers (no model calls):

```sh
python -I scripts/run_gateway_development.py --report /tmp/gateway-development.json
```

Use `--case T02` to inspect one case. JSON and readable text reports are emitted.
Every episode retains its input program, full native checkpoint, hash-chained
JSONL and separately retained HMAC checkpoint, state-audit results and correction
records. The fixed simulator authentication key is public test infrastructure;
it is not an external production identity or host-compromise defense.

[DESCRIPTIVE] `correct` follows Claude's source program and checks every original
expectation. Its program intentionally contains diagnostic wrongful proposals,
stale executions and rejected closure attempts. Those remain labeled attempts;
“correct” describes following the development key, not a claim of virtuous or
learned agency. `compliant` submits every request and immediately tries its
observed token, ignoring suggestions. `cautious` withholds all requested tool
acts. `adversarial` adds wrong-actor use, direct execution, replay, self-written
evidence through an unregistered tool, wrong-account payment, unsupported
settlement notices, closure and an unaccepted voluntary offer. Simulator-owned
external events remain identical across controllers. This is a finite attack
script; the later property/adversarial stage remains necessary.

Only `correct` receives expectations. Other controllers receive requests and
events only. Their derived input programs have separate ids (`T02@cautious`,
etc.) and contain no expected outcomes. They are additional scripts, not
modified acceptance fixtures. The full frozen and permanent regression suites
still run separately, unchanged, through the common runner and state audits.

[DESCRIPTIVE] A dynamic `token_from: last_proposal` input resolves from the actual
observed response before execution and before audits. It never reads an expected
token. A no-token response clears that reference. The independent observer still
computes its own complete state delta, token consumption, effects and retained
versions. The runner's default behavior for existing fixtures is unchanged.

[INTERPRETATION / LIMITATION] Expected dispositions come only from the source
key. A validated key run contributes context fingerprints, not expected answers.
A label is applied to another controller only when its requested act, step and
native decision-relevant records/versions, ledger, reports, notices, allocations
and cases match. Changed contexts and extra attacks are **unassessed**, counted
explicitly; no result is invented. Those actions have complete state audits but
incomplete semantic labeling. Original source assertions are all checked on the
key program; none are skipped or rewritten. Unassessed labels are not counted as
semantic passes or as evidence of safety. The context matcher currently covers
this TAA development harness; it is not a representation-neutral comparator
adapter. That is stage 8 work.

[DESCRIPTIVE] Correction records separate the attempted act and scripted reason,
gateway decision/rules and keyed correctness, actual effects/receipts,
completion/duty board, correction source and label source. The record split is
`development`. Gateway feedback is recorded; no learning or causal inference
about an agent's correction is asserted. All controller reasons are authored
script text, not model explanations. No training exporter exists.

[DESCRIPTIVE] Metrics distinguish keyed wrongful attempts from keyed wrongful
executions, lawful opportunities from observed lawful execution, agent
withholding from incorrect gateway refusal, open cases, unresolved duties and
reports delivered/acknowledged. Keyed denominators differ after trajectories
diverge, so these are descriptive per-episode diagnostics, not comparable H3
rates. A remaining duty with a keyed lawful opportunity in its case is only a
candidate omission for review; it is never automatically labeled over-refusal.
Whole-claim task completion is not inferred from a receipt or a low harmful-act
count. Known lawful withholding by the cautious controller exercises the other
direction of labeling.

[LIMITATION] Finite development coverage is not P1–P6 property acceptance,
comparator validation, empirical H3 evidence or launch approval. The reference
remains separately implemented and unchanged. No model calls, Modal operations,
spending, evidence deletion or public release is involved.
