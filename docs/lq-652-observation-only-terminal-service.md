# LQ-652 — Observation-only Terminal service

## Status

Implemented for Writer and Recovery and integrated into the inert candidate.

## Artifact bridge

The direct wrapper observer now exposes `observe_terminal`; the recorder exposes
`record_terminal`. Typed observation and record values ensure the decoded
document, publication facts, persistent role record, handle, artifact ID, and
terminal correlation remain identical.

## Parent service

`ObservationOnlyManifestHandoffSupervisorTerminalService` accepts only the
existing inspect command. It resolves current journal, runtime, and gate; records
the direct Terminal; validates the profile-specific outcome; and inspects the
same bound engine container.

It returns neutral absence while Terminal is missing or the engine is still
running. Only direct engine `exited`/`dead` invokes the existing Writer or
Recovery terminal journal transition. The persisted result must equal the
decoded child outcome.

The service has no `publish_terminal`, capability executor, capability outcome
port, engine wait, Release wait, or inferred outcome path. LQ-653 supplies
ordering and surface evidence.
