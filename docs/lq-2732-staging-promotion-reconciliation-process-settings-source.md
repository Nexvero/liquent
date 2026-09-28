# LQ-2732: Staging promotion reconciliation process settings source

## Decision

LQ-2732 loads the complete LQ-2731 process settings from one explicit
owner-private file. The file contains exactly the provider-settings path and
database URL projections.

## Observable contract

- The source accepts only an absolute, non-root path without parent traversal.
- The target is a regular owner-held mode-0600 file with one hard link.
- Symbolic links and inheritable descriptors fail closed.
- Content is stable, UTF-8, newline-terminated, and bounded to 8 KiB.
- Both prefixed keys occur exactly once; missing, duplicate, and extra keys fail.
- Value validation remains delegated to LQ-2731.
- All source failures become detail-free process-settings unavailability.

## Safety boundary

The source reads configuration only. It does not expose the database URL in
representation, create an engine, open a database connection, or trigger
reconciliation.

## Deliberate exclusions

LQ-2732 adds no environment lookup, default path, file creation, reload,
watcher, engine construction, migration, bootstrap, CLI, route, trigger,
scheduler, worker, retry, or deployment decision. Process composition remains
separate.
