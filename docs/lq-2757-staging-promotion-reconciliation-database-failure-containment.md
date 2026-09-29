# LQ-2757: Staging promotion reconciliation database failure containment

## Status

Completed as a persistent SQLite and real CLI-composition acceptance audit.
The slice adds tests and documentation only; it changes no production runtime.

## Verified containment

The acceptance coverage starts from the installed LQ-2755 fixture with private
settings, a real migrated SQLite database and one exact unknown-effect
candidate. It then makes the configured database target unavailable while
retaining the original durable database for direct postcondition inspection.

Readiness, candidate audit and reconciliation each return only `unavailable`.
The three bounded invocations perform no provider request and expose neither
database path, database URL nor operation identity.

The failed commands record no durable reconciliation. Direct inspection of the
preserved database confirms that the candidate remains pending in the
unknown-effect index and is available only for a later fresh operator audit
after external database recovery.

## Closed authority boundary

The audit adds no repair or retry authority. It does not recreate, migrate,
replace or reconnect the configured database, contact the provider or start
another reconciliation. It grants neither promotion nor deployment authority
and introduces no command, trigger, scheduler, service or automation.
