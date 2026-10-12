# Haiku 5.5 native output options — owner review, no calls

The owner paused the fresh block and any parser freeze. This is documentation research and a proposal, not an execution approval. The one-object parser remains a draft. No study code, original labels, model evidence, provider ledger, quota, settings or frozen scientific inputs were changed for the ledger-test fix.

The verified descriptive recount is 28 single valid action objects surrounded by text, 11 placeholder-only replies, two XML-style parameter replies, and one multi-action reply among the original 42 malformed episodes. Together with four unfinished replies and two provider refusals, 20 terminal failures are not addressed by the parser amendment. This is not a rescore or a prediction of complete rerun episodes: recovering an intermediate action does not establish how an old episode would have ended. The original first block and Study A labels remain unchanged.

## Native tool use

Anthropic documents Haiku 5.5 client-side tool use. Requests gain `tools` definitions with names, descriptions and `input_schema`; `strict: true` optionally constrains tool inputs. Native responses contain `tool_use` blocks; the next turn carries `tool_result` blocks with their IDs. The evaluator would read these blocks instead of parsing narrative text. A real native call can coexist with prefixed prose without being malformed. With `auto`, a call is not guaranteed, so placeholder-only/no-call responses can still occur. Strictness guarantees the format of calls actually made, not correct judgment.

Forced `any`/specific-tool selection plus strict schemas can enforce a call, but Anthropic states that forced calls skip thinking. This would change the approved reasoning behavior and can force an action when the agent should stop. It is not recommended under the current settings.

Schemas/descriptions become model-visible, and Anthropic adds a tool-use system prompt. The documented Haiku overhead is 286 input tokens per request for automatic choice, 406 for forced choice, before tool definitions/history. These are client tools; no separate client-tool execution fee is listed. No hosted search or other server tool is proposed.

Sources: [tool use and pricing](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview), [tool choice and thinking](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), [strict tool inputs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use).

## Structured JSON output

Haiku 5.5 supports schema-constrained JSON on the direct Claude API used here. Add `output_config.format` with `type: "json_schema"` and the action-envelope schema. Text responses are decoded under that grammar, excluding placeholder-only text, XML wrappers and prose outside the object in ordinary completed answers. Safety refusals and output-limit truncation remain exceptions. No guarantee of a correct or meaningful action follows. Default adaptive thinking can remain; native tool forcing is unnecessary.

The provider injects formatting instructions and bills their tokens. Tool descriptions in the existing world view need not change. However, the schema is model-visible: Anthropic requires closed objects (`additionalProperties: false`). Our current `args` object is open-ended, so this is not a perfectly invisible formatter change. The owner must review the known argument-key vocabulary and its effect on mechanical parameter-error opportunities before freeze. Use no scenario-specific IDs, status/option enums, correct recipients, moral advice or recommended actions. Preserve stop/null, decline, referral, and wrong-but-well-formed choices. No automatic SDK retries or reasoning-extraction fields.

Sources: [structured JSON, model/platform support, exceptions and schema limits](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [Haiku 5.5 migration/platform distinctions](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide).

## Fairness options

1. **All models use equivalent native tool interfaces.** Same semantic tool descriptions and parameter vocabulary, one action per turn, explicit stop representation, identical world/scoring. Preserve full native histories and default reasoning. This changes the common interface and needs a prospective protocol review. Luna needs the Responses API for native functions with default reasoning: Chat Completions native functions require reasoning effort `none`, which we must not silently select. Gemini and Gemma document native functions. Provider wrappers and guarantees still differ; native support alone does not establish equal reliability.
2. **All models use equivalent structured-output constraints.** Luna and Gemini document JSON-schema output; Gemma's Gemini-API guide documents native functions but does not establish equivalent strict JSON-schema guarantees. Existing Google `responseMimeType: application/json` is not proof of the same schema enforcement. Do not call this a matched four-model condition without resolving that capability and schema intersection.
3. **Haiku-only structured JSON with explicit disclosure. Recommended.** This targets the known provider-specific formatting problem with the smallest change to the existing action/history interface and keeps default thinking. State that output assistance differs by provider and was selected after the original Haiku block, before other held-out B runs. This is a comparison of substantive behavior under disclosed provider adapters, not identical raw API formatting ability or a causal test of intrinsic model character. Parameter-error/protocol rates must carry that limitation. A fully matched native-interface study is a larger prospective alternative, not an automatic extension.

Sources: [Luna capability/endpoint restrictions](https://developers.openai.com/api/docs/models/gpt-6-luna), [Gemini capabilities](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite), [Gemma through the existing Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api).

## Recommended option: preliminary cost only

Haiku 5.5 short-context rates remain $0.10/M input and $0.50/M output; cache writes if reported use the archived $0.125/M rate. Structured output adds billed input tokens; documentation provides no fixed injected-token count. These are planning assumptions, not measurements or a quote.

Use the earlier 72-episode point $0.158354445 and an empirical reference of 297 requests (rounded up from 2,961/10). Assume 1,000 additional input tokens per request for schema plus injected format instructions, with no cache discount and unchanged output/history behavior:

- Standard-input point: $0.188054445; 25% planning buffer: $0.23506805625.
- Conservative cache-write-rate calculation: $0.195479445; buffered: $0.24434930625.
- Proposed first-block spending ceiling for separate review: $0.25 **within**, not above, the remaining original Anthropic B allowance $1.940174300. No cap increase is authorized.

For a full new 720-episode Haiku batch at 2,961 requests, the same standard-rate assumption gives $1.879644450 new cost, or $1.964470150 including the retained failed attempt. Its buffered amount including that attempt is $2.4343812625, above the unchanged $2.025 cap. At the conservative cache-write rate, even the unbuffered combined reference is $2.038495150. Completion is not promised; exact schema size, real usage, retries and longer successful episodes can change spending. All existing monetary stops remain. Full-cap Anthropic C/D room remains $3.509428850 below $8; no C/D work or reallocation.

For comparison, automatic native tools add at least $0.0084942 to 297 requests from the documented 286-token system wrapper alone at standard input rates, plus unknown schema/tool-history tokens and changed behavior. That floor is not a total cost forecast. Forced calls' lower/no thinking cannot be used to claim cheaper comparable evaluation.

Pricing source: [Haiku 5.5 overview and current prices](https://platform.claude.com/docs/en/models/haiku-5-5/overview).

Next decision: choose the output mode and approve its offline adapter/schema/protocol preparation. After review, freeze the selected parser/interface and present a hash-bound execution cost plan. **No neutral probe, fresh block, other model, or C/D call is authorized now.**
