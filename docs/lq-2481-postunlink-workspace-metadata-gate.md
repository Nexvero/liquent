# LQ-2481 Post-unlink workspace-metadata gate

- A matching writer-owned evidence entry is removed relative to the held descriptor.
- The workspace descriptor is synchronized immediately afterward.
- Device, inode, exact 0700 mode, and current owner are then measured again.
- Cleanup performs no second unlink or path fallback if terminal metadata differs.
- The descriptor closes through the writer's existing failure cleanup.
- Normal successful writer execution never enters this unlink-only gate.
