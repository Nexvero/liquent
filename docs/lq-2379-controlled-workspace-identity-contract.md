# LQ-2379 Controlled workspace-identity contract

- The orchestration workspace is opened with directory-only and no-follow semantics
  after it is forced to mode 0700.
- It must remain a current-user-owned private directory.
- Device and inode establish one identity for the complete ten-phase run.
- A path, symlink, mode, owner, type, or identity change fails closed.
- Workspace identity grants no publishing or deployment authority.
