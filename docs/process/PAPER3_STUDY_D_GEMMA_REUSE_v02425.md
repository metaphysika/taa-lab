# Study D v02425 — serving-only pair recovery FOR REVIEW

No launch is approved. Pair and virtue each require separate owner approval of
this new exact commit after review. The v02424 once-only launch is consumed;
its STOP, ledger, evidence and trained adapters are preserved, never reset.

## Failure and restored assets

v02423 replaced the 121,758-byte frozen evaluator plan with an administrative
stage summary under the same plan.json name. stages.json was also replaced.
The regenerated integrity index authenticated those replacements; the comparison
wrongly exempted both files. Preparation and review missed this regression.
v02424 therefore trained both full arms and loaded their adapters, then failed
in install_frozen_bundle() on missing bundle_sha256 before acquisition. This is
an asset regression, not a scientific null or format failure. No acquisition,
transfer or scoring ran. v02424 contributes no outcome results; its only reuse
is the source of the completed contrary and neutral adapters and training proof.

Every one of the 18 inherited v02420 asset files is now byte-identical, INCLUDING
plan.json, stages.json, MAC_COMMANDS.md and integrity.json. The original
plan.json is 121,758 bytes; stages.json is 2,872 bytes. There are no exemptions.
New administration uses stage-plan-v02425.json, projections-v02425.json,
MAC_COMMANDS-v02425.md and integrity-v02425.json. The old files remain frozen
historical artifacts: their older model/engine/budget/approval text does not
configure or authorize v02425. The versioned policy and active new index do.

The independent inherited-byte contract pins every original file hash, including
its original index. Required-key/type/count checks cover evaluator plan, bundle
sources, cases, fixture keys, acquisition and transfer cases, training rows/order,
stop proof, pinned config, token fixture, logging and both old/new metadata
indexes. Bundle source hashes must agree with the original plan. A regenerated
new index alone cannot authorize a replacement of any inherited file.

## Source adapters and read-only verification

Source commit 87acef174a03efb266fd57c12e0add13c9426ec8, app
ap-KAVCSaqESVAEvxyYV55QNG. Completed training per arm: 250 steps, 2,000 examples;
contrary 326,496 tokens / loss 0.01723; neutral 298,272 / loss 0.02243.
Coverage 410 modules / 61,214,720 trainable parameters, source sampler/KV/handoff
PASS. Source failure-record training_authorized=false does not erase this
completed, owner-approved full training. All 4 uploads / 104 extracted files
and their 108 hashes remain unchanged; private archive/weights stay out of Git.

Mount taa-study-d-gemma-v02424-private-adapters at /adapters READ ONLY for pair,
using pinned Modal 1.6.2 read_only() (server mount flag AND client write guard).
The old public evidence, CPU and speed Volumes are also mounted read-only.
Resource lookup is inside remote functions; imports/serialization do not hydrate.

Before any GPU reservation/submission, the CPU controller verifies the pinned
24-file public v02424 training/failure evidence set, its original commit,
250 steps / 2,000 examples / exact token counts, training/LoRA settings,
coverage, masks, model revision and absence of scientific requests. For each
/adapters/science/{arm}/final it checks the training-time checkpoint-integrity.json
arm, complete/scientific flags, exact final file roster and every file SHA-256.
It also checks adapter config against the pinned base and LoRA settings. Hashing
streams in 1 MiB chunks to fit the existing small CPU controller memory.

Publish both proofs, full adapter file hashes, sizes, checkpoint-index hash and
public training-record hash durably into NEW pair/adapter-provenance/*.json
BEFORE claiming the new reservation or spawning either GPU worker. Each worker
re-verifies against that published proof before vLLM loads. Missing files,
extra files, symlinks, mismatched hashes, incomplete/wrong-arm checkpoints or
training/config mismatches stop. There is NO pair training call or fallback.
The original public training metadata did not hash private weights; this new
pre-load receipt is their first external hash binding, not an invented old one.
The actual remote private files have not been inspected during offline prep.

The frozen Serving class, seeds, request loop, histories, sampler guard, graphs,
retained prefixes, post-capture KV check, acquisition, transfer and scoring stay
unchanged from v02424. The same post-training body is extracted into a callable
production function; AST checks hold its acquisition/schedule/episode code
identical. Pair skips training only. Virtue still trains its own 2,000-example,
one-epoch adapter, with unchanged LoRA/optimizer and restored assets.

Private source adapters are not copied, downloaded, shared or written by pair.
They stay read-only and retained on a stop. Virtue writes/deletes its own new
private adapter as before. At full study end, deletion of the read-only v02424
source adapters still requires a separate owner-reviewed CPU cleanup with
before/after hashes and deletion receipts; this serving script cannot delete a
read-only source. The study-end deletion commitment remains, not deployment.

## Budget and timing

Owner-reconciled dashboard: $10.93 used / $19.07 remaining. Displayed increase
$4.08 since $6.85 covers the intervening interval, not an itemized per-app invoice.
Prior actual spend is not refunded or reset. The cumulative cap stays $36;
monthly credit refreshes never reset cumulative Study D spend. No card is attached.

Pair per-arm software guard 4,800 s, Modal timeout 5,000 s. Existing reservation:
2 × (5,000 + 120 startup + 2 idle) × $3.20/3,600 + $0.75 = $9.855778.
This is about $9.86, not $9.47; no rate, allowance or timeout is silently cut to
match the rough estimate. Target ceiling is $9.86, with full precision admission.
Virtue remains 8,800 / 9,000 s and $8.483444 (ceiling $8.49), separately approved.
Total future reserves $18.339222; actual plus reserves $29.269222, cumulative
headroom $6.730778. Current credit after pair reserve $9.214222. Only the current
stage must fit current credit; all remaining reserves still fit the cumulative
cap. Virtue refreshes actual spend/credit at its later separately approved launch.

Warm-cache pair projections remove training and its load: same measured serving load
305.100 s, generation 36.2 tokens/s and provisional 300 s allowance. Contrary
nominal 1,994.7 / 1.25× stress 2,493.4 s, stress spare 2,306.6 s. Neutral
2,348.3 / 2,935.4 s, spare 1,864.6 s. Adapter verification is provisionally inside
the existing allowance, not a new measured cost. Skipping training also removes
its incidental HF base-weight cache warmup. The serving-only container may
download base weights again; 305.100 s was measured after training, so is not a
cold-start guarantee. An additional conservative sensitivity adds the earlier
543.607 s full training-load time (including download/load), without pretending
it is a measured serving-only download. Cold-cache stress is 3,172.9 s contrary
/ 3,614.9 s neutral, leaving 1,627.1 / 1,185.1 s inside the same 4,800 s guard.
No base-weight cache or extra resource is added. Virtue's two training-rate
projections remain unchanged. Short-output speed extrapolation and 1.25 stress
are not confidence bounds; full 4,096-token tails do not fit. Stop/incomplete
planned-denominator bounds are retained, with no case/repeat cuts or repairs.

Fresh namespace taa-study-d-gemma-v02425-{budget-once,evidence,private-adapters}
and v02425 per-stage local markers. Source Volumes/ledgers remain untouched.
Pair launch window ends October 26 01:00 UTC exclusive; virtue November 9
01:00 UTC exclusive. Original CPU PASS, selected speed evidence and complete
reviewed pair closure remain required. Virtue is blocked until pair COMPLETE,
audited/reviewed and separately exact-commit approved. No automatic continuation.

## Free CI and Mac review

1. All 18 inherited bytes and required schemas checked independently of the new index.
2. Isolated CPU full post-training rehearsal calls the production function at
   install_frozen_bundle(), uses the REAL staged assets and frozen canonical
   replies instead of vLLM, then actual acquisition/gates/132 transfers per arm,
   parser/scorer, bounds and reports. All three arms run; no training or model
   generation. The real v02424 asset folder MUST reproduce KeyError bundle_sha256;
   v02425 MUST complete 396 scripted transfers. These are CI data, not results.
3. Adapter hash/training proof corruption tests, no-retrain/no-source-commit stop,
   unchanged science/Serving AST and unhydrated serialization with server read-only
   mount inspection. The pinned tiny CPU rehearsal remains as a training diagnostic
   for prospective virtue; it is not a new Modal CPU receipt or GPU verification.

Mac commands: studies/formation-study-d-gemma-stages-v02425/MAC_COMMANDS-v02425.md.
Only after new exact-commit approval and BOTH CI pass: current billing, offline
preflight, then ONE caffeinate/spawn submission; wait for acknowledged SUBMITTED
app/call IDs before closing laptop. Existing/ambiguous markers require review,
not restart. This preparation performs no Modal calls, GPU, downloads or spending.
