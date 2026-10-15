# Owner setup checklist — prepared free base-format gate, NOT APPROVED TO RUN

OpenAI is closed; every paid D design is archival. Free LoRA is primary, but
**this next proposed step is base inference only, zero training**. The exact
notebook tests Llama 3.1 8B Instruct and Qwen2.5 7B Instruct on 17 frozen cases,
two repeats per model. Do not start a runtime, install dependencies, download
weights or execute cells until you separately approve this gate.

## Exact files to review

- [Notebook](study_d_base_format_gate_v0248.ipynb): one file, self-contained,
  credential-free evaluator and case bundle; all execution flags false.
- [Frozen fixture keys](frozen-fixture-keys.json): original answer keys and
  canonical scripted correct traces for all 17 cases; never shown to the model.
- [Thresholds](thresholds.json): fixed parser/action/closure pass criteria and
  W-servility headroom rule; substantive rates descriptive only.
- [Sample and order](fixed-sample-and-schedule.json): exact source cases, source
  hashes and two-repeat schedule, reused identically for both models.
- [Review integrity index](review-integrity.json): SHA-256 of each review file,
  plus the source/evaluator and neutral-data correction manifest.

The fixture keys and thresholds are fixed for this proposed diagnostic. No
model has produced any gate data. Do not change cases/keys/thresholds in response
to a model result or silently substitute a different notebook revision.

## A. Account preparation you handle yourself (no model/GPU execution)

1. **Kaggle:** create/sign in to your free account and verify your email. In
   account settings, complete **Phone Verification** if required for GPU/internet
   access. The official staff guidance restricts GPU access to phone-verified
   accounts. Resolve any verification problem through Kaggle; no account cycling
   or verification workaround. Do not select/start a GPU yet.
2. **Hugging Face:** create/sign in to your personal account. Open the
   [Llama 3.1 8B Instruct page](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct),
   read/accept Meta's license and request access if prompted. Wait for actual
   access under that same HF account. Do not download weights as an access test.
   [Qwen2.5 7B Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) has its
   own model card/license; review it too. Neither access state has been checked
   by the assistant.
3. In [HF Settings → Access Tokens](https://huggingface.co/settings/tokens),
   create a **read-only/fine-grained** token that can read the public gated
   Llama repository you have been granted access to, plus public Qwen files.
   Include the public-gated-repository read permission if the UI requires it.
   No write, upload, model-management or paid inference permissions are needed.
   A token does not grant a license your account lacks.
4. Keep that value private. **Do not paste it into chat, notebook code, a data
   cell, outputs, a Kaggle Dataset, `keys.env` in this repository, a Git commit
   or a screenshot.** The notebook needs only the secret name `HF_TOKEN`.
   No OpenAI, Anthropic, Gemini or Groq key and **no Kaggle API key** is needed
   for the proposed UI workflow. Do not upload any existing credential file.

Official references: [Kaggle GPU verification guidance](https://www.kaggle.com/discussions/product-feedback/268333),
[HF token permissions](https://huggingface.co/docs/hub/security-tokens),
[HF gated-model access](https://huggingface.co/docs/hub/models-gated).
These are public instructions, not an account check or guarantee of free quota.

## B. Only AFTER separate approval of this exact base gate

5. Import the reviewed `.ipynb` into **one private Kaggle notebook** using the
   notebook UI. Do not attach the D training dataset; the small frozen base
   sample is embedded. Check privacy stays private. Do not create a public
   model endpoint, tunnel, server or shared weights. This is not permission
   to run a second copy on Colab as well.
6. In Kaggle's **Add-ons → Secrets** (or the current Secrets panel), add the
   label `HF_TOKEN` and put the token value in that private secret field. Enable
   that secret for this notebook. Never place the value in source. After later
   approval, the guarded setup cell reads `UserSecretsClient().get_secret` into
   process memory for the standard HF downloader; it neither prints nor writes
   the token into run evidence. No credential is read during preparation.
7. Confirm the session is **free** and note the displayed remaining GPU quota.
   Enable internet for dependency/model downloads and select an available free
   **P100 or T4-class** GPU with at least 14 GiB visible on device0. The notebook
   uses device0 only; if T4 x2 is allocated, record that and do not assume the
   quota charges only one device. Never select paid overflow/compute units.
   Record the UTC GPU allocation-start time when the UI allocates the session;
   allocated time includes downloads/setup/idle time, not just inference.
8. In the first configuration cell, only after your actual approval, set:

   | Field | What you enter |
   |---|---|
   | `APPROVAL_GRANTED` | `True` |
   | `ALLOW_DEPENDENCY_INSTALL` | `True` |
   | `ALLOW_WEIGHT_DOWNLOAD` | `True` |
   | `ALLOW_GPU_USE` | `True` |
   | `ALLOW_SECRET_USE` | `True` |
   | `CONFIRM_FREE_RUNTIME` | `True`, only after confirming free allocation |
   | `APPROVAL_RECEIPT` | A non-secret reference/date identifying your explicit base-gate approval |
   | `GPU_ALLOCATION_STARTED_UTC` | Actual ISO UTC timestamp, e.g. the UI allocation start (no invented time) |
   | `GPU_QUOTA_BEFORE_HOURS` | UI remaining quota, or `None` if not displayed |

   Keep after-quota/end-time fields unknown until you have those observations.
   Editing these approved configuration fields changes the notebook file hash;
   retain the original reviewed hash and record the approved configuration,
   while leaving the embedded evaluator/cases/thresholds unchanged.
   Do not change the two models, source bundle, case list, threshold values,
   output ceiling, step limit or generation defaults.
9. Execute the notebook **once**, cell by cell. Setup validates frozen scripted
   keys before model operations; this does not train or provide those keys to
   the model. A mismatch/access failure/OOM/time/context/unclosed-generation guard
   means stop and preserve evidence, **not** rerun, repair, substitute a model,
   reduce the cases or add format coaching. A completed model format failure
   is reported while the other expressly planned model is still evaluated,
   unless an independent runtime guard stopped the session.
10. At the end, keep the credential-free report and raw evidence privately,
    record displayed quota after use and the actual allocation end, and promptly
    **stop/disconnect the GPU**. The report distinguishes generation CUDA seconds,
    model/load/wall seconds and platform quota. Missing UI/end observations remain
    unknown; do not claim CUDA time equals quota hours or that allocation stopped
    just because inference ended. If the kernel has ended, record the final UI
    values in the report accompanying the saved JSON; do not restart inference
    merely to fill accounting fields.
11. Report both models' parse/action/closure metrics, descriptive substantive
    rates, headroom exclusion/bounds, GPU/quota timing and any exact stop. Then
    stop for owner review. **No LoRA training, acquisition/transfer study,
    additional model, quality retry, paid job or public upload follows.**

Kaggle secret API reference: [official Kaggle CLI notebook guidance](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md).

## Colab alternative (choose it instead of Kaggle, not an extra run)

After approval, the same notebook can run privately in Colab. You handle the
Google account and the **Secrets** panel: add `HF_TOKEN` and grant notebook
access. The guarded code uses `google.colab.userdata.get('HF_TOKEN')`, not a
literal key or a Drive credential file. Select free GPU only and record the
same timing/config fields. Free quota/hardware are dynamic, so it may be
unavailable; do not buy units or run a second platform to evade limits.
[Colab resource FAQ](https://research.google.com/colaboratory/faq.html).

**Current stop: review these files/checklist and approve nothing implicitly.
No notebook execution, weight download, GPU use or training has occurred.**
