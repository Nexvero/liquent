# LQ-2389 Terminal workspace-root inventory gate

- Root inventory is checked after controlled evidence readback and before the commit
  boundary.
- Enumeration occurs twice through the same no-follow workspace descriptor.
- Workspace device and inode must remain equal to the run-bound identity.
- Entry-set, type, ownership, mode, link, or evidence-size drift fails closed.
- No later rename can legitimize an invalid private workspace.
