# Live-demo design choices — no launch approval

[OPEN DESIGN / 2026-10-24] Claude’s review of the MCP front notes that the session decision-log resource is readable by the client. Whether a model under test may read it must be fixed in the demo protocol before any live episode, rather than left to the interface’s availability or the model’s choice. Record the permitted resource/tool surface, enforcement and arm-specific differences prospectively. Do not select visibility after seeing outcomes.

The current MCP interface exposes taa://session/decision-log to its authenticated local client. This document does not choose the experimental condition, connect a model, change the interface, authorize spending or approve a launch commit. Chris must approve each paid step and exact launch commit; Claude reviews the protocol and Astra reviews independently.
