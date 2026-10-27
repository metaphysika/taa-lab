[Descriptive] Chris (2026-10-27) accepts the continuation1 guard stop and authorizes this offline repair. Before other work, read-only checks confirmed the stop's observed/current origin tip `6d5523ad58aebdc74b0071b1e423efe7ba731220` is exactly the parent of local settlement `a162e12295d6003de2341569e4fe47bffe79583d`. Every426commit since the previous stop is accounted for by the lease, claim and retained ledger-change events; no other-writer commit was found. All state-history author/committer identities match the existing harness identity. Native usage, source checkpoints, balances, both stopped episodes and markers remain unchanged. The precise underlying sanitized Git failure is not retained.

[Descriptive] Owner-approved results commit59202b84 is now included in results-only PR41 through ordinary mergecbfd701d, preserving both result histories. The repeated credential scan covered all23changed files, both raw archives and326decoded replies: zero matches/no sealedHmaterial. PR41 remains draft/unmerged until Claude and Astra review the completed pilot. Runtime changes are in this separate PR.

[Descriptive] A failed state push or unavailable acknowledgement enters three delayed rounds, waiting10/30/60seconds before each read-only fetch. An observed exact fixed commit confirms publication. Its exact parent permits one ordinary fast-forward re-push of the SAME SHA, followed by another read-only observation, even if that re-push acknowledgement failed. A parent still observed, or an unavailable observation, can advance to the next delayed round; an observed foreign tip stops immediately. Three re-pushes maximum in the operation (four pushes including the initial attempt); no force flag, new commit, reset or foreign-tip overwrite. Local clean/head/parent/state validity is rechecked before each re-push. A known foreign tip seen during the normal post-push check also stops immediately. Every delayed wait, observation (including the observed SHA), re-push intent and re-push result is fsynced into the run journal before further work. Evidence failure/interruption preserves the stopped lease and blocks cleanup/provider requests.

[Descriptive] Continuation2 still needs Chris's receipt for the exact reviewed new code commit. It binds both retained roots, checkpoints `e93bf0e39fd5c00bc2ee0438e9504a5597578b0dff0de36484cf5781543bfc05` and `e83d50ea84f019ba14438af8d870dcac29b243a21a8f89acb8643844fe786d32`, ordinal2 and start_index54. No new receipt field or scientific input is added. A narrowly bound startup exception permits ONLY locala162e122 with exact parent6d5523ad, the second checkpoint above, start54 and a Google-settlement-only two-ledger-file change. Full prior evidence/markers/native-accounting validation is required; arbitrary dirty/ahead/foreign state stays blocked. If already published at that exact settlement, startup proceeds without re-pushing it.

[Descriptive] Under the common flock, after verifying the retained lease against the previous marker and before taking a new lease/claiming continuation2, the harness records the stranded settlement and uses the same delayed recovery rule to publish it. Thus local/published settled balances agree before any new provider request, and the old reply is never processed again. No real state mutation is made by this offline task. A failed bootstrap stops for review; the CLI is not automatically restarted. The existing per-request root/child-chain and reservation/settlement audit remains in force. Index53=P06/conventional/Google/r3 stays a guard stop with its retained reply; index22 remains stopped too. New execution starts only at index54. No markers move, no reserve is manually rewritten, no episode is replaced or rescored.

[Descriptive] Tests use disposable bare Git remotes, denied Python sockets and mocked waits only: same-SHA re-push success from parent, exact arrival despite lost acknowledgement, foreign tip with no re-push, maximumthree re-pushes, and stranded publication before first request. Two retained fixture roots cover indices0–22 and23–53; continuation2 requests only54/55 and preserves every earlier byte. A foreign bootstrap tip admits neither push nor request. Engineering fixtures do not generate scientific expected outcomes. Full/focused/scripted/396stand-in and preservation results follow in the notebook and verification artifact. No model call, H access, science/prompt/measure/default/cap change or continuation2 execution approval.

[Descriptive] Each delayed round permits at most one re-push, followed by an immediate fetch. There can therefore be at most six recovery observations and three re-pushes for a failed publication. An unavailable observation never authorizes a push. The normal initial push is separate from those three re-pushes. A known foreign tip stops without waiting for another round. Publication of the stranded settlement creates no new commit and changes no balance: it sends the existing settlement exactly as recorded.

[Proposal] For a later, separately approved continuation 2, the receipt would bind the reviewed full code commit, both original source checkpoints, ordinal 2 and index 54. The following placeholder is not launch approval:

```json
{
  "owner": "Chris",
  "commit": "<reviewed full new commit>",
  "step": "experiment-a-v01",
  "launch_approved": true,
  "model_returned": {"anthropic": "claude-sonnet-5-5", "google": "gemini-3.8-flash"},
  "continuation": 2,
  "source_checkpoints": [
    "e93bf0e39fd5c00bc2ee0438e9504a5597578b0dff0de36484cf5781543bfc05",
    "e83d50ea84f019ba14438af8d870dcac29b243a21a8f89acb8643844fe786d32"
  ],
  "start_index": 54
}
```

[Proposal] After Chris approves the exact new commit, use a clean detached checkout of that commit and both prior evidence roots, passing `--continue-from` twice and `--continuation 2` to the existing CLI. State must be clean and current, with only the specifically bound stranded settlement allowed to be ahead until startup publishes it. Neither this document nor merging the fix authorizes that command. Models, reasoning defaults and caps remain unchanged; H stays sealed. A further stop requires review and fresh approval, with no automatic CLI restart.

[Descriptive] Final validation passed: **1,856 tests with 36 existing optional skips**, **107 focused tests**, scripted scenarios, preservation of 140 protected files and the original 320 episodes, and **396 canned episodes / 397 chains** with sockets denied. All 396 request bodies and complete episode rows match the accepted stand-in. Read-only real preflight verifies 54 source rows, next index 54, the exact pending settlement and unchanged state bytes, markers and lease. Strict ordinary startup still refuses the ahead state. [Verification, source hashes and retained logs](evidence/experiment-a-repush-v042/verification.json). No real state recovery or model request ran.
