# Paper 3 Stage 1: client infrastructure

Stage 1 implementation and all five current neutral connectivity checks are
complete. Gate 1 is ready for Chris's review and awaits his written approval.
Luna and both Haiku models passed the original batch. The approved Gemini 3.1
Flash-Lite replacement passed after funding. Qwen on confirmed Groq Free passed
after the client-identification repair. All earlier failures remain preserved.
No Stage 2 work has begun.

## Approved scope

Chris approved new formation-specific clients, Python 3.9, and local commits on
`main` for him to push. His misconduct clarification and the approved Qwen
replacement for Llama are recorded in `PAPER3_BUILD_BRIEF.md`. Studies A–D have
not been built. The existing Paper 2 sources and results remain the reference
for those historical experiments.

## Clients and evidence

`formation/clients.py` provides `OpenAIChat`, `ClaudeChat`, `GeminiChat`, and
`GroqChat`, with `chat(system, messages)` returning the same first-JSON-object
parser used by the historical clients. A history contains user/assistant text
and ends with a user message. The new clients also offer a one-message `json`
convenience method. Historical client files and their `json` methods are untouched.

Sampling, effort, and thinking parameters are omitted. JSON is requested in the
neutral prompt; Gemini additionally requests the native JSON response MIME type.
Output ceilings are explicit and include any thinking tokens the provider bills.
Anthropic system instructions are separate from messages; Gemini assistant turns
become native `model` turns. No history is flattened into a single user message.

`FormationRecorder` extends the existing `CallRecorder`. Its input reserve includes
the entire native body, including system text, with a conservative byte-based
estimate. It keeps native request and response JSON, normalized usage, parsed and
raw replies, stop reasons, model identities, request IDs, and safe rate headers.
No request headers, credentials, or provider error bodies are logged. Gemini
output charges include candidate and thought tokens; cached input is a subset
of prompt tokens. Anthropic cache usage is reported separately. No cache is
requested by these clients.

Missing usage or model identity stops the batch. An unexpected returned model
also stops it; there is no silent model substitution. Refusals, empty replies,
truncation, malformed JSON, and transport errors have separate labels. These
are connectivity/transport labels, not the complete Study A outcome set; that
set will be proposed at Gate 2.

## Models and dated prices

Checked against first-party documentation on 2026-10-07. USD per million tokens:

| Pinned model | Input | Output | Connectivity output ceiling |
|---|---:|---:|---:|
| `gpt-6-luna` | $0.10 | $0.50 | 8,192 |
| `claude-haiku-5-5` | $0.10 | $0.50 | 8,192 |
| `claude-haiku-4-5-20251001` | $1.00 | $5.00 | 8,192 |
| `gemini-2.5-flash-lite` | $0.10 | $0.40 | 8,192 |
| `qwen/qwen3.8-27b`, Groq Free account | $0 | $0 | 4,096 |

The new price file preserves September's format and adds short-context stop
thresholds: 272,000 for Luna and 100,000 for Haiku 5.5. The client conservatively
stops if native request bytes exceed those token thresholds, so it cannot
quietly enter the more expensive long-context tier. A future long-context run
needs a new estimate/configuration. No tools, searches, images, or storage are
requested here.

- [Luna model and pricing](https://developers.openai.com/api/docs/models/gpt-6-luna).
- [Anthropic prices](https://platform.claude.com/docs/en/about-claude/pricing)
  and [Haiku 5.5 migration](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide).
  Haiku 5.5's default adaptive thinking and medium effort are left in place.
  Its former temperature 0.2 request would be rejected; the new client omits it.
- [Google prices](https://ai.google.dev/gemini-api/docs/pricing)
  and [2.5 Flash-Lite availability](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite).
  The authorized metadata check returned 45 generation-capable models, preserved
  in `formation-gemini-models-2026-10-07.json`. Flash-Lite 2.5 is visible and has
  the lowest published standard text price among general-purpose Gemini models
  listed. Generation access still needs confirmation; Google restricts 2.5 access
  to previously active users. Moving `latest` aliases are excluded.
- [Groq models](https://console.groq.com/docs/models)
  and [Free limits](https://console.groq.com/docs/rate-limits).
  Llama 3.3 is listed as enterprise access. Chris approved Qwen instead.

## Spending, pacing, and resume

The neutral manifest pins all five IDs and settings. Five nominal requests with
generous 2,000-token input estimates and full output ceilings project **$0.0550288**
combined. This is a ceiling projection, not measured usage or a provider invoice.
The application batch stop is **$0.10**. Formation-wide ledgers stop at **$8 per
paid provider**, reserving headroom below the owner's $10 ceilings. Both Haiku
models share the Anthropic ledger; historical Paper 2 spending is separate.

No automatic retries are made. Each model has at most two logical calls and two
request attempts, allowing one resume of an explicit rate pause; nominal calls
remain one per model and the batch cannot exceed ten attempts. Resumes retain
settled charges and ambiguous reserves. A shared lock prevents concurrent
formation commands. An interrupted lock requires inspection before removal.

Groq requires owner confirmation that the account is Free with billing disabled.
The client cannot independently prove the account plan. It never upgrades it.
The documented Qwen limits are 30 RPM, 1,000 RPD, 8,000 TPM, and 200,000 TPD.
The local guard uses three-second spacing, conservatively reserves whole request
bytes plus output tokens, and persists rolling minute/day allowances. Long
waits become a clean pause. Account-wide exhaustion headers also persist a
pause. A 429 stops with no retry; later use the same command after the reset.

Progress is append-only. Completed checks are skipped. A trial interrupted while
in flight requires evidence inspection; the harness does not repeat an uncertain
request. Resumes reject changed source/manifest/price fingerprints. Errors remain
in the journal; fixing them requires a separately named/versioned run rather
than overwriting evidence. This is infrastructure for future trial resume; no
formation study runner or experiment has been built ahead of its gate.

## Commands

Free estimate, safe to run now:

```bash
cd /Users/cmbp/Documents/GitHub/taa-lab
python3 scripts/formation_connectivity.py --estimate
```

**Only after Chris approves the $0.10 batch and confirms Groq Free:**

```bash
python3 scripts/formation_connectivity.py --approved-cost --confirm-groq-free-account
```

The same command resumes a rate pause. It loads `keys.env` normally without
displaying credentials. Chris must add `GROQ_API_KEY` himself. A nonzero exit
means connectivity remains incomplete. Replies and accounting go into
`results/2026-10-07 v0.21 formation-connectivity r1/`.

## Free verification

The unit suite passes 215 tests, including 22 new formation fixtures. They check
native histories, default settings, usage/caching/thinking arithmetic, complete
system-input reserves, shared provider budgets, missing usage/identity, bad
replies, transport errors, rate pauses, model-list pagination, and resume safety.
All generation in these fixtures is mocked; none calls a model.

The required scripted `python3 run.py --scenario all` also passes. The final
output is preserved under `results/2026-10-07 v0.21 scripted-none r1 stage1 verify/`.
These fixtures verify software, not model behavior or formation predictions.
Local execution used Python 3.13.3. New files also pass Python 3.9 grammar
checks; a separate CI workflow tests the formation fixtures on Python 3.9.
Both GitHub workflows passed for checkpoint `57dc7ad`, including the Python 3.9
formation job. See the 2026-10-08 notebook entry for run links. All 215 tests and
the required scripted scenario check also passed locally on Python 3.9.6 in a
temporary copy of the committed repository.


## Approved Gemini replacement (2026-10-08)

Current Google slot: `gemini-3.1-flash-lite`, held out with the same repeat
count. Standard text rates: $0.25 input / $1.50 output per million tokens;
cached input $0.025. See `studies/provider-prices-2026-10-08.json`. The earlier
table and batch estimate document the original five-model check, preserved
unchanged in its manifest and evidence.

The runner now accepts `--manifest`, fingerprints its selected price file and
effective settings, and requires Groq Free confirmation only for manifests
containing Groq. The Gemini replacement manifest limits calls/attempts to one:

```bash
python3 scripts/formation_connectivity.py --manifest studies/formation-connectivity-gemini31-v021.json --estimate
```

The approved run used the same command with `--approved-cost` in place of
`--estimate`. It is now terminal after HTTP 402; repeating that command will
not retry it. After billing is resolved, use a newly named manifest/output
folder and preserve both previous Gemini failures. No further generation was
made and no account billing settings were changed. All 217 tests and the
scripted checks passed locally on Python 3.9.6.


### Funded check result

`studies/formation-connectivity-gemini31-funded-v021.json` selects the same
approved Gemini model, prices, prompt, ceilings, and one-attempt limit in a new
output folder. It passed after the owner funded the account. Evidence is at
`results/2026-10-08 v0.21 formation-connectivity r1 gemini31 funded/`.
The runner command is `python3 scripts/formation_connectivity.py --manifest
studies/formation-connectivity-gemini31-funded-v021.json --approved-cost`.
A repeated invocation skips the completed check. Do not rerun it to troubleshoot
Groq. The account's actual balance and credit allocation were not inspected.


## Gate 1 report (2026-10-08, v0.21.2)

All five current slots returned parsed {"ok": true}, with valid provider usage
and exactly matching pinned model identity. Prices below are USD per million
tokens, from the dated first-party price sources in the repository:

| Current pinned model | Input / output price | Neutral check input / output tokens | Estimated settled charge |
|---|---|---|---|
| gpt-6-luna | $0.10 / $0.50 | 32 / 29 | $0.0000177 |
| claude-haiku-5-5 | $0.10 / $0.50 | 45 / 9 | $0.0000090 |
| claude-haiku-4-5-20251001 | $1.00 / $5.00 | 29 / 13 | $0.0000940 |
| gemini-3.1-flash-lite | $0.25 / $1.50 | 23 / 5 | $0.00001325 |
| qwen/qwen3.8-27b on confirmed Groq Free | $0 / $0 | 39 / 6 | $0 |

Google slot choice: Gemini 3.1 Flash-Lite, explicitly approved after the older
2.5 model returned HTTP 404; 3.1 costs less than the current 3.5 Flash-Lite and
was listed by the owner's key. The funded generation check confirms access.
The earlier 402 was preserved and resolved after owner funding. Credit allocation
and invoices have not been inspected. Price files retain their checked dates.

All clients omit sampling, effort, and thinking overrides, leaving provider
defaults. Google requests application/json MIME; other clients request JSON in
the neutral prompt. Paid-model output ceiling: 8,192; Qwen: 4,096. Native bodies,
responses, usage, stop reasons, raw replies, identities, and source hashes remain
in their run folders. A neutral pass is infrastructure evidence only.

Groq's metadata comparison isolated request identification: default Python
urllib identity received 403 from the Cloudflare edge; honest TAA-Lab identity
received 200 with the same key and endpoint. The formation Groq client now sends
`User-Agent: TAA-Lab/0.21.2 (Python standard-library API client)`. A separate
one-attempt generation check passed at $0. No billing was enabled, model switched,
key replaced, or rate guard relaxed. See the saved diagnosis file.

Evidence folders:
- `results/2026-10-08 v0.21 formation-connectivity r1 keys-ready/` (Luna and Haiku passes; original Gemini/Groq failures).
- `results/2026-10-08 v0.21 formation-connectivity r1 gemini31/` (preserved 402).
- `results/2026-10-08 v0.21 formation-connectivity r1 gemini31 funded/` (Gemini pass).
- `results/2026-10-08 v0.21.2 formation-connectivity r1 groq identity/` (Qwen pass).

Free checks: 218 tests and the required scripted run pass locally on Python
3.9.6. The original checkpoint's Python 3.9 and main CI workflows passed;
CI for these new local commits awaits Chris's push. Spending stops remain $8
per paid provider with a shared Anthropic ledger. Successful paid-call estimates
total $0.00013395; cumulative ledger including prior failed-request reserves is
$0.01580375. There were no automatic retries. Historical frozen sources,
scenarios, manifests, and model results remain unchanged.

**Owner decision required:** approve Gate 1 before starting Stage 2. No Study A
scenario or scorer has been drafted in anticipation of that approval.
