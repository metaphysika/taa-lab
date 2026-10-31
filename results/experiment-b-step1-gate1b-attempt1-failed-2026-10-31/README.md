# Gate 1b attempt 1: failed harness attempt

Run 41198759544 used main 84070e4b and failed in episode 21,
Haiku 5.5-1-4W, before its episode_end or the final stop/spend record.
This is evidence of a failed attempt only. It is not scored, not pooled,
and not scientific headroom evidence. The next run starts fresh at episode 1;
none of these episodes carries forward into that run.

The raw journal and failed-step log are copied byte-for-byte from the downloaded
artifact. The journal contains 624 lines, 21 episode starts, 20 episode ends,
83 responses and 83 budget_settled records. Retained audit fields from the
interrupted attempt are historical raw data, not accepted scores.

- journal.jsonl SHA-256: a5e658795f3afd275f2a9a1be2c8e3544219ed9c8839910b76d90a743aff18aa
- failed-step.log SHA-256: 5d378f09a473348bc6e58ca664639c244fa60d54e8f97c9494c502b48f00ab69

Summing dollars_upper from every budget_settled record using Decimal gives:

- Luna / OpenAI: $0.030887000.
- Haiku 5.5 / Anthropic: $0.027226250.
- Total: $0.058113250, equal to the final settled cumulative upper bound.

These are harness upper bounds, not billing-provider reconciliation. They are
booked once to the provider ledgers and carried-forward recorded total. The
November ledger stamp does not reset cumulative provider balances or discard
earlier recorded spending. Chris excludes this failed attempt from the fresh
$8 Gate 1b allowance. Provider stops remain OpenAI $8 and Anthropic $13.

The replay fixture tests/fixtures/experiment_b_haiku_4w_replay.json projects the
first three response objects of episode 21 (journal lines 594, 601 and 608).
It retains the original six tool calls, response/model IDs, stop reasons and
input/output usage counts. Thinking blocks, caller metadata and unused usage
fields are omitted. The last read_record targets nonexistent C; the earlier
lawful refund and refund_issued notice are sufficient to reproduce the crash.
No live send is used. No credential exists in this fixture.

Publication checks found no credential-valued fields named Authorization,
x-api-key, api_key, access_token, refresh_token, password or secret anywhere in
the parsed journal, and no API key, GitHub token, Bearer credential or private
key patterns in either raw artifact or the fixture. Environment-variable and
authentication-header names in the approval configuration are names, not keys.

The added evidence directory is outside frozen fixture, schedule, source-manifest
and historical ledger-snapshot inputs. Checked fingerprints are Experiment B
inputs_sha256, schedule_sha256 and workflow_sha256 (unchanged), notebook_sha256
(intentionally changed by the append-only v0.24.37 entry), the unchanged
v0.24.36 canonical configuration/predictions, and immutable formation-ledger
snapshot hashes. No workflow file is edited. Existing CI discovers the offline
tests; the manual experiment workflow is not dispatched.
