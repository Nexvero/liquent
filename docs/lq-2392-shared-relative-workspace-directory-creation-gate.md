# LQ-2392 Shared relative workspace-directory creation gate

- All four allowed workspace children use one creation implementation.
- The workspace is opened directory-only without following links and bound by
  device and inode.
- Each child is created exclusively with mode 0700 relative to that descriptor.
- Child identity is independently measured and the workspace directory synchronized.
- Existing children are rejected rather than reused.
