# LQ-2740: Staging promotion reconciliation settings installation contract

## Decision

LQ-2740 defines a controlled installation boundary for the two owner-private
settings files required by the completed manual reconciliation strand. The
installer receives four explicit absolute paths: provider source, provider
target, process source and process target. It has no default directory and does
not run reconciliation.

## Source contract

Each source must already be a regular file owned by the effective installer
user, have mode `0600`, have exactly one hard link and be opened without
following symbolic links. The source descriptor must not be inheritable.

The provider source is bounded to 4 KiB and contains exactly one newline-ended
UTF-8 projection:

```text
LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=https://PROVIDER_HOST/STATUS_PATH
```

The process source is bounded to 8 KiB and contains exactly the two
newline-ended UTF-8 projections accepted by LQ-2732:

```text
LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE=/ABSOLUTE/PROVIDER_TARGET
LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL=DATABASE_URL
```

All existing LQ-2724, LQ-2725, LQ-2731 and LQ-2732 value and source validation
remains authoritative. The installer does not introduce a second endpoint or
database-URL grammar.

## Target contract

Both targets must be absolute, non-root paths without parent traversal. Their
parent directories must already exist as regular directories owned by the
effective installer user and must not be writable by group or others. Provider
and process targets must be distinct and must not alias either source.

Installation creates both targets with mode `0600`, the effective installer
owner and exactly one hard link. Existing targets, symbolic links, non-regular
objects and path replacement fail closed. No existing file is overwritten,
truncated, renamed aside or removed.

The process projection must reference the exact canonical provider target path.
A source reference to another provider file fails before either target becomes
visible.

## Ordered crash-safe visibility

Both source files are fully read and validated before target creation starts.
Temporary files are created privately in their respective target directories,
written completely, synchronized, revalidated and then published without
replacement. The provider target is published and synchronized first. The
process target is the activation record and is published last.

An interruption may leave a complete private provider target without a process
target. That state is inert because the reconciliation command receives only a
process-settings path. It is a neutral partial installation, never success and
never permission to overwrite the retained provider target. A visible process
target must therefore imply that its exact provider target was already durably
published.

Success is reported only after both target files and their parent-directory
publications are durably synchronized. The installer returns no file content,
endpoint, database URL or path beyond the caller's already supplied values.

## Concurrency and repeat invocation

Concurrent installers cannot share a temporary name or replace a winner.
Exactly one may publish each previously absent target. A later invocation
against either existing target, including an inert retained provider target, is
a neutral refusal, not idempotent success and not permission to compare or
disclose existing content.

## Safety boundary

Installation conveys configuration bytes only. It does not prove that the
provider or database is reachable, that an unknown attempt exists, or that the
caller has promotion authority. It creates no database engine or provider
client and performs no network, schema, migration or reconciliation operation.

## Failure surface

Invalid invocation and neutral target presence remain distinguishable to a
future presentation boundary. Every path, metadata, race, content, validation,
write, synchronization and publication failure is otherwise reduced to one
detail-free technical-unavailability outcome. No new exception name is fixed
by this contract.

## Deliberate exclusions

LQ-2740 adds no implementation, shell command, installed entry point, default
path, environment lookup, settings value, credential, secret manager, file
rotation, update, orphan cleanup, deletion, rollback, reconciliation trigger, retry, timer,
service, worker, route, schema, migration, bootstrap or deployment decision.
Implementation remains the next separate slice.
