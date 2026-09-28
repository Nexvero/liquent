# LQ-1307 Joint engine API source root replacement contract

- Replacing the visible root during capture invalidates the operation.
- Identical names, bytes, modes, and ownership do not preserve identity.
- A new directory inode cannot inherit trust from the opened root.
- A symlink to the original directory is also a different visible object.
- Rebinding is rejected even when child snapshots were already stable.
- No replacement race can produce a successful public snapshot.
- The rule is independent of provenance content correctness.
