# LQ-1435 Joint engine API expected source identity contract

- Operation-bound verification carries the resolved source-root identity.
- The identity contains exactly nonnegative device and inode facts.
- The source loader compares it with the descriptor it actually opens.
- Mismatch fails before source content becomes verification evidence.
- Identity is an internally resolved fact, never caller authority.
- Malformed identities fail closed and expose no technical detail.
- Standalone loading remains available without an expected identity.
