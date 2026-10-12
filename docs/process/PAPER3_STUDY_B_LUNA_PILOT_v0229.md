# Luna-only Study B development pilot — v0.22.9 adapter

Owner approved the exact v0228 72-condition, one-repeat pilot with a $0.25 total cap and existing 2,048 output ceiling. No held-out run, Study B freeze, higher output limit or other stage is authorized. The original corrected cases/keys and neutral system/default settings are hash-bound; no wording tuning during the pilot. Luna is exposed as the development model; these are pilot results, not held-out evidence.

The dedicated runner records full native requests, first replies, exact wire histories, deterministic local effects, separate substance/protocol scores, checkpoints and every attempt reserve/closure. It uses the configured Cloud TAA_OPENAI_API_KEY binding without opening a credential file. No Groq/model metadata probes or new provider/account. A shared exclusive run lock covers requests and retry waits; foreign locks are never removed.

The approved prospective five-total-attempt transport policy is reused unchanged: eligible no-output failures retry with increasing waits and longer provider reset information; every attempt is logged. Any full/partial response bytes block resend. First received malformed/refusing/unfinished replies retain those outcome labels and are not replaced. Retry exhaustion or the eleventh retry-needed request stops for review before any further cell or replacement. Partial/unknown output, identity/usage/size/budget errors or interrupted checkpoints also stop. There is no automatic interrupted-run resume. A transport-lost primary remains unchanged with a pending single labeled end replacement; a safety stop requires separate review first.

All attempt and reserve spending is cumulative in the existing OpenAI ledger, initially $0.2043034. The binding pilot ceiling is initial actual ledger amount + $0.25 (and cumulative $8); all retries and any separately allowed replacements share the same allowance. Uncertain generation costs retain reserves. Paid-provider ledger accounting is an application estimate, not a guaranteed billing cap. Other ledgers/quota and original Study A evidence remain byte-identical.

The exact launch after offline fixture/full regression verification, from /workspace/taa-lab, is:

```
/workspace/haiku55-runtime/venv/bin/python3 scripts/formation_study_b_luna_pilot.py --approved-luna-pilot
```

Output remains the approved `results/2026-10-12 v0.22.8 luna-none r1 study-b pilot`. Execution approval binds the unchanged cost plan plus the tested dedicated adapter and original dependencies. The full-history/replay/closure/identity/usage/ledger audit runs before a completion report. Completed-run invocation audits and returns the saved result without new requests. The original full-batch Study A CLI is never used.

After completion or stop: preserve evidence, report counts by family/rung/pressure and substance/protocol separately, cost and mechanical failures. No wording revision based on held-out results. Gate 5b still requires owner review of the development findings, any prospective draft revisions, prediction pooling/thresholds, uniform output-limit proposal, revised costs/caps and protocol readiness before freeze or held-out calls.
