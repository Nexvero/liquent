# LQ-2494 Immediate parent-workspace gate

- The common parent descriptor is measured again in the precommit sequence.
- Device and inode must equal the identity bound before temporary workspace creation.
- Mode must remain exactly 0700 and owner must remain the current user.
- Parent drift prevents source, destination, or rename acceptance.
- No alternate parent descriptor or path-based fallback is opened.
- The same descriptor remains authoritative through rename and synchronization.
