# LQ-2709: Persistent staging promotion unknown effect

## Decision

LQ-2709 extends the transactional attempt journal with the durable
`effect_unknown` transition. This state is used only after the exact promotion
attempt was persisted as `write_started` and the caller cannot prove whether
the external provider applied the mutation.

Unknown is a safety state, not a failure permission. It blocks blind retry and
preserves the original actor, evidence, candidate, origin, and target binding
for later reconciliation.

## Observable contract

- `record_unknown` accepts only a typed write-started attempt.
- The persisted immutable attempt binding must match that nested attempt
  exactly.
- The complete journal prefix must be `prepared`, then `write_started`.
- The adapter appends `effect_unknown` as the third event in the same database
  transaction that validates the prefix.
- An exact repetition is idempotent and does not append another event.
- Missing, substituted, reordered, malformed, or later state fails closed.
- The unknown event cannot carry a provider receipt.
- The unknown state grants no authority and exposes no retry operation.
- Technical persistence failures remain detail-free.

## Safety boundary

The transition records uncertainty only. It does not infer success or failure,
contact the provider, produce a receipt, or choose a retry policy. A later
reconciler must inspect trusted provider state and bind any conclusion back to
the exact persisted operation.

Authentication still identifies only the actor. Current promotion authority
must have been resolved from the system of record before preparation; neither
session data nor this journal state grants authority.

## Deliberate exclusions

LQ-2709 adds no provider invocation, reconciliation, committed receipt,
automatic retry, scheduler, worker, route, CLI, schema, migration, secret, or
deployment decision. Receipt persistence and unknown-effect reconciliation
remain explicit later slices.
