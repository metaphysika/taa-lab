# PR37 review: three additional guard controls

[Descriptive] Chris relayed Claude's acceptance of c4963480 (durable state
8d46a6f7 plus Chat Completions c4963480), subject to three test additions.
Chris's 2026-10-25 approval of Chat Completions with native function tools and no
reasoning carry-over, identical across arms, is recorded verbatim with the prior
200/401/400 probe table in LAB_NOTEBOOK.md. This stage makes no provider request,
launch or merge. Runtime and frozen inputs remain byte-identical to c4963480.

[Descriptive] The new controls are:

- A launched run must create the durable run.once before its first canned
  transport request. A second launch from either the same or a different Git
  checkout root must raise run_already_used, make no request, create no output
  directory and preserve the original marker bytes. Authorization and source
  verification are mocked to isolate this guard; accounting and state use
  temporary fixtures, never the real state.
- Otherwise valid durable state must fail with durable_state_missing_or_invalid
  when its directory is inside a Git working tree. The fixture first passes
  validation outside Git, then initializes the enclosing Git repository without
  changing its manifest, imported markers or accounting. This avoids the old
  combined test's masking corrupted-marker condition.
- A native finish_reason tool_calls with no calls must stop the whole run as
  unknown_output. A two-episode canned schedule retains only the first episode
  and one charged request; it must never return model_done or continue the second
  episode. Actual usage is settled before the stop.

[Descriptive] The existing in-memory mutation script now exercises all seven
controls, adding removal of each of these three guards. Each mutant must cause
one assertion failure, zero errors, with passing baseline and restored tests.
No scientific fixture or expected moral outcome is changed or generated.

[Descriptive] Initial targeted fixture diagnostics and the mutation script's
initial whitespace-selector diagnostic are retained alongside the final passing
checks. Local unshare is kernel-denied; socket denial and the exact pushed-head
GitHub sudo-unshare result are reported separately. All prior evidence and actual
accounting remain intact. Final validation results are appended after closure.


[Descriptive] Final offline review checks PASS: Python3.11.17 full discovery1193tests/36existing skips/2375.690s; focused61tests/0skips/392.273s with outbound sockets denied; preservation140protected files/320retained episodes; separate30episode canned stand-in COMPLETE; fault probes partial1/exhaustion5/cap0attempts PASS; neutral stand-in COMPLETE inexactly2requests; all35evidence chains verified. All7targeted guard mutants cause exactly1assertion failure/0errors, with baseline/restoredPASS. Scripted all-scenario commandPASS. Runtime/frozen inputs and every prior evidence archive remain byte-identical to c4963480; actual provider accounting and durable state unchanged (step0.008324, OpenAI1.1411209749999984, attempts1/2used, no study/check3claim). No provider requests, spending, merge or launch. Evidence: docs/process/evidence/gateway-live-demo-review-tests-20261025/validation.json and acceptance.zip,7685802bytes/3421members/SHA256940181641f7c316ece4c2dedee8a1b1f139868312b0c07a87ac4452aaaa4f9e2; CRC and every3420member hash verified. Local kernel denies unshare; exact pushed-head namespace CI is recorded separately in the PR description. The evidence-helper diagnostics concern only console/report metadata shape and are preserved; no harness correction or test rerun resulted. Stop after pushing this review update and checking namespace CI; no merge or provider execution.
