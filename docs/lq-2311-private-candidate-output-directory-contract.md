# LQ-2311 private candidate-output directory contract

- Candidate output resides in one real non-symlink directory.
- The directory must be owned by the current local process user.
- Its exact permission mode is owner-only `0700`.
- Device and inode jointly identify the resolved directory object.
- A matching pathname alone is not sufficient identity.
- Directory validity grants no signing or publication authority.
- Cross-host storage and external handoff remain separate boundaries.
