# LQ-2332 Pre-read candidate size gate

- The opened candidate file size must equal its expected size before hashing.
- This comparison occurs after no-follow open and regular-file metadata checks,
  but before the first content read.
- A replaced, expanded, truncated, or unexpectedly empty file fails closed.
- The gate does not consume an unbounded mismatching candidate before rejection.
- No retry or repair path is introduced.
