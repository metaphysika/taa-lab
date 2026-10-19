# v02424 pair — STOP_FOR_REVIEW before acquisition

Reviewed commit: `87acef174a03efb266fd57c12e0add13c9426ec8`.
App: `ap-KAVCSaqESVAEvxyYV55QNG`.
Call: `fc-01M5AKR53RPMGW10H77Q201AR8`.
Owner reports one pair submission October 19, 2026, 12:35–1:28 pm CDT.
Local receipt is 17:35:08 UTC; submission acknowledgement is 17:36:03 UTC.
These are distinct milestones. Owner also reports an earlier preflight never
spawned and an owner-approved retry; no separate first-preflight receipt was
supplied here, so that detail remains attributed to the owner.

| Arm | Training | Examples | Tokens | Reported final training loss |
|---|---|---:|---:|---:|
|Contrary|COMPLETE, 250 optimizer steps|2,000|326,496|0.01723|
|Neutral|COMPLETE, 250 optimizer steps|2,000|298,272|0.02243|

Both losses appear in their preserved training-process logs. Coverage PASS in
both arms: 410 modules / 61,214,720 trainable parameters, architecture-conditioned
v_proj coverage. Sampler and KV checks PASS; each conservative KV margin is
0.100 GiB. Each event journal records serving load and verified adapter handoff,
with no scientific request events. These were full approved training arms,
not diagnostic smoke training. The inherited failure field training_authorized=false
does not negate the completed authorized training.

Both workers then raise KeyError: 'bundle_sha256' in install_frozen_bundle()
(runtime.py line 640 -> base_runtime.py line 40), before acquisition starts.
The controller separately records RuntimeError: acquisition interrupted or
deadline; no transfer. Both worker reports and the controller failure retain
STOP_FOR_REVIEW / no_restart=true. There is no completed pair report or
acquisition decision. No acquisition, transfer, scoring or scientific outcome
results ran. This is an incomplete scientific stage due to a pre-acquisition
software stop, not a scientific null or a format-gate result.

All four uploads are preserved byte-for-byte, with all 104 archive files safely
extracted. ZIP CRC PASS. SHA-256 inventory covers all 108 received/extracted
files. The carried 36 CPU and 26 prior-speed files are byte-identical to the
already preserved returns; the submitted asset-manifest hash matches v02424.
The ZIP, safetensors and full tokenizer are kept locally and ignored by Git.
No adapters from the private scientific Volume were downloaded, modified or
deleted by this chat. Review-stop retention policy remains in force; remote
retention has not been independently checked.

Submission billing: $6.85 used / $23.15 left; cumulative cap $36; reservation
$16.255777778. Post-attempt actual spend and updated dashboard totals have not
been supplied. Wall time and reservation are not an invoice or a refund.

Record only. No study code changes, fix preparation, relaunch, training,
Modal API call, ledger reset or Volume modification. Virtue and any pair rerun
remain unapproved. Await Claude's diagnosis/rerun design and owner review.
