# LQ-2753: Staging promotion reconciliation operator-boundary acceptance

## Status

Completed as a persistent SQLite and real CLI-composition acceptance audit. The
slice adds no new production code, command, provider behavior or authority.

## Verified state transitions

The acceptance coverage starts from one exact durable unknown-effect attempt
and uses the installed command implementations with private process/provider
settings and the real migration head.

For an exact committed provider observation it proves:

```text
`pending` → `reconciled` → `idle`
```

The sequence performs exactly one provider request, records one exact durable
reconciliation and removes the operation from the current unknown-effect index.
No operation identity crosses either CLI presentation boundary.

For a provider observation that remains pending it proves:

```text
`pending` → `idle` → `pending`
```

The sequence performs exactly one provider request and records no durable
reconciliation. The original unknown-effect candidate remains eligible. This
closes an ambiguity in the operator wording: reconciliation `idle` means only
that the bounded pass recorded no reconciliation. It does not prove that the
candidate index is empty.

## Operational boundary

The runbook and the historical outcome/CLI contract now use the narrower,
accurate meaning of `idle`. A later candidate audit is a new read-only snapshot.
It does not grant retry authority, reconciliation authority, promotion authority
or deployment authority. Every further reconciliation invocation still requires
a new explicit operator decision.

The audit adds no scheduler, loop, implicit retry, provider mutation, database
bootstrap, migration behavior, settings discovery, log sink or deployment
automation.
