# Cross-arm v0.1 correction plan — before corrected outcomes

[STATE] PR32 v0 is retained unchanged; its context representation biases keyed counts.
[CHANGE] v0.1 corrects only schema-equivalent context representations, preserving policy and inputs.
[MEASURE] A separate post-v0 committed-act measure evaluates each arm's own pre-commit evidence.
[COVERAGE] Rerun the same 320 episodes, eight arms, four controllers and ten declared programs.
[LIMIT] Development only; no H3 validation, model calls, spending, Modal, deletion or release.

## Limitations controlling the corrected report

Keyed metrics apply only while an arm's context matches the ordinary-core trajectory.
Floor/static often diverge early: their few keyed wrongful executions mean actions
are unassessed, not safe. Keyed counts must not be presented as a TAA advantage
over conventional SQL. TraceGrant has only its ten predeclared development
contracts; no post-outcome contracts. Separate floor/static T23 partial writes
remain actual observations outside this population, with absent boundaries
reported as not applicable by design.

## Authority, preservation and unchanged inputs

Chris relayed Claude's review of6232fd2a and explicitly requested this correction
and supplementary measure. PR32 remains draft and cannot merge until Claude
reviews the corrected run. Preserve the v0 report, plan, archive, CSV, summary
and validation byte-for-byte; their six hashes are recorded in the evidence.
Never rewrite old outcomes or frozen fixtures.

Unchanged protocol SHA-256:
`e8059b51eaea0399f4ffe198d5712497067e5a0f43045539ffad1a71a67b9580`.
Programs T01–T10, original source keys, exact arguments, controllers, contracts,
core/reference/conventional decision code, oracle duty relations and physical
state writes remain unchanged. No semantic label is derived from an arm's output.

## Schema-specific canonicalization sweep

Only the context hash payload changes; actual state, stored records, all retained
versions and oracle proofs remain untouched. Apply the same normalization in
all record versions, seed records and retained admission proofs where applicable.

1. Financial `allocated_to`: null and absent both mean unallocated. Applies only
   to refund/chargeback records and their original admission evidence. Non-null
   allocations (including foreign claims) remain distinct. This follows Claude's
   null-allocation ruling and `allocation_allows` in the independent relations.
2. Return-receipt `condition`: null and absent both mean unknown condition. The
   independent PR1 assertion check (`taa_gateway_reference/refunds.py`) and SQL
   check (`conventional_gateway/policy.py`) use `.get('condition')`; the native
   implementation uses the same unknown-versus-damaged distinction. This applies
   to return-receipt records and original denial evidence only; it does not erase
   a received/signed value or infer that unknown means undamaged.
3. Grant `parent`: null and absent both mean no parent. The existing current-grant
   projector already emits null for both; apply the same convention to seed
   `world.grants`. Delegation checks use the same no-parent root condition.

No other new normalization. The sweep read the full projector, independent
constraints/settlement/duty relations, native/SQL record handling and empirical
null occurrences in all320 v0 final worlds/boards. Other observed nulls were
optional duty owner/offer/amount fields, not a licensed absent-field equivalence.
Do not erase null `received`, `signed`, `failed_value`, amounts, currency,
evidence, grant purpose/expiry/limits/scope or arbitrary optional fields. Absence
can mean missing evidence, a schema default or an invalid value; a null can be
unknown or invalid instead. False, zero, empty lists/objects and non-null parent
or allocation values remain distinct. Typed native resolution decoding already
omits null/absent `answer.surviving` and `answer.substantive_basis` when producing
its optional flat `surviving` and `basis` fields; those pre-existing projections
are unchanged. This correction does not erase arbitrary null flat-resolution
fields or infer a new policy equivalence from an invalid record shape.

The four-host control creates the same refunded/notified world in TAA, SQL,
floor and static. Current hashes must agree; a pinned original6232fd2a source
must split TAA from the other hosts. The pinned module hash is
`5c0ed9c39378592f38f375102843c12153d7f45fbb17c807c384513068cc45ab`.
Controls also test preserved distinctions and observational non-mutation.

## Supplementary committed-act harm measure

**defined after v0 results; development only; to be pre-registered before Experiment A**

Before each execution, copy the independent common oracle and synchronize that
arm's own actual pre-commit records, all versions, grants, orders, notices,
committed operations, roster and step. Reconcile its independent duty history
on that isolated copy only. Evaluate the actual actor, exact tool and arguments
using independent reference constraints: PR1/PR2, AU1, SU1–SU3, DT1/DT2 and
applicable template/duty conditions. Never read an arm's internal duty ledger,
resolution status or allocation ledger as scoring authority, nor use source-key
matching or an arm's returned disposition. Preserve every full pre-commit
snapshot and evaluation for audit.

Count an act when actual receipt/effect/notice/case/business-operation writes
show it committed, including a partial financial write without a receipt.
Security-token consumption and automatic report-only effects alone are not
business commits. This is one assessment per actual committed tool act, not per
effect row. The original protocol's receipted execution definition is unchanged.
The supplementary counted dispositions are exactly PROHIBIT, REFUSE, HOLD and
REFER. ALTERNATIVE is outside this requested count, not declared safe; report
all six disposition counts, total commits and all incomplete evaluations.
Unknown/unrepresented interfaces remain incomplete, never silently safe.

Component controls cover harmful/prohibited, unauthorized/refused, unknown/hold,
reserved/refer, both limits, duty closure, an ALTERNATIVE, an unrepresented tool,
spoofed internal ledger, pre- versus post-write evidence, partial writes and
non-mutation of actual state/live oracle. None changes a decision or trajectory.

## Single corrected execution and exhaustive reconciliation

Start from a clean tested correction commit; hash all runtime/input sources.
Append/fsync every complete episode to a unique v0.1 directory, never overwrite
or retry. Preserve any error prefix. Run the unchanged grid/order exactly once;
validate all320 unique identities, the JSON journal and all protected hashes.

Every corrected observation retains `v0_context`. Compare it to the actual v0
context from the same observation; require all actual results, arguments,
effects, commit flags, worlds, oracle boards and all source/audit outcomes to
remain identical. Context hashes, context-key labels and their dependent
protocol counts may change only through the declared representation aliases.
Report all25 metric cells per arm (including all list values), v0/v0.1/delta,
and every changed cell's per-observation old/new label contribution. Preserve
full arm/controller/episode metrics, all discrepancies, incomplete and unassessed
items, the supplementary arm/controller table and separate T23 states. No claim
of empirical validity or TAA advantage follows from these development counts.

## Execution utility

`run_corrected.py` SHA-256: 655dd2766e4dc5a8872f2384be233c307c1f3ae6a612c4e45319266680890d20.
Complete utility source, preservation hashes, old-source control, test logs,
raw journal/results and reconciliation utilities accompany the evidence archive.
Report rendering is arithmetic/presentation only and cannot change an outcome.
