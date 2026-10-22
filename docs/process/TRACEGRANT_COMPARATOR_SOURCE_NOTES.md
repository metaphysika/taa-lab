# TraceGrant comparator: primary-source notes and implementation rulings

Date: 2026-10-22. Author: Claude, from the paper's HTML version (arxiv.org/html/2608.21126v1), read through the web because the build runtime cannot reach arXiv.

## Source status

- Paper: Bohao Liao, Jingchao Wang, Qipeng Song, Jin Cao, Jieling Wang, Boyu Deng (corresponding author). "TraceGrant: A Contract-Governed Security Framework for the Task-Effect Lifecycle of Networked LLM Agents." arXiv 2608.21126v1.
- **No official code repository exists.** The data-availability statement says implementation configurations and trajectory records are "available from the corresponding author upon reasonable request." Only the benchmarks (AgentDojo, ASB) are public.
- A faithful implementation must therefore be built from the paper. Every point the paper leaves open is an implementation choice, recorded in the comparator's implementation matrix.

## What the paper specifies (section numbers from the paper)

**Contract (POEC, §4.2.1, Eq. 1).** A Semantic Contract Compiler turns the trusted request, admitted tool schemas, capability profiles and an argument role catalog into a candidate contract with four parts:
- MAY: permitted tools and operations, target scope, argument constraints, call budgets.
- MUST: a dependency graph of obligations (evidence acquisition, external effects, required outputs).
- BIND: for each authority-bearing argument, the permitted source, expected type, field-level evidence constraints and permitted derivation; for evidence sets, a deterministic selection rule.
- VERIFY: completion requirements on tool identity, arguments, execution status and postconditions.
No field-level schema is given.

**Static validation (§4.2.2, Algorithm 1, Eq. 2).** A candidate becomes the contract only if all five checks pass; otherwise no executable contract exists:
- WellFormed: schemas, argument types and references are consistent.
- ControlSafe: obligation dependencies are acyclic and every hard node is reachable.
- FlowSafe: every authority-bearing argument of every reachable effect has an admissible BIND source and derivation.
- ScopeSafe: effect scopes, argument constraints and call budgets are consistent.
- VerifySafe: every reachable effect has observable verification conditions.
The printed pseudocode is garbled at line 14 (a missing negation on CheckScope); implement the text definitions.

**Compiler (§4.2.1, §5.1.4).** An LLM (DeepSeek-V4-Flash in the experiments). Schema admission, normalization, static analysis and set selection are deterministic. Prompts, output format and capability profiles are not given.

**Obligations (§4.3, Eq. 3, Eq. 9).** States PENDING, ACTIVE, VERIFIED, WAIVED. PENDING becomes ACTIVE when dependencies are satisfied. Admitted evidence or a valid receipt makes it VERIFIED. WAIVED is "a legitimate exemption specified in the Contract", never defined further. Hard obligations are referenced but not defined.

**Evidence and argument proofs (§4.3, Eq. 4).** A record is admitted only if its obligation is ACTIVE and it passes source, query, type and integrity matching. Each authority-bearing argument must cite a constant from the trusted request or an admitted evidence record, through a BIND-allowed derivation. Set selection must return exactly one record. The role catalog separates authority-bearing arguments (recipients, accounts, amounts, scopes) from payload arguments.

**Decision (§4.3, Eq. 5, ordered).** STEP_UP_AUTH if an untrusted payload matches a high-confidence risk pattern; else ALLOW if MAY, active obligation, proofs and budget all hold; else PROOF_GAP if only proofs fail (names the missing slot); else DENY.

**Certificate and receipt (§4.3–4.4, Eq. 6–8).** A one-shot Effect Certificate binds contract id, matched obligation, tool, canonical arguments, proofs and budget state, and is consumed on dispatch; the call must match exactly. A receipt is created only if the certificate matches, execution succeeded, postconditions hold and provenance remains valid; only then does the effect obligation become VERIFIED.

**Final-answer gate (§4.4, Eq. 9).** A success claim is accepted only if every hard obligation is VERIFIED or WAIVED.

**Known gap the authors state (§5.7, §6.3).** An attack succeeded because optional authority-bearing arguments (such as a recipient) were not bound. The authors say such arguments should require BIND proofs.

## Rulings for the offline W0 comparator

The goal is TraceGrant at its strongest faithful form, so that any TAA advantage is not an artifact of a weakened baseline.

1. **Compiler.** Offline runs make no model calls, so the LLM compiler is replaced by a hand-written POEC contract per W0 task, authored before any comparison result is seen and frozen with a hash. All deterministic parts (static checks, admission, decision, certificates, receipts, gate) are implemented as published. A later live comparison may use an LLM compiler only after a separate owner approval.
2. **Optional authority-bearing arguments.** Bind them, as the authors recommend in §6.3. Record that this is the authors' stated fix, not their evaluated configuration.
3. **Hard obligations.** Every effect obligation and every obligation a completion claim depends on is hard.
4. **Waivers.** None, since the paper defines no waiver mechanism. Record that WAIVED is unreachable in this implementation.
5. **Budgets.** Per-tool call budgets fixed in each frozen contract, decremented on certificate issue and restored only on a rolled-back dispatch.
6. **Step-up risk detector.** W0 has no untrusted payload channel matching a risk pattern, so STEP_UP_AUTH never fires, as in the paper's benchmarks (§5.1.4). Record this.
7. **Everything else unspecified** (normalization, receipt fields, postcondition format, selector syntax): choose the simplest form consistent with the text, and list each choice in the implementation matrix with its section reference.
8. **No TAA concepts.** The comparator gets no duty ledger, no live re-evaluation beyond what the paper describes, and no reporting, because TraceGrant does not have them. Each such absence is listed in the matrix as a design difference, not a defect.
9. Optionally, Chris may email the corresponding author to request the implementation configurations. Any material received is recorded as a source and compared against these rulings, but the comparator does not wait for it.
