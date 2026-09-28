# LQ-2730: One-shot staging promotion reconciliation

## Decision

LQ-2730 exposes one explicit process-neutral operation that composes the
database-backed LQ-2729 runtime, executes at most one reconciliation, and closes
the runtime before returning.

## Observable contract

- One invocation composes exactly one runtime.
- The runtime receives the caller-supplied settings path and engine unchanged.
- Execution occurs exactly once and returns either neutral absence or the exact
  durable receipt.
- Unknown result types fail closed.
- The runtime is closed after success, absence, or failure.
- Failures become detail-free one-shot unavailability.

## Safety boundary

The operation is a manual boundary, not a trigger or authority source. It does
not claim, initiate, repeat, or retry promotion work, and it does not own the
database engine.

## Deliberate exclusions

LQ-2730 adds no loop, scheduler, worker, polling, timer, signal handler, CLI,
route, startup hook, DSN source, engine construction, credential, secret,
schema, migration, bootstrap, or deployment decision. External triggering
remains separate.
