# LQ-2736: Staging promotion reconciliation CLI

## Decision

LQ-2736 defines a minimal presentation boundary for LQ-2735. It accepts exactly
one absolute process-settings path and emits only fixed status tokens.

## Observable contract

- Exactly one absolute, non-root path without parent traversal is accepted.
- `IDLE` writes `idle` to stdout and exits zero.
- `RECONCILED` writes `reconciled` to stdout and exits zero.
- Technical unavailability writes only `unavailable` to stderr and exits one.
- Invalid invocation writes only `invalid_invocation` to stderr and exits two.
- Unknown outcomes fail closed as technical unavailability.
- No receipt, operation, path, DSN, credential, or provider detail is emitted.

## Safety boundary

The CLI presents an existing bounded operation. It grants no authority and
does not add retry, looping, migration, bootstrap, or implicit configuration.

## Deliberate exclusions

LQ-2736 adds no installed script entry, packaging wiring, shell wrapper,
scheduler, service unit, route, metric, log sink, retry, or deployment decision.
Installation and invocation remain separate.
