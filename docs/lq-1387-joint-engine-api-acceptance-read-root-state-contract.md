# LQ-1387 Joint engine API acceptance read root state contract

- Read-only registry operations bind complete root metadata.
- Initial, held-final, and visible-final root facts must all agree.
- Device, inode, mode, owner, group, link, size, and timestamps are bound.
- Marker load and registry inspection share the same state policy.
- A transient mutation followed by restoration fails closed.
- State is observed from owned descriptors, never caller assertions.
- Durable record uses its separate expected-mutation policy.
