# LQ-1556 Closed joint engine API operation roots

- Immutable construction validates paths and identities together.
- Root, relative, and parent-traversing paths are rejected.
- Exact source-set and accepted-runs names are required.
- Parent equality prevents cross-operation child composition.
- Identity uniqueness prevents root-child aliasing.
- Redacted representation remains unchanged.
- No serialized form is introduced.
