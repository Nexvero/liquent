# LQ-1552 Closed marker observations in accept and audit

- Descriptor read and record construct the closed value directly.
- One-shot compares closed recorded and final observations.
- Accepted audit compares two closed read observations.
- Every construction rechecks marker semantics.
- Source and operation-root checks remain unchanged.
- Existing command surfaces do not expand.
- Failure continues using the unavailable result.
