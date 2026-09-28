# LQ-1561 Joint engine API operation identity evidence

- Tests cover each possible pairwise identity collision.
- Every collision fails during immutable value construction.
- Authentic operation resolution yields three distinct identities.
- Existing replacement detection remains green.
- Source and acceptance binding tests remain unaffected.
- No filesystem identity is exposed in failures.
- Strict warning treatment guards regressions.
