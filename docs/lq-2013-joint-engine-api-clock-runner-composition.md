# LQ-2013 Joint engine API clock runner composition

- Validated clock reads reuse the shared runner.
- Provider and validator execute within one boundary.
- Existing clock semantics remain unchanged.
- Existing read counts remain unchanged.
- Unavailable clock failures preserve identity.
- System exits continue to propagate.
- No duplicate normalization policy remains.
