# LQ-1339 Joint engine API operation root path contract

- The operation root requires a real no-follow component chain.
- Parent and leaf symlinks cannot identify the operation boundary.
- The visible root must retain its opened device and inode after resolution.
- Missing, replaced, or rebound root paths fail closed.
- Root trust comes from filesystem facts rather than caller assertions.
- Existing owner-private mode and exact-child requirements remain additive.
- Failure exposes neither paths nor underlying operating-system detail.
