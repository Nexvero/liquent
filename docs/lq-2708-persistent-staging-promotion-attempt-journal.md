# LQ-2708: Persistent staging promotion attempt journal

## Decision

LQ-2708 implements the first transactional database adapter behind the
crash-safe promotion-attempt model. It persists only an already validated
`PreparedStagingResearchIndexPromotionAttempt` and the transition from that
exact attempt to `write_started`.

The adapter is a journal, not an authority resolver. Creating a prepared
domain value remains the responsibility of the later composition that freshly
resolves evidence, candidate, operator authority, and target from their
systems of record. A session principal identifies the actor but grants no
promotion authority.

## Observable contract

- `record_prepared` atomically writes the immutable attempt binding and its
  first `prepared` event.
- An exact retry for the same operation and binding is idempotent.
- Reuse of an operation identifier with any different actor, evidence,
  candidate, origin, or target fails closed.
- A partial attempt without its exact first event is never accepted as a
  successful retry.
- `mark_write_started` accepts only the exact persisted prepared binding.
- The `write_started` event is committed before any later provider call may
  begin.
- An exact repeated `mark_write_started` call is idempotent and does not append
  another event.
- Missing, substituted, reordered, malformed, or already advanced journal
  state fails closed.
- Caller-supplied allow values, roles, candidate values, origins, and targets
  are not accepted by this boundary.
- Technical storage failures are reduced to one detail-free unavailability
  result.
- Database identity and connection details are not exposed by representation
  or failure text.

## Transaction boundary

The attempt row and initial event share one database transaction. The
write-started transition verifies the immutable row and complete ordered event
prefix in the same transaction that appends the second event. Consequently,
a later provider adapter can rely on a durable write-started marker before
performing an external mutation.

This slice does not claim a distributed transaction with an external
provider. If a later provider invocation has no conclusive result, the next
slice must record the separate unknown-effect state and prohibit blind retry.

## Deliberate exclusions

LQ-2708 does not:

- resolve current evidence, candidate, authority, or target;
- grant authority from authentication, membership, or research permissions;
- invoke a deployment or promotion provider;
- record unknown effects or committed receipts;
- reconcile provider state or schedule retries;
- add schema, migration, route, CLI, worker, secret, or deployment decisions.

Those responsibilities remain explicit later slices. In particular,
unknown-effect persistence and receipt reconciliation must not be inferred
from the existence of a write-started event.
