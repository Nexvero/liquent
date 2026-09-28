# LQ-1388 Complete joint engine API acceptance read root validation

- Read operations retain initial root metadata before marker access.
- Final validation observes the held working descriptor again.
- A complete no-follow traversal observes the visible root separately.
- Every stable field must match across all three observations.
- Owner-private and non-inheritable checks remain independently enforced.
- Final validation descriptor closure remains locally owned.
- Existing public load and inspection signatures remain unchanged.
