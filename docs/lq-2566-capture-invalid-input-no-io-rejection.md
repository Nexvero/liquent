# LQ-2566 Capture invalid-input no-I/O rejection

- Invalid workspace identity and output name share one preopen decision point.
- Evidence replaces workspace opening with an unreachable test boundary.
- Every malformed or unsupported input rejects before that boundary.
- No listing, stat, child open, callback, or descriptor cleanup occurs.
- Failure exposes no supplied value or operating-system detail.
- No retry, fallback, or name discovery is introduced.
