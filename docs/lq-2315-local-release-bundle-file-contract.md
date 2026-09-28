# LQ-2315 local release-bundle file contract

- The local bundle is one regular non-symlink filesystem object.
- It is owned by the current local process user.
- Exactly one directory entry may link to its inode.
- Its sealed permission mode is owner-read/write only, `0600`.
- Bundle size is positive and at most 64 MiB.
- Complete-file SHA-256 remains its byte identity.
- These facts grant no signing, promotion, or publication authority.
