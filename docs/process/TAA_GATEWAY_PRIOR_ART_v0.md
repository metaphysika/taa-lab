# TAA gateway prior-art note v0 — draft for review

[DESCRIPTIVE] Prepared by Sol on 21 October 2026 from `origin/main` commit
`57253f9303969c199db5b5c5c91c2a6fc0812187`. This is a bounded literature and
documentation review, not a systematic survey, implementation, benchmark,
pre-registration or novelty assessment. No paid model calls or gateway code.

1. [INTERPRETATION] Support tracking and withdrawal already have substantial precedent in truth maintenance.
2. [INTERPRETATION] Contextual authorization and enforcement before tool execution already have substantial precedent in policy engines and MCP gateways.
3. [INTERPRETATION] Explicit obligations, discharge and transfer already have substantial precedent in normative agents and commitment protocols.
4. [INTERPRETATION] Faithfulness and activation-intervention research constrain what a recorded reason can establish about a model.
5. [OPEN QUESTION] Whether TAA's proposed combination adds measurable value over a well-integrated conventional system remains to be tested; no novelty claim is made.

## Scope, labels and verification

[DESCRIPTIVE] The comparison target is the proposed gateway in
[Master Plan v2.1](https://app.notion.com/p/4005b2e94710815cbd50ecfd2810a661) and
[Bridge Specification v0.1](https://app.notion.com/p/4005b2e9471081a38b68da12d1b47f21),
both read on 21 October. The bridge is a draft awaiting independent review;
Claude's gateway core design is still pending. Proposed H5 is not adopted or
pre-registered. This note does not turn those proposals into approved requirements.

[DESCRIPTIVE] The four comparison dimensions are:

| Dimension | Proposed meaning, not an implemented guarantee |
|---|---|
| Live warrant | A particular action is bound to its purpose, scoped grant, excluded means and supporting record versions, checked at execution. |
| Rule-computed dependencies | Trusted rules determine support; a model's explanation alone cannot establish complete dependencies. The exact algorithm awaits design review. |
| Propagating revocation | A changed fact or revoked grant invalidates dependent approvals, including indirect dependents. |
| Duty ledger | A claimant, responsible party and discharge condition persist across refusal, revocation and accepted handoff. |

[DESCRIPTIVE] DESCRIPTIVE labels report source content or inspection; INTERPRETATION
labels identify the author's comparison; OPEN QUESTION labels mark unresolved
differences or proposed tests. There are no new CONFIRMATORY or EXPLORATORY study
results here. A feature not established by the inspected source is not a claim
that the feature is impossible, absent from every implementation, or absent from
the wider literature. Formal language expressiveness is not a deployed guarantee.

[DESCRIPTIVE] Each linked source below was retrieved and inspected on 21 October
2026. Verification depth is stated locally. Search snippets supplied leads;
the comparisons use the primary text, official documentation, or an explicitly
identified primary abstract. No cited experiment was reproduced. Mutable product
documentation is an access-date snapshot, not a frozen software release or
certification of runtime behavior.

## 1. Truth maintenance

### Doyle's justification-based TMS (1979)

[DESCRIPTIVE] Jon Doyle, *A Truth Maintenance System*, MIT AI Memo 521 (June
1979); journal version, *Artificial Intelligence* 12, 231–272. The
[MIT record and abstract](https://dspace.mit.edu/handle/1721.1/5733) describe
maintaining reasons for beliefs, revising beliefs when assumptions fail,
dependency-directed backtracking and explanations. The
[author bibliography](https://groups.csail.mit.edu/medg/people/doyle/publications/)
confirms both versions. Verification: primary repository abstract and author
bibliography; the full scan did not load. The detailed comparison with a
justification-based TMS was also checked in de Kleer's paper, sections 1–2.

[INTERPRETATION] **Overlap:** explicit justifications and reconsideration of
dependent conclusions are direct antecedents for rule-computed support and
propagating invalidation. **Boundary:** a maintained belief is not itself a
scoped executable authority grant; the sources inspected do not establish an
MCP enforcement boundary or the proposed claimant/discharge ledger.

[OPEN QUESTION] Can a conventional JTMS plus an authorization adapter implement
the same warrant lifecycle? Compare complete behavior and configuration effort;
do not call support tracking itself a TAA contribution.

### de Kleer's ATMS (1986)

[DESCRIPTIVE] Johan de Kleer, *An Assumption-based TMS*, *Artificial Intelligence*
28, 127–162. [Author-hosted full text](https://www.dekleer.org/Publications/An%20Assumption-Based%20TMS.pdf).
Verification: abstract and sections 1–3. An ATMS maintains labels of supporting
assumption environments and inconsistent combinations (nogoods), supporting
multiple contexts rather than only one current set of beliefs. Its architecture
separates domain inference from maintenance of support.

[INTERPRETATION] **Overlap:** rule-supplied justifications, alternative support
sets and propagation of inconsistency are relevant to warrant dependencies.
**Boundary:** assumption environments are not automatically authority grants,
and belief consistency supplies neither tool-call mediation nor duty discharge.
An ATMS is not simply an algorithm that deletes all descendants after an event;
alternative valid support matters.

[OPEN QUESTION] Should a corrected dependency lapse a warrant conservatively,
or can an independently sufficient support set keep it valid? The reviewed design
must specify this rather than borrow the name ATMS without its semantics.

## 2. Policy engines and authorization

### OPA / Rego

[DESCRIPTIVE] OPA evaluates declarative rules over structured input and data.
Its official [language](https://www.openpolicyagent.org/docs/policy-language),
[external-data](https://www.openpolicyagent.org/docs/external-data) and
[decision-log](https://www.openpolicyagent.org/docs/management-decision-logs)
documentation was inspected. Dynamic data can accompany each request; freshness
depends on the integration/cache. Logs can bind inputs, decisions and policy
bundle revisions. OPA explicitly distinguishes its cached data from the source
of truth. Verification: introductions and relevant data-update/log-schema sections.

[INTERPRETATION] **Overlap:** contextual checks can implement live permission
conditions and rule-computed decisions; refreshed grants can cause later requests
to be denied. Logs overlap the audit window. **Boundary:** the inspected interfaces
do not by themselves specify persistent warrant objects, their transitive
invalidation graph, or a duty lifecycle. These can be added by the host system.

[OPEN QUESTION] Would OPA plus a versioned store and obligation service match
TAA? It is a stronger comparator than permissions intentionally denied current
evidence. Rego data references and decision logs should not be assumed to be a
complete minimal semantic dependency set without a separate extraction check.

### Cedar (AWS-origin authorization language)

[DESCRIPTIVE] The official [Cedar reference](https://docs.cedarpolicy.com/)
describes authorization over principal, action, resource, context and supplied
entities/relationships. The host obtains an allow/deny decision and enforces it.
Policy validation against a schema is distinct from request evaluation.
Verification: introduction, entities/context and validation descriptions.

[INTERPRETATION] **Overlap:** scoped authority and context-dependent grants can
be represented in conventional policies; new inputs can change later decisions.
**Boundary:** the source does not establish that an allow result creates a
durable warrant with reverse dependency edges or surviving claimant duties.
Current-data retrieval and atomic enforcement remain application responsibilities.

[OPEN QUESTION] Is TAA best implemented above an existing policy engine? Compare
equivalent policies before attributing a benefit to the warrant representation.

### Zanzibar and relationship-based access control

[DESCRIPTIVE] Pang et al., *Zanzibar: Google's Consistent, Global Authorization
System* (USENIX ATC 2019). [Google primary record](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/)
and [full text](https://storage.googleapis.com/gweb-research2023-media/pubtools/5068.pdf).
Verification: abstract, introduction and sections 2.1–2.2. Relation tuples and
userset rewrites express nested permissions. Snapshot freshness constraints
prevent old ACLs from being applied to newer content and can ensure that later
membership checks reflect a removal.

[INTERPRETATION] **Overlap:** authorization from relationships and consistent
handling of changing permissions are directly relevant to scoped authority and
revocation. **Boundary:** external consistency is not the same claim as eagerly
invalidating every downstream warrant. The inspected sections establish no
ledger for positive duties. This note does not assess Zanzibar's internal cache
invalidation or compare its performance with TAA.

[OPEN QUESTION] What consistency contract must hold between a record correction,
authorization check and tool effect? A fair comparator must not serve stale
permissions merely because TAA is given fresher evidence.

### Macaroons / caveated capabilities

[DESCRIPTIVE] Birgisson et al., *Macaroons: Cookies with Contextual Caveats for
Decentralized Authorization in the Cloud* (NDSS 2014).
[Google primary record](https://research.google/pubs/macaroons-cookies-with-contextual-caveats-for-decentralized-authorization-in-the-cloud/).
Verification: primary abstract and bibliographic record. Chained MAC credentials
allow decentralized delegation and caveats restricting the context, including
purpose, in which a service authorizes a request.

[INTERPRETATION] **Overlap:** attenuated authority and caveat checking resemble
warrant scope and live conditions. Merely including a purpose constraint is
already represented in this prior work. **Boundary:** a caveat is not automatically
an understood legitimate end; its meaning depends on its verifier. The inspected
abstract does not establish general transitive revocation or a persistent duty
ledger. It supplies no basis for saying macaroons cannot support either through
additional services.

[OPEN QUESTION] Could caveats referencing authoritative record versions and a
revocation service provide equivalent enforcement? Do not equate token expiry,
rechecking a caveat, and propagating revocation without defining the distinction.

## 3. Normative agents and commitments

### Deontic reasoning in multi-agent systems

[DESCRIPTIVE] Makinson and van der Torre, *Input/Output Logics*, *Journal of
Philosophical Logic* 29 (2000), 383–408.
[Author-hosted full text](https://icr.uni.lu/leonvandertorre/papers/jpl00.pdf).
Verification: abstract, introduction and framework definitions. This formalizes
operations mapping conditions to normative outputs such as obligations, without
treating each norm as an ordinary truth-functional material implication. It is
one relevant formalism, not a survey of all deontic multi-agent logic.

[INTERPRETATION] **Overlap:** rule-derived obligations and explicit separation
of facts from what should follow are relevant to duty computation and warrant
rules. **Boundary:** a normative consequence relation alone is not a durable
runtime ledger, record-version service, revocation mechanism or execution gate.

[OPEN QUESTION] Which semantics does the gateway need for conflicting duties,
exceptions and legitimate discharge? A positive-duty field without a defined
transition system would be weaker than this literature's formal treatment.

### Singh's commitment protocols

[DESCRIPTIVE] Munindar P. Singh, *Formalizing Communication Protocols for
Multiagent Systems* (IJCAI 2007), 1519–1524.
[Proceedings full text](https://www.ijcai.org/Proceedings/07/Papers/245.pdf).
Verification: sections 1–2, especially 2.2. Commitments relate debtor, creditor
and condition. The paper defines creation, discharge, cancellation, release,
assignment and delegation, plus conditional commitments, with protocol rules
constraining permitted transitions.

[INTERPRETATION] **Overlap:** this is close prior art for duties, responsible
parties, beneficiaries, discharge and handoff. **Boundary:** its generic
cancellation/delegation operations do not establish TAA's proposed requirement
that authority revocation cannot itself extinguish a claimant's entitlement;
those constraints require protocol rules. Nor does this paper establish an MCP
record-version warrant implementation.

[OPEN QUESTION] Are the proposed ledger transitions simply a commitment protocol
with stricter cancellation/acceptance rules? Compare against that implementation,
not only against an informal to-do list.

### Electronic institutions

[DESCRIPTIVE] García-Camino, Noriega and Rodríguez-Aguilar, *Implementing Norms in
Electronic Institutions* (AAMAS 2005).
[Author-institution full text](https://www.iiia.csic.es/~jar/papers/2005/pa5d1_667.pdf).
Verification: sections 2–4. Its runtime norm engine represents permissions,
prohibitions, obligations and violations; rules create pending obligations and
retract permissions on specified events or deadlines. It implements these in
Jess. Earlier role/scene foundations are confirmed by Esteva, Padget and Sierra,
*Formalizing a Language for Institutions and Norms* (2002),
[coauthor's institutional record/abstract](https://researchportal.bath.ac.uk/en/publications/formalizing-a-language-for-institutions-and-norms/).

[INTERPRETATION] **Overlap:** explicit institutional roles, event-dependent
permissions, rule consequences and pending obligations cover much of the
gateway's proposed territory. **Boundary:** retraction on a named event does
not establish arbitrary versioned dependency closure; detecting/sanctioning a
violation and preventing a tool effect are distinct mechanisms.

[OPEN QUESTION] What remains different after mapping warrants and duties into
an electronic institution with a tool enforcement point? Accepted transfer and
no-silent-closure are candidate protocol constraints, not established inventions.

## 4. Agent guardrails, MCP gateways and proxies

### Existing MCP authorization gateways

[DESCRIPTIVE] The official
[agentgateway MCP authorization documentation](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/mcp-authz/)
describes CEL policies over tool/target names and authenticated claims. In this
snapshot, `mcpAuthorization` does not receive tool arguments; route-level
authorization can inspect them. Verification: CEL-variable table and the
argument-availability qualification, not just the product overview.

[INTERPRETATION] **Overlap:** external mediation and per-request tool restrictions
are existing capabilities. **Boundary:** the inspected page does not establish
a rule-derived warrant dependency graph or claimant/discharge ledger. The exact
hook and its available information matter to a fair comparison.

[DESCRIPTIVE] IBM ContextForge's official
[plugin catalogue](https://ibm.github.io/mcp-context-forge/using/plugins/plugins/)
documents pre/post tool hooks and optional OPA and Cedar enforcement plugins.
Verification: Policy Enforcement and plugin configuration sections. This is a
documented extension mechanism, not a runtime audit of every execution path.

[INTERPRETATION] **Overlap:** model-independent proxying, interception and policy
evaluation already exist. **Boundary:** the catalogue alone establishes neither
automatic dependency revocation nor obligations surviving handoff. Plugins could
implement those functions; missing catalogue entries do not prove impossibility.

[OPEN QUESTION] Can a plugin on an existing gateway implement the complete
proposal with less complexity? Test direct tools, alternate paths and cached
approvals rather than assuming that being a proxy ensures complete mediation.

### Tool-call guardrail / policy layers

[DESCRIPTIVE] OPA's official
[Agent Tool Calling](https://www.openpolicyagent.org/docs/agent-tool-calling)
guide explicitly places a policy decision before execution in the harness and
allows denial reasons to return to the model. OpenAI Agents SDK's official
[guardrails guide](https://openai.github.io/openai-agents-python/guardrails/)
documents pre/post function-tool guardrails, including local MCP tool wrappers;
it distinguishes these from agent-level checks and lists hosted/built-in tools
and handoffs outside that particular pipeline. Verification: enforcement flow
and Tool guardrails sections.

[INTERPRETATION] **Overlap:** blocking a call, explaining a refusal and allowing a
new attempt already occur in conventional tooling. **Boundary:** a post-execution
check cannot undo an effect; a guardrail outside an execution path cannot mediate
it. Neither inspected interface alone specifies persistent dependency or duty
semantics, but application code can add them.

[OPEN QUESTION] Does TAA improve correctness or auditability over an equally
informed policy layer plus persistent workflow state? Returning a reason for a
refusal is not itself a distinctive training contribution.

## 5. Chain-of-thought faithfulness and process supervision

[DESCRIPTIVE] Turpin et al., *Language Models Don't Always Say What They Think*
(NeurIPS 2023), [proceedings abstract](https://proceedings.neurips.cc/paper_files/paper/2023/hash/ed3fea9033a80fea1376299fa7863f4a-Abstract.html),
find plausible explanations omitting prompt features that affect answers.
Lanham et al., *Measuring Faithfulness in Chain-of-Thought Reasoning* (2023),
[primary abstract](https://arxiv.org/abs/2307.13702), intervene on written reasoning
and find task/model variation in its influence. Chen et al., *Reasoning Models
Don't Always Say What They Think* (2025),
[primary abstract](https://arxiv.org/abs/2505.05410), find that reasoning traces
often omit influential hints. Verification: all three primary abstracts;
these are scoped empirical findings, not universal impossibility results.

[INTERPRETATION] **Overlap:** dependency faithfulness (proposed H5) asks whether
declared support predicts responses to interventions, closely related to this
literature. **Boundary:** written-chain interventions do not automatically reveal
an internal decision representation, and a rule-derived warrant is an external
enforcement object rather than proof of faithful model introspection. The three
studies establish no warrant, revocation or duty-ledger mechanism.

[DESCRIPTIVE] Lightman et al., *Let's Verify Step by Step* (2023),
[primary abstract](https://arxiv.org/abs/2305.20050), compare intermediate-step
process supervision with final-outcome supervision for mathematical reasoning.
Verification: abstract and publication record. Their reported advantage is
specific to the studied training/evaluation setting.

[INTERPRETATION] **Overlap:** structured corrective feedback and matched
outcome/process supervision are direct precedents for the formation comparison.
**Boundary:** improving a mathematical verifier establishes neither positive-duty
transfer nor reliable authorization, and does not test learning from a model's
own corrected tool actions against matched demonstrations.

[OPEN QUESTION] Can H5 distinguish an accurate external causal summary from
faithful introspection? Can H2/H2b beat information/compute-matched process
supervision and account for on-policy distribution matching? A positive result
would not uniquely support a Thomistic explanation.

## 6. Interpretability of decision-making

[DESCRIPTIVE] Turner et al., arXiv:2308.10248 (first posted 2023; inspected v5,
2024), [*Steering Language Models With Activation Engineering*](https://arxiv.org/abs/2308.10248),
describe Activation Addition from contrasted prompt activations. The earlier
title was *Activation Addition: Steering Language Models Without Optimization*.
Panickssery et al., [*Steering Llama 2 via Contrastive Activation Addition*](https://arxiv.org/abs/2312.06681)
(first posted 2023; inspected v4, 2024), average paired residual-stream differences
to steer behavior. Verification: both primary abstracts and version histories.

[DESCRIPTIVE] Wang et al., [*Interpretability in the Wild: a Circuit for Indirect
Object Identification in GPT-2 small*](https://arxiv.org/abs/2211.00593)
(2022; ICLR 2023), investigate a circuit with causal interventions. Verification:
primary abstract and [full-text introduction/method overview](https://arxiv.org/html/2211.00593v1).
Path patching traces effects between components; activation patching helps
investigate component behavior. Its target is linguistic indirect-object
identification, not normative judgment.

[DESCRIPTIVE] Arditi et al., [*Refusal in Language Models Is Mediated by a Single
Direction*](https://arxiv.org/abs/2406.11717) (2024, inspected v3), report that
adding or removing a residual-stream direction changes refusal in the models
studied. Verification: primary abstract and version record. This supplies closer
precedent for intervening on action-selection behavior than topic steering alone.

[INTERPRETATION] **Overlap:** activation steering and causal intervention provide
methods relevant to H4; decoding alone cannot establish use of a representation.
**Boundary:** changing an answer or its tone does not establish a specific
authorization, evidence or duty variable. Refusal can change on harmless as well
as harmful requests, so a refusal direction is not itself a representation of
correct admissibility. These methods provide no external
execution warrant, revocation service or ledger; a behavioral intervention can
also alter unrelated competence or move activations off distribution.

[OPEN QUESTION] For Experiment C, can paired counterfactual activation patching
or steering selectively change the action associated with one decision variable,
while preserving unrelated task performance? Use matched sham/control patches,
pressure-only versus genuine-reason contrasts, and tool effects. The selected
variable must not be defined solely by a verbal label or a successful probe.
Those are design questions, not new experiments authorized by this note.

## 7. Candidate comparisons for the design review

[INTERPRETATION] The sources motivate testing a conventional composition, not
equating conventional authorization with an intentionally weak frozen allowlist.
The low-cost pilot's static-permissions arm remains useful for H3, but cannot by
itself establish an advantage over the strongest related engineering approaches.

| [OPEN QUESTION] Candidate difference | Strong comparison / evidence needed |
|---|---|
| Dependency closure tied to particular executable warrants | JTMS/ATMS support maintenance plus OPA/Cedar checks over the same versioned facts; compare missed invalidations, unnecessary invalidations and work completed. |
| Revocation without loss of what remains owed | A commitment protocol/norm engine with explicit discharge, acceptance and reassignment rules; compare surviving duties and timely completion. |
| One auditable action/purpose/authority/support/duty record | Existing gateway decision logs plus workflow records; compare reconstruction accuracy, configuration effort and runtime cost. |
| Corrected experience teaches transferable control | Matched outcome, successful-trajectory and process-supervised training; retain lawful work, reporting and closure metrics as well as harmful actions. |
| Reasons causally govern model action | Dependency perturbations and targeted activation interventions with controls; an accurate record alone is insufficient. |

[OPEN QUESTION] The gateway design must settle complete mediation, action-time
atomicity, record freshness, policy changes, multiple support sets, indirect
revocation, trusted rule dependency computation, duty creation/discharge and
accepted transfer. No implementation choice is made here. Chris and Astra review
Claude's design before gateway coding; all experiments need their own prospective
plans and approvals. This bounded source review does not establish novelty,
superiority, completeness of the literature, or satisfaction of Milestone 1.
