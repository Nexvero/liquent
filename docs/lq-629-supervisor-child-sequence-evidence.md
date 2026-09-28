# LQ-629 — Supervisor child sequence evidence

## Status

Implemented as executable Writer, Recovery, timeout, and cross-profile evidence.

## Evidence

Both profiles record exactly this event trace:

`load, ready, await, sleep, await, consumed, execute, terminal`

The tests construct real domain Ready, accepted token, Released, execution,
executed outcome, and Completed gate values. Consequently the trace is guarded by
the existing handle, profile, claim, owner, artifact-role, and correlation
validators rather than permissive mocks alone.

A bounded timeout proves that the trace stops after `load, ready, await`; no
Consumed, execution, or terminal method is reached. A Recovery entry with a
Writer expectation fails before loader or wrapper interaction.

Focused coverage also retains the read-only loader, gate wrapper, capability
contract, and controlled executor tests. No Docker daemon, network, database,
subprocess, migration, CLI, or deployment is used.

LQ-630 performs the full completion audit.
