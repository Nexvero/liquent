# LQ-2174 Safe reproducible sdist evidence

- Tests reject traversal, aliases, duplicates, and multiple roots.
- Rejected archives remain byte-identical to their original input.
- Failure leaves no normalization temporary file behind.
- Accepted archives retain deterministic byte identity.
- Existing structure and payload checks remain composed.
- No signing, upload, container, or deployment authority is added.
- Production readiness still depends on external release evidence.
