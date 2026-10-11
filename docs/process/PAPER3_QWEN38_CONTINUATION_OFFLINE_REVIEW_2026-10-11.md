# Qwen frozen Study A: offline 429 review and continuation plan

The retained A_R02 repeat 1 failure is an issued HTTP 429, not a pre-request
quota pause. All 20 issued attempts have journal closure; 19 responses have the
pinned Qwen identity and valid usage. The final rejection has no returned model
identity, native usage or retained error body. It will not be retried or replaced.

## Findings

The rejection headers reported 984 requests and 8,000 tokens remaining. There
was no Retry-After header. The unchanged client therefore persisted its default
24-hour pause, until **2026-10-12T18:41:48.042773+00:00**. That timestamp is a
conservative client default, not a proven provider reset deadline. The cause
cannot be established from these headers. The serialized request was 12,683
bytes, within the frozen byte ceiling; its 12,685 input accounting estimate is
an upper estimate, not measured provider token usage. Waiting alone does not
establish that another issued rejection will be avoided.

Exactly four attempted episodes remain preserved, including the failed cell;
236 cells are untouched, starting A_R03 repeat 1. All 59 frozen files, original
adapter/cost-plan/controller hashes and source snapshot match. All four stored
results/checkpoints reproduce deterministic replay. The cumulative Groq ledger
is $0; the failed 8,000-token quota reservation and other ledgers are unchanged.
The original controller is absent and stopped_for_review; supervision stays off.
No credentials were inspected and no model calls or provider probes were made.

## Concrete continuation plan

`studies/formation-study-a-qwen38-continuation-plan-v0220.json` binds all source
file hashes, the exact ordered 236-cell suffix, frozen inputs/settings, and
current ledgers/quota. It retains the original root and evaluation output.
The cap and maximum additional spending are both $0. All first four cells and
the original 20 journal events must remain unchanged; new events append with
unique IDs. The original stopped manifest/status and all historical logs remain.

A separately reviewed Qwen continuation wrapper is required. The full-batch
runner stops when it encounters the retained fatal checkpoint; the existing
Haiku continuation reviewer accepts only a final Haiku timeout. Neither is an
approved Qwen continuation path. The original frozen adapters must not change.
The new wrapper must execute only the suffix, share the persisted quota/ledger,
resume only pre-request quota pauses and stop on every newly issued failure or
uncertainty. No paid upgrade, history trimming, settings change or retry.

The plan specifies required negative tests, all-cell offline fixtures, evidence
immutability checks and same-root/output/lock guards. Four existing Haiku
continuation fixture tests passed offline; these do **not** validate a new Qwen
adapter. No production code changed. The plan is complete, but execution is
**not ready**: new adapter implementation, tests, hashes and a reviewed launch
command must be prepared first. If unchanged Free limits make requests impossible,
stop for a user decision rather than changing the experiment.

## Next step and approval

Approve offline preparation of the Qwen continuation adapter and fixture tests
against this plan; no model calls. After that preparation passes, present the
exact command and hashes for separate approval to run only the 236 untouched
cells at $0, retaining A_R02 repeat 1 without retrying. Full P6 remains
inconclusive under frozen completeness and identity rules. No other stage advances.
