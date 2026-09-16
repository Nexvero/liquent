# LQ-2710: Persistent staging promotion commit receipt

## Decision

LQ-2710 adds durable recording of a conclusively committed staging promotion.
The journal accepts a receipt only for the exact persisted write-started
attempt. Every immutable binding in the receipt must match the operation,
actor, evidence, candidate, staging origin, and target already stored for that
attempt.

A committed event represents a confirmed provider outcome. It is not created
from absence, timeout, or an unknown effect, and it grants no authority for a
later operation.

## Observable contract

- `record_committed` accepts only a typed write-started attempt and typed
  receipt.
- The receipt must reproduce the complete immutable attempt binding exactly.
- The persisted journal prefix must be `prepared`, then `write_started`.
- The committed event and receipt identity are appended transactionally as the
  third event.
- An exact repetition is idempotent and creates no duplicate event.
- A different receipt, substituted binding, missing attempt, malformed order,
  or later state fails closed.
- `effect_unknown` cannot be rewritten to committed by this boundary.
- Receipt identity is present only on the committed event.
- Technical persistence failures remain detail-free.

## Safety boundary

The adapter records a conclusion supplied by a later trusted provider
composition. It does not invoke a provider, infer completion, resolve current
authority, or reconcile uncertainty. The receipt proves only the recorded
effect for this exact operation and is never reusable authorization.

Authentication continues to identify only the actor. All promotion authority
and target binding originate from the earlier system-of-record resolution, not
from session data, receipt contents, or journal state.

## Deliberate exclusions

LQ-2710 adds no provider invocation, unknown-effect reconciliation, retry,
scheduler, worker, route, CLI, schema, migration, credential, secret, or
deployment decision. Trusted provider composition and reconciliation remain
separate later slices.
