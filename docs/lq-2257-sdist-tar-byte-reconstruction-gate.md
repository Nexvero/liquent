# LQ-2257 sdist TAR byte-reconstruction gate

- The verifier parses bounded entries and retains every payload byte.
- It rebuilds the canonical TAR stream from those interpreted facts.
- Acceptance requires equality with the entire expanded candidate stream.
- Header spelling, checksum spelling, block padding, and PAX drift fail closed.
- Semantic equality alone is deliberately insufficient.
- Existing manifest and envelope checks remain independent defenses.
- Rejection stays detail-limited and leaves the candidate unchanged.
