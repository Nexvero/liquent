# LQ-2731: Staging promotion reconciliation process settings

## Decision

LQ-2731 defines one closed immutable value containing the explicit provider
settings file and database URL needed by a future process composition. The
complete mapping has exactly those two fields and no defaults.

## Observable contract

- The provider settings path is absolute, non-root, canonical, and bounded.
- The database URL is bounded and uses an already supported SQLite or
  PostgreSQL driver.
- Missing, extra, malformed, and non-string values fail closed.
- Representation hides both path and database URL.
- Invalid input becomes detail-free settings unavailability.
- The value is immutable and retains no caller mapping.

## Safety boundary

Configuration identifies resources but grants no authority, trigger, retry, or
promotion capability. The database URL may contain credentials and is therefore
never included in representation.

## Deliberate exclusions

LQ-2731 adds no settings source, environment lookup, default, engine creation,
connection, migration, bootstrap, CLI, route, trigger, scheduler, worker,
polling, retry, or deployment decision. Secure sourcing and process composition
remain separate.
