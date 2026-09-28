# LQ-2317 cross-candidate bundle-identity gate

- The Bundle gate captures the sealed bundle SHA-256 before verification.
- Bundle schema and payload verification then run independently.
- A second sealing pass must return the same complete-file digest.
- Candidate identity must contain that same sealed bundle digest.
- Mutation between build, verification, and descriptor creation fails closed.
- Successful run state retains the sealed digest privately.
- No repair, signing, promotion, or publication action is performed.
