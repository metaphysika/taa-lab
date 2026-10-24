# PR31 conditional review and sensitive overlap regression

[DESCRIPTIVE] The new companion scenario repeats default100 notices until a summed-overlap defect would reach the400 claim.
[DESCRIPTIVE] Correct reference, production and SQL keep coverage100, duty unresolved and closure REFUSE.
[DESCRIPTIVE] Disabling interval merging in each actual call path produces wrong discharge and PERMIT closure; each mutant fails three source checks.
[PRESERVATION] The original Q14 suite, frozen fixtures, superseded source files and production implementations are unchanged.
[GATE] Chris authorizes merge after this addition and green CI; cross-arm scoring follows separately over only the ten declared programs.

## Claude's review relayed by Chris (verbatim)

Claude's review of PR #31 (head 6526bccd): approved on one addition.

Verified locally: all 23 CI steps pass, including every Q14/Q15/Q16 suite, H1, the null-allocation controls, the frozen and regression gates on all backends, P1–P6, adversarial, and the all-arm engineering replay (floor/static partial writes observed, non-applicable fault boundaries labeled by design, TraceGrant limited to its ten programs). Frozen fixtures unchanged; superseded scenarios byte-identical.

Claude mutation-tested the production gateway; all five mutants were caught: union replaced by summed overlap (R-Q14-support-falls), first-tried instead of least-recent routing (R-Q15-least-recent), no redirect on ineligibility (seven Q15 scenarios), fallback renewal within an episode (nine Q16 scenarios), no capacity check on acceptance (six Q16 scenarios).

Required before merge: R-Q14-repeated-default cannot detect double counting, because three 100 notices total 300, below the 400 claim, so the duty is unresolved either way. Add a sensitive version in which counting overlap more than once would reach the claim (for example claim 250 with a single 250 settlement, two default 100 notices plus one 150 notice with portion [100,250); or repeated identical notices that would sum to the claim). Keep the original. Show the new scenario fails with summed overlap and passes on your code, on all three backends. Then merge on green CI with all other counts unchanged.

Next, in its own PR: cross-arm scoring under the committed protocol, over the ten declared development programs only. Report the full table: every arm, every metric, all discrepancies, incomplete and unassessed items, plus the TraceGrant coverage limit and the floor/static partial-write observations, with no interpretation beyond the protocol's definitions. No model calls, Modal operations, spending, deletions or public releases.

## Addition and mutation depth

`tests/regression_scenarios/q14_overlap.yaml` adds R-Q14-overlap-reaches-claim
outside the frozen bundle and original18-case Q14 file. Claim400, settlement250:
four committed default100 notices all cover [0,100), not400. A subsequent closure
proposal must be REFUSE. The fourth notice is essential to this mutation's
wrong-discharge/closure contrast; coverage is also checked after the third.

`tests/q14_overlap_support.py` executes this trace through the existing common
runner with explicit proposal-origin bindings and independent state audits.
It compiles an in-memory copy of each implementation's interval routine with
only its merging branch disabled. SQL is patched at `ledger.compute`, the
imported function actually called; the first preflight patched the definition
module instead and failed to install the mutant. That failed harness attempt
and interrupted obsolete discovery prefix are retained. No production source,
expected outcome or matching rule changed to obtain a pass.

Current/mutant/restored observations are retained, including actual duty state.
Each backend has15 source assertions; reference/production each have86 state
audits, SQL310. Correct/restored results are identical with0 discrepancies or
incomplete. Each installed mutant has3 source discrepancies, including duty
wrongly discharged at step5 and closure PERMIT at step6, with0 incomplete.
The new unit method and standalone CI gate keep this control in acceptance.

Final discovery, unchanged-count comparisons and hashes are recorded in the
companion evidence before commit. No scoring has run in this addition.

## Completed local acceptance

Full discovery:1,098 methods (the original1,097 plus the companion test),36
existing optional skips,0 failures/errors,1739.969 seconds. Scripted all-scenarios
passes. Seven fresh acceptance commands verify15 unchanged cohort comparisons
(frozen and permanent on all three backends; Q14/Q15/Q16 on all three). Their
assertion/audit/discrepancy/incomplete counts match the reviewed6526bccd evidence
exactly. All runtime, protocol, controller and protected source diffs are empty.

Evidence: [validation.json](evidence/gateway-pr31-overlap/validation.json) and
acceptance.zip, including the complete mutant/current observations, actual
wrong-discharge and PERMIT endpoint verification, the failed harness preflight
and interrupted obsolete discovery prefix. Final GitHub CI remains required
before merge; no cross-arm scoring has run in this addition.
