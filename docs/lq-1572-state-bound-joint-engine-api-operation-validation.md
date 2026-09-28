# LQ-1572 State-bound joint engine API operation validation

- Final validator resolves all paths, identities, and states again.
- Immutable equality checks unchanged topology.
- Transient chmod followed by restoration changes state evidence.
- Generic and audit wrappers reject that mutation.
- Root replacement checks remain independently active.
- Failure stays detail-free.
- Existing callers retain default strict validation.
