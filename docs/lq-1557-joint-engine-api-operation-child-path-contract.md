# LQ-1557 Joint engine API operation child path contract

- Source path must end exactly in source-set.
- Acceptance path must end exactly in accepted-runs.
- Both paths must have one identical operation parent.
- Absolute paths cannot target the filesystem root.
- Parent traversal components are forbidden.
- Mismatch invalidates the complete topology.
- No path normalization supplies missing intent.
