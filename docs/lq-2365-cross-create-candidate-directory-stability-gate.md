# LQ-2365 Cross-create candidate-directory stability gate

- Workspace device and inode must remain stable across child creation and directory
  synchronization.
- Resolved workspace and child identities are rechecked before handoff.
- If creation succeeded but a later creation check fails, the empty child is removed
  relative to the same workspace descriptor.
- Replacement, redirection, sync failure, or cleanup failure cannot yield success.
- No retry silently reuses an uncertain directory.
