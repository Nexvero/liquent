# LQ-2301 terminal candidate-identity gate

- Candidate identity is derived only after bundle verification succeeds.
- Current verification bytes must still match their captured digest.
- Pair and verification identities must retain strict SHA-256 syntax.
- Bundle bytes are read and hashed at terminal identity derivation.
- Successful Bundle facts expose bundle, report, and candidate digests.
- The resulting state explicitly remains non-promotable.
- Failure is detail-limited and performs no publication action.
