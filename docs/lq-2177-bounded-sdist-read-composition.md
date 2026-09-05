# LQ-2177 Bounded sdist read composition

- Filesystem type and compressed size are checked before tar parsing.
- Member iteration stops as soon as the count bound is exceeded.
- Metadata bounds are checked before regular payloads are retained.
- Each extracted payload is compared with its declared size.
- Canonical topology validation remains mandatory.
- Deterministic rewrite runs only after every read check passes.
- The original archive remains unchanged on rejection.
