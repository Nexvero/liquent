# LQ-2551 Immutable intermediate-expectation contract

- One verifier invocation uses one fixed snapshot of expected names and identities.
- Later mutation of the supplied mapping cannot alter that running decision.
- The snapshot is created before workspace opening or filesystem observation.
- Every topology and child comparison reads only the local snapshot.
- No successful check writes filesystem facts back into expected state.
- Snapshot isolation grants no release, publication, or deployment authority.
