# LQ-2735: Staging promotion reconciliation process outcome

## Decision

LQ-2735 wraps the readiness-gated process in a minimal outcome boundary. A
successful invocation reveals only whether no candidate was available or one
operation was reconciled; technical failure remains detail-free unavailability.

## Observable contract

- The ready process is invoked exactly once with the supplied settings path.
- Neutral absence maps to `IDLE`.
- An exact durable receipt maps to `RECONCILED`.
- Receipt identity and content are not retained or exposed.
- Unknown results and technical failures fail closed.
- Failure details, DSNs, paths, and provider data do not cross the boundary.

## Safety boundary

An outcome is operational observation, not authority, permission, or a retry
instruction. `IDLE` and `RECONCILED` expose no receipt or operation identity.

## Deliberate exclusions

LQ-2735 adds no exit-code mapping, stdout or stderr format, CLI, route, metric,
log, scheduler, retry, loop, or deployment decision. External presentation
remains separate.
