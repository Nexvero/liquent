# LQ-2734: Readiness-gated staging promotion reconciliation process

## Decision

LQ-2734 places the existing database readiness probe in front of one-shot
staging promotion reconciliation. Execution is possible only when the database
is reachable and already at the expected migration head.

## Observable contract

- Process settings are loaded and one engine is created.
- The existing database readiness probe runs exactly once before execution.
- Only an exact ready result permits the one-shot operation.
- Database unavailability, schema mismatch, and malformed readiness fail closed
  without provider access or reconciliation.
- The process-owned engine is disposed in every outcome.
- Failures become detail-free ready-process unavailability.

## Safety boundary

Readiness is a prerequisite, not authority. The gate never applies migrations,
creates schema, bootstraps facts, or converts an unready database into ready.

## Deliberate exclusions

LQ-2734 adds no migration, schema creation, bootstrap, retry, waiting, loop,
scheduler, worker, CLI, route, signal handling, or deployment decision.
External invocation remains separate.
