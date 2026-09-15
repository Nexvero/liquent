# LQ-2679 — Staging Research-index evidence writer

## Outcome

This slice adds a local owner-private, no-replace writer for the canonical
sanitized acceptance evidence defined by LQ-2678.

## Storage boundary

The writer accepts one absolute target path and one exact validated three-stage
handoff. It encodes the evidence before opening storage. The target parent must
already exist as a real directory, be owned by the effective process user, and
have exact mode `0700`.

The parent is held by descriptor without following a symbolic link. The target
is created relative to that descriptor with exclusive creation, no symlink
following, close-on-exec, and exact mode `0600`. Existing paths are never
replaced, including symbolic links.

The canonical bytes are written completely. Zero-length writes and all partial
technical failures fail closed. The file is synchronized before close and the
held directory is synchronized before success is returned. If publication has
not completed, an exclusively created partial file is removed through the held
directory descriptor.

## Failure semantics

Invalid paths, unsafe parent facts, conflicts, encoding failures, short writes,
and filesystem failures collapse to one detail-free storage-unavailable signal.
No successful return is possible for partial, replaced, or non-private evidence.

## Exclusions

The writer does not create directories, choose a path, read evidence, list
evidence, retain credentials, acquire responses, revoke access, restore state,
execute staging checks, deploy, or promote. The evidence remains non-authority:
storage does not turn an acceptance result into permission to mutate a system.

## Next slice

A later slice may add a bounded owner-private reader using the same descriptor
and canonical-validation boundary. Real execution and promotion remain separate.
