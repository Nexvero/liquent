# LQ-641 — Observation-only Release service

## Status

Implemented as `ObservationOnlyManifestHandoffSupervisorReleaseService` for
Writer and Recovery.

## Implementation

The service accepts only prepared, release-committed, or running states with one
stable Release ID. It resolves the exact persistent runtime and gate before any
new effect.

For the initial transition it commits Release first, publishes exactly one
canonical Release-token file, and persists those actual publication facts.
Retries reuse an exact persisted token and never republish a divergent token.

It then calls only `record_consumed` on the direct observation bridge. Absence
returns without engine inspection or Running transition. Exact child Consumed is
required before direct engine `running` and the existing Running journal record.

The source contains no `await_release`, `publish_consumed`, Writer/Recovery
execute, or Terminal publish path. It therefore cannot duplicate child-owned
capability effects.

LQ-642 closes the parallel service strand and records the remaining wiring
boundary.
