# LQ-2336 Candidate artifact-name binding contract

- Candidate facts bind the exact bundle file name and verification-evidence file
  name alongside their existing SHA-256 digests.
- A digest cannot be detached from its semantic file name in the descriptor.
- Names originate from the artifacts produced by the controlled local gate.
- No caller-selected alias or remote destination name is accepted.
- Packaging and publication naming remain outside this slice.
