# LQ-645 — Observation-only Prepare candidate graph

## Status

Implemented as an inert dependency composition, not application wiring.

## Graph

`CandidateObservationOnlyManifestHandoffSupervisorPrepareService` exposes the
existing profile-specific Prepare methods. Each method invokes exactly two
components in order:

1. the LQ-644 persistent launch prefix;
2. the LQ-640 direct Ready completion.

Neutral prefix absence and service conflict are returned directly. Any other
unexpected prefix shape is technical unavailability. Ready completion is never
called after either condition.

The candidate has no fallback to the old Prepare service and no access to
Release, Consumed, capability execution, Terminal, settings, or process
configuration.

## Evidence

Static executable evidence verifies preserved mutation ordering, complete launch
anchors, running before prefix result, prefix before Ready completion, and the
absence of child-owned effects. Existing direct observer and compatibility
regressions remain green.

LQ-646 closes the extraction and candidate-composition strand.
