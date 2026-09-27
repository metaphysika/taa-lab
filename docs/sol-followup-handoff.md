# Starting prompt for the Sol implementation chat

Copy the text below into a new chat opened in `/Users/cmbp/Documents/GitHub/taa-lab`. Select Sol using the model control. This file does not create or message another chat.

---

I want you to implement a bounded follow-up study for TAA Lab, then help me run it cheaply and draft a new paper for Astra to review.

Read `docs/followup-testing-roadmap.md` in full first. Also read `CLAUDE.md`, the latest `LAB_NOTEBOOK.md` entries, and the relevant code. The older roadmap and handoff contain stale passages: the v0.18.1 final Luna and Haiku runs are already complete. Do not repeat them unnecessarily.

The question is whether temporary resource reservations and conditional commitments protect pending obligations without causing harmful holds or preserving obsolete approvals. Keep the study in the existing simulated logistics world. Do not implement the latest Paper 2 v0.3 Section 2.2 as my approved design; I do not agree with its present account of L0-E correction.

Begin with the free stages. Fix and regression-test the two bugs Astra confirmed: `_premise_rereview` overwrites the requested target with a state dictionary, and an always-allowed report can erase an unreviewed external change through rebaselining. Add honest obligation-specific outcome measurements and provider-level call/token/cost accounting before paid testing. Preserve historical code references, scenarios, and results.

Implement the smallest reservation/referral lifecycle that covers the roadmap's cases. A hold is not permission; unanswered referrals cannot become approvals. Use a declared scripted authority schedule for delayed replies, denials, withdrawals, and no-answer cases. Report it as simulation of authority handling, not validation of human judgment. Keep the repaired TAA control, modified TAA, strengthened per-act judge, and free expiring-policy control fairly comparable. Do not give only TAA the information or reply mechanism needed to succeed.

Work autonomously on reversible implementation and free verification. Keep Python readable and prefer the standard library. After meaningful code changes run the existing unit/scripted checks and the new tests. Write predictions before the runs they govern, keep all model evidence, and version changes. Do not read, print, or copy `keys.env`; the harness may load it normally.

I want quick, inexpensive iterations: free deterministic fixtures first, then narrowly targeted Luna smoke/pilot runs, then a frozen Luna-and-Haiku evaluation. Aim for roughly $7 total API expenditure for this study. Before paid execution, give me the exact commands, current-price basis, measured/projected call and dollar budget, and stop limits. I can run the commands in Terminal. Do not treat my previous $7 bill or the old final-run approval as authorization for a new paid batch. Once I authorize a batch and cap, proceed within them without asking for each individual call.

Use the roadmap's final matrix if the measured pilot says it fits; otherwise apply its scope-reduction rule before freezing. Do not selectively remove difficult cases after final results or tune to the final Haiku replies. At most two substantive policy revisions after the first paid smoke batch, followed by a written checkpoint if the design still fails.

When the results are available, produce the full return package specified in the roadmap and create a new DOCX draft from my latest supplied paper, preserving the old draft. Report both favorable and unfavorable findings. Decide whether it belongs in an updated Paper 2 or a separate follow-up based on what was learned. Flag the philosophical Section 2.2 for my own review rather than treating it as settled. Use the documents skill and render/inspect the new DOCX.

Start by briefly confirming the current repository state and explaining the first implementation milestone. Do not stop at another plan unless you encounter a material ambiguity that blocks the authorized work.
