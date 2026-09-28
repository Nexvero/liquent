# LQ-1411 Joint engine API acceptance pre-create root contract

- The visible registry root is revalidated immediately before creation.
- Held and visible root identities must still agree at that boundary.
- Parent disappearance, replacement, or symlink rebinding fails closed.
- Failure precedes marker pathname open, allocation, or write.
- The gate is read-only and does not mutate an empty registry.
- Callers cannot skip the gate or supply a replacement root identity.
- Existing final post-write root validation remains independently required.
