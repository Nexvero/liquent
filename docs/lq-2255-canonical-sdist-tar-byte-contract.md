# LQ-2255 canonical sdist TAR byte contract

- Accepted TAR semantics have exactly one canonical byte representation.
- Member order, headers, payload blocks, end markers, and padding are bound.
- Reader tolerance does not enlarge the accepted release-artifact language.
- Equivalent alternate number or checksum encodings are rejected.
- PAX is emitted only when the canonical writer requires it.
- The requested epoch remains the sole time input.
- This contract grants no build, signing, or publication authority.
