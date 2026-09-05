# LQ-2353 Cross-seal bundle stability gate

- Bundle device, inode, size, and modification time must remain stable from the
  initial open metadata through synchronization and hashing.
- The sealed mode must be exactly 0600.
- The open parent directory must retain its bound identity before descriptors close,
  followed by the existing resolved-parent recheck.
- Replacement or mutation cannot produce a valid sealed digest.
- No retry accepts a changing bundle.
