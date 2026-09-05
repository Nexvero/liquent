# LQ-2187 Normalized sdist output contract

- Temporary normalized output is untrusted until reread and verified.
- Output names, types, modes, sizes, and payload hashes match input facts.
- Output members appear in canonical name order.
- Every output member carries the fixed epoch and neutral ownership.
- Gzip metadata carries the same epoch and no optional header fields.
- Verification succeeds before atomic replacement of the source artifact.
- A serializer defect therefore fails closed without publication authority.
