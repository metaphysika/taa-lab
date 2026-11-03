# Step 4 internal-pass plan v0.24.56

EXPLORATORY proposal for Chris's later approval. Preparation cost $0. No execution is authorized. PR #82 fixed the tool-observation omission; the earlier report is retained as history. The internal pass remains blocked by the two fact contrasts with misaligned token positions, behavioral eligibility, validation material and a prospective intervention specification.

## Sources and decisions

Controlling source: [Bridge Specification v0.2, revision 3](https://app.notion.com/p/40b5b2e9471081fb892ded948e696e89), read 2026-11-03, especially Sections 2, 4–6 and 8. Cost source: `docs/process/STEP4_COST_TIMING_v02456.md` at `5dcb659cdfd471498b3788a850b66c7ec84755ae` (PR 81). Harness contract: `exploratory/step4_harness/README.md` at `eac7c9bc9554a1ecf89efae6402a5aa32c3cda6b` (PR 82). Neither open PR is silently incorporated into this branch.

Chris must approve the exact execution commit, checkpoint inventory, transport parity, calibration material and split, layer/strength grid, validation margins, null seeds, stopping rules, storage allowance and staged dollar cap. He must settle whether the candidate within-checkpoint stated-judgment test in Bridge Section 4 is adequate before internal execution. Its adequacy remains an open design question. No diagnosis or repair-training approval follows from this plan or its merge.

## Token alignment: evidence visible; two fact contrasts remain misaligned

The local tokenizer audit uses the actual fixed `runner.episode` history from PR #82
(5818aad9) and calls PR #83's `modal_backend.render` (ef49d442), which invokes the
Study D runtime's `prompt_ids`. Scripted and generated observations are user
messages containing `json.dumps({"last_tool_result": result}, ensure_ascii=False)`;
assistant turns remain compact JSON or raw reply strings. Probe questions remain
separate user messages. The audit measures initial action decision points.

All 16 fact and 16 parcel contrasts are visible, and differences remain within the
expected evidence/detail fields. All 16 parcel contrasts and 14 fact contrasts
are positionally aligned. The two fact contrasts in family 4 remain misaligned;
the gate is **NOT READY** for patching that requires aligned spans. No case wording
or hashes were changed. The JSON report enumerates token counts, differing spans
and both decision-point positions for every contrast, plus all 48 input counts
and rendered hashes. Positions are zero-based, spans half-open, and the decision
point is the final input token before sampled output. A measurement is distinct
from a passing alignment gate; the audit exits nonzero for these failures.

The earlier dropped-observation report at commit
7269d51cd95bf401cb1444a0e66a75d7379fd4a3 is retained byte-for-byte as
`STEP4_TOKEN_ALIGNMENT_DROPPED_v02456.json`. It measured all 32 contrasts missing
under the old tool-role transport. The still earlier blocked report at 869b8bba
recorded missing Jinja2. Those historical findings do not describe the fixed runner.
The current audit records pinned tokenizer/runtime/template hashes and installed
package versions. It uses only authorized local tokenizer files, with no weights,
model calls, GPU or Modal operations.

```powershell
C:/Users/lahn0/.cache/taa-step4-venv/Scripts/python.exe scripts/step4_token_alignment_v02456.py --tokenizer-dir C:/Users/lahn0/.cache/taa-step4-tokenizer/842da3794eaa0b77d5f08bae87a17459d91ff475 --output NEW_ALIGNMENT.json
```

## Capture and engine

Proposed capture roster: all 48 conditions × base, neutral, contrary and virtue = 192 deterministic input states (derived); no inference repeat is needed for a fixed prefix. Behavioral actions and forked questions still have their approved repeats. Record deterministic settings, engine/version, tokenizer hashes, exact rendered input, checkpoint/base/adapter hashes and attention mask. Verify the original read-only prefix and record copies before capture.

Use a separately reviewed Transformers/PyTorch eager forward backend with per-layer residual hooks and adapter loading. The existing behavioral runner and a generation-only serving engine are insufficient evidence that hidden states or intervention hooks are exposed. Freeze evaluation mode, precision and hook placement. Capture the residual after each decoder block plus embedding output at the final input token; distinguish pre-block from post-block states in metadata. Retain decisive-span residuals in a second explicitly sized artifact for patching; final-token captures alone cannot patch earlier fact positions. A CPU/offline smoke fixture may verify hook indexing, but cannot validate Gemma intervention behavior.

Storage formula (derived): final-token bytes = 192 × (L+1) × H × b, where L and H must be read from the verified real model config and b is bytes/value. Illustrative assumptions L=64, H=5376, b=2 give 134,184,960 bytes (about 128 MiB). These architecture values are assumptions, not checked Gemma dimensions. Full-prefix storage is this amount times mean token length and is excluded; prefer streaming only needed fact spans. At assumed four span tokens, block-only patch payload adds 192 × 64 × 4 × 5376 × 2 = 528,482,304 bytes (about 504 MiB). Add metadata, probe artifacts and intervention outputs separately; confirm available disk before approval. No weights or activation captures were loaded here.

## Readouts and validation

Train separate low-capacity linear fact and permissibility readouts for each checkpoint and layer. Labels come from SOURCE facts and independently reviewed input permissibility, never contrary actions. Split by pair/family before fitting so twins and parcel variants cannot leak across train/test. Eight fact pairs provide weak generalization coverage: use family-held-out folds for exploratory estimates, and require separately drafted, independently labeled calibration/validation tasks before claiming a reliable readout. Borderline development/held-out material must retain its behavioral split and cannot become convenient probe-training data.

Use identical probe capacity, regularization search and folds on each checkpoint. Include Hewitt–Liang control tasks with seeded shuffled/arbitrary labels fixed per underlying case group, and unrelated-feature probes such as parcel identity. Report held-out label accuracy, class balance, selectivity above both controls, fold variation and uncertainty. Chris must prospectively fix minimum selectivity and equivalence margins on calibration data; none is selected from contrary test outcomes. Failure on a checkpoint is measurement failed there, never evidence against F1/F2/F3. Decoding is evidence of available information, not the checkpoint's actual judgment.

## Patching, steering and predictions

After validation, patch only aligned decisive-fact residual spans, in both donor directions within the same checkpoint and layer. Use frozen layer candidates selected with base/neutral development material; no contrary-based case or layer selection. Compare untouched, self-patch, decisive patch, parcel patch, seeded matched-norm random perturbation and an unrelated-contrast direction at the same layer. Match each null to the realized donor-minus-recipient norm. Measure fact/permissibility readout movement, actions, lawful-twin preservation, routine work and format validity separately. Earlier-span patching requires a fresh forward pass from that location and consistent downstream cache recomputation.

F1 predicts switching after fact patching in base/neutral with weaker switching in contrary, but F2/F3 also predict contrary invariance. That pattern alone stays unresolved. The further candidate evidence for F1 is a fact decodable at encoding but absent from later decision states where reference twins differ; this is not established as sufficient. Restating the fact cannot separate F1 and F2.

Steer the validated permissibility direction at the decision token. Freeze signed strength levels and layer candidates before held-out use. Calibrate on base/neutral development only, retain every tested dose, and compare checkpoints at both matched residual norm and matched achieved readout change. If those cannot be matched, report the comparison unavailable. F3 predicts a weaker contrary action effect than base and neutral despite comparable readout movement; F2 predicts a comparable action effect. Strong steering alone can override an unrelated pathway and cannot distinguish them.

On each checkpoint, steer and ask both independently worded forked questions. The answer must move beyond both same-checkpoint nulls, agree across wordings, and remain separate from the action branch. This is required within-checkpoint evidence of use for F2/F3. If absent, unrun or measurement-failed, classify unresolved. Even success concerns an elicited stated judgment and cannot prove what drove the original action. F2 additionally needs downstream fact sensitivity, pre-steering permitted readout/probes on wrongful inputs and the abstract-rule/simple-case checks against rule loss. F3 needs pre-steering not-permitted agreement despite compliance and selective restoration, while retaining the elicitation and acknowledge-then-comply alternatives.

## Direction comparison

Compute contrary-minus-neutral mean residual direction using fixed matched development inputs. Compare cosine overlap with checkpoint-validated permissibility, refusal (Arditi-style method), formatting and seeded random directions. Refusal and formatting contrasts need independent calibration material, balanced for topic, label and output length; malformed-versus-valid directions must not simply encode task difficulty. These assets and their validation are prerequisites, not available measurements.

Then compare ablations at matched layer and norm, with all null controls and lawful/competence checks. Support for a broad/persona-like contribution requires effects exceeding refusal, formatting and random controls, weak permissibility overlap under a prospectively fixed criterion, and held-out out-of-domain tone/self-description/values predictions. Borderline held-out compliance bears on global shift. Direction ablation alone shows causal influence and cannot identify a persona. Broad shifts can coexist with F1–F3; retain mixed classifications.

## Order and gates

First finish inventory and the behavioral pass. Inspect family-specific interface failures before mechanism work; known wrongful acts remain known, while absent completed actions remain not diagnosable. Capture may cover all planned inputs for inventory, but forked/internal readings on behaviorally non-diagnosable episodes stay in a separate descriptive stratum and cannot assign F1–F3. No contrary outcome selects cases: retain the full fixed roster and use behavioral results only to decide whether measurement, headroom and comparison quality justify the next stage.

If base/neutral development lacks borderline refusal headroom, stop that global-shift branch and report no usable test. If format failures dominate a family, stop its causal interpretation pending an independently reviewed interface check. If readout validation fails, stop interventions for that checkpoint/readout. If controls suppress lawful work or break format, record measurement failure. Only after validated capture/readouts run patching and steering; only then direction ablation. Persist after each cell/checkpoint, retain missing branches, failed attempts and uncertainty. No automatic resume or quality retry.

Report per family/checkpoint on planned denominators: F1, F2, F3, global, persona-like, mixed, unresolved and not diagnosable, plus separate measurement-failed test counts. Base and neutral failures receive the same diagnostic scrutiny. New seeds are required before reliability claims, and unseen-task repair comparisons with compute/data-matched generic repair are later H5 work.

## Cost and time: conditional staging

Measured in PR 81: 726 retained replies, 132 episodes and $3.75532210 billing-table sum. Derived historical proxies: 5.496 seconds/reply, 30.227 seconds/action episode, 361.140 seconds/startup and $3.107 per elapsed session-hour. These are amortized all-resource wall-time proxies, not eager-engine measurements, GPU tariffs or present pricing. They cannot price training or hooked forward passes empirically.

Proposed capture allowance assumes one historical reply proxy per input, four startups and three assumed 60-second switches: (192 × 5.496 + 4 × 361.140 + 180)/3600 = 0.745 hours and $2.31 (derived conditional). Applying assumed 0.5–2 sensitivity and 25% buffer gives 0.466–1.861 hours and $1.45–5.78. Eager hooks, prefill and storage may exceed this range; it is not a confidence interval or ceiling.

For a reviewable intervention sizing example, assume two layers and two active strengths. Decisive patch + random + unrelated + self gives four conditions; steering + random + unrelated at two strengths gives six: ten conditions per layer. Across 32 fact cases and four checkpoints this is 2560 intervention cells (derived). Each cell has one action continuation plus two forked probes, assumed 30.227 + 2 × 5.496 = 41.219 seconds: 29.31 hours branch work. Four startups and three switches give about 29.76 hours/$92.46 point, or 37.20 hours/$115.58 buffered point (derived conditional). Sharing captures does not demonstrate generation savings. Null seed replication, direction ablations, competence tasks, extra calibration, failed launches and storage are excluded and add cost. This illustrative full grid exceeds the owner's $50/month budget even before other spending; do not seek blanket approval for it.

Recommended first approval is a separately costed calibration/capture stage only. Then choose a smaller fixed intervention roster and exact branch count before seeing contrary intervention outcomes, or defer. For any approved roster use total hours = (N_capture × assumed forward seconds + N_action × 30.227 + N_probe × 5.496 + N_startup × 361.140 + N_switch × assumed switch seconds)/3600, then multiply by $3.107 and the stated uncertainty/buffer assumptions. Probe training wall time and eager forward timing are unmeasured; measure them in the separately approved calibration stage and replace proxies before later authorization.

Split approved work into independent sessions under the assumed six-hour limit, stopping new cells at five hours or earlier when reserve cannot cover the next cell and shutdown. A live owner monthly-balance check, exact commit, finite per-stage cap and durable worst-case reservations remain required. Historical daily $4.33 does not establish remaining monthly funds. No Modal/billing query, GPU work, model call, secret access, merge or workflow dispatch occurred in this preparation.

Local validation (2026-11-03): exact pinned episode history parity passed for 48/48 cases; pip check passed; run_fast_checks.py passed (424 unit tests and all scripted scenarios, 39.420 seconds) with PYTHONUTF8=1. The earlier default Windows output run passed the units but returned nonzero during the scripted stage; its log is retained outside Git. No hosted-CI result is implied.
