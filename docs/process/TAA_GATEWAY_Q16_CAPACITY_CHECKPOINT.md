Historical Q16 checkpoint record; current status: [v0.3.2 candidate](TAA_GATEWAY_V032_IMPLEMENTATION.md).

# Q16 capacity and bounded transfer — draft PR #31 checkpoint

ENGINEERING: customer-duty acceptance now requires capacity as well as standing; tool acceptance also requires AU1 authority.
ENGINEERING: core, reference and SQL independently derive capacity from actual roster facts or a complete discharge-capable grant path.
ENGINEERING: initial incapacity, bounded loss/recovery episodes and concurrent offers preserve accountability and existing windows.
COVERAGE: 16 source-derived Q16 scenarios run on all three implementations; the two superseded source files remain intact.
GATE: Q14 is now integrated and separately documented; combined acceptance and completed-PR review remain required before merge or scoring.

## Implementations and scope

Source: unchanged approved Clarifications v0.3.2 revision3.1, Q16, with Q11/Q12
and H1. Q16 supplies no permission through institutional standing or IR1.
Missing evidence does not remove capacity. A direct path must have valid
ancestry, live purpose, scope and sufficient limits, with both notice templates
on one path for D_resolve. No composed grant fragments or IR1 capacity.

- Core `DutyEngine.capacity_from_view` uses the core's own grant-path checks.
  DU4's read view records capacity facts in its support set. Post-authority rule
  context supplies the actual step; prohibited-stage inputs remain independent
  of actor/grant. `ownership` independently handles reconciliation. The clock
  expires offers, while phase2 decides ownership after phase1 capacity changes;
  restoration at the expiry step therefore prevents premature unownership.
- Reference `capacity`/`discharge_path` and its duty relation are independently
  encoded over facts, grants and recorded windows. No core authorization,
  decision, discharge or transaction code is imported.
- SQL `Policy.capacity`/`grant_live` and `Ledger._customer_duty` use the SQL
  snapshot and its own ancestry and limit rules. No core/reference imports.
- External oracle uses the permitted independent reference relations over each
  arm's actual records, grants, authenticated inputs and committed operations.
  Its native duty/ownership/allocation ledgers are never scoring inputs.

A new acceptance without capacity is refused, logged, and does not change the
live offer. The owner remains accountable during incapacity. The fallback opens
at most once per episode, inherits a live window, never offers to itself, and
unownership waits for the last live offer. Recovery ends the episode while
preserving outstanding offers; a later loss inherits a still-live fallback or
opens one new normal window when none remains.

## Acceptance and source lineage

Sixteen cases exercise institutional and grant capacity, tool/message paths,
per-refund limits, scope, purpose, ancestry, initial incapacity, recovery on both
sides of expiry, renewed loss, no self-offer and last-live-window handling.
Each current backend passes 119 source assertions; independent state audits
reference/core/SQL are 494/510/2290. Three positive controls remain positive on
pinned9135bcdb. All backend-designated sensitivity targets fail there. Before
runs explicitly retain incomplete assertions caused by the older result shape;
none is credited as a passing check. Full raw reports accompany final evidence.

Exactly two active permanent scenarios are replaced under Q16, with explicit
`historical_id` lineage. Original Q11/Q12 YAML remains byte-identical and can be
loaded for historical sensitivity; the active permanent population stays32.
Counts affected by those two new source sequences must be reported separately
from the unchanged frozen534 assertions. The old SQL component expecting L to
take the duty is likewise updated to the approved Q16 rule, preserving its
before failure. Frozen v0.2.2/W0, controllers, contracts and matching protocol
are unchanged. No expected outcome comes from an implementation.

Original Q14 authoring drafts remain history; v1 was activated byte-for-byte as the Q14 acceptance suite. No final
cross-arm scores, empirical H3 claims, model calls, Modal operations, spending,
deletions, Notion edits or public releases. This checkpoint awaits Claude review.

## Property-gate compatibility repair

The first generated-property campaign passed all29 programs/58 executions and
5,348 checks, but the P2 mutation worker raised TypeError: its test-only
`waive(ctx, view)` adapter had not been updated for Q16's capacity argument.
The gate correctly failed instead of crediting an unexecuted mutation. The
adapter now forwards that argument; it still waives exactly the closure duty
check, with all expected outcomes and mutation intent unchanged. A fresh P2
worker detects the intended P2 property failure and one independent T09 source
failure, without a worker exception. The full six-mutant campaign and full
unit discovery are rerun after the repair. Failed/interrupted prefixes remain
in the evidence; none is reported as a passing acceptance campaign.

Only `tests/gateway_properties/mutants.py` changed in that repair. The source
snapshot before/after and that one-file delta are retained. The arm replay's
runtime, driver, observer, fixtures and inputs remained byte-identical, so its
ongoing results are still current runtime evidence. No P1–P6 expectation or
frozen outcome is altered to obtain a pass.
