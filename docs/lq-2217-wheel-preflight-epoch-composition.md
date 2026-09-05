# LQ-2217 Wheel preflight epoch composition

- WheelGate reads the epoch established by SourceGate.
- The shared wheel verifier receives that epoch explicitly.
- SdistGate passes the same epoch for its rebuilt wheel.
- Missing or malformed run-context epoch fails before acceptance.
- Direct and rebuilt wheel hashes remain independently compared.
- sdist normalization continues to use the same source fact.
- No caller-controlled timestamp assertion enters artifact metadata.
