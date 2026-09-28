# LQ-648 — Inert exclusive supervisor candidate composition

## Status

Implemented as `compose_candidate_manifest_handoff_supervisor_graph` and an
immutable candidate bundle.

## Composition

The function constructs one canonical control codec, one child file wrapper, one
read-only parent observer, one persistent exact-fact recorder, the parent launch
prefix, direct Ready completion, candidate Prepare, observation-only Release,
one child process, and one read-only execution reconciler.

Construction performs no dependency method call, database operation, file I/O,
engine request, clock read, sleep, or capability execution. Missing dependencies
and invalid wait bounds fail detail-free.

Only `OneShotManifestHandoffSupervisorChildProcess` receives
`child_capability_executor`. The parent Release receives the control publisher
for Release-token output but no executor. Compatibility services are not imported
or constructible from this function.

The returned type fixes `terminal_observation_complete` and `production_ready`
to false. LQ-649 provides executable dependency-exclusivity evidence.
