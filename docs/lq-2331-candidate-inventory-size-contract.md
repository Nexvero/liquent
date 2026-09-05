# LQ-2331 Candidate inventory size contract

- Every expected candidate digest has one corresponding expected byte size.
- Digest and size mappings must describe exactly the same three file names.
- Sizes are positive integers, exclude booleans, and cannot exceed the existing
  local release-bundle resource ceiling.
- Missing, additional, malformed, or oversized size claims are rejected.
- A size claim is measured evidence, not caller-granted authority.
