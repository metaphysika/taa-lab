# Independent conventional comparator: SQL kernel review

1. [DESCRIPTIVE] This is an independent relational storage/transaction component, not the completed comparator.
2. [DESCRIPTIVE] Its representation and exact matching protocol were committed at `4338a7c8` before its first component outcome run.
3. [DESCRIPTIVE] Twenty-one component tests pass; six deliberate mutations are detected by assertion failures, with no import/runtime-error substitutes.
4. [LIMITATION] W0 policy, persistent duty/report semantics, and the common-runner adapter remain unimplemented for this arm.
5. [INTERPRETATION] Matching correct behavior will count as success for both strongest arms; these results do not test H3.

## What is implemented

[DESCRIPTIVE] `conventional_gateway/kernel.py` uses only the Python standard
library. It imports neither existing gateway implementation. Current state is
queried from append-only SQL version relations; no TAA warrant, justification
or computed support-set representation is stored. SQLite triggers reject UPDATE
and DELETE of historical records, duties, handles and audit rows.

[DESCRIPTIVE] The host issues opaque sessions; authenticated envelopes bind the
sender, channel, recipient, step, message identity and payload. Source-write
rights distinguish create from field-level correction. The configured trust
boundary sets evidential status. An agent note cannot become evidence by
supplying an evidential flag. Accepted message identities prevent replay.

[DESCRIPTIVE] Action handles bind the authenticated actor, exact JSON arguments,
epoch, expiry and staged-effect digest. Issuance and audit-only writes do not
advance the epoch. A relevant batch advances it once and voids every remaining
live handle. Plain ticks do not; live-handle expiry does. An execution checks its
handle and current host-configured policy within `BEGIN IMMEDIATE`, stages real
SQL rows, writes effects, consumes the handle, runs the configured duty-update
callback, writes a receipt with the pre-transaction epoch, and advances once.
The callbacks are trusted host configuration, never agent inputs. They are not
the outstanding W0 implementation.

[DESCRIPTIVE] Fault injection interrupts actual SQL work at all seven published
transaction boundaries. Partial rows are captured before SQL rollback; rejected
attempt diagnostics are logged afterward. A failed attempt leaves the domain
snapshot unchanged and the original handle can be retried. The snapshot includes
all historical versions, accepted-message identities and staged rows, not just
current business records. Audit events form a hash chain. Authenticated complete
checkpoints bind its count, contents and state; restoration verifies both the
authentication and chain. Every appended relation version logs its complete
payload. A component test reconstructs the record, handle, duty and receipt
histories from those events and compares them with actual SQL state. The full
episode renderer remains a later stage. Checkpoint authentication is host protection, not a
claim of security against a compromised host.

## Tests and sensitivity

[DESCRIPTIVE] `tests/test_conventional_kernel.py` has 21 tests. They cover source
identity and field rights, replay, historical immutability, checkpoint tampering
and truncation, detached policy snapshots, epoch changes, expiry boundaries,
actor/argument binding, current-policy rechecks, staged-effect drift, atomic
receipt/duty/effect changes, all seven actual rollback boundaries, successful
retry, and absence of imports from either gateway implementation.

[DESCRIPTIVE] `scripts/check_conventional_kernel.py` creates isolated copies;
it does not modify the working source. Removing actor binding, exact argument
binding, epoch comparison, expiry-boundary handling, SQL rollback, or correction
field restrictions causes the designated test to fail by assertion. Baseline:
21 tests, zero failures/errors/skips. All six mutants are detected, with no
errors/skips accepted as detections. Working-source hashes are unchanged during
the campaign. Compact evidence is in `evidence/conventional-kernel/validation.json`.

[DESCRIPTIVE] Initial mutation attempts are retained in the local evidence
directory; its initial error and failed-gate JSON are also preserved alongside
the committed compact evidence. One run stopped on a non-unique expiry mutation anchor. The next run
correctly failed its gate: a missing reason caused a test error, and the rollback
control exposed omitted staged rows in the snapshot. The snapshot and assertions
were strengthened; no frozen outcome was edited. Only the final clean campaign
is acceptance evidence. This is test development, not blinded verification.

[DESCRIPTIVE] Python 3.11.17 repository discovery completed with **938 tests,
36 skips, zero failures/errors** in 1,474.016 seconds. All historical scripted
scenarios passed. Collection began before the final SQL snapshot/guard/logging
hardening; all 21 current component tests and six mutants were rerun separately
with the pinned final sources. Existing native gateway/reference code was
unchanged. An execution transport reset detached the original session; its
completed OK summary and process termination were observed, but the native
exit status was not recovered. `broad_checks.json` records that distinction and
log hashes. CI repeats discovery against the actual PR head. Frozen bundle
zip, extracted bytes and manifest still verify unchanged.

## Incomplete coverage and next work

[LIMITATION] No W0 comparison episode has run through this component. The policy
callback in the tests is a deliberately small test policy. It does not supply
W0 authority, support, prohibitions, caps, reservations or closure. The sample
duty-update callback tests transaction membership, not DU1–DU6. Grant ancestry
and expiries, report routing, corrections/reopening and simultaneous transfers
still need their independent domain layers and tests.

[LIMITATION] Common-runner coverage is therefore **not run / incomplete**:
54 frozen scenarios, 32 permanent regression scenarios (including the three
hidden-state controls), and three additional adversarial controls. No zero
discrepancy or state-audit count is claimed for this arm. The permanent regression
format contains 242 source blocks before negative-control wrapping; acceptance
runs report ordinary source assertions and mutation-detection guards separately.
Future acceptance must preserve that distinction and run the same observer.

[LIMITATION] This component has one host-owned in-memory SQL connection per
world. No multi-worker throughput, durable crash recovery, external service,
live-agent or unfamiliar-domain result is claimed. Configured callbacks are
trusted code; the agent-facing interface has not been built.

[PROTOCOL] Claude review and green CI are required before merge. This component
does not clear the full-comparator gate. Q14–Q16 remain drafts. No model calls,
Modal operations, spending, Notion edits, evidence removal or public release.
