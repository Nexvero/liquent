# LQ-2729: Database-backed staging promotion reconciliation runtime

## Decision

LQ-2729 composes the existing database unknown index, exact unknown reader, and
attempt journal into the controlled LQ-2728 runtime. All three adapters receive
the same caller-owned SQLAlchemy engine.

## Observable contract

- Composition requires one existing engine and one explicit settings path.
- The same engine backs candidate discovery, exact reload, and final recording.
- A durable unknown can be reconciled through one explicit runtime execution.
- A reconciled operation is absent from the next database-backed selection.
- An empty database remains neutral without provider access.
- Invalid engines and downstream wiring failures become detail-free
  composition unavailability.
- Closing the runtime does not dispose the caller-owned engine.

## Safety boundary

Database composition grants no authority and creates no attempt, user,
workspace, membership, or role. It only connects existing read and finalization
adapters to the already bounded runtime.

## Deliberate exclusions

LQ-2729 adds no engine construction, DSN source, migration, schema creation,
bootstrap, seed, transaction redesign, scheduler, loop, retry, route, CLI,
credential, secret, or deployment decision. Process-level wiring remains
separate.
