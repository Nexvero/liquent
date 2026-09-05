# LQ-628 — One-shot supervisor child process

## Status

Implemented as `OneShotManifestHandoffSupervisorChildProcess` with separate
Writer and Recovery entry methods.

## Implementation

Construction is inert and accepts only process-owned dependencies and wait
bounds. Each profile entry rejects the other profile before load or Ready.

The loader returns the canonical typed document already bound by LQ-625. The
child publishes Ready from that document's gate, polls only the existing
`await_release` boundary, publishes Consumed, and then constructs the existing
prepared and execution types from the document's handle, claim, owner, request,
and gate.

The existing controlled executor performs the capability. The child accepts
only the exact profile-specific executed value and publishes Terminal from its
correlated outcome. It does not inspect Docker, persist parent state, fabricate
an outcome, or reinterpret authority.

## Closed behavior

Wrong expectations, profiles, document requests, clock values, token types,
execution results, and terminal results fail detail-free. Gate conflicts are
returned without later effects. Dependencies and numeric bounds are absent from
`repr`.

LQ-629 provides executable ordering and no-effect evidence.
