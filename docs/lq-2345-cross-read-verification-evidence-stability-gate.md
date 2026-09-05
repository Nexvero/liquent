# LQ-2345 Cross-read verification-evidence stability gate

- Device, inode, size, and modification time must remain stable while evidence is
  read from its open descriptor.
- Observed bytes must equal the canonical expected payload and its bound digest.
- The open parent identity and the resolved parent identity after close must remain
  the same as the bundle gate's original identity.
- Drift is rejected without retry, repair, or normalization.
- Validation remains local and non-promotable.
