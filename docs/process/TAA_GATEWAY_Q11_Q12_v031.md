[DESCRIPTIVE] Q11/Q12 from Claude, relayed by Chris on 2026-10-22, are copied verbatim into the alignment document.
[DESCRIPTIVE] Tool authority and acceptance standing are separate; concurrent offer windows survive authority loss unchanged.
[DESCRIPTIVE] Ten new Sol-authored regressions supplement the unchanged frozen v0.2.2 bundle and original eight regressions.
[DESCRIPTIVE] Both backends run through the same independent observer; the three original deadline mutations remain detected.
[LIMITATION] This delta requires Claude's review and green CI before merge; these are offline engineering checks, not empirical H3 validation.

# Q11/Q12 delta for Claude review

[DESCRIPTIVE] PR #19 was already merged at `59e48fcf5bcf6da5ae99cb0523f602187bb7e71a`
when these clarifications arrived. This is a new fix branch from that main commit;
the merged PR and frozen fixtures are not rewritten.

[DESCRIPTIVE] Production's virtual ACCEPT authority path is removed. AU1 still
checks a real scoped grant; DU4 checks live standing separately from DU1 closure.
Message acceptance verifies an authenticated sender against the offer without
granting tool authority. The reference resolves a duty's claim for grant scope
and rejects missing standing. Production setup now actually seeds additional
declared grants, which the new positive and negative grantee controls require.

[DESCRIPTIVE] Each backend independently represents multiple outstanding offers.
An existing fallback offer keeps its expiry; a different recipient's offer stays
open while a new five-step fallback window opens. Either valid acceptance closes
all competing offers. Expiry becomes unowned only once every window is inactive.
Accepted ownership does not itself grant refund authority; the authority baseline
distinguishes absent authority at acceptance from a later loss. The reference now
represents and dispatches the unowned-duty report with its own version and deadline.

[DESCRIPTIVE] Clock boundaries use every live window and ignore closed windows.
A separate component control checks expiry and authority loss at the same step:
phase 1 expires the voluntary offer before phase 2 opens a new fallback window.
The old implicit single-offer fields remain a projection for existing consumers.

[DESCRIPTIVE] The common runner's new `live_offers` observation reads actual duty
state, never returned descriptions. The full independent state-delta guard and
all hidden-state negative controls remain. Frozen outcomes, source lists and
manifests are unchanged; new regressions are outside the frozen bundle. The
reference imports no core decision, authorization, discharge or transaction code.

## Validation

[DESCRIPTIVE] Final observed counts are recorded in
`evidence/gateway-q11-q12/validation.json`. Each check is an individual source
assertion, state audit or hidden-state detection guard, not an independent trial.
Full reports are retained as CI artifacts.

| Backend / suite | Scenarios | Source | State audits | Detection guards | Discrepancies | Incomplete |
|---|---:|---:|---:|---:|---:|---:|
| Production frozen | 54 | 534 | 1,751 | 0 | 0 | 0 |
| Reference frozen | 54 | 534 | 1,704 | 0 | 0 | 0 |
| Production all regressions | 18 | 169 | 524 | 3 | 0 | 0 |
| Reference all regressions | 18 | 169 | 504 | 3 | 0 | 0 |
| Production Q11/Q12 only | 10 | 112 | 312 | 0 | 0 | 0 |
| Reference Q11/Q12 only | 10 | 112 | 299 | 0 | 0 | 0 |

[DESCRIPTIVE] The focused 188-test suite passes. After adding the same-step
expiry control and ordering correction, the affected reference/spot-check subset
passes 47 tests, including the new control against both backends. That is 189
distinct focused tests; CI runs all 189 together. The three original boundary
component tests remain unchanged. Their comparison mutation targets follow the
new per-offer fields: all three originals pass; each mutant yields exactly one
assertion failure and zero errors. The source validator reports 49 definitions
and variants checked, zero errors; the supplied zip and manifest verify unchanged.

## Before/after sensitivity

[DESCRIPTIVE] `scripts/check_gateway_q11_q12.py` uses current hand-authored
expectations and the common observer with either implementation package tree.
CI pins the before checkout to `59e48fcf`; local before packages were extracted
from that commit, and the report records their hashes. It requires failures in
every defect-targeted case for its designated backend, with correct cases kept
as positive controls. Before failures are evidence of test sensitivity, not
passing validation. They are never used to infer expected outcomes.

[DESCRIPTIVE] Before reference: 14 discrepancies and four incomplete descriptive
fields among 378 reached checks (97 source, 281 audits); three scenarios also
abort with two invalid-acceptance ValueErrors and one missing-report-id KeyError,
leaving 15 source assertions unreached. Before production: 28 discrepancies and
four incomplete descriptive fields among 424 checks (112 source, 312 audits).
All designated defect cases reproduce. After: all ten scenarios and all 112
source assertions execute in each backend with zero discrepancies or incomplete.

[DESCRIPTIVE] Cases cover F's refused tool call followed by accepted message;
scoped tool authority without standing; standing and authority together;
out-of-scope refusal; preserved fallback expiry with acceptance at 6 or unowned
at 7; either concurrent winner and rejection of the second acceptance; both
windows expiring; and acceptance while only the later fallback window remains.
They carry the requested attribution, `Sol-authored from Claude's Q11/Q12
clarification; expectations reviewed by Claude`. This attributes the scenario
expectations to Chris's relayed clarification; implementation approval is pending.

[LIMITATION] The two v0.3.2 questions about explicit coverage portions and an
implicated current report recipient remain conservatively implemented as
previously documented. No model calls, Modal operations, spending, evidence
removal, Notion edits or public releases occurred. Merge is not launch approval.
