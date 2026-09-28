# LQ-1569 Joint engine API operation state invariants

- Root and child state must identify directories.
- Effective process ownership is mandatory.
- Exact owner-private mode 0700 is required.
- State device and inode must match bound identity.
- Malformed or foreign state invalidates the topology.
- Authentic descriptor state remains accepted.
- Failure reveals no metadata.
