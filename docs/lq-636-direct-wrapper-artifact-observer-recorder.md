# LQ-636 — Direct wrapper artifact observer and recorder

## Status

Implemented as two narrowly separated application components.

## Read-only observer

`ReadOnlyManifestHandoffSupervisorWrapperArtifactObserver` exposes only
`observe_ready` and `observe_consumed`. It reads through the existing reader,
decodes through the existing canonical codec, validates every binding, and
returns an existing typed publication carrying the actual encoded facts.

It has no publisher, engine, journal, executor, authority, path, or clock
dependency. Absence returns `None`; every malformed or divergent document fails
detail-free.

## Persistent recorder

`PersistentManifestHandoffSupervisorWrapperArtifactRecorder` invokes the
observer first. Only an exact observed publication is translated into the
existing persistent Ready or Consumed record command. The recorded result is
then compared again with gate ID, handle, role, and correlation.

It preserves an existing runtime conflict and never writes when observation is
absent or invalid. It cannot publish a control file, execute a capability, alter
the engine, or advance a journal.

LQ-637 supplies executable direct-observation evidence.
