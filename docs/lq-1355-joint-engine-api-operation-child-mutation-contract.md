# LQ-1355 Joint engine API operation child mutation contract

- Any fixed-child metadata mutation during resolution invalidates binding.
- Restoring private mode does not erase the changed ctime fact.
- Touching a child directory invalidates its timestamp continuity.
- A mutation of either child invalidates the entire operation root.
- No retry or fresh-baseline fallback follows detected mutation.
- The gate is independent of child contents and cryptographic validity.
- Rejection occurs before an immutable result is returned.
