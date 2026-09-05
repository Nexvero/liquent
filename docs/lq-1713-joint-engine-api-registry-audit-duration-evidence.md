# LQ-1713 Joint engine API registry audit duration evidence

- Tests provide deterministic outer monotonic values.
- A 29-second registry audit succeeds.
- Duration above 30 seconds fails.
- Evidence rechecks complete before final time capture.
- Root validation still follows the timing gate.
- Empty registry remains supported.
- Evidence is local and deterministic.
