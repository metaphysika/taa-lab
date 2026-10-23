[DESCRIPTIVE] Stage 7 is updated onto merged Q11/Q12 main `b5126451`; its four controllers and answer keys are unchanged.
[DESCRIPTIVE] All five paired development families and four controllers still produce 40 episodes and 3,316 checks, with zero discrepancies/incomplete observations.
[DESCRIPTIVE] The updated focused suite passes 197 tests; all eight driver/scoring controls remain.
[LIMITATION] 195 semantic label actions remain explicitly unassessed; no H3 rates or complete semantic coverage are claimed.
[LIMITATION] This PR remains unmerged pending Claude review and green CI; later stages stay separate PRs.

# Refund development driver for Claude review

[DESCRIPTIVE] The original stage 7 report and evidence are retained in
`TAA_GATEWAY_STAGE7_PRE_Q11_Q12_v031.md` and the original
`evidence/gateway-stage7/validation.json`. New post-clarification evidence is
`evidence/gateway-stage7/post-q11-q12.json`. No historical output is erased.

[DESCRIPTIVE] The catalog reads Claude's frozen W0 and T01–T10 keys unchanged,
with five paired families. The correct controller follows the diagnostic key;
it has not learned competence and intentionally submits some wrongful probes.
Compliant, cautious and adversarial controllers receive inputs without expected
outcomes. External events stay simulator-owned. All episodes are development
material, not held-out or training exports.

[DESCRIPTIVE] The common runner's optional `token_from: last_proposal` input
resolves the latest observed token before execution/audits and clears after a
no-token response. It never reuses an old token by default. Both backends and
the merged Q11/Q12 `live_offers` projection retain their behavior. The runner
computes its own full delta and compares returned descriptions, never using
those descriptions as world truth. No decision, authorization, discharge or
transaction code or frozen expectation changes in this stage.

[DESCRIPTIVE] Correction records keep attempted act/scripted reason, gateway
response/keyed correctness, actual effects/receipts, completion and duty board,
feedback source and label source. Keyed labels apply only to the same act/step
and matching actual context. Other changed contexts/actions remain unassessed.
The report distinguishes wrongful attempts/effects, lawful opportunities and
withholding, erroneous refusals, duties and reporting. An unresolved duty is
only a candidate omission, not automatic over-refusal.

[DESCRIPTIVE] Final post-main run: 40 episodes, **3,316 checks** = 117 unchanged
source assertions + 3,199 independent state audits; **zero discrepancies and
zero incomplete observations**. Separately: **195 unassessed semantic actions**
and ten keyed lawful withholdings by the cautious controller. Different keyed
denominators after divergent trajectories cannot establish comparative H3 rates.
All 197 focused tests pass, including the eight driver/scoring/integrity controls.
Each episode retains actual native state, its input program and observations,
authenticated JSONL and a separately retained trusted simulator checkpoint.

[DESCRIPTIVE] Accepted main's permanent suites include production frozen
54 scenarios / 534 source + 1,751 audits and 18 regressions / 169 source + 524
audits + 3 guards; reference 534 + 1,704 and 169 + 504 + 3. Those main checks
have zero discrepancies/incomplete and all hidden-state controls detected.
CI repeats them with this merged runner, including both historical before/fix
guards. Q13's further regression additions are a separate fix PR, not silently
folded into this stage.

[LIMITATION] The finite adversarial controller is not the complete adversarial
acceptance stage. Properties, attack coverage, conventional comparators and
MCP/replay remain separately reviewed work. The comparator scorer must use a
representation-neutral protocol rather than native context hashes as universal
truth. No model calls, Modal operations, spending, evidence deletion, Notion
edits or public releases occurred. This is bounded engineering evidence;
Claude review and all green CI are required before merge.
