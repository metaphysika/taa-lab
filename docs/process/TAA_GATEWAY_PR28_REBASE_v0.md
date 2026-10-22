# PR #28 rebase and clarification-gate repair

Scope: integrate the reviewed stacks and repair explicit C4 binding arguments.
Authority: Chris relayed Claude's approval, conditional on this repair and CI.
Fixtures: frozen expectations, POEC contracts and conservative Q14–Q16 behavior stay unchanged.
Evidence: compare each gate with its own reviewed parent; count differences stop acceptance.
Merge: require every CI workflow green on the repaired head before merging #28.

[DESCRIPTIVE] Chris relayed Claude's local review on 2026-10-22. The approved
#27 dependency stack was merged in order: #23 (Q13), #21 (properties), #25
(adversarial), #26 (SQL kernel), #27 (conventional W0). Every approved head had
successful Gateway, Harness and Formation workflows. No head branch was deleted.
PR #28 was then rebased onto main at `9918d1af51aa16d1a8d5ae6351bc553f296dcbee`.
It retains the stage 7/controller and TraceGrant changes originally filed in
#20/#24, plus C1/C4. Workflow conflicts retain every step from both stacks; the
combined component command contains both sets of tests. Repeated upload paths
were deduplicated. Both introductory README paragraphs and notebook entries
were retained.

[DESCRIPTIVE] `scripts/check_gateway_q11_q12.py` and
`scripts/check_gateway_q13.py` were the only external callers of `runner._run`.
Each now calls `prepare(case)` inside the case/backend loop, then passes the
prepared case and that fresh proposal-origin binding table as the fourth
argument. `_run` still requires the argument. No optional default, fallback to
native issuance order, expected-outcome edit or decision-rule change was added.
The C4 binding table is never shared between backend runs.

[DESCRIPTIVE] The combined discovery inventory is the exact multiset union of
both reviewed trees: main contributes 981 collected tests; the complete old
#28 tree contributes 944; their union is 1,014. There are no added or missing
test identities beyond that union. The earlier #28 historical run collected
942 before its last two controls; its final focused rerun and the complete
pre-rebase source inventory remain separately recorded. These dependency
inventory totals are distinct from per-gate scenario/assertion counts, which
must match their respective reviewed evidence.

[DESCRIPTIVE] Local checks include the current Q11/Q12 and Q13 gates on both
backends and their pinned pre-change implementations. The workflow's historical
spot-check and adversarial baseline checks are retained as well. Their deliberate
failures are sensitivity evidence, not ordinary-run passing outcomes. The normal
frozen, regression, property, adversarial, conventional, controller and TraceGrant
gates retain their strict discrepancy/incomplete checks. All 19 gateway run commands passed locally (17 workflow commands plus the
two repaired current-version gates), including all four pinned baseline
sensitivity checks. Full discovery completed **1,014 tests, 36 skipped, zero
failures or errors**, in 2,467.452 seconds. Scripted all-scenarios also passed.
Every count comparison against the respective reviewed evidence is unchanged:
conventional 11,737 checks; properties 5,348 with six mutants; adversarial
3,206 reference / 3,277 production; controllers 3,316; TraceGrant 1,190.
Compact counts, comparisons, source hashes and retained result hashes are in
[validation.json](evidence/gateway-pr28-rebase/validation.json).

[INTERPRETATION] This is an engineering integration repair. It establishes no
empirical H3 result. C2, C3 and cross-arm scoring are separate follow-up work.
No model calls, Modal operations, spending, evidence removal, Notion edits or
public release occur.
