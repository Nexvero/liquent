# LQ-2361 Shared private-directory identity foundation

- Atomic writes, bundle sealing, identity input reads, descriptor checks, evidence
  checks, and terminal inventory checks use the descriptor-measured identity.
- Each later operation must reopen without following links and match device/inode.
- This makes one private directory fact the common local candidate boundary.
- A replaced or redirected directory fails a later equality check.
- No filesystem identity is treated as remote publication authority.
