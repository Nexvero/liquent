# LQ-2680 — Staging Research-index evidence reader

## Outcome

This slice adds the bounded owner-private reader corresponding to the LQ-2679
writer and LQ-2678 canonical evidence codec.

## Read boundary

The reader accepts one explicit absolute path. Its parent must be a real
owner-owned directory with exact mode `0700`. The parent and evidence file are
opened with close-on-exec and no symbolic-link following, and the child is
resolved relative to the held parent descriptor.

The evidence must be a regular owner-owned single-link file with exact mode
`0600`, a positive size, and at most 8192 bytes. Reads are bounded independently
of the advertised size. Device, inode, mode, owner, link count, and size must
remain unchanged across the read, and the bytes read must equal the held
descriptor's size.

Only the LQ-2678 decoder may turn bytes into a successful value. It repeats
canonical byte validation, closed type reconstruction, same-run handoff
validation, and final outcome recomputation.

## Failure semantics

Missing paths, unsafe metadata, links, oversize, short or changing reads,
malformed bytes, noncanonical bytes, and decode failures collapse to the same
detail-free storage-unavailable signal as writing. No parser, path, operating
system, evidence, credential, response, or operator detail is returned.

## Exclusions

The reader does not create, replace, repair, delete, list, retain, or mutate
evidence. It performs no network access, acquisition, credential lookup,
revocation, restore, staging execution, deployment, or promotion. Decoded
evidence remains an observation and grants no authority.

## Next slice

A later slice may compose exact staged acquisition, handoff evaluation, and
owner-private evidence publication. Real promotion remains separate.
