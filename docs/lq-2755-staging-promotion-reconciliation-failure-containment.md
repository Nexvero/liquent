# LQ-2755: Staging promotion reconciliation failure containment

## Status

Completed as a persistent SQLite and real CLI-composition failure-path audit.
The slice adds no production code, command, runtime trigger or authority.

## Verified failure transitions

The acceptance coverage installs a private provider/process settings pair,
migrates a real SQLite database to the current head and records one exact
unknown-effect candidate. It then exercises two independent provider failures:

- a provider HTTP failure with a private response detail;
- a malformed provider response with a private operation-like detail.

Both cases prove the same closed transition:

```text
`ready` → `pending` → `unavailable` → `pending`
```

Each bounded reconciliation attempt performs exactly one provider request. The
CLI exposes only `unavailable`, records no durable reconciliation and leaves the
original unknown-effect candidate eligible for a later fresh audit.

## Containment boundary

Neither the operation identity nor any response body detail crosses the CLI
boundary. The HTTP status, decoder error and exception chain remain private.
The failed invocation does not remove, replace, claim or mutate the durable
candidate.

An `unavailable` result grants no automatic retry authority. A later candidate
audit is only a fresh read-only snapshot, and any later reconciliation still
requires a new explicit operator decision. The audit grants neither promotion
nor deployment authority.

No scheduler, loop, retry policy, provider mutation, settings discovery,
database bootstrap, log sink or deployment automation is introduced.
