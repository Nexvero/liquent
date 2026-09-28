# LQ-1367 Joint engine API single operation wrapper contract

- Accept and audit flows must use one common boundary wrapper.
- No mode may independently omit or reorder final validation.
- Resolution occurs exactly once before the internal operation.
- Revalidation occurs exactly once after the internal operation.
- Internal operations receive only resolved source and acceptance paths.
- The wrapper does not reinterpret verification or registry outcomes.
- Public command modes and arguments remain unchanged.
