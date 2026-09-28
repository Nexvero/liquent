# LQ-2299 local release-candidate identity contract

- One local candidate binds bundle, distribution pair, and verification report.
- Source commit and package version remain explicit candidate facts.
- The sdist participates through the source-bound distribution-pair digest.
- Byte-equal bundle content with another pair is a different candidate.
- Byte-equal artifacts with another report are a different candidate.
- Candidate identity is local evidence, never promotion authorization.
- Signing, registration, and publication remain separate boundaries.
