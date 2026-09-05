# LQ-644 — Persistent parent launch prefix

## Status

Implemented for Writer and Recovery with the existing command, journal, runtime,
gate, and engine boundaries.

## Implementation

`PersistentManifestHandoffSupervisorParentLaunchPrefix` preserves the established
restart-safe ordering: register, commit launch, resolve/create, bind runtime,
bind gate, inspect, conditionally start, inspect running.

Every resolved or created fact is compared with registration, handle, creation,
control directory, image, launch document ID, launch digest, profile, and runtime
container. Existing prepared retries cannot recreate a missing runtime or restart
a created container.

The immutable `LaunchedManifestHandoffSupervisorParentPrefix` validates journal
state, persistent bindings, engine identity, profile, and direct running state.
It carries no authority or mutation method.

The implementation contains no Ready, journal-gated, Release, Consumed,
capability, or Terminal operation. LQ-645 composes it with direct Ready
completion in an unselected candidate.
