# Offline MCP front v0.1

[IMPLEMENTATION] Thin JSON-RPC stdio adapter, pinned to MCP protocol 2025-06-18.
[IDENTITY] A trusted host supplies an existing authenticated SimulatorAuthority.Session; wire claims never select an actor.
[PATHS] Registered tools propose; explicit execution/withdrawal use the unchanged runtime and decision/event log.
[VALIDATION] Scripted client, frozen traces, permanent regressions and common state audits; no live model client.
[LIMIT] Local simulator session binding, not remote authentication, deployment or launch approval.

## Interface

Start locally with a trusted host-selected actor and world:

```sh
python -m taa_gateway.mcp_server \
  --world tests/expected_traces/v0.2.2/world_W0.yaml --actor A \
  --log /tmp/new-episode.jsonl --checkpoint /tmp/new-checkpoint.json
```

Both output files must be new and distinct. `--setup` optionally supplies a
trusted host JSON setup. It is not a wire operation. The CLI creates an ephemeral
simulator authentication key, retains it only in process memory and never sends
it to the client or writes it to the log. For an embedding with an existing
world, construct `Server(runtime, authenticated_session, tools, event_log)`;
it uses that world's existing authority and key setup unchanged.

The client initializes with `protocolVersion: "2025-06-18"`, empty capabilities
and clientInfo, then sends `notifications/initialized`. Supported methods are
initialize, ping, tools/list, tools/call, resources/list and resources/read.
Requests and responses are one finite JSON object per UTF-8 line. Duplicate
keys, non-finite JSON, batches, oversized frames and invalid request shapes are
rejected. An oversized frame closes the connection without executing its tail.
Unsupported protocol versions fail explicitly. No sampling, model endpoint,
HTTP listener, OAuth flow, subscriptions or remote authentication is installed.

Every registered business tool is listed with its existing argument schema.
Calling it is a proposal only: its arguments pass unchanged to Runtime.propose.
Optional `_meta` fields order_reference, claimed_purpose, claimed_grant and
claimed_reasons pass through the existing proposal path. They confer no
authority. `taa_propose` accepts the full raw core proposal for clients needing
that representation. The core assigns acting_party from the bound Session,
including when a raw proposal claims a different actor.

`taa_execute` accepts token_id and optional exact tool/arguments and calls the
existing atomic Runtime.execute. It does not mint permission or select another
party. `taa_withdraw` calls the existing runtime withdrawal method. Business
refusals are normal gateway results; unregistered/schema-invalid tool requests
carry the core rejection in structuredContent with isError. Text content is the
canonical encoding of the same structured result.

There is no wire method for a host event, reviewer envelope, clock tick, roster
change, grant amendment, direct record write, fault injection or restore. In
frozen acceptance, the trusted host supplies those inputs through the existing
production host adapter. Faults stay out of band and exercise the runtime's
actual transaction boundaries. Unknown business tool names still reach the
core rejection/audit path; transport errors are log-only with no revision change.

## Decision log and authenticity

`taa://session/decision-log` is a read-only resource containing existing core
event rows produced during this session's own call intervals. It does not
synthesize checks, retain a parallel authorization state, expose seeding events
or claim to be a complete independently authenticated chain. Incidental duty
and report events caused by a session's calls remain in that view. Full logs
and separately retained ending checkpoints are host exports at stdio EOF.

The identity boundary is the existing simulator authority's object-identity
Session binding, selected by the trusted process owner. An untrusted client
cannot bind a new Session. The CLI's ephemeral-key setup is for offline tests,
not a claim of production authentication, durable restart or host security.
No live model client is connected, and this PR does not approve one.

## Offline acceptance

```sh
python -m unittest tests.test_gateway_mcp -v
python -I scripts/check_gateway_mcp.py --report /tmp/new-mcp-acceptance.json
```

The scripted client round-trips actual MCP JSON through Server.serve's line
framer. The common runner supplies frozen expectations and independently
audits full actual before/after state, including token effects, retained
versions and transaction rollback. Its state-delta comparison guard stays on.
The established three hidden-state negative controls remain acceptance.
The adapter imports the production host normalization, never the reference
model or frozen answer keys as decision logic. Expected outcomes are unchanged.

A separate subprocess test exercises a real stdin/stdout pipe: initialize,
list tools, propose a permitted refund, execute the dynamically returned token,
close stdin, and verify the retained log/checkpoint. It does not hard-code the
gateway token or call a model. Component tests also cover forged Session
objects, claimed actors, cross-actor token use, replay, withdrawal, exact-argument
mismatch, schema failures, inaccessible host methods and framing errors.


## Integration with comparison v0.2

This branch integrates the preserved MCP checkpoint with comparison-fix publication head `74c5b0a0`. Frozen expectations, production decisions, actor binding and the common state-delta audits are unchanged. The scripted acceptance also runs the two separate comparison-review traces (parent customer scope and C→F→C acknowledgment) through the MCP transport. The TraceGrant injected-drift probe stays in its comparator tests; no new contract or outcome is authored.

Registered tool results remain the core's existing results. W0's read_record currently has an abstract empty effect; this transport adds no separate evidence-export API. Live-client task-context delivery is outside this offline front. No remote authentication, deployment, model connection or launch is implied.

## Completed acceptance on the comparison-fix base

Full repository discovery passes **1,121 tests** (36 optional skips), and scripted scenarios pass. Seven component methods pass. The real subprocess test follows the dynamically returned token across stdin/stdout and retains a native log/checkpoint; it makes no model call.

| Suite | Scenarios | Source assertions | State audits | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|
| frozen-v022 | 54 | 534 | 1751 | 0 | 0 |
| permanent-regressions | 32 | 218 | 671 | 0 | 0 |
| h1 | 5 | 26 | 64 | 0 | 0 |
| q14_null_allocation | 3 | 9 | 34 | 0 | 0 |
| q14 | 18 | 102 | 548 | 0 | 0 |
| q14_overlap | 1 | 15 | 86 | 0 | 0 |
| q15 | 9 | 32 | 211 | 0 | 0 |
| q16 | 16 | 119 | 510 | 0 | 0 |
| comparison_review_v02 | 2 | 7 | 32 | 0 | 0 |

**Total: 140 scenarios, 1,062 source assertions, 3,907 state audits and 4,972 checks, including all three detected hidden-state controls; 0 discrepancies and 0 incomplete items.** These are engineering checks, not model trials or H3 validation.

[Validation and source hashes](evidence/gateway-mcp-v01/validation.json) and acceptance.zip retain the full checks and negative-control observations. Frozen fixtures, all v0/v0.1 scoring records and the runtime’s decision/transaction/duty code remain unchanged. Claude review and green CI are required before merge. No launch, model connection, spending or public release is approved.
