# LQ-2188 Normalized sdist manifest verifier

- Input facts form an ordered in-memory manifest after bounded reading.
- Regular payload identity is represented by SHA-256.
- Directory identity includes name, type, mode, and declared size.
- The temporary archive is parsed through all existing safety gates.
- Its reconstructed manifest must equal the input manifest exactly.
- Missing, additional, reordered, or changed members fail closed.
- The verifier performs no extraction and no network operation.
