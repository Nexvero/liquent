# LQ-2754: Staging promotion reconciliation operator rehearsal

## Status

Completed as one closed acceptance rehearsal across the already installed
operator commands. The slice adds no new production code, command, runtime
trigger or authority.

## Rehearsed chain

The persistent acceptance coverage creates private source settings, installs
them without replacement, migrates a real SQLite database to the current head,
records one exact unknown-effect attempt and executes the real CLI compositions
in runbook order:

```text
`installed` → `ready` → `pending` → `reconciled` → `idle`
```

The same sources are then submitted to the installation command again. The
existing targets remain unchanged and the command returns the neutral
`present` result.

## Verified boundaries

The rehearsal proves that the complete manual command chain:

- accepts the provider/process pair produced by the no-replace installer;
- observes the installed process settings as ready;
- observes exactly one eligible durable candidate;
- performs exactly one provider request during the bounded reconciliation;
- records one exact durable reconciliation;
- removes the reconciled operation from the current unknown-effect index;
- returns to a detail-free `idle` candidate audit;
- preserves no-replace installation behavior on a repeated attempt;
- exposes no settings path, endpoint, database URL or operation identity.

The rehearsal does not grant reconciliation authority. The test's invocation is
only fixture-scoped acceptance evidence; a real invocation still requires the
explicit operator decision already required by the runbook. It does not grant promotion or deployment authority.

No scheduler, loop, automatic retry, settings discovery, provider mutation,
database bootstrap, log sink or deployment automation is introduced.
