# Retained-log replay / audit window v0.2.0

Generate static pages from the retained scoring archive; no policy, oracle or episode is executed.

```sh
python -m replay.build --validation docs/process/evidence/gateway-cross-arm-scoring-v02/validation.json --output /tmp/new-taa-replay
```

The output directory must be new. Open index.html locally. The builder checks the archive and every member checksum, then validates retained before/after state changes. V0.2 pages use actual initial channels, host inputs, changes and projected event rows directly, without importing controllers or decoding a new schedule. Comparison pages show the same program/controller across arms and filter by observed step.

The independently implemented conventional arm exports a projected log with a signed ending checkpoint. A later snapshot replaces that ending checkpoint with new event rows and a new checkpoint. The viewer preserves and displays both sides of that projected tail change; it does not mistake it for an append-only authenticated native stream. No HMAC authentication or independently retained native ending checkpoint is claimed for the scoring archive.

Historical v0.1 input remains supported with its explicitly missing channels. It needs the hash-pinned input schedule sources, and never reconstructs missing token or report states from the final oracle board. The original v0.1.1 artifact and its source checkpoint f0e40cc1 remain preserved.

For a separately retained native core JSONL log and independent ending checkpoint:

```sh
python -m replay.build --native-log /tmp/episode.jsonl --trusted-checkpoint /tmp/checkpoint.json --output /tmp/new-native-view
```

That mode checks canonical encoding, sequence, hashes and the supplied ending count/head, but does not authenticate the HMAC or the host. Keys are never read or included. Pages contain no remote assets or network requests. The supplementary measure is committed acts disallowed by the reference policy, defined after v0 results, development only and to be pre-registered before Experiment A. ALTERNATIVE remains separate.
