# LQ-627 — Child-owned supervisor sequence contract

## Status

Accepted as the closed one-shot sequence for one already-created wrapper child.

## Required order

The child must complete these transitions in order:

1. load and externally verify the immutable launch document;
2. publish the bound Ready artifact;
3. wait within a process-owned bound for the matching Release token;
4. publish Release Consumed;
5. construct the existing profile-specific prepared/execution value;
6. invoke exactly one existing capability executor;
7. publish the correlated terminal envelope.

No stage may be skipped or supplied as a caller boolean. A `SessionPrincipal`,
role, membership, permission, environment value, or label does not authorize
execution. The only execution capability remains the structurally valid
`ReleasedManifestHandoffSupervisorGateWrapper`.

## Waiting and failure

The release wait uses injected monotonic time, a positive maximum duration, a
positive bounded polling interval, and an injected sleeper. Wall time is read
only after Release Consumed to timestamp the prepared process and must be aware
UTC.

Absence before the deadline is not Release. Timeout, regressing or malformed
clocks, malformed stages, and dependency failures remain existing detail-free
technical unavailability. A timeout does not consume, execute, or publish a
terminal outcome.

Gate-artifact conflicts remain neutral closed conflicts and never advance to the
next effect.

## Scope

This contract introduces no process entrypoint, settings, CLI, Compose,
application-factory, Docker wiring, persistence, migration, or parent cutover.
LQ-628 implements the isolated child orchestrator.
