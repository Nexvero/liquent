# LQ-2344 No-follow verification-evidence read gate

- `verification.json` is opened without symbolic-link traversal.
- The opened object must be a mode-0600 regular file owned by the current user,
  have exactly one link, and match the expected bounded size.
- Reading, byte comparison, and SHA-256 verification use the same descriptor.
- Path-based replacement cannot become trusted evidence during validation.
- Failures remain detail-free at the existing local gate boundary.
