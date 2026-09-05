# LQ-1804 Bounded terminal joint engine API registry audit

- Registry audit uses initial, final, and terminal monotonic reads.
- Reads must be nondecreasing across the sequence.
- Terminal elapsed duration must not exceed policy.
- Accepted-source audit retains its existing three-read sequence.
- Both modes now include all terminal work in timing.
- No new clock implementation is introduced.
- Public status semantics remain stable.
