# LQ-2712: Staging promotion reconciliation observation

## Decision

LQ-2712 defines the trusted observation boundary that precedes the persistent
reconciliation transition from LQ-2711. The caller supplies only the exact
unknown-effect value. It cannot supply a receipt, success flag, role, target,
or authority assertion.

A provider-facing observer receives the fully bound unknown attempt and may
return a committed observation containing the exact receipt and an aware
observation time. Neutral absence means that commitment is not currently
proven; the attempt remains unknown and no journal write occurs.

## Observable contract

- Reconciliation accepts only a typed unknown-effect value.
- The outcome observer is the sole source of a committed observation.
- The returned receipt must match operation, actor, evidence, candidate,
  staging origin, and target exactly.
- A matching observation is passed to the dedicated reconciliation recorder.
- The recorder must return the same exact receipt.
- No observation produces neutral absence and no mutation.
- Substituted observations, malformed values, observer failures, recorder
  failures, and inconsistent results fail closed with detail-free technical
  unavailability.
- Every call observes current provider state; no result is cached or reused.
- Neither observation nor receipt grants authority or permits retry.

## Safety boundary

This slice composes trusted observation and persistence but does not implement
provider I/O. It never converts ambiguity into success. Timeout, absence, or
technical failure leaves the durable `effect_unknown` history unchanged.

The session principal remains only the previously bound actor identity. The
observer must derive provider outcome from trusted state for the operation; it
must not accept caller-provided allow values or outcome claims.

## Deliberate exclusions

LQ-2712 adds no concrete provider reader, network protocol, negative outcome,
automatic retry, scheduler, worker, route, CLI, schema, migration, credential,
secret, or deployment decision. The provider adapter and operational trigger
remain explicit later slices.
