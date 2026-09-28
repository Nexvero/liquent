# LQ-2263 canonical wheel compressed-byte contract

- An accepted wheel has one canonical complete ZIP byte representation.
- Equal names, metadata, payloads, and RECORD facts alone are insufficient.
- Alternate valid Deflate streams are rejected fail closed.
- Member order remains the order emitted by the controlled wheel build.
- Central-directory and local-header bytes are jointly bound.
- The locked local runtime supplies the canonical compression behavior.
- This contract grants no installation, signing, or publication authority.
