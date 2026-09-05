# LQ-2376 Preparse gate-receipt resource gate

- Receipt type and byte length are checked before `json.loads` executes.
- An invalid-size receipt is not decoded, normalized, truncated, or retried.
- This bounds parser input independently for every phase.
- Rejection uses the existing detail-limited controlled-preflight boundary.
- No gate can enlarge final evidence through an unbounded receipt payload.
