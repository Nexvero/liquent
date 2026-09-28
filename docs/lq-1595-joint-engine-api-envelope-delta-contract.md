# LQ-1595 Joint engine API envelope delta contract

- Added acceptance digest must bind the observed run envelope.
- Matching run ID with another digest is insufficient.
- Canonical digest syntax does not establish envelope identity.
- Source-derived build supplies the expected digest.
- One-shot cryptographic verification remains independently required.
- No digest normalization or caller override occurs.
- Mismatch fails detail-free.
