# Claude review of draft PR #31 at 9135bcdb (relayed by Chris)

1. Null-allocation fix: approved as implemented. allocation_allows treats null and absent as unallocated, binds a refund proof to its own duty, lets a claimant notice cite a payment used for the same claim's duty (Q14/T20), and keeps other-claim allocation blocked. Historical counts unchanged. Keep both permanent controls.

2. The 98 "unsupported" replay instances need two different treatments:
 a) TraceGrant, 84 instances (no frozen POEC contract): correct to leave unrun. Do NOT author contracts for frozen traces, regressions, H1 or Q14 suites; anyone who writes them now knows the expected outcomes. Cross-arm scoring stays limited to the ten declared development programs, and every report must state the TraceGrant arm's coverage limit plainly. If wider TraceGrant coverage is wanted later, Astra will author contracts blind to outcomes.
 b) Floor and static T23, 14 instances: relabel. These arms lack atomicity by design, so a mid-write failure is a real behavior to observe, not an unsupported case. Give the business hosts an out-of-band fault adapter that injects at each boundary they actually have (for example after the effect write and before the receipt/log write), and record the resulting actual state, including partial writes, through the common state audits. Boundaries with no counterpart (token consumption, duty update, revision advance) are reported as "not applicable by design" with the reason, never "unsupported". This does not block Q14–Q16 but must be complete before Astra's comparator review.

3. Continue Q14–Q16 in this draft PR. Final scoring remains held until Claude reviews the completed PR. No model calls, Modal operations, spending, deletions or public releases.
