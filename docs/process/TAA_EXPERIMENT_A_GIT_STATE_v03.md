# [Descriptive] Experiment A state v0.3 — public operational branch, private H

[Descriptive] Chris's 2026-10-26 decision replaces the lost external-state design for Experiment A. The fresh environment has no `/workspace/taa-experiment-a-evidence/state/`: its operational files, H encodings and H expected key are unavailable. Nothing was recovered byte-for-byte, no earlier run is relabeled, and no seal is replaced. This implementation starts from PR40 `01a1d8af53dc2491999d951c23410977a81a9583`. No model/provider call, Anthropic check attempt2, pilot, H encoding/access or merge is authorized or performed.

## [Descriptive] Reconstructed state

[Descriptive] The dedicated [experiment-state branch](https://github.com/metaphysika/taa-lab/tree/experiment-state) has an orphan root commit `2d436a82005489a144607c7abf45337bdb7681f8`, with **only seven state files**. The old directory and remote state branch were absent when inspected. All reconstructed ledgers/markers explicitly identify their provenance; reconstruction.json records the loss and owner authority. New JSON ledger amounts use decimal strings, preserving the owner-supplied digits rather than inventing original serialization bytes.

| State | Owner-supplied reconstruction |
|---|---|
| Anthropic cumulative | 6.201251249999988 dollars |
| Google cumulative | 3.6689896000000046 dollars |
| Experiment A step | 0.39615025 dollars |
| Anthropic check1 | used; checkpoint097421a2c8f730ae1c6b054636cbf0ecc3abc262115d1e7d4ef568b870b7c30d |
| Google check1 | used; checkpoint401724451795fe0738ed7adb403288622943f008a50ae893ac71ef1489db576b |
| Pilot once marker | absent; no pilot has run |

[Descriptive] Files: state.json, ledgers/claude.json, ledgers/google.json, step-budget.txt, check-anthropic-000001.once, check-google-000001.once and reconstruction.json. The prior401 reservation remains in the supplied cumulative/step totals. No reserve is subtracted, spend reset, old failure deleted or attempt made available again. Historical Paper3 ledger/evidence files in the PR branch stay byte-identical; they are historical snapshots, not this runner's new accounting source. No other paid-stage continuation is authorized.

## [Descriptive] Worktree and publication protocol

[Descriptive] `TAA_EXPERIMENT_STATE_WORKTREE` configures the state worktree; the default is `/workspace/taa-experiment-state`. It must be a **separate linked worktree of the run repository**, never inside or enclosing the run checkout. Its checked-out branch must be experiment-state, or a detached HEAD exactly at origin's experiment-state tip. This supports a second linked worktree without bypassing stale-state checks. Run-code authorization still requires the exact clean Chris-approved launch commit.

[Descriptive] State startup validates the schema, amounts, file allowlist and absence of interrupted pending writes, then requires a clean worktree and fetches origin's experiment-state tip. Local HEAD must equal the fetched tip. Fetch observes only: the harness never merges, resets, cleans, rebases or discards an ahead commit. Missing origin/network access is a hard stop. Only operational ledgers, markers, the reconstruction record and an active-run.json lease are allowed in the state index; requests, replies, arbitrary receipt fields, local output paths, keys and H files are not published.

[Descriptive] Before any claim, a local flock in the common Git metadata prevents simultaneous writers sharing a repository. The runner also commits and pushes an exclusive active-run.json lease for coordination across independently synchronized state copies. A leftover lease after a crash or failed publication requires owner review; the harness does not reclaim it automatically. Both providers share the same lease and step budget.

[Descriptive] A check/run claim is permanent, committed and pushed before budget use. New markers bind the exact approved commit and current lease; even a directly constructed Adapter cannot reuse a prior lease's marker. Public claims retain a hash of the output path, not the path or arbitrary approval content. Reservations and settlements atomically replace their pending local accounting files, then each create a separate commit and push it. State-mode arithmetic writes exact decimal strings. Stand-in fixture accounting stays local and is accepted only by the existing exact ScriptedTransport guard; a live Adapter requires a state-bound budget.

[Descriptive] Each push uses an explicit expected old remote tip (`--force-with-lease=refs/heads/experiment-state:<old-tip>`). Every new commit is checked to be a direct child of that validated tip, with an allowed tree and only the intended changed paths. The push uses that fixed commit SHA rather than a movable HEAD; the lease provides compare-and-swap rejection, not permission to rewrite history. A concurrent remote update rejects the push. The runner then fetches and verifies acknowledgement. Dirty/ahead files, local commits and the remote active lease are retained on failure, with no rollback or further request. An acknowledgement failure is also a hard stop, even if the remote may have accepted the push.

[Descriptive] Each physical request rechecks code authorization and current state, reserves/publishes its conservative charge, and rechecks state/claim immediately before transport. Every native usage settlement is pushed before another request. A settlement push failure occurs after a received reply: that reply/evidence is retained, the remotely published reservation remains conservative, and the next request is blocked. Transport retries retain the existing approved retry/no-resend policy, with a separate published reservation for every physical attempt. Normal completion or a reviewed stop publishes lease release; once markers are never removed.

[Descriptive] Fresh-session setup, when state is clean and only behind:

```sh
git fetch origin experiment-state
git worktree add -b experiment-state /workspace/taa-experiment-state origin/experiment-state
export TAA_EXPERIMENT_STATE_WORKTREE=/workspace/taa-experiment-state
```

[Descriptive] If the local experiment-state branch already exists, omit `-b experiment-state` and use that branch. For an existing clean state worktree, fetch there and `git merge --ff-only FETCH_HEAD`, then let State validate exact equality. Ahead/dirty state, a failed push or a retained active lease is a review stop: do not reset it, clear markers, delete the lease or launch another process. This setup does not approve model calls. Git commit identity, write access to origin and network access must work before a request can be admitted.

## [Descriptive] H stays outside every repository

[Descriptive] Neither H01–H12 nor the H expected key is stored on experiment-state or in any other repository. Only the existing public `H.sha256` and `expected-key-H-astra-v01.sha256` bind the lost private bytes. The pilot program loader still rejects H before any file read; its frozen396-episode schedule remains D+P only. No H recovery is attempted now.

[Descriptive] The committed `experiment_a.cases.encode_program` serializes a complete owner-supplied structural program definition (`brief`, `events`, `rung`, `setup`) as sorted, two-space-indented UTF8 JSON plus one LF, without inferring records, rules or outcomes. The prior build had committed structural checks and materialized P encodings; this change makes that canonical serialization an explicit reusable encoder. Dry check only: P01 encoded twice produces identical bytes, also identical to the original committed P01; SHA256 `7ba16c288655fd943e5ac2fd113e190d22006cacfc06d98dc775c7d45c2cbbad`. No P file changes. This proves P serialization determinism; it does not claim recovery of lost H.

[Descriptive] At a separately Chris-approved unsealing, Chris supplies the approved H definitions and Astra's original key text. Encode the twelve programs with this committed encoder **outside every Git worktree/repository**; preserve all exact ancillary JSON members from the original sealing definition (including the pair catalog/provenance if present). Do not invent omitted metadata or normalize the key. Store the supplied key as its exact UTF8 bytes. Existing sealed_digest binds the sorted filename-to-content-SHA256 JSON manifest (two-space indent, final LF), including every JSON member, not just the twelve programs. Verify that digest against H.sha256 and the key's raw-file digest against expected-key-H-astra-v01.sha256. If either differs, STOP: no new seal, key adjustment, evaluation, or model path. Missing original ancillary bytes can prevent a match; do not claim reconstruction from program prose alone. A hash match itself is not model-launch approval.

## [Descriptive] Offline validation

[Descriptive] Tests use local bare Git remotes and linked worktrees only; provider transport is mocked and Python sockets denied. They cover reconstructed totals/used markers, second-worktree synchronization, dirty/stale/wrong-branch state, published claims/reservations/settlements at each transport boundary, lease-bound claims, simulated and actual remote push rejection, concurrent-tip rejection, failed settlement blocking the next request, no live fixture-budget bypass, P determinism and no H reads from the pilot. Earlier setup-test failures and the encoder's initially too-narrow top-level schema are retained; only test plumbing/canonical serializer validation changed, never a case or expected key. Final focused/full/scripted/preservation/stand-in results and archive hashes are recorded beside this report after validation completes.

[Descriptive] Final validation PASS: full1,836tests/36existing optional skips;272focused checks; scripted-all; strict preservation140protected files/original320episodes;396/396stand-in episodes/397verified chains. P01 twice-encoded bytes match the unchanged committed program. All396stand-in request bodies and episode rows equal the prior archived stand-in exactly. Actual public state is clean/up-to-date at2d436a82005489a144607c7abf45337bdb7681f8, with no subsequent operational mutation. [Final evidence and retained diagnostics](evidence/experiment-a-git-state-v03/verification.json). No model calls, attempt2, pilot or H access; stop for Chris's separate approval.
