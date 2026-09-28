# LQ-2397 Terminal distribution-artifact inventory gate

- The bundle phase revalidates the distribution pair before checking its directory.
- Directory identity and exact entry names are checked before and after both reads.
- File device, inode, size, and modification time must remain stable while hashing.
- The canonical two-file inventory digest is emitted in terminal bundle-gate facts.
- Drift prevents candidate construction and controlled-preflight success.
