# LQ-2265 wheel compressed-byte reconstruction gate

- The verifier retains each bounded member payload after integrity reading.
- It reconstructs the complete wheel through the canonical renderer.
- Acceptance requires equality with every original archive byte.
- Deflate choices and ZIP structural spelling are therefore observable facts.
- A mismatch yields one detail-limited wheel verification failure.
- Verification leaves the candidate and source tree unchanged.
- Existing identity, metadata, member-set, and RECORD gates still run.
