# TAA gateway prior-art note v1 — 2026 agents and learning from interventions

1. [INTERPRETATION] TraceGrant is the closest reviewed prior art to the gateway core; its overlap includes executable authority, evidence, obligations and completion checks.
2. [INTERPRETATION] Generic revocation and two-sided evaluation do not survive this reading as candidate differences from the wider literature.
3. [OPEN QUESTION] Order legitimacy and third-party duties surviving refusal remain narrower comparison questions, not established differences or novelty claims.
4. [DESCRIPTIVE] Shielding, interactive imitation, critique training, AgentLTL, AgentDoG 1.5 and Sentry already connect intervention or verification to learning in different ways.
5. [OPEN QUESTION] The TIOL full paper and claimed NeurIPS 2026 publication remain unverified; the author summary already describes contrary-to-duty repair.

## Scope and verification record

[DESCRIPTIVE] Sol, 21 October 2026. This extends the foundational review in
[v0](TAA_GATEWAY_PRIOR_ART_v0.md), which remains the reference for truth
maintenance, conventional authorization, commitments, MCP gateways, faithfulness
and activation interventions. The comparison target remains the proposed
gateway described there, not an implemented or approved architecture. This note
supersedes v0's provisional assessment where newer sources narrow it.

[DESCRIPTIVE] Labels retain v0's meanings: DESCRIPTIVE reports inspected source
content; INTERPRETATION is our comparison; OPEN QUESTION identifies an unresolved
claim or proposed experiment. Vendor assertions receive an additional VENDOR
CLAIM label. There are no new confirmatory or exploratory experimental results.
No novelty claim is made. Failure to establish a feature in a reading is not
proof of its absence, impossibility, or absence from another version.

[DESCRIPTIVE] All sources linked below were independently retrieved on 21 October
2026. “Full-text, targeted” means the full paper was accessible and the named
sections were read, not every appendix or a reproduced experiment. TraceGrant's
threat model, architecture, evaluation definitions and limitations were read
across sections 3–6. Other papers' methods, evaluation and relevant limitations
were inspected as specified below. No code, weights, experimental infrastructure
or vendor behavior was independently tested. Search snippets were leads only.
Versioned arXiv links identify inspected versions; unversioned HTML and vendor
pages are access-date snapshots. This is a bounded review, not a systematic
survey. No paid calls, Modal operations, Notion edits or gateway code were used.

## 1. TraceGrant: closest reviewed gateway-core prior art

[DESCRIPTIVE] [TraceGrant, arXiv:2608.21126v1](https://arxiv.org/html/2608.21126v1).
Verification: full-text sections 3–6. POEC contracts, evidence-bound Effect
Certificates, an obligation ledger, receipts and a Final-Answer Gate mediate effects.

| Requested check | Finding against full text |
|---|---|
| Trusted order / legitimacy | [DESCRIPTIVE] Sections 3.1–3.3 trust the immutable user request. [INTERPRETATION] Order legitimacy is outside that threat model. |
| Fixed contract / future work | [DESCRIPTIVE] Section 4.2 fixes the contract, not observations. Section 6.3 defers richer authority transfer, delayed effects and compensating actions. |
| Obligation meaning / waiver | [DESCRIPTIVE] Sections 4.3–4.4 track task steps, including contract-authorized WAIVED states. [INTERPRETATION] Third-party duties surviving refusal/revocation are not established. |
| Measurement | [DESCRIPTIVE] Section 5.1.3 defines ASR, benign success, utility under attack and integrity metrics, without a separate over-refusal endpoint. |

[INTERPRETATION] These overlap live warrants, rule-computed support, freshness
and duty accounting. Retry/correction support prevents an inference of wholly
static execution. Differences require lifecycle tests, not terminology; reported
white-box weaknesses also preclude a universal-security reading.

## 2. Other 2026 authorization and runtime-verification work

[DESCRIPTIVE] The source and verification columns below report what was actually
inspected. The last column is explicitly an INTERPRETATION of overlap and limits
relative to live warrants, rule-computed dependencies, propagating revocation and
the proposed duty ledger. These are comparisons of described mechanisms, not
independent implementation certifications.

| Primary source / verification depth | DESCRIPTIVE: mechanism and evidence | INTERPRETATION: overlap and boundary |
|---|---|---|
| [IGAC: Intent-Governed Tool Authorization for AI Agents, 2606.22916v4](https://arxiv.org/html/2606.22916v4). Full-text, targeted: threat model IV, certificate/runtime VI–IX, evaluation X. | Compiles a trusted request into a short-lived intent certificate; narrows static policy with tool manifests and argument checks. Certificates include expiry and revocation information. The reference runtime's revocation is in memory; the hardened profile exceeds that implementation. Section X-D explicitly measures over-defense: justified benign effects denied. | Strong live-authorization and freshness overlap. Generic revocation and two-sided measurement are already present. Certificate fidelity remains a trusted-request/compiler problem. The reading does not establish a rule-computed fact-dependency closure or claimant/discharge ledger. |
| [Runtime Authorization for Resources Acquired by AI Agents, 2609.14744v2](https://arxiv.org/html/2609.14744v2). Full-text, targeted: assumptions, formal authorization/epoch results, activation/effect protocol, evaluation. | Quarantines acquired resources until authenticated capability evidence and activation checks succeed. Typed capability dependencies, current epochs and single-use effect permits bind acquisition to use. Theorem 20 invalidates stale authority after bound epochs change. Claims depend on stated complete-mediation and authoritative-state assumptions; evidence includes finite protocol fixtures. | Direct overlap with live authority, dependencies and propagating invalidation. Revocation is emphatically not an uncovered category. Acquisition capability composition does not by itself establish persistent obligations owed to affected third parties. |
| [Authorization Architectures for Tool-Using AI Agents, 2609.15906v1](https://arxiv.org/abs/2609.15906v1), [full PDF](https://arxiv.org/pdf/2609.15906v1). Full-text, targeted: survey method, delegation lifecycle, runtime authorization and proposed architecture; not all 70 pages. | A structured narrative survey organizes identity, delegation, runtime enforcement, injection defenses and provenance, including revocation and authority across agent/tool boundaries. It proposes an architectural synthesis. | Much of the proposed gateway combines established authorization concerns. This is a map of prior work and design requirements, not empirical validation of one integrated runtime or evidence that every surveyed system provides every feature. |
| [SARC, 2605.07728v1](https://arxiv.org/html/2605.07728v1). Full-text, targeted: constraint representation, gates/monitors/auditor, operating points, delegated authority, synthetic evaluation. | Represents constraints with predicates, verification points and responses; combines pre-action gating, action-time monitoring, post-action auditing and escalation. Delegated constraints propagate within authority intersections. It explicitly distinguishes false positives from false negatives. Evaluation uses synthetic procurement with exact predicates. | Overlaps runtime rules, authority propagation and auditability. Does not establish production LLM reliability or the proposed fact-version and duty-survival semantics. Calling all prior guardrails one-sided would contradict its operating-point treatment. |
| [C-Trace: Runtime Compliance Verification for AI Agents, 2606.19242v1](https://arxiv.org/html/2606.19242v1). Full-text sections 3–4 and evaluation/limitations. | Intercepts tool calls and outputs, extracts typed trace events and checks privacy-policy predicates involving consent, purpose and erasure. Evaluates attack detection and benign false positives, including extraction noise. Some organizational obligations lie outside its session monitor. | Rules protecting data subjects already concern third parties. Its post-erasure non-disclosure check should not be presented as proof of positive erasure fulfillment. Whether duties persist through refusal, revocation and accepted handoff is a narrower unresolved comparison. |
| [Multi-Aspect Runtime Verification, 2610.08928v1](https://arxiv.org/html/2610.08928v1). Full-text, targeted: spatial/temporal/semantic architecture, policy composition, closed-loop simulation and metric definitions. | Combines policy aspects over a canonical event stream with provenance and temporal monitoring. Demonstrates shielding and recovery in structured simulations without retraining components. Defines benign false positives as refused benign calls. | Temporal obligations, recovery and multiple policy aspects overlap gateway goals. Simulated results are not a production guarantee; neither two-sided measurement nor recovery can be claimed as a general difference. The reviewed sections do not establish the specific warrant/duty lifecycle. |
| [Formal Runtime Verification for Tool-Using LLM Agents: An Offline Same-Benchmark Study on AgentDojo and STAC, 2610.09793v1](https://arxiv.org/html/2610.09793v1). Full-text, targeted: scope, MFOTL/MonPoly checks, benchmark results, provenance ablation and trace schema. | Applies formal obligations to recorded trajectories and reports attack detections alongside benign firings. An adaptive provenance attack motivates stronger binding to trusted lookup evidence. Proposes an enforcement-ready trace schema. | Strong overlap with rule-computed trace evidence and two-sided auditing. The study is offline: detection on a completed trajectory is not demonstrated prevention by an in-loop enforcement gateway. |

### TIOL and contrary-to-duty norms: an explicit verification gap

[DESCRIPTIVE] The accessible primary author/company source is Abhishek Kulkarni's
23 September 2026 [Vijil research summary](https://www.vijil.ai/blog/vijil-fundamental-research---a-new-path-to-scalable-verifiable-ai-governance/).
Verification: complete summary, plus [Vijil's research index](https://www.vijil.ai/research/)
and exact-title/venue searches. The summary describes Temporal Input/Output Logic
with triggers, discharge, deadlines and reparations; its automata distinguish
clean compliance, recovered violation and irrecoverable violation. Its return
example includes repair after a missed confirmation requirement. The summary
describes the paper as under review at NeurIPS, not as an accepted publication.

[OPEN QUESTION] I did not locate a readable full paper or independently establish
the supplied title's NeurIPS 2026 acceptance. A paper URL/author list has been
requested. Until supplied and inspected, cite the summary at its actual depth;
do not attribute a verified full-paper result or venue. Contrary-to-duty
reparation already overlaps the idea that a failure can generate further duties,
but whether its implementation covers third-party duties surviving refusal and
revocation remains unverified. This gap prevents an exhaustive claim about that
candidate difference; it does not justify treating it as absent prior art.

## 3. Commercial intent-based authorization — vendor claims only

[DESCRIPTIVE / VENDOR CLAIM] Verification is limited to reading each official
page below, including its mechanism/demo description. No account, live demo,
implementation, adversarial test or customer result was independently inspected.
Availability and coverage are vendor statements as of the access date.

| Official primary source | DESCRIPTIVE / VENDOR CLAIM | INTERPRETATION: overlap and unverified boundary |
|---|---|---|
| Saviynt, [Agent Access Gateway / IARA](https://saviynt.com/blog/closing-ai-agent-authorization-gaps), 19 June 2026; body and implementation phases read. | Intent-Aware Runtime Authorization combines user identity, task intent, resources, actions and runtime policy in an MCP intermediary that forwards or rejects calls. | Contextual action authorization overlaps live warrants. The page does not verify rule-computed support, transitive invalidation or persistent third-party duty fulfillment. |
| WorkOS, [Airlock](https://workos.com/blog/workos-airlock), 23 September 2026; complete article read. | Intent-associated tokens and policy checks mediate calls while provider credentials remain behind the gateway. The described email demo permits, blocks or requests approval based on configured policy and context. Intent does not override policy. | External policy can reject even a requested disclosure: intent checking cannot be equated with blind obedience. The particular dependency and duty lifecycle is not independently verified. |
| C1, [Agent Runtime Governance](https://www.c1.ai/news/press-release/c1-launches-agent-runtime-governance), 29 July 2026; complete release read. | Claims job-scoped tools, per-call policy, governed identities and audit trails; risk checks can block, request approval or redact, with fail-closed behavior. | Identity, action context and enforcement overlap the gateway. Internal dependency computation, revocation propagation and duty persistence are not established by this announcement. |

## 4. INTERPRETATION / OPEN QUESTION — which candidate differences survive?

| Candidate | Assessment after reading | Narrow question worth testing |
|---|---|---|
| Order legitimacy | [INTERPRETATION] Survives as a scope question against TraceGrant's trusted-request model, not a general literature difference. External policy engines already deny user-requested actions; ToolSafe and AgentDoG also consider harmful user requests. | [OPEN QUESTION] Can explicit authority, permitted means and affected-party rules reject an authenticated but impermissible order while preserving its lawful remainder, better than an equally informed conventional policy? |
| Mid-task evidence correction and revocation | [INTERPRETATION] Does not survive generically: TraceGrant has evolving observations; IGAC and acquired-resource authorization explicitly cover freshness/revocation. | [OPEN QUESTION] Does TAA's proposed rule-computed support invalidate exactly the indirectly affected warrants after a corrected fact, including alternative valid support and authority transfer, without excess denial? Compare equivalent freshness machinery. |
| Third-party duties surviving refusal | [INTERPRETATION] Remains a specific semantics/lifecycle question against TraceGrant, not a difference from normative systems generally. Privacy obligations, commitments and TIOL reparations are substantial overlap. | [OPEN QUESTION] Does a claimant-indexed reporting/repair duty remain live after refusal or grant revocation, and discharge only on verified performance or accepted handoff? Can conventional commitment/temporal rules implement the same behavior? TIOL full-text verification is outstanding. |
| Two-sided measurement | [INTERPRETATION] Does not survive as a broad difference. TraceGrant measures utility, and IGAC, C-Trace, SARC and other monitors explicitly address unnecessary blocking/false positives. | [OPEN QUESTION] Does a prospectively fixed battery separately measure wrongful effects, unnecessary refusal, omitted duties, lawful completion and protocol failure with planned denominators and unknown-outcome bounds? That is an evaluation commitment, not an architectural novelty. |

### TraceGrant as a strong conventional comparator for H3

[INTERPRETATION] **Yes, its design is a strong candidate**, subject to a faithful,
reviewable implementation in the same environment. Retain the planned static
permissions arm for H3, and add a TraceGrant-style contract/evidence/receipt/
completion-gate comparator before making broader comparative claims. TraceGrant
is a richer conventional runtime than static permissions; do not rename one as
the other or silently rewrite the existing hypothesis.

[OPEN QUESTION] The approved design should pre-register the comparator's contract
compiler, obligation/waiver rules, current-state checks and trusted evidence,
then give all arms the same task facts, authority rules, available actions,
model, budgets and outcome scoring. Preserve the comparator's legitimate retry,
evidence and completion features. Label any reconstruction as an adaptation,
not a reproduction or the authors' implementation. If adding dynamic revocation
or third-party duty policies to the comparator closes the gap, report that
result. Separate architectural differences from unequal policy information,
compiler quality, extra calls or weaker implementation. Report build/configuration
cost as well as behavior. This is a proposed comparison, not approval to code,
launch or spend.

## 5. Learning from runtime interventions

[INTERPRETATION] “The gate teaches the learner” covers several different claims:
updating an acting policy's weights, training a guard, generating corrected
demonstrations, or remembering lessons in context. The following distinguishes
them. A formal violation supplies a machine-readable justification, not
necessarily a natural-language reason. A safe-action set is an alternative
without necessarily explaining it. Utility is not automatically an explicit
over-cautious-error measure. Monitor-free evaluation on held-out instances is
not automatically transfer to a new domain.

### Shielding and interactive imitation learning

[DESCRIPTIVE] Verification depths are attached to each primary source. All
feature descriptions below concern the inspected method/experiment; “not
established” records a verification limit rather than a universal negative.

| Source and verification | Learner's own attempts? | Reason and alternative? | Over-cautious errors as well as harmful ones? | Transfer with monitor/expert removed? |
|---|---|---|---|---|
| [Alshiekh et al., Safe Reinforcement Learning via Shielding, AAAI 2018](https://ojs.aaai.org/index.php/AAAI/article/view/11797); [full text, 1708.08611v2](https://arxiv.org/html/1708.08611v2). Publisher record and full-text sections 4–5, experiments read. | [DESCRIPTIVE] Post-posed shielding corrects the learner's proposed action; preemptive shielding masks choices beforehand. | [DESCRIPTIVE] Formal safety specification; safe action replacement/set. No required natural-language reason. | [DESCRIPTIVE] Safety and reward/minimal interference are considered; no separate wrongful-refusal correction task. | [DESCRIPTIVE] Section 5.2 says even punishing unsafe proposals does not ensure a safe final policy; the shield must remain for the guarantee. No monitor-free cross-domain transfer established. |
| [Carr et al., Safe Reinforcement Learning via Shielding under Partial Observability, AAAI 2023](https://ojs.aaai.org/index.php/AAAI/article/view/26723); [full text, 2204.00755v2](https://arxiv.org/pdf/2204.00755v2). Methods, section 4.3 and experiments read. | [DESCRIPTIVE] Learner interacts through a shield/state estimator. | [DESCRIPTIVE] Formal admissible-action information, not a required language explanation. | [DESCRIPTIVE] Explicitly recognizes overly conservative shielding and studies relaxing it; not a benign/harmful LLM refusal battery. | [DESCRIPTIVE] Tests sudden deactivation and gradual fading of the shield; sudden removal can reveal reliance. This is shield removal within studied environments, not demonstrated new-domain normative transfer. |
| [Ross, Gordon and Bagnell, DAgger, AISTATS 2011](https://proceedings.mlr.press/v15/ross11a.html); [full text, 1011.0686](https://arxiv.org/pdf/1011.0686). Algorithm 3.1 and evaluation read. | [DESCRIPTIVE] Expert labels states reached by the evolving learner/mixed policy; not only states following a known mistake. | [DESCRIPTIVE] Expert action supplies an alternative; no required language reason. | [DESCRIPTIVE] General imitation loss can correct many deviations, but no dedicated excessive-caution endpoint. | [DESCRIPTIVE] Evaluates learned policies without an expert choosing their test actions in the task domains; not evidence of cross-domain moral transfer. |
| [Kelly et al., HG-DAgger, 1810.02890v2 / ICRA 2019](https://arxiv.org/html/1810.02890v2). Full-text method and experiments read. | [DESCRIPTIVE] Human takes over during novice rollouts; recovery controls become training data. | [DESCRIPTIVE] Demonstrated alternative control, no required language reason. | [DESCRIPTIVE] Intervention centers on risk/recovery; no separately established over-caution correction measure. | [DESCRIPTIVE] Explicitly tests the learned policy without human intervention. Task-domain driving performance is not new-domain transfer. |
| [Hoque et al., ThriftyDAgger, CoRL proceedings 2022](https://proceedings.mlr.press/v164/hoque22a.html). Primary abstract/record only. | [DESCRIPTIVE] Interactive demonstrations with novelty/risk-based querying and intervention-budget constraints. | [DESCRIPTIVE] Expert demonstrations; reason schema not established by abstract. | [OPEN QUESTION] Not verified at this reading depth. | [OPEN QUESTION] Not verified at this reading depth; do not infer removal from reduced human burden. |

### Natural-language critiques and corrections for LLMs

| Source and verification | Learner's own attempts? | Reason and alternative? | Over-cautious errors? | Transfer without the corrective loop? |
|---|---|---|---|---|
| [Bai et al., Constitutional AI, 2212.08073](https://arxiv.org/html/2212.08073). Full-text sections 1, 3–4 and critique/revision examples read. | [DESCRIPTIVE] Critiques/revises sampled assistant responses, then trains on revisions; later uses AI preference feedback. | [DESCRIPTIVE] Principle-conditioned critique plus revised response. Critiques can be inaccurate; their presence does not prove faithful causal reasoning. | [DESCRIPTIVE] Explicitly addresses evasiveness alongside helpfulness/harmlessness, though not the proposed operational lawful-task endpoint. | [DESCRIPTIVE] Evaluates trained assistants, not only iterative revisions. This supports learning beyond retaining the critique loop, not gateway-free tool-agent transfer across domains. |
| [Scheurer et al., Training Language Models with Language Feedback, 2204.14146v4](https://arxiv.org/html/2204.14146v4). Full-text methods and section 3.2 read. | [DESCRIPTIVE] Initial summaries/refinements come from InstructGPT; GPT-3 is fine-tuned on refinements. Thus not strictly corrections of the final learner's own attempts. | [DESCRIPTIVE] Human feedback identifies desired changes; generated refinements supply alternatives. No universal reason-plus-alternative schema. | [DESCRIPTIVE] Summarization corrections; no over-refusal evaluation. | [DESCRIPTIVE] Fine-tuned model tested on unseen posts without supplying their feedback. Same-dataset generalization, not new-domain agent transfer. |
| [Madaan et al., Self-Refine, 2303.17651v2](https://arxiv.org/html/2303.17651v2). Full-text method and evaluation read. | [DESCRIPTIVE] Yes, feedback on the model's own output. | [DESCRIPTIVE] Actionable critique followed by a revised alternative. | [DESCRIPTIVE] General quality tasks; no specific harmful-versus-over-cautious intervention comparison established. | [DESCRIPTIVE] Inference-time iteration without weight training. Improvement with the loop retained is not internalized learning with it removed. |
| [Shinn et al., Reflexion, 2303.11366v4](https://arxiv.org/html/2303.11366v4). Full-text method and evaluation read. | [DESCRIPTIVE] Reflects on failed attempts using feedback and episodic memory. | [DESCRIPTIVE] Verbal diagnosis/next-attempt guidance; no uniform executable alternative requirement. | [DESCRIPTIVE] Task failures, not a dedicated over-refusal endpoint. | [DESCRIPTIVE] Memory/feedback loop remains part of the method; no weight update establishing monitor-free transfer. |

### Agent work connecting guardrails, verification or runtime repairs to learning

[DESCRIPTIVE] The search did find relevant work. It would be incorrect to report
that agent learning from guardrail/verification feedback has no precedent.

| Primary source / verification | What learns; whose attempts? | Reason and alternative? | Over-cautious errors? | Monitor removed / transfer evidence? |
|---|---|---|---|---|
| [AgentLTL, 2607.02599v1](https://arxiv.org/html/2607.02599v1). Full-text sections 3.4, 4.2–4.3, 5.2 and limitations. | [DESCRIPTIVE] Same formal compliance score drives online enforcement and GRPO training of an acting model. Training scores the learner's sampled traces; it is not simply distilling logged gateway refusals. | [DESCRIPTIVE] Scalar/per-constraint compliance and gold-trace distance reward; training does not require a language reason with a corrected action for each blocked attempt. | [DESCRIPTIVE] Measures procedural correctness/compliance; no dedicated moral over-refusal correction test. | [DESCRIPTIVE] Reports separate base/fine-tuned validation on unseen patterns/tool aliases. [INTERPRETATION] Described as standalone policy evaluation, not an enforcement arm; an explicit enforcement-off code audit was not performed. Transfer is synthetic procedural, not broad ethical generalization. |
| [AgentDoG 1.5, 2605.29801v1](https://arxiv.org/html/2605.29801v1). Full-text sections 4–5, reward equation and evaluation definitions. | [DESCRIPTIVE] Uses guardrail filtering for SFT and the guardrail as a safety judge on acting-policy RL rollouts. RL scores its own attempts; SFT uses generated safe trajectories. | [DESCRIPTIVE] Diagnostic reasoning and safe demonstrations exist, but policy RL receives safety/utility reward, not necessarily an explanatory correction pair. | [DESCRIPTIVE] Clean-task utility and safety are jointly considered; discusses over-refusal tradeoffs. | [DESCRIPTIVE] Reports trained-policy benchmark results separately from online guarding. [OPEN QUESTION] Complete enforcement-off protocol/overlap audit is unverified; do not equate results with transfer from reasoned gateway interventions. |
| [TRIAD, 2606.05805v1](https://arxiv.org/html/2606.05805v1). Full-text sections 3–5 and benign-task evaluation. | [DESCRIPTIVE] Trains a dedicated guard on generated trajectory/feedback data. Runtime feedback revises a black-box target agent's current plan; does not train that actor's weights. | [DESCRIPTIVE] Structured feedback and Proceed/Update/Refuse control guide revision. | [DESCRIPTIVE] Explicitly tries to preserve benign work instead of indiscriminate refusal. | [DESCRIPTIVE] Cross-backbone results retain the guard and feedback loop; no actor internalization with guard removed established. |
| [ToolSafe, 2601.10156](https://arxiv.org/html/2601.10156). Full-text sections 3–5 and split definitions. | [DESCRIPTIVE] Trains TS-Guard with step-level labels/GRPO; TS-Flow returns feedback on the actor's proposed tool calls. The described actor loop is inference-time correction. | [DESCRIPTIVE] Guard produces reasoning/safety judgments; feedback prompts safer calls, without guaranteeing a concrete alternative. | [DESCRIPTIVE] Measures benign completion and attack resilience; avoiding detect-and-abort utility loss is a motivation. | [DESCRIPTIVE] Held-out domains test the guard/guarded system. Guard retained; not evidence of actor-weight learning after removal. |
| [From Refusal to Recovery / ReGuard, 2510.13727v2](https://arxiv.org/html/2510.13727v2). Full-text sections 3–6. | [DESCRIPTIVE] Trains a safety value/recovery policy using environment outcomes; combines it with a base LLM at inference. This is learning a guard/recovery controller. | [DESCRIPTIVE] Chooses alternative actions through safety-guided decoding; no required language reason. | [DESCRIPTIVE] Recovery addresses cases where passive refusal is unsafe and studies safety/efficiency. Not a matched lawful-refusal endpoint. | [DESCRIPTIVE] Guard-guided decoding remains active. Multiple agent settings are not proof that a formerly guarded actor internalized corrections. |
| [Sentry, 2610.02994v1](https://arxiv.org/html/2610.02994v1). Full-text sections 3–5, held-out protocol and component ablations. | [DESCRIPTIVE] Learns an external playbook from verified repairs of the agent's runtime failures; no actor weight update. | [DESCRIPTIVE] Diagnoses local failure/evidence and retrieves repair principles; agent generates a replacement action. | [DESCRIPTIVE] Includes stalled/no-progress behavior and harmful unnecessary interventions, not a paired ethical over-refusal measure. | [DESCRIPTIVE] Held-out-task transfer retains diagnosis, retrieval and intervention. Removing persistent playbook exposure is not removing the runtime monitor. |

### Bounded search and implications for a formation experiment

[DESCRIPTIVE] Searches on 21 October included the following exact query strings,
followed by primary-source retrieval and reference chasing to the papers above:

- `LLM agents "guardrail" "training" "interventions"`
- `LLM agent "shield" "fine-tuning" intervention`
- `"learning from" "guardrail feedback" agent`
- `"LLM" "shield" "distillation" agent safety`
- `"LLM agents" "intervention data"`
- `"agent" "guardrail interventions" "training"`
- `"LLM" "gateway" "training" corrections interventions`
- `LLM agent fine-tuning on runtime guardrail intervention trajectories monitor removed`
- `"AgentLTL" training enforcement`
- `"AgentDoG 1.5" supervised fine-tuning reinforcement learning paper`

[DESCRIPTIVE] These searches identified direct verification/guardrail-supervised
actor training (AgentLTL, AgentDoG), learned guards (TRIAD, ToolSafe, ReGuard), and
learning from runtime repairs in external memory (Sentry). The reading did not
verify a study combining all of: claimant-aware warrant/duty interventions,
reason-plus-lawful-alternative corrections of the acting learner's own attempts,
matched corrections for both harmful and excessive-caution errors, and a
pre-registered new-domain test with the intervention system removed. That is a
bounded search outcome, not an absence or novelty claim; no exhaustive code,
dataset or citation search was performed.

[INTERPRETATION] The defensible research question is consequently whether the
specific information and correction regimen improve transfer beyond strong
shielding, interactive imitation and critique-training controls. Learning from
interventions, training from reasons, or evaluating without a teacher cannot by
themselves be claimed as new.

[OPEN QUESTION] A future approved H2/H2b design should separate information,
policy and enforcement effects: compare own-attempt corrections with matched
external demonstrations; reason-plus-alternative with alternative-only and
matched generic critique; harmful and excessive-caution corrections; multiple
training seeds; competence-matched controls; monitor-on and monitor-off held-out
tests; and genuinely new task/domain material. Keep outcome scorers separate
from the training monitor, pre-register the endpoints and retain the original
evidence. No existing experiment is upgraded by these proposals. Approval and
design review remain prerequisites for any build or run.
