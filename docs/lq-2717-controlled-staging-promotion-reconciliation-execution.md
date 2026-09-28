# LQ-2717: Controlled staging promotion reconciliation execution

## Decision

LQ-2717 composes candidate selection with the existing single-operation
reconciliation boundary. One invocation selects and processes at most one
durable Unknown operation. It never loops over the index and never retries a
provider mutation.

Selection remains separate from execution. The selected identity is reloaded
through LQ-2714, so an index result cannot bypass exact durable-history
validation or supply authority.

## Observable contract

- The candidate selector is invoked exactly once.
- Neutral absence returns without loading or observing an operation.
- At most the first selected operation is passed to LQ-2714.
- A committed trusted observation returns the exact durable receipt.
- No committed observation returns neutral absence without recording.
- Selection, reader, observer, and recorder failures become detail-free
  execution unavailability.
- An inconsistent operation result fails closed.
- One invocation performs no loop, retry, claim, or batch processing.

## Safety boundary

This execution reconciles an uncertain prior effect; it does not initiate or
repeat promotion. Candidate identity is not authority, ownership, or proof of
provider success. LQ-2714 reloads the complete Unknown value before the trusted
observer can run.

Concurrent executions may select the same candidate. The observer is read-only
and the reconciliation recorder remains responsible for exact idempotence.
This slice makes no exclusivity or fairness guarantee.

## Deliberate exclusions

LQ-2717 adds no claim, lease, lock, cursor, loop, scheduler, worker, concrete
provider adapter, automatic retry, route, CLI, schema, migration, credential,
secret, or deployment decision. Production triggering and provider transport
remain separate later slices.
