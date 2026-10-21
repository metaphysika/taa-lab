# Study D adapter inventory — 21 October 2026

[DESCRIPTIVE] Record-based inventory by Sol. This reports public pre-load verification receipts, not a successful live listing or a new inspection of private adapters. No adapter was downloaded, mounted, read, shared or deleted. No Modal function, app, sandbox or compute job was launched.

## Sources and attempted live listing

[DESCRIPTIVE] Synced main: `57253f9303969c199db5b5c5c91c2a6fc0812187`. The already committed public return `results/gemma-v02429-virtue-return-001.zip` has SHA-256 `40a5eb78fac84c9624f1ac756b12ca4ba195c17a3e7e602a0d0e8f95e1babeaa`, independently checked locally. Its public receipts were compared field-for-field with the [PR #6 deletion-plan manifest](https://github.com/metaphysika/taa-lab/blob/af6abe99548c7f6b0d7c8d22d1c6b4aa7bb1641e/studies/formation-study-d-analysis-v02430/private-adapter-deletion-plan.json); all three final-checkpoint records match. Fetching that branch for read-only inspection did not merge, rebase or modify PR #6.

[DESCRIPTIVE] The Modal SDK was absent. Modal 1.6.2 was installed only into a temporary local virtual environment. Inspection of its `volume ls` and `Volume.iterdir` implementation established metadata RPCs rather than remote function execution. One listing was attempted:

```bash
timeout 40 /tmp/taa-modal-inventory-venv/bin/modal volume ls taa-study-d-gemma-v02424-private-adapters / --json
```

[DESCRIPTIVE] It exited 124 at the local 40-second timeout without output. No successful live metadata result or absence claim follows. The transport/authorization cause is unknown. No alternative compute-based inventory was attempted. The SDK used the inherited credentials and default environment selection; no credential values or files were inspected. The intended historical workspace/environment was not independently resolved by a successful live response.

## Final scientific adapters already on record

[DESCRIPTIVE] Paths below are relative to named Modal Volumes. The logical `volume/path` notation is not a public download URL. Sizes and hashes are those in the saved receipts, not newly measured on Modal.

### Contrary

[DESCRIPTIVE] Volume: `taa-study-d-gemma-v02424-private-adapters`. Directory: `science/contrary/final`.

| File | Recorded bytes | Recorded SHA-256 |
|---|---:|---|
| `README.md` | 5,196 | `0d7a307737986b63085c0c6efc7f1a8ff3507f226e4d30fb2f506fc8e393eae3` |
| `adapter_config.json` | 1,144 | `ee54de04f7c36d143b9b5e9daf80094915e7b19618bfb41e77dd5a6ecfd38859` |
| `adapter_model.safetensors` | 244,980,744 | `00e8e3a249aaad138ed7e697408e49370cfe44739eadd6dbcaceef01ff93ae5d` |
| `checkpoint-integrity.json` | Not recorded in this receipt | `08b856ac12cc52ba4a94a572e2711c6d35ffdabc93aec72e9e879701be66eee1` |

[DESCRIPTIVE] Receipt inside the public ZIP: `prior-pair/pair/contrary/reused-adapter-verification.json`. Saved status: PASS. Source training commit: `87acef174a03efb266fd57c12e0add13c9426ec8`. The receipt says the original private training-time index and hashes were first externally bound by this pre-load receipt; it is not a fresh cryptographic verification of today's retained files.

### Neutral

[DESCRIPTIVE] Volume: `taa-study-d-gemma-v02424-private-adapters`. Directory: `science/neutral/final`.

| File | Recorded bytes | Recorded SHA-256 |
|---|---:|---|
| `README.md` | 5,196 | `0d7a307737986b63085c0c6efc7f1a8ff3507f226e4d30fb2f506fc8e393eae3` |
| `adapter_config.json` | 1,144 | `ee54de04f7c36d143b9b5e9daf80094915e7b19618bfb41e77dd5a6ecfd38859` |
| `adapter_model.safetensors` | 244,980,744 | `0d92f06cf0d1429ade1e28490245def4a48b51b5675e989deffbec53b346d8af` |
| `checkpoint-integrity.json` | Not recorded in this receipt | `1ef4be1712a75bc6596e3717ad047844c5c61807cd96a02b8acf550e60060b97` |

[DESCRIPTIVE] Receipt inside the public ZIP: `prior-pair/pair/neutral/reused-adapter-verification.json`. Saved status: PASS. Source training commit: `87acef174a03efb266fd57c12e0add13c9426ec8`. The receipt says the original private training-time index and hashes were first externally bound by this pre-load receipt; it is not a fresh cryptographic verification of today's retained files.

### Virtue

[DESCRIPTIVE] Volume: `taa-study-d-gemma-v02428-private-adapters`. Directory: `science/virtue/final`.

| File | Recorded bytes | Recorded SHA-256 |
|---|---:|---|
| `README.md` | 5,196 | `0d7a307737986b63085c0c6efc7f1a8ff3507f226e4d30fb2f506fc8e393eae3` |
| `adapter_config.json` | 1,144 | `ee54de04f7c36d143b9b5e9daf80094915e7b19618bfb41e77dd5a6ecfd38859` |
| `adapter_model.safetensors` | 244,980,744 | `a2e04e6231908d15c5b8fc78472da534a23a213aa62ca9c29e420d53af3006f7` |
| `checkpoint-integrity.json` | Not recorded in this receipt | `10ed7ae89d403c4a6b34808cc9a4e6168e166603eb8cf0d28403c8bd44630259` |

[DESCRIPTIVE] Receipt inside the public ZIP: `virtue/virtue/reused-adapter-verification.json`. Saved status: PASS. Source training commit: `0c4946574f32d305b8e4272459a004d6cb460fc3`. The receipt says the original private training-time index and hashes were first externally bound by this pre-load receipt; it is not a fresh cryptographic verification of today's retained files.

## Aliases, incomplete coverage and retention

[DESCRIPTIVE] The v02426 neutral continuation reused `taa-study-d-gemma-v02424-private-adapters/science/neutral/final` read-only. It is not a fourth trained final adapter. The name `taa-study-d-gemma-v02426-private-adapters` occurs in unused code but its existence is unconfirmed; do not infer another stored copy from that name.

[DESCRIPTIVE] The three listed final payloads total 734,961,252 bytes (about 0.684486 GiB), excluding the three integrity indexes. This is a subtotal from recorded file sizes, not a total Volume measurement. Intermediate checkpoints, optimizer/training artifacts, diagnostic adapters, snapshots, other Volumes and any local copies have not been inventoried live. Their absence is not established. The read-only listing returned no current file names, index sizes, timestamps or total stored bytes.

[DESCRIPTIVE] The approved retention state is unchanged: adapters remain private; deletion waits through Paper 3 outline review and requires separate explicit owner approval of the exact manifest and named Volumes. All evidence, public receipts, ledgers and once markers remain intact.

## Storage cost visibility

[DESCRIPTIVE] [Modal pricing](https://modal.com/pricing), retrieved 21 October 2026, lists Volumes at **$0.09/GiB-month**, including **1 TiB/month free**. This is a public tariff, not account billing evidence. The [official Volume CLI reference](https://modal.com/docs/cli/latest/volume) documents the metadata listing command used above.

[INTERPRETATION] At that headline rate, only the three recorded final payloads would represent about $0.062/month before included storage and any applicable account terms. This is not a current charge estimate for all retained Study D artifacts: the account-wide allowance, actual retained contents, retention duration and any billable excess are unknown.

[DESCRIPTIVE] **Visible current storage charge: unavailable.** No current billing dashboard or itemized storage record was retrieved. The prior owner attestation of $25.32 used / $4.68 remaining is an aggregate historical dashboard total after v02429, not a storage invoice or current balance. No new paid operation was authorized or performed.
