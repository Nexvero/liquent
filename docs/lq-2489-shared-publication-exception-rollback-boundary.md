# LQ-2489 Shared publication-exception rollback boundary

- Controlled rejection and operating-system failure share one rollback contract.
- Both pass parent identity, fixed names, and workspace identity unchanged.
- Rollback occurs only after the forward rename flag is set.
- Neither branch suppresses or replaces the original detail-limited rejection.
- No second parent descriptor, alternate output, or recursive cleanup is introduced.
- The surrounding temporary-directory lifecycle handles a restored workspace normally.
