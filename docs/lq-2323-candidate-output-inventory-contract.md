# LQ-2323 Candidate output inventory contract

- A local release candidate output contains exactly the sealed bundle,
  `verification.json`, and `release-candidate.json`.
- Every entry is a regular file; symbolic links and other filesystem object types
  are rejected without interpretation.
- Missing, additional, temporary, or stale entries make the candidate invalid.
- This slice adds no promotion, publication, signing, or remote-storage behavior.
- The candidate remains local and explicitly non-promotable.
