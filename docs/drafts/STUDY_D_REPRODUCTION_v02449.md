# Study D stored-evidence reproduction v02449

1 November 2026. **PASS: both stored-evidence analyses reproduce.** This is the
$0 reproduction record for Master Plan v3.0, Path and program, step 2, "Recover
and reproduce Study D from stored evidence." Source: main
`2470537f85e2b03ff87556ba39a552a9aee024cf`. No new scientific observations.

## Inventory

[Complete inventory](STUDY_D_INVENTORY_v02449.tsv): 1,555 tracked files and 2,294
non-directory members of ten stored ZIPs, each with path, byte size and SHA-256.
File hashes use Git's source bytes, not Windows checkout line endings. Selection
is every tracked path matching `(?i)study[-_ ]d|^results/gemma-v024`, union the
repository inputs named by the v02430/v02431 manifests. Repeated evidence copies
remain separate inventory entries; counts are not independent observations.

- `studies/` (1,351 files): gate/training plans, staged datasets and frozen
  evaluator bundles, source pins, returned base/engineering evidence, public
  training/adapter receipts, result audits and the private-adapter deletion
  manifest. Earlier Llama/Qwen diagnostic and failed-stage records remain stored.
- `results/` (11 files): five v02425-v02429 return ZIPs, four v02430 primary
  outputs and two v02431 exploratory outputs. The primary manifest pins all
  347/396/569 members of the v02425/v02426/v02429 returns and 77 repository inputs;
  replay verifies them and the inherited evidence. All ten inventoried ZIPs pass
  CRC checks, including the five earlier archives under `studies/`.
- `scripts/` (117), `formation/` (19), `tests/` (26), and `docs/process/` (31):
  analysis, admission, sampler and runtime code; offline tests; gates, execution
  reports, v02430 analysis/deletion plan and v02432 summary. Execution scripts
  were inventoried, not launched. `docs/REPRODUCE.md` covers older gateway studies;
  the Study D commands are in its v02430/v02431 process records.

## What reproduced

The unchanged `scripts/study_d_analysis_v02430.py` independently replayed all
**394/396** planned transfer results, including exact first replies, full
histories, seeds and frozen scoring. Counts are contrary 132, neutral 130, virtue
132. All three acquisition gates reproduce at 100/100; public training receipts
agree on 2,000 examples and 250 steps per arm.

| Published quantity | Reproduced result |
|---|---|
| W executed-servility bounds, contrary / neutral / virtue | 84.375% / 12.50-51.5625% / 0-6.25% |
| D-P2, contrary minus neutral | +32.8125 to +71.875 points; SUPPORTED |
| D-P3 / D-P4 / secondary D-U | INCONCLUSIVE / INCONCLUSIVE / AGAINST |
| D-P2 marginal 97.5% lower limit | 14.43 points, below the 15-point threshold |

`scripts/study_d_exploratory_v02431.py` also reproduces: neutral S 12.50-18.75%,
D-P3 benefit +6.25 to +18.75 points, D-P4 +46.875 to +65.625 points. These remain
**EXPLORATORY, POST-HOC**; no primary verdict changes. All six generated files
match the stored outputs after CRLF-to-LF normalization, including audit
provenance, case tables, confidence intervals and bootstrap results. Saved-field
checks also confirm the summary's 40 neutral unfinished episodes ending in the
literal tool string `"null"`, 29 with substantive requirements completed, and
spontaneous shading 20/20 contrary, 0/20 neutral, 0/20 virtue.

## Replay conditions and limits

Local Python 3.12.14, standard library, CPU only; the documented CI uses 3.11.
An ordinary Windows run fails on CRLF pins, then default decoding and path
serialization. A temporary Git archive with `core.autocrlf=false` and
`core.eol=lf`, explicit `-X utf8`, and forward-slash path serialization resolves
these platform differences without changing any source, pin or scientific rule.
In that temporary snapshot, run each script with a separate empty output folder:

```powershell
$wrapper = "import pathlib,runpy,sys; original=pathlib.PureWindowsPath.__str__; pathlib.PureWindowsPath.__str__=lambda path: original(path).replace(chr(92),'/'); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')"
python -I -X utf8 -c $wrapper scripts/study_d_analysis_v02430.py --output <empty-primary-folder>
python -I -X utf8 -c $wrapper scripts/study_d_exploratory_v02431.py --output <empty-exploratory-folder>
```

Two interrupted neutral units (one W, one U) remain missing under no-resend;
neither was reconstructed. Neutral noncompletion and virtue malformed replies
still limit interpretation. No informative null or across-training replication
is established. Training, generation and scientific checkpoint integrity were
not rerun or independently reverified from weights.

## Recorded adapter availability

The [deletion manifest](../../studies/formation-study-d-analysis-v02430/private-adapter-deletion-plan.json)
records contrary and neutral at
`taa-study-d-gemma-v02424-private-adapters/science/{contrary,neutral}/final`, and
virtue at `taa-study-d-gemma-v02428-private-adapters/science/virtue/final`.
Each scientific adapter weight file is recorded as 244,980,744 bytes, with
config, README and checkpoint-index hashes. v02426 reused neutral read-only;
`taa-study-d-gemma-v02426-private-adapters` is only an unconfirmed code name.

The recorded state is private retention with deletion on hold pending outline
review and separate exact approval. There is no deletion/absence receipt here;
**current Modal existence, intermediate checkpoints and extra copies are
unverified**. Scientific adapter/base weights are not in this repository;
public ZIPs do contain small random-model CPU-rehearsal weights, not the trained
Gemma checkpoints. The frozen base revision is
`google/gemma-4-31B-it@842da3794eaa0b77d5f08bae87a17459d91ff475`.

No model call, Modal operation, live inventory, weight download, training,
secret access or workflow dispatch occurred. Cost: **$0**. Existing evidence
and `results/` were not changed.
