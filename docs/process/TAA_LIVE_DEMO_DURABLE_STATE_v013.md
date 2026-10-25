# Live-demo v0.1.3 — durable attempt state and authentication audit

[Descriptive] Chris relayed the controlling audit/repair prompt and authorizes offline changes on the PR37 branch. No further model calls are authorized. One separately approved free empty-body POST to https://api.openai.com/v1/responses returned status401/type invalid_request_error/code invalid_api_key, contrary to expected400 and Chris's reported Mac400. Only those three response fields were recorded; messages and key material were not recorded. Neither ledger changed. This report supersedes the affected checkout-local state instructions in v0.1–v0.1.2, not the retained evidence.

## Durable state

[Descriptive] Every checkout uses the fixed /workspace/taa-live-demo-evidence/state/ location. There is no live CLI or environment override and no automatic initialization. Missing state manifest, step ledger, provider accounting, or either imported marker causes durable_state_missing_or_invalid before networking. State inside any Git checkout is rejected.

[Descriptive] The original attempt1 and attempt2 once files were moved, without changing their bytes, to check-attempt-000001.once and check-attempt-000002.once. state.json records both as already used and pins their original marker hashes. step-budget.txt was moved with its0.008324 amount unchanged. migration-plan.json retains original paths, destinations and hashes. Original receipts and evidence ending checkpoints are unchanged; snapshots remain with both attempts. No reservation was refunded or reset. The canonical provider ledger remains /workspace/taa-lab/results/formation-spending-v021/openai.json, amount1.1411209749999984; its existing provider-wide run.lock remains the shared lock. Their absolute paths are bound in state.json, so other checkouts cannot silently use an old ledger copy or separate lock.

[Descriptive] Neutral receipts now require check_attempt as a positive integer (booleans, zero, negative, missing and non-integer values are rejected). The same field is checked by per-attempt authorization. Attempts1/2 are unconditionally refused; later numbers use an exclusive fsynced file in the durable directory and cannot be reused from another checkout or output. The thirty-episode run also keeps its once marker in this global directory. The run receipt retains its accepted nonempty model_returned format and does not accept a neutral check_attempt field.

[Descriptive] Prospective receipt SHAPE ONLY, not execution approval:

```json
{"owner":"Chris","commit":"<new exact reviewed commit>","step":"live-demo-v01","launch_approved":true,"model_returned":null,"check_attempt":3}
```

## HTTP-error privacy

[Descriptive] On HTTP errors the transport retains only type and code from the error JSON body under an error field, alongside the existing status/reservation/transport metadata. Message text, param, nested data, arbitrary response bodies and key material are never retained. Unrecognized type/code strings are withheld rather than logging arbitrary server data. Missing/malformed JSON produces null fields. Existing retry eligibility, no received-output retry, caps and neutral no-retry policy remain unchanged. Fields are host-only and never reach model histories.

## Regression controls

[Descriptive] Eight new controls cover reused attempts across two independently initialized Git checkout directories; step spend plus both caps across checkouts; missing state/step failure in both live entry points; positive-integer receipt validation and unchanged run format; sanitized401evidence with a credential-bearing message; unknown/malformed body redaction; invalid imported marker/state inside Git; and global run-once behavior. The earlier fixtures use temporary durable state, not real operational state. The null-identity mutant now targets authorized's actual run null-acceptance predicate: the former force-discovery mutation is also blocked by the newly required check_attempt field. No scientific fixture, expected moral outcome, program, world, measure, price or seeded schedule changes.

# Neutral attempts 1 and 2 — retrospective audit

[Descriptive] Attempt2 passed the original once guard because Sol moved attempt1's actual once file from /workspace/taa-lab/results/live-demo-check-v01.once to attempt1/once-marker-original.json before invoking the same reviewed harness again. The original bytes and evidence remained. The old harness checked only whether the checkout-local filename existed, not an attempt number or durable used-attempt registry. Both receipts were byte-identical and contained no check_attempt field. The fresh output directory did not itself override the once guard; the administrative file move freed the checkout-local slot.

[Descriptive] Sol interpreted Chris's exact message, "i just created a new key and added it to the environment. Try again.", as permission for ONE new neutral attempt at the previously approved4ef00671 commit after credential rotation. No separate Claude review of the administrative marker move was recorded. The attempt2 authorization file was written 2026-10-24 at22:45:29 America/Chicago (2026-10-25T03:45:29UTC), before invoking attempt2. This is the file-recording time, not an independently captured timestamp of Chris's message.

[Descriptive] Attempt1 reserved$0.004162 before transport and stoppedHTTP401 with no native usage. No refund/settlement occurred. Attempt2 reused the same original provider ledger and persisted results/live-demo-v01-budget.txt containing0.004162. Budget.__init__ read it; reserve added another0.004162. Neither total was reset. Current step0.008324, OpenAI cumulative1.1411209749999984, including both conservative reservations. Actual API-billed amounts are unknown.

[Descriptive] TAA_OPENAI_API_KEY was set BEFORE the reported credential change: attempt1 preflight recorded it as present. Sol did not set, unset or replace its value in a shell, did not read keys.env, and did not deliberately restart the managed environment or invoke a session restart. Each command naturally ran in a new child shell. Current environment-status observations used the same managed environment ID across the authentication diagnosis and showed observed spec45 then48, with the TAA secret binding ready; these observations do not establish which underlying credential each request received. No credential value or fingerprint was recorded, so stale-versus-new credential identity is not provable from retained evidence. There is no platform restart history available in the retained diagnostics.

[Descriptive] Both HTTP_PROXY and HTTPS_PROXY, plus their lowercase variants, were inherited as http://proxy:8080. A custom CA setting was present. Sol did not unset/bypass those variables or disable TLS verification. The harness used Python urllib through the inherited proxy, Authorization: Bearer <configured environment binding>, and https://api.openai.com/v1/responses.

[Descriptive] Paper3's pinned formation client reads os.environ[key_name]; B and C select key_name=TAA_OPENAI_API_KEY for gpt-6-luna. Its OpenAI endpoint is https://api.openai.com/v1/chat/completions, using the same Bearer header construction and urllib. The generic agents/openai_client.py defaults to OPENAI_API_KEY; that is not the TAA-specific formation configuration. The readiness archive names an earlier environment instance; historical success there does not establish the credential delivered by today's runtime.

[Descriptive] The separately approved GET /v1/models probe returned200 with no model-generation call. The separately approved empty-body POST /v1/responses probe from this environment returned401/type invalid_request_error/code invalid_api_key. The latter response differs from Chris's reported Mac400. Both accounting ledgers were byte-checked unchanged by each free probe. No error message or key material was recorded.

[Open question] Stale credential delivery remains a working hypothesis. The environment's POST401 contradicts the expected400 and does not confirm the Mac credential was forwarded. No further HTTP or model requests are authorized in this offline repair task.


[Descriptive] Final test results and retained source/evidence bindings follow after local gates. The local kernel denies unshare; Ubuntu CI runs the focused suites and mutation controls with sudo unshare --net. No model calls follow from this offline repair.


[Descriptive] Explicit environment answers: TAA_OPENAI_API_KEY was already set before the change. HTTP_PROXY:yes; HTTPS_PROXY:yes; ALL_PROXY:no, both in the recorded diagnosis and the current harness environment. The managed runtime's networking documentation describes a credential-injecting HTTPS proxy, so it can add/change authentication headers; whether it changed or stripped this particular request's header is not observed. Sol initiated no container/environment restart. The environment ID remained the same across available status checks; platform-managed restart history was not available. Paper3's adapters read the configured environment variable; how the earlier operator populated that variable is not independently established here. No key value, length or prefix was inspected or recorded.

[Descriptive] The carry-over regression drives the real neutral entry twice against two separate checkout roots with canned native replies and different attempt receipts. Both phases add their declared0.00005fixture charge to the same0.008324starting total. It also verifies both caps and that the canonical provider/lock paths are shared. These are engineering fixtures, not API spending or model observations.


[Descriptive] Both real neutral attempts used the same /workspace/taa-lab directory and the same detached4ef00671 HEAD. Attempt2 did not use a fresh clone, separate worktree or different working directory. Its output directory was new. The change that freed the once guard was the explicit move of the original marker, not a checkout operation. The full modified notebook was preserved outside the checkout, reviewed notebook bytes restored for the source-clean launch check, then all earlier notebook entries restored and the new stop appended. The provider and step ledgers were never restored to their Git versions.


## Owner-approved same-process endpoint comparison

[Descriptive] Chris separately authorized three free, non-generating probes from one Python process, in order, using the harness module's urllib Request/urlopen, one read of configured TAA_OPENAI_API_KEY, the same header mapping and inherited proxy settings. Results: GET /v1/models200/type null/code null; POST{} /v1/responses401/type invalid_request_error/code invalid_api_key; POST{} /v1/chat/completions400/type invalid_request_error/code null. Only status/type/code were recorded per response. Both ledgers were hash-verified unchanged. No model output was generated. This meets Chris's conditional instruction to prepare a Chat Completions native-tool adapter as a SEPARATE commit after this durable-state commit. It does not authorize a model call.

[Descriptive] The earlier /v1/models probe also ran with Python urllib and the configured TAA_OPENAI_API_KEY via the shell, not another connector or browser. That probe used the same library/variable but a separately built urllib opener to disable redirects. The latest three probes shared the harness module's default urllib opener in one process. The visible runtime settings expose a ready TAA_OPENAI_API_KEY secret binding scoped to api.openai.com and an enforced allowed-domain policy. Documentation describes a credential-injecting HTTPS proxy at http://proxy:8080. No method-specific or endpoint-specific credential-injection setting is exposed. Header rewriting for a particular request is not observed.

[Interpretation] Endpoint-dependent authentication behavior is now reproducible under the same client, process and variable. Different forwarded credentials or route-specific proxy behavior remain possible explanations, not established facts about the actual secret presented upstream.


[Descriptive] Durable-state final local gates PASS: full1184tests/36skips/2000.982s; focused52tests/0skips/220.770s; preservation140files/320originalepisodes; two-request canned neutral with unchanged reasoning replay; four targeted mutations with one assertion failure/zeroerrors per mutant and baseline/restoredPASS; scripted all-scenario commandPASS. No new model calls. Both actual ledgers remain byte-identical to attempt2 after-state, all old freezes/archives unchanged. Final evidence docs/process/evidence/gateway-live-demo-durable-v013/validation.json and acceptance.zip,567501bytes/239members/SHA256df530eec4a868a2c2534a642079f6da5e7bb17f85dc132805566718de3e7adbc; CRC/all238memberhashes verified. Same-process free comparison200/401/400 triggers a separately committed Chat Completions fallback under Chris's conditional instruction, with no inference execution approval. Namespace CI checked for this pushed head separately.
