# Strong conventional comparator: pre-evaluation protocol

Status: implementation protocol, recorded before running this comparator. This
document does not report a comparison result. Claude review is pending.

## Representation and shared requirements

INTERPRETATION / IMPLEMENTATION CHOICE: The conventional arm uses a relational
SQLite store, flat constraints over its current rows, and serializable state
transitions. Its action handles bind actor, exact arguments, epoch and expiry.
It does not store TAA warrants or rule-computed justification/support sets.
Changes invalidate handles through a monotonically increasing epoch; execution
rechecks current constraints inside the same transaction as its effects.

REQUIREMENT: Its policy must implement the same W0 prohibitions, complete grant
paths, support conditions, caps, persistent third-party obligations, accepted
transfers, report routing, corrections and closure constraints as TAA. These
requirements are not deliberately weakened to create a contrast. Design v0.3,
Clarifications v0.3.1, and approved Q11–Q13 control. Q14–Q16 remain drafts:
retain the documented conservative interpretations until authorized otherwise.

REQUIREMENT: No decision, authorization, discharge, or transaction code may be
imported from `taa_gateway` or `taa_gateway_reference`. Sharing input fixtures,
serialization conventions, the common runner, and independent state audits is
permitted. The SQL implementation must perform its own state transitions; a
different wrapper around either existing policy is not this arm.

## Matching and scope

PROTOCOL: Run the same input events, tools, arguments, initial records, roster,
scripted controllers and event ordering. Match discrete dispositions, actual
effects, ownership/resolution, recipients and deadlines exactly; there is no
numeric tolerance. Retain all discrepancies and incomplete assertions. Unknown
semantic labels remain unassessed. Neither reference output nor production
output generates an expected outcome.

PROTOCOL: Acceptance includes the unchanged frozen v0.2.2 bundle, permanent
regression scenarios and reviewed adversarial controls through the same runner
and full-state audits. Inject faults at real SQL transaction boundaries and
retain the three hidden-state negative controls. A component test pass is not
full comparator acceptance.

INTERPRETATION: Matching correct behavior is success for both strongest arms.
Differences are implementation or policy questions until reviewed, not evidence
that TAA is superior. This offline development work selects no empirical H3
endpoint, tolerance or claimed advantage. It provides no novelty, transfer,
training, or population-effect claim.

## Review boundary

The storage/transaction kernel is a prerequisite, not a policy implementation.
Until its independent W0 constraint and duty layers are connected and the full
common-runner suites execute, every full-comparator scenario is **incomplete**.
Unit tests of the kernel must be reported separately; zero kernel failures must
never be presented as zero comparator discrepancies or complete acceptance.

Claude review and green CI are required before merge. Astra reviews the
conventional arms before live step 3. No live calls, spending, Modal operations,
Notion edits or public release are authorized here.
