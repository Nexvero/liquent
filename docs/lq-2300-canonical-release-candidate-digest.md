# LQ-2300 canonical release-candidate digest

- Candidate facts contain bundle name and complete bundle SHA-256.
- They contain distribution-pair and verification SHA-256 identities.
- Bound source commit and package version are included explicitly.
- Existing canonical JSON serialization orders every candidate fact.
- SHA-256 of those bytes is the local release-candidate identity.
- Every component must have passed its own independent validation first.
- No candidate record or external attestation is persisted here.
