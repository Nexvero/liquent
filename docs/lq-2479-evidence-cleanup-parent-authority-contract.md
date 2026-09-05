# LQ-2479 Evidence-cleanup parent-authority contract

- Writer cleanup authority depends on both created file and workspace identities.
- A matching child inode alone cannot authorize unlink from a changed parent state.
- The held workspace descriptor must remain private and current-user-owned.
- Device and inode must equal the identity measured before exclusive creation.
- Parent identity or metadata drift preserves the current evidence entry.
- This narrow authority grants no recursive or unrelated deletion capability.
