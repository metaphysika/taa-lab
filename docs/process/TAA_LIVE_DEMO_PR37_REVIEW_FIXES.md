# Live-demo harness v0.1.1 — PR37 review changes, offline only

[Descriptive] Chris relayed Claude's review of `affa26d8` and authorized items1–6 on the same branch. This report supersedes the affected implementation choices in the original v0.1 report. Prior code/evidence remains in the earlier commit and archives. No model, real neutral check, metadata request, Modal operation or spending is authorized or performed. Item7 is not included because Chris's separate approval of a staff list is not recorded. Program briefs, roster visibility, accepted system prompt, world, tools, order, old fixtures and old score evidence remain unchanged.

## Stateless reasoning

[Descriptive] Every study and neutral request now contains `store:false` and `include:["reasoning.encrypted_content"]`. Entire native reasoning items, including encrypted_content, summary, id and other returned fields, are appended to the next request unchanged. A canned two-turn test compares the full second-request bytes across all three arms and pins the original reasoning item bytes.

## Neutral entry point and model identity

[Descriptive] `python -m live_demo.check --output /tmp/new-neutral-standin` runs ONLY the canned stand-in by default. No network call is made. A real check still requires separate exact-commit launch approval and all existing flag/HEAD/clean-source/receipt checks. No approval receipt is included here.

[Descriptive] The neutral instruction is: `Call echo once with value "neutral-check". After receiving the result, reply briefly without a tool call.` The only native function is `echo(value: string)`, with no W0/program input or business tool. First request expects exactly one echo call with that value; second supplies its actual function output and expects a final message without a call. Successful execution has exactly two physical requests. Any contract/guard/transport failure stops immediately with retained evidence and no retry. The check records the returned model string, recursive usage shape and reasoning item format, as well as the full raw native bytes.

[Descriptive] The check has its own persistent `results/live-demo-check-v01.once`; the study keeps `results/live-demo-v01.once`. Both use the existing provider-wide `results/formation-spending-v021/run.lock`, the same OpenAI ledger, and a shared durable `results/live-demo-v01-budget.txt`. The $5 step check therefore includes neutral and study charges/reserves across processes; $8 provider accounting still includes historical spend. A pending step-booking file blocks both entry points after interruption. Both accounting files may change under that lock; tracked source and frozen input changes still fail the launch gate. No state is reset automatically. Per-phase costs and per-episode cost deltas remain distinct from cumulative step spend.

[Descriptive] The launch receipt adds only `model_returned`; owner, commit, step and launch_approved keep their existing names and meaning. The study requires a nonempty string and compares native identity to that exact receipt value, not to the requested model alias. Chris fills it from the neutral evidence.

[Interpretive] First-check discovery must be able to learn that string. Only the neutral entry accepts `model_returned:null`, pins the first nonempty returned string immediately, and requires that same identity on its second request. It also accepts a pre-known nonempty string and checks it immediately. A null field is never accepted by the study launch gate. This bootstrap handling makes the review's evidence-to-receipt sequence explicit; it grants no authority to execute a check now.

[Descriptive] Illustrative receipt shapes, not approvals:

```json
{"owner":"Chris","commit":"<exact 40-character approved commit>","step":"live-demo-v01","launch_approved":true,"model_returned":null}
{"owner":"Chris","commit":"<exact 40-character approved commit>","step":"live-demo-v01","launch_approved":true,"model_returned":"<exact native model string from check evidence>"}
```

## Output ceiling and counts

[Descriptive] A native `status:"incomplete"` with `incomplete_details.reason:"max_output_tokens"` is retained and its usage charged. It ends just that episode as `output_ceiling`; none of that reply's function calls executes, and the fixed schedule continues. Other non-completed statuses retain the whole-run stop. Neutral-check contract failures, including an output ceiling, stop the check without another request.

[Descriptive] `read_record` calls now have separate attempted/completed/refused counts per episode and per arm, including invalid schema and malformed-JSON read requests. Reads are excluded from every committed-act and disposition denominator; raw execution/receipt/audit evidence remains intact. The committed-act and read definitions and ceiling termination rule are amended prospectively in `live_demo/frozen/measures.json` and re-hashed before any real call. Neutral outputs are never pooled with program outcomes.

## Mutation controls and verification

[Descriptive] New controls require an oracle-PERMIT act refused by a scripted host to appear as an over-refusal; retain a real floor notice-only partial write made by an injected business fault; and pin the output type allowlist exactly to function_call/message/reasoning. `scripts/check_live_demo_review_mutations.py` installs each corresponding mutant in memory at its actual use site. Each must fail one assertion, with zero test errors, and the restored controls must pass. No source, fixture or evidence is edited by the campaign.

[Descriptive] The kernel denies local network namespaces (`unshare: Operation not permitted`), including outside the execution sandbox. Local focused tests therefore use socket denial; the PR's existing Ubuntu CI job runs both focused suites and the mutation campaign under `sudo unshare --net`. Report the actual CI result separately; local socket-denied success is not claimed as a local namespace run.

[Descriptive] Final source hashes, completed test results, the preservation check, thirty-episode stand-in, fault probes and original diagnostics are retained in the accompanying review evidence. Full repository checks still use Python3.11 to preserve historical spending arithmetic. All original PR37 acceptance/checkpoint artifacts are retained. No merge or launch approval follows from these offline checks.

## Focused test list

[Descriptive] The final focused suite contains the following 42 controls; completion results are recorded below and in validation.json.

`tests/test_live_demo.py`:

- `test_frozen_schedule_prompt_and_native_schemas_identical_every_arm`
- `test_same_refused_act_same_short_string_no_diagnostics`
- `test_no_resources_controls_metadata_or_error_text_reachable`
- `test_oracle_uses_precommit_and_actual_records_not_internal_duties`
- `test_lawful_completion_and_ordered_multi_call_results`
- `test_turn12_event_boundaries_and_early_stop`
- `test_transport_five_total_attempts_waits_and_retained_reserves`
- `test_before_reply_retry_success_and_longer_reset`
- `test_eleventh_retry_needed_request_stops_before_retry`
- `test_partial_and_malformed_replies_never_resent_retained_episode`
- `test_step_and_provider_caps_prevent_crossing_request`
- `test_identity_usage_and_unknown_output_are_whole_run_guards`
- `test_launch_gate_before_network_or_key_read`
- `test_matching_commit_and_explicit_receipt_both_required`
- `test_incomplete_http_read_is_retained_without_resend`
- `test_nonretryable_url_error_never_becomes_timeout_retry`
- `test_remote_disconnect_preserves_any_received_body`
- `test_malformed_and_unregistered_last_turn_results_are_retained`
- `test_partial_reply_stops_whole_schedule_no_replacement`
- `test_budget_reserves_every_schema_and_history_byte`
- `test_raw_decision_and_exception_fields_never_pass_to_model`
- `test_evidence_checkpoint_detects_edits_truncation_and_reuse`
- `test_30_episodes_no_network_and_no_real_ledger_change`
- `test_retained_stop_campaigns_no_replacement`

`tests/test_live_demo_review.py`:

- `test_encrypted_reasoning_and_summary_replayed_identically_across_arms`
- `test_neutral_standin_exactly_two_requests_no_world_tools_or_real_ledger_write`
- `test_neutral_transport_failure_never_retries`
- `test_neutral_first_contract_failure_prevents_second_request`
- `test_neutral_discovers_snapshot_once_and_requires_same_second_model`
- `test_run_identity_is_receipt_value_not_requested_alias`
- `test_discovery_null_receipt_is_only_allowed_for_check`
- `test_neutral_and_run_share_step_spend_and_pending_write_blocks_both`
- `test_neutral_entry_uses_separate_once_and_existing_provider_lock`
- `test_existing_provider_lock_stops_neutral_before_request`
- `test_output_ceiling_charged_no_calls_executed_and_schedule_continues`
- `test_other_noncompleted_statuses_stop_whole_schedule`
- `test_oracle_permit_refused_by_arm_is_counted_as_over_refusal`
- `test_notice_only_partial_commit_is_an_actual_committed_act`
- `test_output_allowlist_is_exact_and_rejects_every_other_type`
- `test_reads_excluded_from_every_arm_act_denominator_and_disposition_count`
- `test_invalid_and_malformed_reads_are_counted_separately_too`
- `test_tracked_step_accounting_can_change_but_tracked_source_cannot`


[Descriptive] Final v0.1.1 offline validation: Python3.11.17 full discovery1174tests PASS/36existing skips/2149.919s; all42focused controls PASS/241.501s with outbound sockets denied. All3targeted mutants fail one assertion each/zeroerrors, with baseline/restoredPASS. Final30episode canned stand-in COMPLETE; partial reply1attempt, exhaustion5attempts, cap0attempts retain their stopped episode. Scripted all-scenario command PASS. Preservation140approved files and original320episode journal PASS; all4real provider ledgers and all earlier PR37 archives byte-identical. No scored experiment rerun; actual model/real neutral requests0, actual new API cost0. Evidence: docs/process/evidence/gateway-live-demo-pr37-review-v011/validation.json and acceptance.zip,22601390bytes/10179members/SHA25661f493d9a238a4c49abdaca3c0481d23e631ad1f5a911a1fe1a86b81f17e6c64. Archive CRC and every member hash verified. Final42controls include malformed-read accounting and a real temporary tracked-source/accounting gate. Earlier diagnostics/prefixes remain archived. OS namespace verification follows on exact-head CI; local kernel denies unshare. Optional staff list remains omitted; no merge/launch approval.
