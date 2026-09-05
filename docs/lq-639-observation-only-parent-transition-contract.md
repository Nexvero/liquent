# LQ-639 — Observation-only parent transition contract

## Status

Accepted as the parallel parent transition contract before an explicit cutover.

## Prepare completion

Registration, launch commitment, runtime binding, gate binding, create, and start
remain a separately completed prefix. The observation-only Prepare completion
accepts only `launch_committed` or an idempotent `prepared_gated` retry.

It requires the exact bound runtime and gate, the complete launch ID/digest
engine observation, and direct engine `running`. It then records only Ready bytes
observed through LQ-636. Absent Ready returns neutral `None` and cannot advance
the journal. Only a persisted exact Ready permits `prepared_gated`.

## Release

The parent resolves exact persistent bindings and direct Ready, commits one
stable Release ID, and publishes only its Release-token document. It persists
that publication idempotently.

The parent then reads and persists direct child Consumed through LQ-636. Absent
Consumed returns neutral `None`. Only exact Consumed plus direct engine `running`
permits the journal's Running observation.

The service never calls `await_release`, `publish_consumed`, a Writer/Recovery
executor, or Terminal publication.

## Retry and conflict

Committed Release retries reuse the same token ID and Release ID. Existing token
facts must match exactly. Divergence is a closed service conflict and never a
second token or execution. Technical failure remains detail-free.

## Scope

No existing service is replaced and no composition selects this path. There is
no schema, migration, port, settings, entrypoint, Compose, or deployment change.
LQ-640 implements the parallel services.
