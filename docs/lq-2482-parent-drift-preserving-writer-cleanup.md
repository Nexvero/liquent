# LQ-2482 Parent-drift-preserving writer cleanup

- A write failure may coincide with a late workspace permission change.
- Even when the created file inode still matches, parent mode drift prevents unlink.
- The current evidence entry is preserved for owner-controlled inspection or cleanup.
- The writer still returns one detail-limited controlled-preflight rejection.
- No chmod repair, forced removal, recursive deletion, or ownership inference occurs.
- Temporary-directory lifecycle remains responsible outside this narrow helper.
