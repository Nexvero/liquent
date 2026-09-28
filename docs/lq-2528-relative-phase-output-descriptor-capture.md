# LQ-2528 Relative phase-output descriptor capture

- Capture opens only one of the four fixed phase-output names.
- The open is directory-only, read-only, relative, and no-follow.
- Missing, linked, inaccessible, and non-directory targets fail closed.
- Initial child metadata comes from the held descriptor, not its path.
- Device and inode are returned only after every capture check succeeds.
- Caller-selected names cannot enter the capture boundary.
