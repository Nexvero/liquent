# LQ-2733: Owned staging promotion reconciliation process

## Decision

LQ-2733 composes the secure LQ-2732 process-settings source, the existing
database engine factory, and the LQ-2730 one-shot operation. Each invocation
owns exactly one engine and disposes it before returning.

## Observable contract

- One explicit settings path is loaded exactly once.
- One engine is created from the validated database URL.
- The provider settings path and engine are passed to one one-shot execution.
- Neutral absence and exact receipts pass through unchanged.
- The engine is disposed after success, absence, or failure.
- Unknown results and downstream failures become detail-free process
  unavailability.
- Settings failure creates no engine and executes no reconciliation.

## Safety boundary

Process ownership covers resource lifetime only. It grants no promotion
authority, performs no migration or bootstrap, and does not repeat work.

## Deliberate exclusions

LQ-2733 adds no migration, schema creation, bootstrap, readiness gate, CLI,
route, signal handling, scheduler, worker, polling, retry, environment lookup,
or deployment decision. External invocation and schema readiness remain
separate.
