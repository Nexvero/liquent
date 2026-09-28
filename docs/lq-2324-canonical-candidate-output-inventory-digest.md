# LQ-2324 Canonical candidate output inventory digest

- The inventory binds each expected file name to its current SHA-256 digest and
  byte size.
- Facts are ordered by file name and serialized with the existing canonical JSON
  representation before hashing.
- Directory enumeration order therefore cannot change the inventory identity.
- A digest mismatch is rejected instead of being repaired or normalized.
- The digest identifies this local three-file output only; it is not a signature.
