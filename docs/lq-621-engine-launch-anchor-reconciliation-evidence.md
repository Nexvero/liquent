# LQ-621 — Engine launch anchor reconciliation evidence

## Status

Implemented as focused executable evidence over the real local Docker HTTP
translation and engine adapter.

## Evidence

The tests prove that a fresh create emits the exact six-label set and returns the
same launch identifier and digest in its acknowledgement. A retry finding one
exactly matching container adopts it without issuing another create.

Independent cases mutate only the launch document identifier or only its digest.
Both return the existing engine conflict and leave the transport call sequence at
find plus inspect. No create follows the divergent observation.

Digest boundary cases reject uppercase, shortened, non-hexadecimal, and prefixed
values. Existing security-profile, terminal-state, bounded-response,
owner/reader-policy, and detail-free failure evidence remains green.

## Scope boundary

The evidence uses no Docker daemon, network, database, migration, CLI, settings,
or deployment. LQ-622 performs the completion and regression audit.
