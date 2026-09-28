# LQ-1533 Joint engine API source root state invariants

- Root mode must represent a directory with exact mode 0700.
- Root owner must equal the current effective process owner.
- Device, inode, and remaining state fields stay nonnegative.
- Regular-file or permissive-directory state is rejected.
- Foreign-owner state is rejected.
- Authentic descriptor-derived root state remains accepted.
- Failure reveals no root metadata.
