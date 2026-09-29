# LQ-2758: Staging promotion reconciliation schema mismatch containment

## Status

Completed as a persistent SQLite and real CLI-composition acceptance audit.
The slice adds tests and documentation only; it changes no production runtime.

## Verified containment

The acceptance coverage starts from the installed LQ-2755 fixture with private
settings, a real migrated SQLite database and one exact unknown-effect
candidate. It then changes only the recorded Alembic revision so that the
database reports a schema revision mismatch while retaining all durable rows.

Readiness, candidate audit and reconciliation each return only `unavailable`.
The three bounded invocations perform no provider request and expose neither
database URL, operation identity nor the unexpected revision.

The failed commands record no durable reconciliation. Direct inspection of the
database confirms that the candidate remains pending in the unknown-effect
index and is available only for a later fresh operator audit after an external
schema correction.

## Closed authority boundary

The audit adds no migration or retry authority. It does not upgrade, downgrade,
stamp, repair or replace the database, contact the provider or start another
reconciliation. It grants neither promotion nor deployment authority and
introduces no command, trigger, scheduler, service or automation.
