# LQ-2714: Staging promotion reconciliation operation

## Decision

LQ-2714 composes persistent unknown-attempt resolution with trusted outcome
observation for one explicitly identified operation. The input is only an
opaque operation identity. No receipt, success flag, role, target, or authority
claim enters through this boundary.

The operation first resolves the durable unknown value from the system of
record. Only an exact result bound to the requested operation is passed to the
trusted reconciliation flow from LQ-2712.

## Observable contract

- The caller supplies one valid opaque operation identity.
- The persistent unknown resolver is called exactly once.
- Missing, incomplete, or already completed operations return neutral absence
  without contacting the outcome observer.
- A resolved unknown value must be exact and bound to the requested operation.
- The trusted observer and reconciliation recorder are invoked only after that
  validation.
- No committed observation returns neutral absence and leaves persistence
  unchanged.
- A matching committed observation returns the exact recorded receipt.
- Substituted resolver results, malformed identifiers, observer failures,
  recorder failures, and inconsistent return values fail closed with
  detail-free unavailability.
- The operation performs no scan, claim, retry, or batch processing.

## Safety boundary

This composition triggers observation, not promotion. It cannot replay the
provider mutation and cannot turn absence into success. Its operation identity
is a lookup key, not authority. Authentication, membership, or a caller role is
neither accepted nor inferred.

Each invocation reloads durable state and observes provider state afresh. A
completed operation becomes neutral on later calls because the unknown reader
no longer resolves it.

## Deliberate exclusions

LQ-2714 adds no operation enumeration, queue claim, lease, scheduler, worker,
route, CLI, concrete provider adapter, automatic retry, schema, migration,
credential, secret, or deployment decision. Operational discovery and provider
transport remain explicit later slices.
