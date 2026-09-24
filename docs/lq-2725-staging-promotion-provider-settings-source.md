# LQ-2725: Staging promotion provider settings source

## Decision

LQ-2725 loads the LQ-2724 endpoint settings from one explicit owner-private
file. The source accepts an absolute path supplied by trusted composition and
reads exactly one complete environment-style projection.

## Observable contract

- The source accepts only an absolute, non-root `Path` without parent traversal.
- The target is a regular, owner-held, mode-0600 file with one hard link.
- Symbolic links and inheritable descriptors fail closed.
- Content is bounded to 4 KiB and must be complete UTF-8 ending in one newline.
- The projection contains exactly the provider endpoint key and one value.
- Endpoint validation remains delegated to the closed LQ-2724 settings value.
- Invalid paths, metadata, content, races, and reads become detail-free
  settings unavailability.

## Safety boundary

The file is routing configuration, not a credential store, authority source,
or proof that provider content is trusted. Loading settings performs no network
request and does not create a client or observer.

## Deliberate exclusions

LQ-2725 adds no environment lookup, default path, file creation, credential,
secret, mutation, watcher, reload, retry, scheduler, startup wiring, route,
CLI, schema, migration, or deployment decision. Lifecycle composition remains
separate.
