[DESCRIPTIVE] PR #16 merged as `2bbcd348` after Claude's approval and all CI passed; its state-delta comparison guard is unchanged.
[DESCRIPTIVE] Stage 4 adds the five-stage evaluator with explicit three-valued results and the v0.3.1 disposition order.
[DESCRIPTIVE] Evidence reads retain actual record versions and negative queries; each candidate uses one complete grant path, purpose and scope.
[DESCRIPTIVE] Stage 4 returns decisions only: no executable token, protected effect, automatic duty transition or report dispatch is implemented here.
[DESCRIPTIVE] This separate PR requires Claude review and green CI; full production trace acceptance remains incomplete until the later stages exist.

# Stage 4 review record

[DESCRIPTIVE] Controlling sources are Design v0.3 and the unchanged frozen bundle's Clarifications v0.3.1, including Q10's inactive-boundary rule. Base is the PR #16 merge, `2bbcd348096d158f29afe5edeac62ed5466ab094`. Chris's relayed Claude approval covers PR #16, not this new implementation. No expected outcome was generated from the reference model or changed. The two v0.3.2 questions in [the alignment document](TAA_GATEWAY_ALIGNMENT_v031.md) remain open; this stage makes no new DU1-portion or report-redirection decision.

## Implementation and API

| Location | Behavior |
|---|---|
| `taa_gateway/act.py`: `Tool`, `ToolRegistry` | Trusted, fixed tool registration, local-only argument schemas, effect descriptions from arguments/records, and resource projections. Reject unregistered tools before evaluation. Raw proposal claims are not supplied to descriptors or predicates. |
| `taa_gateway/rules.py`: `Outcome`, `Rule`, `evaluate_rule` | Explicit satisfied/violated/unknown results. Prohibition failure is PROHIBIT; known other failure is REFUSE; unknown is HOLD or REFER for an explicitly reserved question. Callbacks are trusted simulator code, not model/reviewer inputs. |
| `taa_gateway/rules.py`: `EvidenceView` | Private snapshot reads restricted to declared record kinds. Non-evidential records are never returned as evidence. Queries retain every matched version and empty results, with defensive copies. |
| `taa_gateway/grants.py`: `GrantPolicy` | Read-only complete-path checks: acting party, action, roster standing, scope, purpose, live conditions, expiry, and one level of delegation. Root/parent failure cannot be repaired by another grant. Roster standing comes from versioned party records and a fixed jurisdiction-to-actions policy. |
| `taa_gateway/pipeline.py`: `Pipeline.evaluate` | Authenticated proposal normalization via `StoredOrders`; description; prohibition, authority, support, determination, duty, in that order; strict aggregation. Identical actor/act/revision returns a recorded decision. A revision race aborts publication. |

[DESCRIPTIVE] The result includes the computed act/hash, state revision, actor, exact arguments, rule results, stage aggregates, complete justification where available, associated stored orders and report candidates. Every decision logs the verbatim raw proposal. PERMIT is explicitly `executable: false`, `token: null`: callers cannot use a stage 4 result as an execution capability. Returning `report_candidates` is not report delivery and does not satisfy P5.

[DESCRIPTIVE] Prohibition callbacks receive only computed effects, arguments and resource projections; grant, purpose, stored-order records and issuer context are excluded. All applicable stages are assessed even after a failure. Within a selected path the aggregate can only tighten: PROHIBIT > REFUSE > REFER > HOLD > ALTERNATIVE > PERMIT. Distinct grant paths are assessed separately; the least restrictive **complete** path may be selected, but checks or evidence from different paths are never combined.

[DESCRIPTIVE] ALTERNATIVE requires a concrete registered act that passes a separate complete assessment using the same grant, with alternative recursion disabled. Every original failure must be a known support/determination failure; authority, duty, prohibition or unknown failures cannot be hidden by a suggestion. Only then do those failed rules carry ALTERNATIVE in the original path's ordered aggregation. Refund amounts must remain positive. No alternative executes; it must be resubmitted. The built-in per-refund cap applies at evaluation. Unknown limit forms fail closed; cumulative accounting and the transaction-time recheck belong to stage 5.

[DESCRIPTIVE] Rule support sets come from actual reads, including reads showing a prohibition inapplicable. `@kind:<kind>` is a reserved synthetic query identity, not an evidential record: its query value contains the full ordered matching version set, including non-evidential matches excluded from predicate results. An empty set is retained explicitly. Concrete lookups retain actual version/content or absence. Rule facts fit the existing justification schema; this is conservative full-kind tracking, not selective invalidation. Record IDs beginning with `@` are rejected by the evaluator. Stage 5 still must invalidate globally on relevant insertions or changes.

[DESCRIPTIVE] Tool and rule configuration is fixed for the lifetime of an evaluator; mutable input dictionaries and returned values are copied. Callbacks are trusted Python policy code and are not sandboxed. The agent receives only its session/proposal interface, never the simulator store, authority, callbacks or authentication key. Runtime policy/tool changes need the later single revisioned write path; changing a Python closure or the host itself is outside this interface's threat boundary.

## Mapping supplement for Claude review

[DESCRIPTIVE] The [W0 mapping](TAA_EXPECTED_TRACE_MAPPING_v022.md) still applies to the reference. Stage 4 supplies generic mechanisms, not the W0 importer or complete W0 policy. The development component tests use their own IDs and Sol-authored expectations, not new independent acceptance fixtures.

| W0 concept | Stage 4 contract / remaining binding |
|---|---|
| Registered tools, AU1, export_records | `Tool.name`, `authorization_rule`, `referral`; W0 importer must preserve literal tool/rule IDs. Export with no authorization rule refers; an unregistered name raises. |
| PR1/PR2, SU1–SU3, DT1/DT2, DU constraints | Trusted `Rule` callbacks plus built-in grant cap. Full W0 rule bodies and literal ID binding remain for the refunds-world adapter; development callbacks are not claimed as W0 conformance. |
| G0/G1/P1, parties and jurisdictions | Existing grant/purpose/party schemas; `GrantPolicy` binds actual versions, roster jurisdiction standing, live chain and scope. Fixed standing policy maps jurisdictions to actions, not authenticated users directly to permission. |
| Stored orders / T39 attribution | Existing authenticated `StoredOrders`. Association by requested tool/arguments; a prohibited assertion is attributed only if requested in `asserts`; a prohibited argument only if requested explicitly. Agent additions do not name the issuer. Reporting/routing is deferred to stage 6. |
| Duty closure / DU1 | Stage 4 duty predicates read ledger records. The component closure predicate refuses any unresolved duty regardless of overdue status. Creation, discharge, allocations, reopening and transfer are not implemented by the pipeline. |
| Tokens, receipts, faults, state audits | No token or transaction adapter yet. The production adapter must expose full actual state to the unchanged runner/observer, not construct observations from decision descriptions. |

## Verification and incomplete coverage

[DESCRIPTIVE] Local offline verification: **135 component tests pass**, comprising 90 existing foundation/reference/runner tests and 45 new pipeline tests. New controls cover the disposition lattice and ordered stages; unknown/violated support; fresh reads after corrections; unchanged prohibitions; authenticated actors and ignored claims; no grant-fragment composition; roster corrections; delegation/expiry/revocation; reserved questions; closure with unresolved non-overdue duties; order omission/forgery and attribution; all-condition alternative checks; zero/malformed alternatives; non-evidential evidence; snapshot/caller mutation; undeclared reads; remote-schema rejection; and revision races. Core/reference imports remain separated. These are engineering component tests, not P1–P6 property acceptance or empirical H3 evidence.

| Suite / backend | Scenarios | Source assertions | Additional checks | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|
| Frozen v0.2.2 / reference | 54 | 534 | 1,704 state audits | 0 | 0 |
| Regressions / reference | 8 | 57 | 205 state audits + 3 hidden-state guards | 0 | 0 |
| Frozen + regressions / production | 62 pending | 591 unexecuted | State audits and real-state fault controls not run | Not assessed | 591 source assertions unverified: no production backend yet |

[DESCRIPTIVE] Source validation still reports 49 traces/variants, zero errors; all manifest entries verify. The frozen zip/hash, bundle, regression expectations, reference implementation, common runner and independent state observer have no changes from merged main. No assertion is skipped and counted as passing. Reference counts do **not** stand in for the incomplete production row. CI adds the new component module while retaining the existing reference, regression and pre-fix guards.

[DESCRIPTIVE] Full production acceptance must run both source suites through the **same** runner and independent state audits, including the runner-computed delta comparison. Its out-of-band fault adapter must mutate real production state; each T23 fault must be injected at its actual transaction boundary and show rollback, not the ideal early-abort reference abstraction. Every skipped/unimplemented source assertion remains incomplete and blocks full gateway acceptance. No trace expectation may be generated from the reference or changed to fit either implementation.

[DESCRIPTIVE] No model calls, Modal operations, spending, deletions, Notion edits or public releases. No empirical results or launch approval are produced. Stage 5 onward and this PR's merge remain subject to the build plan's stage review gates.
