# LQ-2373 Cross-read controlled-evidence stability gate

- Evidence device, inode, size, and modification time must remain stable across the
  bounded descriptor read.
- Workspace device and inode must remain stable for the same operation.
- Byte, mode, ownership, link, size, identity, or topology drift fails closed before
  the workspace can cross its commit boundary.
- No retry normalizes changing evidence.
- Successful readback grants no publication or deployment authority.
