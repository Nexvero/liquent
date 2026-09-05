# LQ-2207 Wheel RECORD integrity contract

- RECORD binds every wheel member by exact name, digest, and size.
- Its row order equals the canonical ZIP member order.
- Every non-RECORD payload uses SHA-256 and exact decimal byte length.
- RECORD has one self-row with empty digest and size fields.
- Missing, additional, duplicate, reordered, or malformed rows fail closed.
- Parsed RECORD data cannot broaden wheel identity or authority.
- The contract adds no installation or publication operation.
